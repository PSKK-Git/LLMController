from llmcontroller.config import settings
from llmcontroller.providers.base import LLMProvider
from llmcontroller.providers.claude import MODEL_ALIASES, ClaudeProvider
from llmcontroller.providers.openai import ALL_OPENAI_COMPATIBLE, OpenAIProvider

PROVIDER_FOR_MODEL: dict[str, str] = {model: "anthropic" for model in MODEL_ALIASES}
PROVIDER_FOR_MODEL.update({model: "openai" for model in ALL_OPENAI_COMPATIBLE})


def provider_name_for_model(model: str) -> str:
    if model not in PROVIDER_FOR_MODEL:
        raise ValueError(f"Unknown model: {model}")
    return PROVIDER_FOR_MODEL[model]


def get_provider(model: str) -> LLMProvider:
    name = provider_name_for_model(model)
    if name == "anthropic":
        return ClaudeProvider(api_key=settings.anthropic_api_key)
    if name == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
    raise ValueError(f"Unsupported provider: {name}")
