import pytest


@pytest.mark.asyncio
async def test_redis_roundtrip(redis_client):
    await redis_client.set("k", "v")
    assert await redis_client.get("k") == "v"
    assert await redis_client.incr("counter") == 1
