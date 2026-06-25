from llmcontroller.config import settings
from llmcontroller.providers.base import LLMProvider
from llmcontroller.providers.claude import MODEL_ALIASES, ClaudeProvider

PROVIDER_FOR_MODEL: dict[str, str] = {model: "anthropic" for model in MODEL_ALIASES}


def provider_name_for_model(model: str) -> str:
    if model not in PROVIDER_FOR_MODEL:
        raise ValueError(f"Unknown model: {model}")
    return PROVIDER_FOR_MODEL[model]


def get_provider(model: str) -> LLMProvider:
    name = provider_name_for_model(model)
    if name == "anthropic":
        return ClaudeProvider(api_key=settings.anthropic_api_key)
    raise ValueError(f"Unsupported provider: {name}")
