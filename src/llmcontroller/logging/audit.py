import sys
import uuid

from llmcontroller.db.database import async_session_factory
from llmcontroller.db.models import LLMRequest


async def record_request(
    *,
    api_key_id: uuid.UUID,
    org_id: uuid.UUID,
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    actual_cost: float,
    latency_ms: int,
    status_code: int,
    request_id: uuid.UUID,
    error_message: str | None = None,
) -> None:
    """Fire-and-forget audit write. Never raises into the request path."""
    try:
        async with async_session_factory() as session:
            session.add(
                LLMRequest(
                    api_key_id=api_key_id,
                    org_id=org_id,
                    model=model,
                    provider=provider,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    actual_cost=actual_cost,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    request_id=request_id,
                    error_message=error_message,
                )
            )
            await session.commit()
    except Exception as exc:  # audit must never break the response
        print(f"[audit] failed to record request {request_id}: {exc}", file=sys.stderr)
