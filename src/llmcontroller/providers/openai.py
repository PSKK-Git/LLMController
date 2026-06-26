from openai import AsyncOpenAI

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse

# Native OpenAI models.
OPENAI_MODELS: set[str] = {"gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"}

# Models reachable via an OpenAI-compatible base_url (Mistral, proxies, etc.).
GATEWAY_MODELS: set[str] = {
    "mistral-small-latest",
    "mistral-large-latest",
    "claude-opus-4-7",
    "gemini-2.5-flash",
}

ALL_OPENAI_COMPATIBLE: set[str] = OPENAI_MODELS | GATEWAY_MODELS


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        resp = await self.client.chat.completions.create(
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens or 1024,
            temperature=request.temperature if request.temperature is not None else 0.7,
        )
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=request.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            stop_reason=choice.finish_reason or "stop",
        )

    async def list_models(self) -> list[str]:
        return sorted(ALL_OPENAI_COMPATIBLE)
