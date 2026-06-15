from types import SimpleNamespace

import langchain_openai
import pytest

from yuxi.agents.models import load_chat_model
from yuxi.models.providers.cache import model_cache


@pytest.mark.parametrize(
    ("provider_id", "expected_disable_streaming"),
    [
        ("siliconflow-cn", "tool_calling"),
        ("siliconflow", "tool_calling"),
        ("openai-compatible", None),
    ],
)
def test_openai_compatible_tool_streaming_policy(
    monkeypatch: pytest.MonkeyPatch,
    provider_id: str,
    expected_disable_streaming: str | None,
):
    captured = {}
    info = SimpleNamespace(
        provider_id=provider_id,
        provider_type="openai",
        model_id="test-model",
        model_type="chat",
        api_key="test-key",
        base_url="https://example.test/v1",
    )

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(model_cache, "get_model_info", lambda _spec: info)
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChatOpenAI)

    load_chat_model(f"{provider_id}:test-model")

    assert captured.get("disable_streaming") == expected_disable_streaming
