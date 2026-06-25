# Tech Stack & Design Rationale (Interview Reference)

Every technology in LLMController, what it does, and **why it was chosen over
the common alternatives**. Organized by layer.

---

## Language & Web Framework

### Python 3.12
- **Role:** primary language.
- **Why:** the LLM/AI ecosystem is Python-first — official SDKs (Anthropic,
  OpenAI), data tooling, and the hiring target's stack are all Python.
- **Why not Go/Node/Java:** Go is great for raw throughput but has thinner
  first-party LLM SDKs; Node fits I/O-bound gateways but Python keeps us aligned
  with the AI ecosystem and the role's stack; Java is heavier to iterate on.

### FastAPI
- **Role:** HTTP API framework (routing, validation, OpenAPI docs, DI).
- **Why:** native `async` (essential for an I/O-bound proxy that mostly waits on
  upstream LLM calls), Pydantic-based request/response validation, and
  auto-generated OpenAPI/Swagger docs for free.
- **Why not Flask:** Flask is sync-first; async support is bolted on. No built-in
  validation or schema docs.
- **Why not Django/DRF:** batteries-included and heavyweight — ORM, admin,
  templating we don't need for a thin gateway. Async support is still maturing.
- **Why not Node/Express:** would split the stack off the AI ecosystem and lacks
  Pydantic-grade validation.

### Uvicorn
- **Role:** ASGI server that actually runs the async app.
- **Why:** the standard high-performance ASGI server FastAPI is designed for.

---

## Data & Persistence

### PostgreSQL
- **Role:** system of record — orgs, API keys, request audit log, (later) quotas
  and cost aggregates.
- **Why:** strong relational integrity (foreign keys across orgs/keys/requests),
  exact `DECIMAL` money math, rich indexing and analytical queries for cost
  reports, and a first-class managed option on every cloud.
- **Why not MongoDB:** our data is highly relational and money needs exact
  decimals — a document store fights both.
- **Why not MySQL:** Postgres has stronger types (native UUID, `NUMERIC`),
  better JSON, and is the common choice for this kind of platform.

### SQLAlchemy 2.0 (async) + asyncpg
- **Role:** ORM + async Postgres driver.
- **Why async:** a gateway handling many concurrent requests must not block the
  event loop on DB I/O; async keeps one process serving many in-flight requests.
- **Why not Django ORM:** tied to Django; async story weaker.
- **Why not raw SQL:** loses type-safe models, migrations integration, and
  injection-safe query building.
- **Why asyncpg over psycopg2:** psycopg2 is synchronous and would block the
  event loop — a deliberate deviation from the original spec for correctness.

### Alembic
- **Role:** database schema migrations (versioned, repeatable).
- **Why:** the standard migration tool for SQLAlchemy; lets schema evolve safely
  across environments and is what runs on container startup.

### Redis (Phase 2)
- **Role:** real-time rate-limiting / quota counters.
- **Why:** in-memory, atomic `INCR` with TTL — sub-millisecond quota checks on
  the hot path, which a relational DB can't match per-request.
- **Why not do it in Postgres:** every request would hammer the DB; Redis is the
  right tool for high-frequency ephemeral counters.

---

## Security & Auth

### SHA-256 API-key hashing (not bcrypt)
- **Role:** store a one-way hash of each API key; look keys up by hash.
- **Why SHA-256:** API keys are high-entropy random strings, so a fast
  deterministic hash is both safe and **lookup-able** (`WHERE key_hash = ...`).
- **Why not bcrypt:** bcrypt is salted/non-deterministic — you literally cannot
  find a key by its bcrypt hash. bcrypt is for *low-entropy passwords*, not API
  keys. (Genuine correction to the original spec.)

---

## LLM Integration

### Anthropic SDK (`AsyncAnthropic`)
- **Role:** talk to Claude models.
- **Why:** official, maintained, async client.
- **Provider abstraction:** an `LLMProvider` ABC normalizes requests/responses
  so OpenAI/Ollama adapters drop in later without touching the gateway — the
  Adapter + Factory patterns in action.

