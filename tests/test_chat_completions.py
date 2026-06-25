import pytest

from llmcontroller.auth.security import generate_api_key
from llmcontroller.db.models import ApiKey, Organization
from llmcontroller.providers.base import LLMResponse


@pytest.fixture
def stub_claude(monkeypatch):
    async def fake_chat(self, request):
        return LLMResponse(
            content="Hello from Claude",
            model=request.model,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            stop_reason="end_turn",
        )

    monkeypatch.setattr("llmcontroller.providers.claude.ClaudeProvider.chat", fake_chat)
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "test")


@pytest.mark.asyncio
async def test_chat_completion_end_to_end(client, db_session, stub_claude):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    resp = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "Hello from Claude"
    assert body["usage"]["total_tokens"] == 15
    assert resp.headers["X-Cost-This-Request"] == "0.00010500"


@pytest.mark.asyncio
async def test_unknown_model_returns_400(client, db_session, stub_claude):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    resp = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 400
