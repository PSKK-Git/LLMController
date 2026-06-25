from openai import AsyncOpenAI

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse

OPENAI_MODELS: set[str] = {"gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"}


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

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
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            stop_reason=choice.finish_reason or "stop",
        )

    async def list_models(self) -> list[str]:
        return sorted(OPENAI_MODELS)
