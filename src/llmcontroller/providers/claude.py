from anthropic import AsyncAnthropic

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse

# Friendly model name -> Anthropic API model ID. Verify against current docs.
MODEL_ALIASES: dict[str, str] = {
    "claude-3-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
}


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        api_model = MODEL_ALIASES.get(request.model, request.model)
        message = await self.client.messages.create(
            model=api_model,
            messages=request.messages,
            max_tokens=request.max_tokens or 1024,
            temperature=request.temperature if request.temperature is not None else 0.7,
        )
        return LLMResponse(
            content=message.content[0].text,
            model=request.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            total_tokens=message.usage.input_tokens + message.usage.output_tokens,
            stop_reason=message.stop_reason or "end_turn",
        )

    async def list_models(self) -> list[str]:
        return list(MODEL_ALIASES.keys())
