import redis.asyncio as aioredis

# Fixed-window TTLs per quota type (seconds).
TTL_SECONDS: dict[str, int] = {
    "requests_per_minute": 60,
    "tokens_per_day": 86400,
    "cost_per_month": 2592000,
}


class RedisQuotaEngine:
    """Fixed-window quota counters backed by Redis.

    consume() increments the window counter by `amount`; if the new total would
    exceed `limit`, it rolls the increment back and reports denial.
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    def _key(self, api_key_id: str, quota_type: str) -> str:
        return f"quota:{api_key_id}:{quota_type}"

    async def consume(
        self, api_key_id: str, quota_type: str, limit: int, amount: int = 1
    ) -> tuple[bool, int]:
        key = self._key(api_key_id, quota_type)
        new = await self.redis.incrby(key, amount)
        if new == amount:  # first write in this window
            await self.redis.expire(key, TTL_SECONDS.get(quota_type, 3600))
        if new > limit:
            await self.redis.decrby(key, amount)
            return False, max(0, limit - (new - amount))
        return True, limit - new

    async def current(self, api_key_id: str, quota_type: str) -> int:
        val = await self.redis.get(self._key(api_key_id, quota_type))
        return int(val) if val else 0
