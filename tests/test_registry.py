import pytest

from llmcontroller.providers.claude import ClaudeProvider
from llmcontroller.providers.factory import get_provider, provider_name_for_model
from llmcontroller.providers.openai import OpenAIProvider
from llmcontroller.providers.registry import provider_for_model


def test_mistral_routes_to_mistral_endpoint(monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.mistral_api_key", "m-key")
    cfg = provider_for_model("mistral-small-latest")
    assert cfg.name == "mistral"
    assert cfg.type == "openai"
    assert cfg.base_url == "https://api.mistral.ai/v1"
    assert cfg.api_key == "m-key"


def test_each_family_routes_to_its_own_provider():
    assert provider_name_for_model("claude-3-sonnet") == "anthropic"
    assert provider_name_for_model("gpt-4o") == "openai"
    assert provider_name_for_model("mistral-large-latest") == "mistral"


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        provider_name_for_model("no-such-model")


def test_factory_builds_correct_adapter(monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "a")
    monkeypatch.setattr("llmcontroller.config.settings.mistral_api_key", "m")
    assert isinstance(get_provider("claude-3-sonnet"), ClaudeProvider)
    mistral = get_provider("mistral-small-latest")
    assert isinstance(mistral, OpenAIProvider)
