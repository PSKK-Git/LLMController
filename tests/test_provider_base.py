import pytest

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse


def test_llm_request_defaults():
    req = LLMRequest(model="claude-3-sonnet", messages=[{"role": "user", "content": "hi"}])
    assert req.stream is False
    assert req.max_tokens is None


def test_llm_response_fields():
    resp = LLMResponse(
        content="hello", model="claude-3-sonnet",
        input_tokens=5, output_tokens=3, total_tokens=8, stop_reason="end_turn",
    )
    assert resp.total_tokens == 8


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
