from unittest.mock import AsyncMock, MagicMock

import pytest

from llmcontroller.providers.base import LLMRequest
from llmcontroller.providers.claude import ClaudeProvider


@pytest.mark.asyncio
async def test_chat_maps_response():
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text="Hello there")]
    fake_message.model = "claude-3-5-sonnet-20241022"
    fake_message.stop_reason = "end_turn"
    fake_message.usage = MagicMock(input_tokens=12, output_tokens=4)

    provider = ClaudeProvider(api_key="test")
    provider.client.messages.create = AsyncMock(return_value=fake_message)

    req = LLMRequest(model="claude-3-sonnet", messages=[{"role": "user", "content": "hi"}])
    resp = await provider.chat(req)

    assert resp.content == "Hello there"
    assert resp.input_tokens == 12
    assert resp.output_tokens == 4
    assert resp.total_tokens == 16
    assert resp.stop_reason == "end_turn"
    called_kwargs = provider.client.messages.create.call_args.kwargs
    assert called_kwargs["model"] == "claude-3-5-sonnet-20241022"
    assert called_kwargs["max_tokens"] == 1024
