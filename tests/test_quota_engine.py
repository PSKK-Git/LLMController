import pytest

from llmcontroller.quota.engine import RedisQuotaEngine


@pytest.mark.asyncio
async def test_consume_within_limit(redis_client):
    eng = RedisQuotaEngine(redis_client)
    allowed, remaining = await eng.consume("key1", "requests_per_minute", 3, 1)
    assert allowed is True
    assert remaining == 2


@pytest.mark.asyncio
async def test_consume_blocks_over_limit(redis_client):
    eng = RedisQuotaEngine(redis_client)
    for _ in range(3):
        await eng.consume("key1", "requests_per_minute", 3, 1)
    allowed, remaining = await eng.consume("key1", "requests_per_minute", 3, 1)
    assert allowed is False
    assert remaining == 0
    assert await eng.current("key1", "requests_per_minute") == 3


@pytest.mark.asyncio
async def test_window_ttl_is_set(redis_client):
    eng = RedisQuotaEngine(redis_client)
    await eng.consume("key1", "requests_per_minute", 5, 1)
    ttl = await redis_client.ttl("quota:key1:requests_per_minute")
    assert 0 < ttl <= 60


@pytest.mark.asyncio
async def test_token_amount_consumption(redis_client):
    eng = RedisQuotaEngine(redis_client)
    allowed, remaining = await eng.consume("key1", "tokens_per_day", 1000, 250)
    assert allowed is True
    assert remaining == 750
