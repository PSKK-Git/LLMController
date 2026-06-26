from dataclasses import dataclass

from llmcontroller.config import settings


@dataclass(frozen=True)
class ProviderConfig:
    name: str            # routing/audit name, e.g. "mistral"
    type: str            # adapter type: "anthropic" | "openai"
    api_key: str
    base_url: str | None = None


def providers() -> dict[str, ProviderConfig]:
    """Built fresh each call so monkeypatched/env settings are honored."""
    return {
        "anthropic": ProviderConfig("anthropic", "anthropic", settings.anthropic_api_key),
        "openai": ProviderConfig("openai", "openai", settings.openai_api_key, settings.openai_base_url),
        "mistral": ProviderConfig("mistral", "openai", settings.mistral_api_key, settings.mistral_base_url),
        "proxy": ProviderConfig("proxy", "openai", settings.proxy_api_key, settings.proxy_base_url or None),
    }


# Each supported model -> the provider that serves it.
MODEL_TO_PROVIDER: dict[str, str] = {
    "claude-3-sonnet": "anthropic",
    "claude-3-opus": "anthropic",
    "claude-3-haiku": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-3.5-turbo": "openai",
    "mistral-small-latest": "mistral",
    "mistral-large-latest": "mistral",
    "gemini-2.5-flash": "proxy",
    "claude-opus-4-7": "proxy",
}


def provider_for_model(model: str) -> ProviderConfig:
    if model not in MODEL_TO_PROVIDER:
        raise ValueError(f"Unknown model: {model}")
    return providers()[MODEL_TO_PROVIDER[model]]


def known_models() -> list[str]:
    return sorted(MODEL_TO_PROVIDER)
