import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from LLM.llm_config_manager import LLMConfig, LLMConfigManager, _client_base_url
from api import create_app


class _FakeMessage:
    content = "你好，我已经可以回答问题。"


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    choices = [_FakeChoice()]


class _FakeCompletions:
    def create(self, **_kwargs):
        return _FakeResponse()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeClient:
    chat = _FakeChat()


class _BrokenClient:
    class chat:
        class completions:
            @staticmethod
            def create(**_kwargs):
                raise RuntimeError("not openai compatible")


class _StreamOnlyClient:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                if not kwargs.get("stream"):
                    raise RuntimeError("Stream must be set to true")
                return iter([
                    {"choices": [{"delta": {"content": "stream "}}]},
                    {"choices": [{"delta": {"content": "answer"}}]},
                ])


class _FakeAnthropicResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        return {"content": [{"type": "text", "text": "Anthropic fallback OK"}]}


class LlmEnvApiTests(unittest.TestCase):
    def test_anthropic_openai_compatible_base_url_adds_v1(self):
        self.assertEqual(
            _client_base_url("anthropic", "https://example.test/api"),
            "https://example.test/api/v1",
        )
        self.assertEqual(
            _client_base_url("anthropic", "https://example.test/api/v1"),
            "https://example.test/api/v1",
        )

    def test_anthropic_env_config_is_loaded_without_exposing_key(self):
        env = {
            "ANTHROPIC_BASE_URL": "https://example.test/api",
            "ANTHROPIC_AUTH_TOKEN": "secret-token",
            "ANTHROPIC_MODEL": "gpt-5.4",
        }
        with patch.dict(os.environ, env, clear=False):
            manager = LLMConfigManager(load_from_env=False)
            manager.load_env_configs(overwrite=True)
        cfg = manager.get_config("anthropic")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.base_url, "https://example.test/api")
        self.assertEqual(cfg.model, "gpt-5.4")
        listed = manager.list_configs()["anthropic"]
        self.assertTrue(listed["has_api_key"])
        self.assertNotIn("api_key", listed)
        self.assertEqual(manager.get_default_provider(), "anthropic")

    def test_ai_ask_endpoint_uses_configured_model(self):
        app = create_app()
        client = app.test_client()
        cfg = LLMConfig(
            provider="anthropic",
            api_key="secret-token",
            base_url="https://example.test/api",
            model="gpt-5.4",
        )
        with (
            patch("api.ai.config_manager.get_default_provider", return_value="anthropic"),
            patch("api.ai.config_manager.get_config", return_value=cfg),
            patch("api.ai.get_llm_client", return_value=_FakeClient()),
        ):
            r = client.post("/api/ai/ask", json={"question": "你好"})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("answer", data)
        self.assertNotIn("api_key", data)

    def test_ai_ask_endpoint_supports_stream_only_openai_gateway(self):
        app = create_app()
        client = app.test_client()
        cfg = LLMConfig(
            provider="anthropic",
            api_key="secret-token",
            base_url="https://example.test/api",
            model="gpt-5.4",
        )
        with (
            patch("api.ai.config_manager.get_default_provider", return_value="anthropic"),
            patch("api.ai.config_manager.get_config", return_value=cfg),
            patch("api.ai.get_llm_client", return_value=_StreamOnlyClient()),
        ):
            r = client.post("/api/ai/ask", json={"question": "你好"})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["protocol"], "openai-compatible-stream")
        self.assertEqual(data["answer"], "stream answer")

    def test_ai_ask_endpoint_falls_back_to_anthropic_messages(self):
        app = create_app()
        client = app.test_client()
        cfg = LLMConfig(
            provider="anthropic",
            api_key="secret-token",
            base_url="https://example.test/api",
            model="gpt-5.4",
        )
        with (
            patch("api.ai.config_manager.get_default_provider", return_value="anthropic"),
            patch("api.ai.config_manager.get_config", return_value=cfg),
            patch("api.ai.get_llm_client", return_value=_BrokenClient()),
            patch("api.ai.requests.post", return_value=_FakeAnthropicResponse()) as post,
        ):
            r = client.post("/api/ai/ask", json={"question": "你好"})

        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["protocol"], "anthropic-messages")
        self.assertEqual(data["answer"], "Anthropic fallback OK")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://example.test/api/v1/messages")
        self.assertEqual(kwargs["headers"]["x-api-key"], "secret-token")


if __name__ == "__main__":
    unittest.main()
