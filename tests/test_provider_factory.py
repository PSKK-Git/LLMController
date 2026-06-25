import pytest

from llmcontroller.providers.claude import ClaudeProvider
from llmcontroller.providers.factory import get_provider, provider_name_for_model


def test_provider_name_for_known_model():
    assert provider_name_for_model("claude-3-sonnet") == "anthropic"


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        provider_name_for_model("gpt-4")


def test_get_provider_returns_claude(monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "test")
    provider = get_provider("claude-3-sonnet")
    assert isinstance(provider, ClaudeProvider)
