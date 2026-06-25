from unittest.mock import AsyncMock, MagicMock

import pytest

from llmcontroller.providers.base import LLMRequest
from llmcontroller.providers.factory import get_provider, provider_name_for_model
from llmcontroller.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_chat_maps_response():
    fake = MagicMock()
    msg = MagicMock()
    msg.message.content = "hello"
    msg.finish_reason = "stop"
    fake.choices = [msg]
    fake.usage = MagicMock(prompt_tokens=8, completion_tokens=2, total_tokens=10)

    p = OpenAIProvider(api_key="test")
    p.client.chat.completions.create = AsyncMock(return_value=fake)

    resp = await p.chat(LLMRequest(model="gpt-4o", messages=[{"role": "user", "content": "hi"}]))
    assert resp.content == "hello"
    assert resp.input_tokens == 8
    assert resp.total_tokens == 10
    assert resp.stop_reason == "stop"


def test_factory_routes_gpt_to_openai(monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.openai_api_key", "test")
    assert provider_name_for_model("gpt-4o") == "openai"
    assert isinstance(get_provider("gpt-4o"), OpenAIProvider)
