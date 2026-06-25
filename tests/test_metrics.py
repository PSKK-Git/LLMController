import pytest
import redis.asyncio as aioredis

from llmcontroller.auth.security import generate_api_key
from llmcontroller.db.models import ApiKey, Organization
from llmcontroller.providers.base import LLMResponse

TEST_REDIS = "redis://localhost:6379/15"


@pytest.fixture
def stub_claude(monkeypatch):
    async def fake_chat(self, request):
        return LLMResponse(
            content="hi", model=request.model,
            input_tokens=10, output_tokens=5, total_tokens=15, stop_reason="end_turn",
        )
    monkeypatch.setattr("llmcontroller.providers.claude.ClaudeProvider.chat", fake_chat)
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "test")
    monkeypatch.setattr("llmcontroller.config.settings.redis_url", TEST_REDIS)


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_families(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "llm_requests_total" in resp.text
    assert "llm_request_duration_seconds" in resp.text


@pytest.mark.asyncio
async def test_success_records_request_metric(client, db_session, stub_claude):
    r = aioredis.from_url(TEST_REDIS); await r.flushdb(); await r.aclose()
    org = Organization(name="Acme"); db_session.add(org); await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    ok = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert ok.status_code == 200

    m = await client.get("/metrics")
    assert 'status="200"' in m.text
    assert "llm_cost_total_usd" in m.text
