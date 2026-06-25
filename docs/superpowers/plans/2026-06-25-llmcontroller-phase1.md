# LLMController Phase 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working `POST /v1/chat/completions` endpoint that authenticates an API key, routes to Anthropic Claude, calculates cost, and writes an audit record — runnable locally via docker-compose.

**Architecture:** FastAPI gateway with an async SQLAlchemy/PostgreSQL persistence layer. Requests are authenticated by a SHA-256-hashed API key looked up in the DB, routed through a provider-abstraction layer to Claude, priced via a static pricing table, and audited via a FastAPI BackgroundTask (non-blocking).

**Tech Stack:** Python 3.11, FastAPI, async SQLAlchemy 2.0 + asyncpg, Alembic, Anthropic SDK, PostgreSQL, pytest + pytest-asyncio + httpx.

## Global Constraints

- Python version: **3.11+**
- API key storage: **SHA-256 hex digest** of the plaintext key (deterministic, lookup-able). *Deviation from spec's bcrypt — bcrypt is non-deterministic and cannot be looked up. Documented in Task 3.*
- Database access: **async** (SQLAlchemy async engine + asyncpg). *Deviation from spec's psycopg2-binary — async is required for the non-blocking request path.*
- Plaintext API keys are **never stored or logged** — shown to the caller exactly once at creation.
- Audit writes must **not block** the request response (use BackgroundTasks).
- All new code lives under `src/llmcontroller/`; all tests under `tests/`.
- Money stored as `DECIMAL(12, 8)`; cost calculations rounded to 8 decimal places.

---

## File Structure

| Path | Responsibility |
|---|---|
| `requirements.txt` | Pinned dependencies |
| `docker-compose.yml` | Local Postgres + Redis |
| `.env.example` | Documented env vars |
| `src/llmcontroller/config.py` | Settings (pydantic-settings) |
| `src/llmcontroller/main.py` | FastAPI app, router wiring, `/health` |
| `src/llmcontroller/db/database.py` | Async engine, session factory, `Base`, `get_db` |
| `src/llmcontroller/db/models.py` | `Organization`, `ApiKey`, `LLMRequest` ORM models |
| `src/llmcontroller/auth/security.py` | API key generation + SHA-256 hashing |
| `src/llmcontroller/auth/dependencies.py` | `authenticate` dependency (key → org) |
| `src/llmcontroller/cost/pricing.py` | Static per-model pricing table |
| `src/llmcontroller/cost/calculator.py` | `calculate_cost` |
| `src/llmcontroller/providers/base.py` | `LLMRequest`, `LLMResponse`, `LLMProvider` ABC |
| `src/llmcontroller/providers/claude.py` | `ClaudeProvider` (Anthropic adapter) |
| `src/llmcontroller/providers/factory.py` | `get_provider(model)` |
| `src/llmcontroller/api/schemas.py` | HTTP request/response Pydantic models |
| `src/llmcontroller/api/admin.py` | Admin router (create org, create key) |
| `src/llmcontroller/api/routes.py` | `/v1/chat/completions` router |
| `src/llmcontroller/logging/audit.py` | `record_request` audit writer |
| `alembic.ini`, `migrations/` | Alembic config + initial migration |
| `tests/conftest.py` | pytest fixtures (test DB, async client) |

---

## Task 1: Project Scaffold, Config, and Health Endpoint

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/llmcontroller/__init__.py` (empty)
- Create: `src/llmcontroller/config.py`
- Create: `src/llmcontroller/main.py`
- Test: `tests/__init__.py` (empty), `tests/conftest.py`, `tests/test_health.py`

**Interfaces:**
- Produces: `settings` (instance of `Settings`) with attributes `database_url: str`, `redis_url: str`, `anthropic_api_key: str`, `admin_token: str`; FastAPI `app` in `main.py`.

- [ ] **Step 1: Create `requirements.txt`**

```text
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.4
pydantic-settings==2.3.4
sqlalchemy[asyncio]==2.0.31
asyncpg==0.29.0
alembic==1.13.2
anthropic==0.39.0
python-dotenv==1.0.1
greenlet==3.0.3

