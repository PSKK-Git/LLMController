import pytest
from sqlalchemy import select

from llmcontroller.db.models import ApiKey, Organization


@pytest.mark.asyncio
async def test_can_persist_org_and_key(db_session):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()

    key = ApiKey(org_id=org.id, key_hash="abc123", name="prod")
    db_session.add(key)
    await db_session.commit()

    result = await db_session.execute(select(ApiKey).where(ApiKey.key_hash == "abc123"))
    found = result.scalar_one()
    assert found.org_id == org.id
    assert found.revoked is False
