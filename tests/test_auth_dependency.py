import pytest


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401(client):
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_key_returns_401(client):
    resp = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-nope"},
        json={"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401
