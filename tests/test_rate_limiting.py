import pytest
import redis.asyncio as aioredis

from llmcontroller.auth.security import generate_api_key
from llmcontroller.db.models import ApiKey, Organization, Quota
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


async def _seed(db_session, quota_type, limit):
    r = aioredis.from_url(TEST_REDIS)
    await r.flushdb()
    await r.aclose()
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    key = ApiKey(org_id=org.id, key_hash=key_hash, name="prod")
    db_session.add(key)
    await db_session.flush()
    db_session.add(Quota(org_id=org.id, api_key_id=key.id, quota_type=quota_type, limit_value=limit))
    await db_session.commit()
    return plaintext


@pytest.mark.asyncio
async def test_requests_per_minute_429(client, db_session, stub_claude):
    plaintext = await _seed(db_session, "requests_per_minute", 1)
    headers = {"Authorization": f"Bearer {plaintext}"}
    body = {"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]}

    r1 = await client.post("/v1/chat/completions", headers=headers, json=body)
    assert r1.status_code == 200
    assert r1.headers["X-RateLimit-Remaining"] == "0"

    r2 = await client.post("/v1/chat/completions", headers=headers, json=body)
    assert r2.status_code == 429
    assert r2.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_no_quota_means_unlimited(client, db_session, stub_claude):
    # key with no quota rows -> never rate limited
    r = aioredis.from_url(TEST_REDIS)
    await r.flushdb()
    await r.aclose()
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    headers = {"Authorization": f"Bearer {plaintext}"}
    body = {"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]}
    for _ in range(3):
        resp = await client.post("/v1/chat/completions", headers=headers, json=body)
        assert resp.status_code == 200