# Testing
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0
pytest-cov==5.0.0
```

- [ ] **Step 2: Create `.env.example`**

```text
DATABASE_URL=postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-replace-me
ADMIN_TOKEN=dev-admin-token-change-me
```

- [ ] **Step 3: Create `src/llmcontroller/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    admin_token: str = "dev-admin-token-change-me"


settings = Settings()
```

- [ ] **Step 4: Create `src/llmcontroller/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="LLMController", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
```

- [ ] **Step 5: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/conftest.py`:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from llmcontroller.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

Create `tests/test_health.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_health_returns_healthy(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}
```

Create `pytest.ini` at repo root:

```ini
[pytest]
asyncio_mode = auto
pythonpath = src
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example pytest.ini src/llmcontroller/ tests/
git commit -m "feat: project scaffold, config, and health endpoint"
```

---

## Task 2: Local Dev Environment (docker-compose)

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Produces: a Postgres instance reachable at `postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller` and Redis at `redis://localhost:6379/0`.

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: llm
      POSTGRES_PASSWORD: llm
      POSTGRES_DB: llmcontroller
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U llm"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 2: Start and verify the database is reachable**

Run: `docker compose up -d && docker compose ps`
Expected: both `postgres` and `redis` services show as running (postgres healthy).

- [ ] **Step 3: Create the test database**

Run: `docker compose exec postgres psql -U llm -d llmcontroller -c "CREATE DATABASE llmcontroller_test;"`
Expected: `CREATE DATABASE`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: local dev environment with postgres and redis"
```

---

## Task 3: Database Layer — Engine, Session, ORM Models

**Files:**
- Create: `src/llmcontroller/db/__init__.py` (empty)
- Create: `src/llmcontroller/db/database.py`
- Create: `src/llmcontroller/db/models.py`
- Test: `tests/test_models.py`
- Modify: `tests/conftest.py` (add DB fixtures)

**Interfaces:**
- Produces:
  - `Base` (DeclarativeBase) and `get_db()` async dependency yielding `AsyncSession`, plus `engine` and `async_session_factory` in `database.py`.
  - ORM models in `models.py`:
    - `Organization(id: UUID, name: str, created_at, updated_at)`
    - `ApiKey(id: UUID, org_id: UUID, key_hash: str, name: str|None, created_at, last_used, expires_at, revoked: bool)`
    - `LLMRequest(id: UUID, api_key_id: UUID, org_id: UUID, model: str, provider: str, prompt_tokens, completion_tokens, total_tokens, estimated_cost, actual_cost, latency_ms, status_code, error_message, masked_prompt, masked_response, request_id, created_at)`

- [ ] **Step 1: Create `src/llmcontroller/db/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from llmcontroller.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 2: Create `src/llmcontroller/db/models.py`**

