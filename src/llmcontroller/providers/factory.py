from llmcontroller.providers.base import LLMProvider
from llmcontroller.providers.claude import ClaudeProvider
from llmcontroller.providers.openai import OpenAIProvider
from llmcontroller.providers.registry import MODEL_TO_PROVIDER, provider_for_model


def provider_name_for_model(model: str) -> str:
    if model not in MODEL_TO_PROVIDER:
        raise ValueError(f"Unknown model: {model}")
    return MODEL_TO_PROVIDER[model]


def get_provider(model: str) -> LLMProvider:
    cfg = provider_for_model(model)
    if cfg.type == "anthropic":
        return ClaudeProvider(api_key=cfg.api_key)
    if cfg.type == "openai":
        return OpenAIProvider(api_key=cfg.api_key, base_url=cfg.base_url)
    raise ValueError(f"Unsupported provider type: {cfg.type}")
