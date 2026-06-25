from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llmcontroller.api.schemas import (
    CreateKeyRequest,
    CreateKeyResponse,
    CreateOrgRequest,
    CreateOrgResponse,
    CreateQuotaRequest,
    CreateQuotaResponse,
)
from llmcontroller.auth.security import generate_api_key
from llmcontroller.config import settings
from llmcontroller.db.database import get_db
from llmcontroller.db.models import ApiKey, Organization, Quota

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/organizations", response_model=CreateOrgResponse)
async def create_org(
    body: CreateOrgRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> CreateOrgResponse:
    org = Organization(name=body.name)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return CreateOrgResponse(org_id=org.id)


@router.post("/api-keys", response_model=CreateKeyResponse)
async def create_key(
    body: CreateKeyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> CreateKeyResponse:
    plaintext, key_hash = generate_api_key()
    api_key = ApiKey(org_id=body.org_id, key_hash=key_hash, name=body.name)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return CreateKeyResponse(api_key=plaintext, api_key_id=api_key.id)


@router.post("/quotas", response_model=CreateQuotaResponse)
async def create_quota(
    body: CreateQuotaRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> CreateQuotaResponse:
    result = await db.execute(select(ApiKey).where(ApiKey.id == body.api_key_id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    quota = Quota(
        org_id=api_key.org_id,
        api_key_id=body.api_key_id,
        quota_type=body.quota_type,
        limit_value=body.limit_value,
        model=body.model,
    )
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return CreateQuotaResponse(quota_id=quota.id)
