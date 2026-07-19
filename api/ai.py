"""Lightweight LLM Q&A API.

This endpoint is intentionally separate from the full BusinessAgent SSE route.
It gives local deployments a simple JSON way to verify that a configured model
can answer normal questions before using the heavier data-analysis workflow.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
import requests

from .state import config_manager
from LLM.llm_config_manager import LLMConfig, get_llm_client


bp = Blueprint("ai", __name__)


def _message_text(message: Any) -> str:
    return str(message or "").strip()


def _safe_error_text(text: Any, secret: str | None = None) -> str:
    msg = str(text or "")
    if secret:
        msg = msg.replace(secret, "[redacted]")
    return msg[:800]


def _coerce_temperature(value: Any) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        temperature = 0.2
    return max(0.0, min(temperature, 2.0))


def _openai_stream_text(stream: Any) -> str:
    parts: list[str] = []
    for chunk in stream:
        choices = getattr(chunk, "choices", None)
        if not choices and isinstance(chunk, dict):
            choices = chunk.get("choices")
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if delta is None and isinstance(choice, dict):
            delta = choice.get("delta")
        content = getattr(delta, "content", None)
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        if content:
            parts.append(str(content))
    return "".join(parts).strip()


def _call_openai_compatible(
    provider: str,
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
) -> tuple[str, str]:
    client = get_llm_client(provider)
    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        answer = response.choices[0].message.content if response.choices else ""
        return answer or "", "openai-compatible"
    except Exception as exc:
        if "stream must be set to true" not in str(exc).lower():
            raise
        stream = client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        return _openai_stream_text(stream), "openai-compatible-stream"


def _anthropic_endpoint_candidates(base_url: str | None) -> list[str]:
    base = (base_url or "https://api.anthropic.com").rstrip("/")
    if base.endswith("/messages"):
        candidates = [base]
    elif base.endswith("/v1"):
        candidates = [f"{base}/messages"]
    else:
        candidates = [f"{base}/v1/messages", f"{base}/messages"]

    seen: set[str] = set()
    return [url for url in candidates if not (url in seen or seen.add(url))]


def _anthropic_messages_payload(
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    system_parts: list[str] = []
    conversation: list[dict[str, str]] = []

    for message in messages:
        role = message.get("role")
        content = _message_text(message.get("content"))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        if role not in {"user", "assistant"}:
            continue
        if conversation and conversation[-1]["role"] == role:
            conversation[-1]["content"] += "\n\n" + content
        else:
            conversation.append({"role": role, "content": content})

    payload: dict[str, Any] = {
        "model": cfg.model,
        "messages": conversation,
        "max_tokens": max_tokens,
        "temperature": min(temperature, 1.0),
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    return payload


def _call_anthropic_messages(
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
) -> tuple[str, str]:
    payload = _anthropic_messages_payload(
        cfg,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    headers = {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": cfg.api_key,
        "authorization": f"Bearer {cfg.api_key}",
    }

    last_error = ""
    for endpoint in _anthropic_endpoint_candidates(cfg.base_url):
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=(10, 60),
            )
        except requests.RequestException as exc:
            last_error = _safe_error_text(exc, cfg.api_key)
            continue

        if response.ok:
            data = response.json()
            parts: list[str] = []
            for item in data.get("content", []):
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(parts).strip(), "anthropic-messages"

        last_error = f"{response.status_code} {response.text[:500]}"
        if response.status_code not in {404, 405}:
            break

    raise RuntimeError(_safe_error_text(last_error or "Anthropic request failed", cfg.api_key))


def _call_model(
    provider: str,
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    protocol: str = "",
) -> tuple[str, str]:
    if provider == "anthropic" and protocol.lower() == "anthropic":
        return _call_anthropic_messages(
            cfg,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    try:
        return _call_openai_compatible(
            provider,
            cfg,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as openai_exc:
        if provider != "anthropic":
            raise
        try:
            return _call_anthropic_messages(
                cfg,
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as anthropic_exc:
            openai_error = _safe_error_text(openai_exc, cfg.api_key)
            anthropic_error = _safe_error_text(anthropic_exc, cfg.api_key)
            raise RuntimeError(
                "OpenAI-compatible call failed: "
                f"{openai_error}; Anthropic Messages call failed: {anthropic_error}"
            ) from anthropic_exc


@bp.post("/api/ai/ask")
def ask_ai():
    body = request.get_json(silent=True) or {}
    question = _message_text(body.get("question") or body.get("message"))
    if not question:
        return jsonify({"error": "question 不能为空"}), 400

    provider = _message_text(body.get("provider")) or config_manager.get_default_provider()
    if not provider:
        return jsonify({"error": "未配置任何 LLM 模型"}), 400

    cfg = config_manager.get_config(provider)
    if cfg is None or not cfg.api_key:
        return jsonify({"error": f"模型未配置或缺少 API Key: {provider}"}), 400

    system = _message_text(body.get("system")) or "你是一个可靠的中文数据分析助手。"
    history = body.get("history") if isinstance(body.get("history"), list) else []
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in history[-10:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = _message_text(item.get("content"))
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    max_tokens = body.get("max_tokens")
    try:
        max_tokens = int(max_tokens) if max_tokens not in (None, "") else 2048
    except (TypeError, ValueError):
        max_tokens = 2048
    max_tokens = max(1, min(max_tokens, 8192))

    temperature = _coerce_temperature(body.get("temperature", 0.2))

    try:
        answer, protocol = _call_model(
            provider,
            cfg,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            protocol=_message_text(body.get("protocol")),
        )
        return jsonify({
            "ok": True,
            "provider": provider,
            "model": cfg.model,
            "protocol": protocol,
            "answer": answer or "",
        })
    except Exception as exc:
        return jsonify({
            "error": f"LLM 调用失败: {_safe_error_text(exc, cfg.api_key)}",
            "provider": provider,
            "model": cfg.model,
        }), 502
