import uuid

from pydantic import BaseModel


class CreateOrgRequest(BaseModel):
    name: str


class CreateOrgResponse(BaseModel):
    org_id: uuid.UUID


class CreateKeyRequest(BaseModel):
    org_id: uuid.UUID
    name: str | None = None


class CreateKeyResponse(BaseModel):
    api_key: str
    api_key_id: uuid.UUID


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    message: ChatMessage


class ChatCompletionResponse(BaseModel):
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage


class CreateQuotaRequest(BaseModel):
    api_key_id: uuid.UUID
    quota_type: str
    limit_value: int
    model: str | None = None


class CreateQuotaResponse(BaseModel):
    quota_id: uuid.UUID
