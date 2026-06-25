import pytest


@pytest.mark.asyncio
async def test_index_served(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "LLMController" in resp.text
    assert "/v1/chat/completions" in resp.text