> Note on `key_hash`: this stores a **SHA-256 hex digest** of the plaintext API key, NOT bcrypt. SHA-256 is deterministic so the key can be found by hashing the incoming key and querying `WHERE key_hash = ...`. bcrypt (the spec's original choice) is salted and produces a different output every time, making lookup impossible.

```python
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from llmcontroller.db.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class LLMRequest(Base):
    __tablename__ = "llm_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    masked_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    masked_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Add DB fixtures to `tests/conftest.py`**

Replace the file contents with:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from llmcontroller.db.database import Base, get_db
from llmcontroller.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller_test"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Write the failing test**

Create `tests/test_models.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (requires docker-compose Postgres running from Task 2)

- [ ] **Step 6: Commit**

```bash
git add src/llmcontroller/db/ tests/conftest.py tests/test_models.py
git commit -m "feat: async db layer and ORM models"
```

---

## Task 4: Alembic Setup and Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/` (dir)
- Create: `migrations/versions/0001_initial.py`

**Interfaces:**
- Produces: a runnable `alembic upgrade head` that creates `organizations`, `api_keys`, `llm_requests` with their indexes.

- [ ] **Step 1: Initialize Alembic scaffolding**

Run: `alembic init migrations`
Expected: creates `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/`.

- [ ] **Step 2: Point `alembic.ini` at the database**

In `alembic.ini`, set:

```ini
sqlalchemy.url = postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller
```

- [ ] **Step 3: Configure `migrations/env.py` for async + metadata**

Replace the body of `migrations/env.py` with:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from llmcontroller.db.database import Base
from llmcontroller.db import models  # noqa: F401  (ensures models are imported)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

- [ ] **Step 4: Autogenerate the initial migration**

Run: `alembic revision --autogenerate -m "initial" --rev-id 0001_initial`
Expected: creates `migrations/versions/0001_initial.py` containing `create_table` calls for all three tables.

- [ ] **Step 5: Apply and verify the migration**

Run: `alembic upgrade head && docker compose exec postgres psql -U llm -d llmcontroller -c "\dt"`
Expected: lists `organizations`, `api_keys`, `llm_requests`, `alembic_version`.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini migrations/
git commit -m "feat: alembic setup and initial migration"
```

---

## Task 5: API Key Security (generation + SHA-256 hashing)

**Files:**
- Create: `src/llmcontroller/auth/__init__.py` (empty)
- Create: `src/llmcontroller/auth/security.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Produces:
  - `KEY_PREFIX = "sk-"`
  - `hash_api_key(key: str) -> str` — returns SHA-256 hex digest
  - `generate_api_key() -> tuple[str, str]` — returns `(plaintext_key, key_hash)` where `plaintext_key` starts with `KEY_PREFIX`

- [ ] **Step 1: Write the failing test**

Create `tests/test_security.py`:

```python
from llmcontroller.auth.security import KEY_PREFIX, generate_api_key, hash_api_key


def test_hash_is_deterministic():
    assert hash_api_key("sk-abc") == hash_api_key("sk-abc")


def test_hash_is_64_hex_chars():
    h = hash_api_key("sk-abc")
    assert len(h) == 64
    int(h, 16)  # raises if not hex


def test_generate_returns_prefixed_key_and_matching_hash():
    plaintext, key_hash = generate_api_key()
    assert plaintext.startswith(KEY_PREFIX)
    assert key_hash == hash_api_key(plaintext)


def test_generated_keys_are_unique():
    k1, _ = generate_api_key()
    k2, _ = generate_api_key()
    assert k1 != k2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'llmcontroller.auth.security'`

- [ ] **Step 3: Create `src/llmcontroller/auth/security.py`**

```python
import hashlib
import secrets

KEY_PREFIX = "sk-"


def hash_api_key(key: str) -> str:
    """Deterministic SHA-256 hex digest used for DB lookup."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (plaintext_key, key_hash). Plaintext is shown to the caller once."""
    plaintext = KEY_PREFIX + secrets.token_urlsafe(32)
    return plaintext, hash_api_key(plaintext)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_security.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/llmcontroller/auth/ tests/test_security.py
git commit -m "feat: api key generation and sha-256 hashing"
```

---

## Task 6: Pricing Table and Cost Calculator

**Files:**
- Create: `src/llmcontroller/cost/__init__.py` (empty)
- Create: `src/llmcontroller/cost/pricing.py`
- Create: `src/llmcontroller/cost/calculator.py`
- Test: `tests/test_cost_calculator.py`

**Interfaces:**
- Produces:
  - `PRICING: dict[str, dict[str, float]]` keyed by model, each with `"input_per_1k"` and `"output_per_1k"`
  - `calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float` (rounded to 8 dp; raises `ValueError` for unknown model)

- [ ] **Step 1: Write the failing test**

Create `tests/test_cost_calculator.py`:

```python
import pytest

from llmcontroller.cost.calculator import calculate_cost


def test_known_model_cost():
    # claude-3-sonnet: input 0.003/1k, output 0.015/1k
    # 1000 in, 1000 out => 0.003 + 0.015 = 0.018
    assert calculate_cost("claude-3-sonnet", 1000, 1000) == pytest.approx(0.018)


def test_zero_tokens_is_zero():
    assert calculate_cost("claude-3-sonnet", 0, 0) == 0.0


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        calculate_cost("does-not-exist", 10, 10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cost_calculator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/llmcontroller/cost/pricing.py`**

```python
# USD price per 1,000 tokens. Update when providers change pricing.
PRICING: dict[str, dict[str, float]] = {
    "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
}
```

- [ ] **Step 4: Create `src/llmcontroller/cost/calculator.py`**

```python
from llmcontroller.cost.pricing import PRICING


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost in USD, rounded to 8 decimal places."""
    if model not in PRICING:
        raise ValueError(f"Unknown model: {model}")
    pricing = PRICING[model]
    input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
    return round(input_cost + output_cost, 8)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cost_calculator.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add src/llmcontroller/cost/ tests/test_cost_calculator.py
git commit -m "feat: pricing table and cost calculator"
```

---

## Task 7: Provider Base Types

**Files:**
- Create: `src/llmcontroller/providers/__init__.py` (empty)
- Create: `src/llmcontroller/providers/base.py`
- Test: `tests/test_provider_base.py`

**Interfaces:**
- Produces:
  - `LLMRequest(model: str, messages: list[dict], temperature: float|None = None, max_tokens: int|None = None, stream: bool = False)` (Pydantic model)
  - `LLMResponse(content: str, model: str, input_tokens: int, output_tokens: int, total_tokens: int, stop_reason: str)` (Pydantic model)
  - `LLMProvider` ABC with `async def chat(self, request: LLMRequest) -> LLMResponse` and `async def list_models(self) -> list[str]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_provider_base.py`:

```python
import pytest

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse


def test_llm_request_defaults():
    req = LLMRequest(model="claude-3-sonnet", messages=[{"role": "user", "content": "hi"}])
    assert req.stream is False
    assert req.max_tokens is None


def test_llm_response_fields():
    resp = LLMResponse(
        content="hello",
        model="claude-3-sonnet",
        input_tokens=5,
        output_tokens=3,
        total_tokens=8,
        stop_reason="end_turn",
    )
    assert resp.total_tokens == 8


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_provider_base.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/llmcontroller/providers/base.py`**

```python
from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    stop_reason: str


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_provider_base.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/llmcontroller/providers/__init__.py src/llmcontroller/providers/base.py tests/test_provider_base.py
git commit -m "feat: provider base types and abstract interface"
```

---

## Task 8: Claude Provider Adapter

**Files:**
- Create: `src/llmcontroller/providers/claude.py`
- Test: `tests/test_claude_provider.py`

**Interfaces:**
- Consumes: `LLMRequest`, `LLMResponse`, `LLMProvider` from `providers/base.py`.
- Produces:
  - `MODEL_ALIASES: dict[str, str]` mapping public model names to Anthropic API model IDs.
  - `ClaudeProvider(api_key: str)` with `chat` and `list_models`. `chat` uses `AsyncAnthropic`, defaults `max_tokens` to 1024, maps the public model name through `MODEL_ALIASES`, and returns an `LLMResponse`.

> The Anthropic API requires real model IDs (e.g. `claude-3-5-sonnet-20241022`). `MODEL_ALIASES` maps the friendly names used in the pricing table to those IDs. Verify the IDs against current Anthropic docs before going live.

- [ ] **Step 1: Write the failing test**

Create `tests/test_claude_provider.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from llmcontroller.providers.base import LLMRequest
from llmcontroller.providers.claude import ClaudeProvider


@pytest.mark.asyncio
async def test_chat_maps_response():
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text="Hello there")]
    fake_message.model = "claude-3-5-sonnet-20241022"
    fake_message.stop_reason = "end_turn"
    fake_message.usage = MagicMock(input_tokens=12, output_tokens=4)

    provider = ClaudeProvider(api_key="test")
    provider.client.messages.create = AsyncMock(return_value=fake_message)

    req = LLMRequest(model="claude-3-sonnet", messages=[{"role": "user", "content": "hi"}])
    resp = await provider.chat(req)

    assert resp.content == "Hello there"
    assert resp.input_tokens == 12
    assert resp.output_tokens == 4
    assert resp.total_tokens == 16
    assert resp.stop_reason == "end_turn"
    # verify the alias was applied in the API call
    called_kwargs = provider.client.messages.create.call_args.kwargs
    assert called_kwargs["model"] == "claude-3-5-sonnet-20241022"
    assert called_kwargs["max_tokens"] == 1024
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_claude_provider.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/llmcontroller/providers/claude.py`**

```python
from anthropic import AsyncAnthropic

from llmcontroller.providers.base import LLMProvider, LLMRequest, LLMResponse

# Friendly model name -> Anthropic API model ID. Verify against current docs.
MODEL_ALIASES: dict[str, str] = {
    "claude-3-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
}


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        api_model = MODEL_ALIASES.get(request.model, request.model)
        message = await self.client.messages.create(
            model=api_model,
            messages=request.messages,
            max_tokens=request.max_tokens or 1024,
            temperature=request.temperature if request.temperature is not None else 0.7,
        )
        return LLMResponse(
            content=message.content[0].text,
            model=request.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            total_tokens=message.usage.input_tokens + message.usage.output_tokens,
            stop_reason=message.stop_reason or "end_turn",
        )

    async def list_models(self) -> list[str]:
        return list(MODEL_ALIASES.keys())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_claude_provider.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/llmcontroller/providers/claude.py tests/test_claude_provider.py
git commit -m "feat: claude provider adapter"
```

---

## Task 9: Provider Factory

**Files:**
- Create: `src/llmcontroller/providers/factory.py`
- Test: `tests/test_provider_factory.py`

**Interfaces:**
- Consumes: `ClaudeProvider`, `MODEL_ALIASES`, `settings.anthropic_api_key`.
- Produces:
  - `PROVIDER_FOR_MODEL: dict[str, str]` mapping each known model to a provider name (`"anthropic"`).
  - `provider_name_for_model(model: str) -> str` (raises `ValueError` if unknown).
  - `get_provider(model: str) -> LLMProvider` returning a `ClaudeProvider` for anthropic models.

- [ ] **Step 1: Write the failing test**

Create `tests/test_provider_factory.py`:

```python
import pytest

from llmcontroller.providers.claude import ClaudeProvider
from llmcontroller.providers.factory import get_provider, provider_name_for_model


def test_provider_name_for_known_model():
    assert provider_name_for_model("claude-3-sonnet") == "anthropic"


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        provider_name_for_model("gpt-4")


def test_get_provider_returns_claude(monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "test")
    provider = get_provider("claude-3-sonnet")
    assert isinstance(provider, ClaudeProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_provider_factory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/llmcontroller/providers/factory.py`**

```python
from llmcontroller.config import settings
from llmcontroller.providers.base import LLMProvider
from llmcontroller.providers.claude import MODEL_ALIASES, ClaudeProvider

PROVIDER_FOR_MODEL: dict[str, str] = {model: "anthropic" for model in MODEL_ALIASES}


def provider_name_for_model(model: str) -> str:
    if model not in PROVIDER_FOR_MODEL:
        raise ValueError(f"Unknown model: {model}")
    return PROVIDER_FOR_MODEL[model]


def get_provider(model: str) -> LLMProvider:
    name = provider_name_for_model(model)
    if name == "anthropic":
        return ClaudeProvider(api_key=settings.anthropic_api_key)
    raise ValueError(f"Unsupported provider: {name}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_provider_factory.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/llmcontroller/providers/factory.py tests/test_provider_factory.py
git commit -m "feat: provider factory"
```

---

## Task 10: Authentication Dependency

**Files:**
- Create: `src/llmcontroller/auth/dependencies.py`
- Test: `tests/test_auth_dependency.py`

**Interfaces:**
- Consumes: `hash_api_key` (security), `ApiKey` (models), `get_db`.
- Produces:
  - `authenticate(authorization: str | None = Header(...), db: AsyncSession = Depends(get_db)) -> ApiKey` — extracts the bearer token, hashes it, looks up a non-revoked, non-expired `ApiKey`, updates `last_used`, and returns it. Raises `HTTPException(401)` on any failure.

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth_dependency.py`:

```python
import pytest

from llmcontroller.auth.security import generate_api_key
from llmcontroller.db.models import ApiKey, Organization


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
```

> Note: these tests exercise the 401 paths through the chat route built in Task 12. They will pass once Task 12 is complete. In this task, verify the dependency imports cleanly (Step 4).

- [ ] **Step 2: Create `src/llmcontroller/auth/dependencies.py`**

```python
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
```

- [ ] **Step 3: Verify the dependency imports cleanly**

Run: `python -c "import sys; sys.path.insert(0, 'src'); from llmcontroller.auth.dependencies import authenticate; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add src/llmcontroller/auth/dependencies.py tests/test_auth_dependency.py
git commit -m "feat: api key authentication dependency"
```

---

## Task 11: Admin Endpoints (create org, create API key)

**Files:**
- Create: `src/llmcontroller/api/__init__.py` (empty)
- Create: `src/llmcontroller/api/schemas.py`
- Create: `src/llmcontroller/api/admin.py`
- Modify: `src/llmcontroller/main.py` (include admin router)
- Test: `tests/test_admin.py`

**Interfaces:**
- Consumes: `get_db`, `generate_api_key`, `Organization`, `ApiKey`, `settings.admin_token`.
- Produces:
  - `require_admin(x_admin_token: str | None = Header(...))` dependency raising 401 unless it matches `settings.admin_token`.
  - `POST /admin/organizations` → `{ "org_id": "<uuid>" }`
  - `POST /admin/api-keys` body `{ "org_id": "<uuid>", "name": "..." }` → `{ "api_key": "sk-...", "api_key_id": "<uuid>" }` (plaintext shown once)
  - Pydantic schemas in `schemas.py`: `CreateOrgRequest`, `CreateOrgResponse`, `CreateKeyRequest`, `CreateKeyResponse`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_admin.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_org_requires_admin_token(client):
    resp = await client.post("/admin/organizations", json={"name": "Acme"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_org_and_key(client, monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.admin_token", "secret")
    headers = {"X-Admin-Token": "secret"}

    org_resp = await client.post("/admin/organizations", json={"name": "Acme"}, headers=headers)
    assert org_resp.status_code == 200
    org_id = org_resp.json()["org_id"]

    key_resp = await client.post(
        "/admin/api-keys", json={"org_id": org_id, "name": "prod"}, headers=headers
    )
    assert key_resp.status_code == 200
    body = key_resp.json()
    assert body["api_key"].startswith("sk-")
    assert "api_key_id" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin.py -v`
Expected: FAIL (404 — routes not registered)

- [ ] **Step 3: Create `src/llmcontroller/api/schemas.py`**

```python
import uuid

from pydantic import BaseModel


class CreateOrgRequest(BaseModel):
    name: str


class CreateOrgResponse(BaseModel):
    org_id: uuid.UUID


class CreateKeyRequest(BaseModel):
    org_id: uuid.UUID
    name: str | None = None


class CreateKeyResponse(BaseModel):
    api_key: str
    api_key_id: uuid.UUID
```

- [ ] **Step 4: Create `src/llmcontroller/api/admin.py`**

```python
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from llmcontroller.api.schemas import (
    CreateKeyRequest,
    CreateKeyResponse,
    CreateOrgRequest,
    CreateOrgResponse,
)
from llmcontroller.auth.security import generate_api_key
from llmcontroller.config import settings
from llmcontroller.db.database import get_db
from llmcontroller.db.models import ApiKey, Organization

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
```

- [ ] **Step 5: Register the router in `src/llmcontroller/main.py`**

Replace `main.py` with:

```python
from fastapi import FastAPI

from llmcontroller.api import admin

app = FastAPI(title="LLMController", version="0.1.0")
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_admin.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add src/llmcontroller/api/ src/llmcontroller/main.py tests/test_admin.py
git commit -m "feat: admin endpoints for org and api key creation"
```

---

## Task 12: Chat Completions Endpoint + Audit Logging

**Files:**
- Create: `src/llmcontroller/logging/__init__.py` (empty)
- Create: `src/llmcontroller/logging/audit.py`
- Create: `src/llmcontroller/api/routes.py`
- Modify: `src/llmcontroller/api/schemas.py` (add chat schemas)
- Modify: `src/llmcontroller/main.py` (include routes router)
- Test: `tests/test_chat_completions.py`

**Interfaces:**
- Consumes: `authenticate` (returns `ApiKey`), `get_provider`, `provider_name_for_model`, `calculate_cost`, `LLMRequest`, `async_session_factory`.
- Produces:
  - `record_request(...)` in `audit.py` — opens its own session via `async_session_factory` and inserts an `LLMRequest` row (used as a BackgroundTask so it never blocks the response).
  - `POST /v1/chat/completions` returning an OpenAI-style body `{ "model", "choices": [{"message": {"role": "assistant", "content": ...}}], "usage": {"prompt_tokens", "completion_tokens", "total_tokens"} }` plus header `X-Cost-This-Request`.

- [ ] **Step 1: Add chat schemas to `src/llmcontroller/api/schemas.py`**

Append:

```python
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    message: ChatMessage


class ChatCompletionResponse(BaseModel):
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage
```

- [ ] **Step 2: Create `src/llmcontroller/logging/audit.py`**

```python
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
```

> Note: `record_request` uses `async_session_factory` (the app's real DB), not the test session. The end-to-end test in Step 5 asserts on the HTTP response, not the audit row; manual verification (final section) confirms the row is written against the dev DB.

- [ ] **Step 3: Create `src/llmcontroller/api/routes.py`**

```python
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from llmcontroller.api.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatUsage,
)
from llmcontroller.auth.dependencies import authenticate
from llmcontroller.cost.calculator import calculate_cost
from llmcontroller.db.models import ApiKey
from llmcontroller.logging.audit import record_request
from llmcontroller.providers.base import LLMRequest
from llmcontroller.providers.factory import get_provider, provider_name_for_model

router = APIRouter(prefix="/v1", tags=["llm"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    api_key: ApiKey = Depends(authenticate),
) -> ChatCompletionResponse:
    try:
        provider_name = provider_name_for_model(body.model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

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
    except Exception as exc:  # provider failure
        latency_ms = int((time.perf_counter() - start) * 1000)
        background_tasks.add_task(
            record_request,
            api_key_id=api_key.id,
            org_id=api_key.org_id,
            model=body.model,
            provider=provider_name,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            actual_cost=0.0,
            latency_ms=latency_ms,
            status_code=502,
            request_id=request_id,
            error_message=str(exc),
        )
        raise HTTPException(status_code=502, detail="Provider request failed") from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    cost = calculate_cost(body.model, result.input_tokens, result.output_tokens)

    background_tasks.add_task(
        record_request,
        api_key_id=api_key.id,
        org_id=api_key.org_id,
        model=body.model,
        provider=provider_name,
        prompt_tokens=result.input_tokens,
        completion_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        actual_cost=cost,
        latency_ms=latency_ms,
        status_code=200,
        request_id=request_id,
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
```

- [ ] **Step 4: Register the router in `src/llmcontroller/main.py`**

Replace `main.py` with:

```python
from fastapi import FastAPI

from llmcontroller.api import admin, routes

app = FastAPI(title="LLMController", version="0.1.0")
app.include_router(admin.router)
app.include_router(routes.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
```

- [ ] **Step 5: Write the failing test**

Create `tests/test_chat_completions.py`:

```python
import pytest

from llmcontroller.auth.security import generate_api_key
from llmcontroller.db.models import ApiKey, Organization
from llmcontroller.providers.base import LLMResponse


@pytest.fixture
def stub_claude(monkeypatch):
    async def fake_chat(self, request):
        return LLMResponse(
            content="Hello from Claude",
            model=request.model,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            stop_reason="end_turn",
        )

    monkeypatch.setattr("llmcontroller.providers.claude.ClaudeProvider.chat", fake_chat)
    monkeypatch.setattr("llmcontroller.config.settings.anthropic_api_key", "test")


@pytest.mark.asyncio
async def test_chat_completion_end_to_end(client, db_session, stub_claude):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    resp = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "Hello from Claude"
    assert body["usage"]["total_tokens"] == 15
    # cost = (10/1000*0.003)+(5/1000*0.015) = 0.00003 + 0.000075 = 0.000105
    assert resp.headers["X-Cost-This-Request"] == "0.00010500"


@pytest.mark.asyncio
async def test_unknown_model_returns_400(client, db_session, stub_claude):
    org = Organization(name="Acme")
    db_session.add(org)
    await db_session.flush()
    plaintext, key_hash = generate_api_key()
    db_session.add(ApiKey(org_id=org.id, key_hash=key_hash, name="prod"))
    await db_session.commit()

    resp = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 400
```

> Note: `record_request` runs as a BackgroundTask against the real `async_session_factory` (dev DB). In tests this writes to whatever DB the app's factory points at; the assertions here are on the HTTP response only, so the background write does not affect test outcomes. (Wiring the audit writer to honor the test session override is a Phase 2 refinement.)

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_chat_completions.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Run the full suite**

Run: `pytest -v`
Expected: all tests PASS, including `tests/test_auth_dependency.py` (the route now exists, so the 401 paths resolve correctly).

- [ ] **Step 8: Commit**

```bash
git add src/llmcontroller/logging/ src/llmcontroller/api/routes.py src/llmcontroller/api/schemas.py src/llmcontroller/main.py tests/test_chat_completions.py
git commit -m "feat: chat completions endpoint with cost calc and async audit logging"
```

---

## Manual End-to-End Verification (after all tasks)

- [ ] **Step 1: Apply migrations and start the app**

```bash
docker compose up -d
alembic upgrade head
ANTHROPIC_API_KEY=<real-key> uvicorn llmcontroller.main:app --reload --app-dir src
```

- [ ] **Step 2: Create an org and key**

```bash
curl -s -X POST localhost:8000/admin/organizations \
  -H "X-Admin-Token: dev-admin-token-change-me" \
  -H "Content-Type: application/json" -d '{"name":"Acme"}'
# → {"org_id":"..."}

curl -s -X POST localhost:8000/admin/api-keys \
  -H "X-Admin-Token: dev-admin-token-change-me" \
  -H "Content-Type: application/json" -d '{"org_id":"<org_id>","name":"prod"}'
# → {"api_key":"sk-...","api_key_id":"..."}
```

- [ ] **Step 3: Make a real chat completion**

```bash
curl -i -X POST localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-sonnet","messages":[{"role":"user","content":"Say hi in 3 words"}]}'
# → 200 with assistant content; X-Cost-This-Request header present
```

- [ ] **Step 4: Confirm the audit row was written**

```bash
docker compose exec postgres psql -U llm -d llmcontroller \
  -c "SELECT model, total_tokens, actual_cost, status_code FROM llm_requests ORDER BY created_at DESC LIMIT 1;"
# → one row matching the request just made
```

---

## Self-Review Notes

- **Spec coverage (Phase 1):** scaffold ✓ (T1), docker-compose ✓ (T2), schema+migrations ✓ (T3,T4), auth ✓ (T5,T10), Claude adapter ✓ (T7,T8,T9), cost calc ✓ (T6), chat endpoint ✓ (T12), audit logging ✓ (T12), admin key creation ✓ (T11). Redis quotas, OpenAI/Ollama adapters, PII masking, and Prometheus metrics are **Phase 2+** and intentionally excluded.
- **Deviations from spec (intentional, documented):** SHA-256 instead of bcrypt for key hashing (lookup correctness); async SQLAlchemy + asyncpg instead of psycopg2 (non-blocking path).
- **Type consistency:** `LLMRequest`/`LLMResponse` field names are consistent across base, claude, factory, and routes. `generate_api_key() -> (plaintext, key_hash)` used consistently in security, admin, and tests. `record_request(...)` keyword signature matches its call sites in `routes.py`.
