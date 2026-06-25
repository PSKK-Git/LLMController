import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llmcontroller.api.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatUsage,
)
from llmcontroller.auth.dependencies import authenticate
from llmcontroller.cache.redis_client import get_redis
from llmcontroller.cost.calculator import calculate_cost
from llmcontroller.db.database import get_db
from llmcontroller.db.models import ApiKey, Quota
from llmcontroller.logging.audit import record_request
from llmcontroller.observability import metrics
from llmcontroller.providers.base import LLMRequest
from llmcontroller.providers.factory import get_provider, provider_name_for_model
from llmcontroller.quota.engine import RedisQuotaEngine

router = APIRouter(prefix="/v1", tags=["llm"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    api_key: ApiKey = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
) -> ChatCompletionResponse:
    try:
        provider_name = provider_name_for_model(body.model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

    quotas = (
        await db.execute(select(Quota).where(Quota.api_key_id == api_key.id))
    ).scalars().all()

    redis = get_redis()
    engine = RedisQuotaEngine(redis)
    key_id = str(api_key.id)
    try:
        # --- pre-call quota enforcement ---
        for q in quotas:
            if q.quota_type == "requests_per_minute":
                allowed, remaining = await engine.consume(key_id, q.quota_type, q.limit_value, 1)
                if not allowed:
                    metrics.quota_rejections_total.labels("requests_per_minute").inc()
                    metrics.requests_total.labels(body.model, provider_name, "429").inc()
                    raise HTTPException(
                        status_code=429, detail="Rate limit exceeded",
                        headers={"Retry-After": "60"},
                    )
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            elif q.quota_type == "tokens_per_day":
                if await engine.current(key_id, q.quota_type) >= q.limit_value:
                    metrics.quota_rejections_total.labels("tokens_per_day").inc()
                    metrics.requests_total.labels(body.model, provider_name, "429").inc()
                    raise HTTPException(
                        status_code=429, detail="Daily token quota exceeded",
                        headers={"Retry-After": "3600"},
                    )

        provider = get_provider(body.model)
        llm_request = LLMRequest(
            model=body.model,
            messages=[m.model_dump() for m in body.messages],
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )

        request_id = uuid.uuid4()
        start = time.perf_counter()
        try:
            result = await provider.chat(llm_request)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            metrics.requests_total.labels(body.model, provider_name, "502").inc()
            metrics.request_duration.labels(body.model, provider_name).observe(latency_ms / 1000)
            background_tasks.add_task(
                record_request,
                api_key_id=api_key.id, org_id=api_key.org_id, model=body.model,
                provider=provider_name, prompt_tokens=0, completion_tokens=0,
                total_tokens=0, actual_cost=0.0, latency_ms=latency_ms,
                status_code=502, request_id=request_id, error_message=str(exc),
            )
            raise HTTPException(status_code=502, detail="Provider request failed") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        cost = calculate_cost(body.model, result.input_tokens, result.output_tokens)

        for q in quotas:
            if q.quota_type == "tokens_per_day":
                await engine.consume(key_id, q.quota_type, q.limit_value, result.total_tokens)

        # --- metrics ---
        metrics.requests_total.labels(body.model, provider_name, "200").inc()
        metrics.tokens_total.labels(body.model, "input").inc(result.input_tokens)
        metrics.tokens_total.labels(body.model, "output").inc(result.output_tokens)
        metrics.cost_total.labels(body.model).inc(cost)
        metrics.request_duration.labels(body.model, provider_name).observe(latency_ms / 1000)

        background_tasks.add_task(
            record_request,
            api_key_id=api_key.id, org_id=api_key.org_id, model=body.model,
            provider=provider_name, prompt_tokens=result.input_tokens,
            completion_tokens=result.output_tokens, total_tokens=result.total_tokens,
            actual_cost=cost, latency_ms=latency_ms, status_code=200, request_id=request_id,
        )

        response.headers["X-Cost-This-Request"] = f"{cost:.8f}"
        return ChatCompletionResponse(
            model=result.model,
            choices=[ChatChoice(message=ChatMessage(role="assistant", content=result.content))],
            usage=ChatUsage(
                prompt_tokens=result.input_tokens,
                completion_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
            ),
        )
    finally:
        await redis.aclose()
