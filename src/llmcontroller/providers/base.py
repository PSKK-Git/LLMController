from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    stop_reason: str


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...
