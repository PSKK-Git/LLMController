from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llmcontroller.auth.security import hash_api_key
from llmcontroller.db.database import get_db
from llmcontroller.db.models import ApiKey


async def authenticate(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    key_hash = hash_api_key(token)

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if api_key is None or api_key.revoked:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if api_key.expires_at is not None and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")

    api_key.last_used = datetime.utcnow()
    await db.commit()
    return api_key
