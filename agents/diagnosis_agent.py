from __future__ import annotations

from typing import Any


def summarize_diagnoses(diagnoses: list[dict[str, Any]]) -> list[str]:
    if not diagnoses:
        return ["未命中预设经营异常规则。"]
    return [
        f"{item.get('severity')}｜{item.get('rule_id')}｜{item.get('title')}｜可信度 {item.get('confidence')}"
        for item in diagnoses
    ]