---

## Frontend

### Vanilla HTML + CSS + JavaScript (served by FastAPI)
- **Role:** a basic chat UI — enter key, pick model, send, see reply + cost.
- **Why:** the UI is small and the goal is to demonstrate the *gateway*. Plain
  HTML/JS means **zero build step, no npm, a tiny Docker image**, and it's served
  same-origin by FastAPI so there are **no CORS** issues.
- **Why not React/Next.js:** would add a Node toolchain, a build pipeline, and a
  second deployable for a handful of form fields — over-engineering for this
  scope. (React makes sense once the UI grows: dashboards, auth, real-time usage
  charts.)
- **Why not Vue/Angular:** same reasoning — framework overhead unjustified for a
  single-screen demo.

---

## Containerization & Deployment

### Docker (multi-stage) + Docker Compose
- **Role:** package the app into one portable image; compose runs app + Postgres
  + Redis together on one host.
- **Why:** identical environment locally and in the cloud; "build once, run
  anywhere." Compose is the simplest orchestration for a single-VM deploy.
- **Why not Kubernetes:** massive operational overhead for one small service —
  K8s is justified at multi-service / multi-node scale, not here.

### Terraform (Infrastructure as Code)
- **Role:** declaratively provision the cloud — network, firewall, VM, startup.
- **Why:** reproducible, version-controlled, reviewable infra; `destroy` cleans
  up everything (no orphaned resources / surprise bills). Cloud-agnostic via
  providers.
- **Why not the cloud console (clicking):** not reproducible, not reviewable,
  easy to leave costly resources running.
- **Why not Ansible:** Ansible is configuration management (mutating existing
  servers), not provisioning; Terraform owns the resource lifecycle.
- **Why not CloudFormation:** AWS-only. Terraform works across AWS/OCI/GCP/Azure.
- **Why not Pulumi:** great tool, but Terraform/HCL is the industry-standard
  expectation and what the role asks for.

### Oracle Cloud Infrastructure — Always Free
What we actually provision (all within the Always-Free tier):

| Resource | Purpose |
|---|---|
| **Compute: VM.Standard.A1.Flex** (ARM Ampere, 2 OCPU / 12 GB) | runs the Docker stack |
| **VCN + Subnet** | private network for the VM |
| **Internet Gateway + Route Table** | outbound/inbound internet access |
| **Security List** | firewall — open ports 22 (SSH) and 8000 (app) |
| **Oracle Linux 9 image** | the VM OS |
| **cloud-init script** | installs Docker, clones repo, runs compose on boot |

- **Why Oracle Always Free:** the only major cloud with a **forever-free** VM
  generous enough (up to 4 ARM cores / 24 GB RAM) to run the whole stack at $0 —
  no 12-month cliff.
- **Why not AWS:** the spec's ECS Fargate + ALB design isn't free (Fargate has no
  free tier; an ALB is ~$16/mo), and EC2/RDS free tier expires after 12 months.
- **Why not GCP:** the Always-Free `e2-micro` is only 1 GB RAM — too cramped for
  Postgres + Redis + app together.
- **Why not Azure:** free tier is 12-month/credit-based, not forever-free for a VM.
- **Why not Fly.io / Render / Railway:** all removed or time-limited their truly
  free tiers (Render's free Postgres expires; Railway/Fly are pay-as-you-go).

---

## Testing

### pytest + pytest-asyncio + httpx
- **Role:** unit + integration tests; httpx's ASGI transport drives the API
  in-process.
- **Why:** the de-facto Python test stack; pytest-asyncio runs async tests,
  httpx exercises real HTTP routes without a live server. 23 tests run against
  real Postgres (DB/auth/admin) with a stubbed Claude (chat path).

---

## One-Line Interview Summary

> "An async FastAPI LLM gateway: SHA-256-keyed auth, Claude via a provider
> abstraction, exact Postgres cost accounting, a zero-build chat UI, all
> containerized and provisioned with Terraform onto Oracle Cloud's forever-free
> tier — chosen deliberately over AWS/GCP for true $0 hosting."
