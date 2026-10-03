# ERAGA — Development Roadmap & Step-by-Step Build Guide

> **E**nterprise **R**etrieval-**A**ugmented **G**eneration **A**ssistant
> Companion to [`ERAGA.md`](./ERAGA.md) (architecture) and [`ERAGA1.md`](./ERAGA1.md) (notes).
>
> **Stack philosophy: 100% free and local.** No API keys, no cloud costs. Models run on your
> machine via **Ollama**, vectors live in **PostgreSQL + pgvector**, everything else is open source.

---

## 📑 Table of Contents

- [0. Stack & Current Status](#0-stack--current-status)
- [1. Prerequisites & Setup](#1-prerequisites--setup)
- [2. Phase 0 — Project Scaffolding ✅](#2-phase-0--project-scaffolding)
- [3. Phase 1 — RAG Foundation ✅](#3-phase-1--rag-foundation)
- [4. Phase 2 — Retrieval + RAG API ✅](#4-phase-2--retrieval--rag-api)
- [5. Phase 3 — Enterprise Features (Auth, ACL, Audit)](#5-phase-3--enterprise-features)
- [6. Phase 4 — Retrieval Quality + Evaluation](#6-phase-4--retrieval-quality--evaluation)
- [7. Phase 5 — Production Engineering](#7-phase-5--production-engineering)
- [8. Phase 6 — Advanced GenAI](#8-phase-6--advanced-genai)
- [9. Phase 7 — Frontend & DevOps](#9-phase-7--frontend--devops)
- [10. Testing Strategy](#10-testing-strategy)
- [11. Continuous Commands Cheat Sheet](#11-continuous-commands-cheat-sheet)
- [12. Troubleshooting (real issues hit)](#12-troubleshooting-real-issues-hit)

---

## 0. Stack & Current Status

### The free / local stack

| Layer | Tool | Cost | Notes |
|---|---|---|---|
| Language | Python 3.11+ | Free | developed/tested on 3.13 |
| API framework | FastAPI + Uvicorn | Free | auto Swagger at `/docs` |
| LLM runtime | **Ollama** | Free | local, no API key |
| LLM model | **Qwen 2.5 3B / Llama 3.2 / Mistral** | Free | swap with one env var |
| Embeddings | **nomic-embed-text** (768-d) | Free | or `bge-m3` |
| Vector DB | **PostgreSQL 16 + pgvector** | Free | HNSW index |
| Keyword search | **rank-bm25** | Free | in-process |
| Orchestration | LangChain text-splitters + custom pipeline | Free | |
| Document parsing | PyMuPDF / python-docx / BeautifulSoup | Free | |
| Frontend | React / Next.js | Free | Phase 7 |
| Containers | Docker / docker compose | Free | |
| CI | GitHub Actions | Free | |
| API testing | Swagger UI + Postman | Free | |

### Current status

| Phase | Item | Status |
|---|---|---|
| **0** | Project scaffolding, config, health endpoints | ✅ **Done** |
| **0** | `pyproject.toml`, `.env`, `.gitignore`, tests | ✅ **Done** |
| **1** | PDF/DOCX/HTML/MD/TXT loaders, cleaner, chunker | ✅ **Done** |
| **1** | Ollama + offline hash embeddings (768-d) | ✅ **Done** |
| **1** | pgvector store, HNSW index, ACL-aware SQL search | ✅ **Done** |
| **1** | Ingest/search CLI scripts | ✅ **Done** |
| **2** | LLM client (Ollama + fake), prompt templates | ✅ **Done** |
| **2** | Hybrid retrieval (dense + BM25 + RRF) | ✅ **Done** |
| **2** | `POST /api/v1/chat/query` + citations | ✅ **Done** |
| **2** | Streaming SSE, retrieve-only, context-preview | ✅ **Done** |
| **2** | Document upload/list/delete API | ✅ **Done** |
| **3** | JWT auth, RBAC, conversation memory, feedback | ⬜ Next |
| **4** | Query rewriting, re-ranking, RAGAS eval | ⬜ Planned |
| **5** | Redis cache, Celery, Docker Compose, CI | ⬜ Planned |
| **6** | Agentic RAG (SQL/tool agents), guardrails | ⬜ Planned |
| **7** | React UI, Kubernetes, cloud deploy | ⬜ Planned |

**Verified state:** 79 tests passing · 80% coverage · `ruff` + `mypy` clean · 15 chunks ingested.

---

## 1. Prerequisites & Setup

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | python.org / pyenv |
| Git | any | git-scm.com |
| Docker Desktop | latest | docker.com |
| Ollama | latest | **ollama.com/download** (optional for offline mode) |

### 1.1 Start PostgreSQL + pgvector (Docker)

> ⚠️ Use host port **55432**, not 5432 — a locally installed PostgreSQL service often already
> owns 5432 and the container will either fail to bind or exit with code 255.

```bash
docker run -d --name eraga-pg \
  -e POSTGRES_USER=eraga \
  -e POSTGRES_PASSWORD=eraga \
  -e POSTGRES_DB=eraga \
  -p 55432:5432 \
  pgvector/pgvector:pg16
```

Verify pgvector:

```bash
docker exec eraga-pg psql -U eraga -d eraga \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" \
  -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Lifecycle:

```bash
docker stop eraga-pg      # stop
docker start eraga-pg     # start again (data persists)
docker rm -f eraga-pg     # delete container + data
```

### 1.2 Install Ollama models (recommended, ~2 GB)

```bash
ollama pull qwen2.5:3b        # LLM  (~1.9 GB) — or llama3.2 / mistral / gemma3
ollama pull nomic-embed-text  # embeddings (~275 MB)
ollama serve                  # usually already running after install
```

Then in `.env`:

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
```

**No Ollama yet?** The repo ships two offline providers so everything still runs:

| Provider | Values | Behaviour |
|---|---|---|
| `LLM_PROVIDER` | `fake` | deterministic extractive answer, instant |
| `EMBEDDING_PROVIDER` | `hash` | deterministic 768-d hashing embedder |

### 1.3 Clone, venv, install

```bash
git clone https://github.com/hipradeep/eraga.git
cd eraga

python -m venv .venv
.\.venv\Scripts\Activate.ps1          # PowerShell (Windows)
# source .venv/bin/activate            # macOS / Linux

pip install -e ".[ingest,llm,retrieval,dev]"
```

Extra sets: `ingest` (parsers), `llm` (ollama client), `retrieval` (bm25), `queue`, `security`, `eval`, `dev`, `all`.

---

## 2. Phase 0 — Project Scaffolding

**Goal:** config loading, FastAPI skeleton, health checks, first tests. **✅ Complete.**

### Files

| File | Purpose |
|---|---|
| `pyproject.toml` | deps, extras, pytest/ruff/mypy config, `[build-system]` |
| `.env.example` | committed template (Ollama + pgvector) |
| `.env` | local values (git-ignored) |
| `app/config.py` | `Settings` via pydantic-settings, cached `get_settings()` |
| `app/main.py` | lifespan, CORS, timing middleware, error handler, routers |
| `tests/conftest.py` | `client` (sync) + `async_client` fixtures |

### `pyproject.toml` — key sections

```toml
[build-system]                                   # REQUIRED, else setuptools
requires = ["setuptools>=68", "wheel"]           # auto-discovery fails on a
build-backend = "setuptools.build_meta"          # flat layout with many top-level dirs

[project]
name = "eraga"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic>=2.8",
    "pydantic-settings>=2.4", "sqlalchemy[asyncio]>=2.0", "asyncpg>=0.29",
    "alembic>=1.13", "pgvector>=0.3.6", "python-multipart>=0.0.9", "httpx>=0.27",
]

[project.optional-dependencies]
ingest    = ["pymupdf>=1.24", "python-docx>=1.1", "beautifulsoup4>=4.12",
             "langchain-text-splitters>=0.2"]
llm       = ["langchain-ollama>=0.2", "langchain-core>=0.3"]
retrieval = ["rank-bm25>=0.2.2", "langchain-postgres>=0.0.9"]
queue     = ["celery>=5.4", "redis>=5.0"]
security  = ["python-jose[cryptography]>=3.3", "passlib[bcrypt]>=1.7"]
eval      = ["ragas>=0.1"]
dev       = ["pytest>=8.3", "pytest-asyncio>=0.23", "pytest-cov>=5.0", "ruff>=0.6", "mypy>=1.11"]
all       = ["eraga[ingest,llm,retrieval,queue,security,eval,dev]"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"   # CRITICAL — see troubleshooting #6
asyncio_default_test_loop_scope = "session"
testpaths = ["tests"]
addopts = "-q --cov=app --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["docs", "data", ".venv", "alembic"]  # keep ruff out of markdown code blocks

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.ruff.lint.per-file-ignores]
"app/api/routes/*.py" = ["B008"]   # FastAPI Depends() in defaults is intentional
```

### `.env` essentials

```env
DATABASE_URL=postgresql+asyncpg://eraga:eraga@localhost:55432/eraga
OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER=fake              # -> ollama once models are pulled
LLM_MODEL=qwen2.5:3b
EMBEDDING_PROVIDER=hash        # -> ollama once models are pulled
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
ADMIN_ROLES=admin
```

### `app/config.py` — key settings

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ollama_base_url: str = "http://localhost:11434"
    llm_provider: str = "ollama"           # ollama | fake
    llm_model: str = "qwen2.5:3b"
    embedding_provider: str = "ollama"     # ollama | hash
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768               # nomic-embed-text / bge-m3 are 768-d
    database_url: str = "postgresql+asyncpg://eraga:eraga@localhost:55432/eraga"
    top_k: int = 8
    rerank_top_n: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 120
```

### Run & verify

```bash
uvicorn app.main:app --reload --port 8000
# Swagger UI -> http://localhost:8000/docs

curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/models
pytest
```

### ✅ Definition of Done

- [x] `GET /health`, `/health/db`, `/health/models` return 200
- [x] `pytest` green
- [x] `ruff check .` and `mypy app` clean

---

## 3. Phase 1 — RAG Foundation

**Goal:** file → clean → chunk → embed → pgvector → similarity search. **✅ Complete.**

### Files

| File | Purpose |
|---|---|
| `app/models/base.py` | `Base`, `TimestampMixin` |
| `app/models/document.py` | documents table + ACL roles |
| `app/models/chunk.py` | chunks + `vector(768)` + ACL roles |
| `app/models/audit.py` | `query_audits` |
| `app/ingestion/loaders.py` | PDF / DOCX / HTML / MD / TXT → `DocumentBlock` |
| `app/ingestion/cleaner.py` | normalise, de-hyphenate, drop page artefacts |
| `app/ingestion/chunker.py` | structure-aware recursive chunking |
| `app/ingestion/pipeline.py` | orchestrate + failure-safe document status |
| `app/retrieval/embeddings.py` | `OllamaEmbedder` + `HashEmbedder` |
| `app/retrieval/vector_store.py` | ACL-filtered SQL similarity search |
| `infra/schema.sql` | full DDL incl. HNSW + GIN indexes |
| `scripts/init_db.py` | apply schema, sync metadata, verify index |
| `scripts/ingest.py` / `scripts/search.py` | CLI |

### Key design decisions

**1. ACL is enforced in SQL, never in Python.** The `allowed_roles` filter is a PostgreSQL array
overlap predicate inside the retrieval query, so unauthorised chunks never leave the database:

```python
stmt = (
    select(Chunk, distance)
    .join(Document, Document.id == Chunk.document_id)
    .where(Chunk.allowed_roles.overlap(roles))      # <-- access control here
    .order_by(distance)
    .limit(top_k)
)
```

**2. Embedding dimension must match the schema.** `nomic-embed-text` and `bge-m3` are **768-d**.
The `OllamaEmbedder` raises an actionable error on mismatch instead of failing deep in Postgres:

```python
raise ValueError(
    f"embedding dimension mismatch: model '{self._model}' returned {actual}, "
    f"but schema is vector({self._dimension}). Change EMBEDDING_DIM and "
    f"ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector({actual});"
)
```

**3. `HashEmbedder` makes the whole pipeline testable offline.** Deterministic token hashing,
L2-normalised, 768-d. Lexically similar text scores higher — enough to verify retrieval, ACL and
citations with no model server.

### Schema highlights (`infra/schema.sql`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id            UUID PRIMARY KEY,
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(768),
    page_number   INTEGER,
    section       TEXT,
    char_count    INTEGER NOT NULL DEFAULT 0,
    metadata      JSONB NOT NULL DEFAULT '{}',
    allowed_roles TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_chunks_roles ON document_chunks USING gin (allowed_roles);
CREATE INDEX idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### Run & verify

```bash
python scripts/init_db.py          # apply schema, verify HNSW index
python scripts/ingest.py data/samples/leave_policy.md data/samples/deployment_policy.md \
    --department HR --roles "admin,HR"
# [OK ] leave_policy.md: 8 chunks
# [OK ] deployment_policy.md: 7 chunks

python scripts/search.py "annual leave entitlement for employees with less than 1 year" \
    --roles "admin,HR"
python scripts/search.py "leave entitlement" --roles CONTRACTOR      # -> no authorised chunks
```

### ✅ Definition of Done

- [x] `scripts/ingest.py` produces `status=ready` with chunk counts
- [x] `scripts/search.py` returns ranked chunks with section/page provenance
- [x] Unauthorised role retrieves **zero** chunks (verified in `tests/test_db.py`)

---

## 4. Phase 2 — Retrieval + RAG API

**Goal:** grounded answers with citations over HTTP. **✅ Complete.**

### Files

| File | Purpose |
|---|---|
| `app/rag/prompt_templates.py` | system prompt, numbered context, `NO_CONTEXT_ANSWER` |
| `app/rag/llm_client.py` | `OllamaLLM` (`/api/chat`) + `FakeLLM` |
| `app/rag/pipeline.py` | retrieve → generate → validate citations → audit |
| `app/retrieval/keyword_search.py` | BM25 + `reciprocal_rank_fusion` |
| `app/retrieval/hybrid_retriever.py` | dense + sparse fusion, `RetrievedChunk` |
| `app/schemas.py` | `QueryRequest/Response`, `Citation`, `DocumentResponse` |
| `app/api/routes/chat.py` | query / retrieve / stream / context-preview |
| `app/api/routes/documents.py` | upload / list / delete / reindex |

### The pipeline

```
question
   │
   ├─ embed_query()  ──► pgvector cosine search (ACL in SQL) ─┐
   │                                                          ├─ RRF fusion ─► top_n
   └─ BM25 over the same ACL-filtered candidates ────────────┘
                                                               │
                    Ollama LLM (grounded prompt) ◄─────────────┘
                               │
                    citation validation → audit row → response
```

### Guardrails that are actually implemented

| Guardrail | Behaviour |
|---|---|
| **No-context refusal** | zero chunks → the exact string `I don't have enough information to answer this.` |
| **Fabricated citation rejection** | markers like `[7]` with only 3 sources → answer replaced with the refusal |
| **Grounding flag** | `grounded: bool` in every response |
| **Heuristic confidence** | retrieval score × citation usage, 0 when refusing |
| **Audit trail** | every query logged; audit failure never breaks the user's answer |

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/chat/query` | grounded answer + citations |
| POST | `/api/v1/chat/retrieve` | raw chunks + dense/keyword/fused scores (tuning) |
| POST | `/api/v1/chat/stream` | SSE: `answer` tokens → `citations` → `done` |
| GET | `/api/v1/chat/context-preview` | exact prompt context (debug grounding) |
| GET | `/api/v1/documents` | list (ACL-scoped) |
| POST | `/api/v1/documents` | upload + ingest (multipart) |
| DELETE | `/api/v1/documents/{id}` | delete doc + chunks |

### Role header — and the trap that bit us

Roles currently come from an `X-Roles` header (Phase 3 replaces it with JWT). FastAPI derives the
parameter name from the function argument, so `x_roles: str | None` looks for a header literally
named `x_roles` — **not** `X-Roles`. Without an explicit alias the header is silently ignored and
every request defaults to `admin`:

```python
RolesHeader = Annotated[str | None, Header(alias="X-Roles")]
```

### Run & verify

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
# authorised
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" -H "X-Roles: admin,HR" \
  -d '{"question":"What is the leave entitlement for less than 1 year of service?","top_k":4}'

# denied -> grounded:false, citations:[], refusal answer
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" -H "X-Roles: CONTRACTOR" \
  -d '{"question":"leave entitlement"}'
```

### ✅ Definition of Done

- [x] `POST /api/v1/chat/query` returns answer + citations
- [x] Insufficient context triggers the exact refusal
- [x] SSE emits `answer` → `citations` → `done`
- [x] Upload ingests a document and scopes it to roles
- [x] ACL verified end-to-end over HTTP (`CONTRACTOR` gets nothing)

---

## 5. Phase 3 — Enterprise Features

**Goal:** replace the trusted header with real auth; add conversations, feedback. **⬜ Next.**

### Work items

1. **JWT auth** — `app/security/auth.py` using `python-jose` + `passlib[bcrypt]`
   (`create_access_token`, `decode_access_token`), `POST /api/v1/auth/token`.
2. **RBAC dependency** — `app/security/rbac.py` `current_user()` → replace `RolesHeader`.
3. **Chunk-level ACL** — already enforced in SQL; now source roles from verified claims.
4. **Login flow** — `app/models/user.py` (`users`, `roles`, `user_roles`); seed an admin.
5. **Conversation memory** — `app/models/conversation.py`; summarise old turns, keep recent verbatim.
6. **Feedback** — `POST /api/v1/feedback`, `feedback` table → feeds the Phase 4 eval set.

### Tests to add

```python
def test_query_without_token_is_401(client): ...
def test_token_with_wrong_role_cannot_read_hr_chunk(client): ...   # the critical one
def test_expired_token_is_401(client): ...
def test_feedback_persists(client): ...
```

### ✅ Definition of Done

- [ ] `/api/v1/chat/*` requires a valid JWT
- [ ] A token whose roles exclude `HR` provably cannot retrieve HR chunks
- [ ] Every query writes an audit row with the real user id
- [ ] Feedback endpoint persists and is queryable

---

## 6. Phase 4 — Retrieval Quality + Evaluation

**Goal:** measurable quality with free local tooling. **⬜ Planned.**

### Golden dataset first

`eval_data/golden.jsonl` — 30–50 hand-verified Q/A pairs. This is the single most valuable asset
in the repo; build it **before** tuning anything.

```json
{"question": "What is the leave entitlement for employees with < 1 year service?", "ground_truth": "15 days pro-rated", "department": "HR", "required_roles": ["HR"]}
```

### Local evaluation without API keys

RAGAS normally calls an LLM; point it at Ollama by wrapping the local client as the evaluator LLM,
or use the lighter-weight local metrics:

| Metric | How |
|---|---|
| **Hit rate@k** | golden chunk/doc appears in top-k (no LLM needed) |
| **MRR** | mean reciprocal rank of the golden chunk |
| **Citation accuracy** | cited section == golden source section |
| **Faithfulness** | RAGAS + Ollama judge |
| **Answer relevance** | RAGAS + Ollama judge |
| **Latency P50/P95** | wall-clock around `hybrid_retrieve` / full answer |

### Query rewriting & re-ranking (free options)

- **Rewrite** with the local LLM (`qwen2.5:3b`) — expand acronyms, add synonyms.
- **Re-rank** with a local cross-encoder (`BAAI/bge-reranker-base` via `sentence-transformers`)
  — no Cohere key needed.

### Experiment ledger

| Change | Hit@5 | MRR | Faithfulness | P95 ms |
|---|---|---|---|---|
| baseline (dense only) | | | | |
| + BM25 hybrid | | | | |
| + cross-encoder rerank | | | | |
| + query rewrite | | | | |

> Never merge a retrieval change without before/after numbers in the PR description.

### ✅ Definition of Done

- [ ] `eval_data/golden.jsonl` ≥ 30 items
- [ ] `python -m app.evaluation.runner` prints a metrics table using local models
- [ ] ≥ 3 documented experiments with measured deltas

---

## 7. Phase 5 — Production Engineering

**Goal:** caching, async ingestion, containers, CI, observability. **⬜ Planned.**

- **Redis cache** — identical question → cached answer; embedding cache keyed by text hash.
- **Celery worker** (`workers/ingestion_worker.py`) — bulk ingestion off the request path.
- **Docker** — multi-stage image, `docker compose` with `api` + `worker` + `postgres` + `redis`
  + optional `ollama` service.
- **Observability** — Prometheus `/metrics`, OpenTelemetry spans for `retrieve`/`rerank`/`llm`,
  Grafana panels for latency P50/P95 and cost.
- **CI** (`.github/workflows/ci.yml`) — ruff + mypy + pytest against a `pgvector/pgvector:pg16`
  service container; coverage gate ≥ 70%.

### ✅ Definition of Done

- [ ] `docker compose up` yields a healthy API locally
- [ ] 2nd identical question served from cache (< 200 ms)
- [ ] Celery ingests a 50-page PDF without blocking the API
- [ ] CI green on every PR

---

## 8. Phase 6 — Advanced GenAI

**Goal:** agentic RAG and guardrails, still free. **⬜ Planned.**

- **Query router** — classify `policy | howto | analytics | general` via the local LLM.
- **SQL agent** — read-only role, table allow-list, mandatory `LIMIT`; never emit DDL/DML.
- **Guardrails** — input prompt-injection checks, output citation validation (already seeded in
  `app/rag/pipeline.py`), PII masking.
- **Local multi-model** — route easy queries to `qwen2.5:3b`, hard ones to a 7B/14B model.

### ✅ Definition of Done

- [ ] Router picks the right tool ≥ 90% of golden questions
- [ ] Fabricated-citation and cross-tenant tests pass
- [ ] Cost dashboard exists (local = compute time, not USD)

---

## 9. Phase 7 — Frontend & DevOps

**Goal:** chat UI + deployment. **⬜ Planned.**

- **Next.js chat UI** — streaming answers, clickable citations, role-aware.
- **Admin panel** — upload docs, set `allowed_roles`, see ingestion status.
- **Kubernetes** — `infra/k8s/deployment.yaml` + `service.yaml` + HPA.
- **Release pipeline** — PR (lint/types/tests/eval) → build image → staging smoke test →
  manual approval → prod canary.

### ✅ Definition of Done

- [ ] Chat UI streams answers with clickable citations
- [ ] Admin can upload a PDF and restrict roles
- [ ] HPA scales under a 50 RPS load test

---

## 10. Testing Strategy

| Layer | What | Needs services? |
|---|---|---|
| Unit | cleaner, chunker, RRF, ACL logic, citations, prompts | No |
| Embeddings | determinism, dimension, similarity ordering | No |
| Integration | ingestion, pgvector search, ACL in SQL, audit | Postgres |
| Contract | endpoint status/shape, SSE events, upload validation | Postgres |
| Evaluation | golden set metrics | Postgres + Ollama |
| E2E/load | UI → API, 50 RPS | full stack |

```bash
pytest                                    # everything
pytest tests/test_ingestion.py -v          # one file
pytest -k "acl or citation" -v             # by keyword
pytest --cov=app --cov-report=html         # coverage report -> htmlcov/index.html
```

DB tests **skip automatically** if PostgreSQL is unreachable, so `pytest` still works without Docker.

---

## 11. Continuous Commands Cheat Sheet

```bash
# ---- environment ----
.\.venv\Scripts\Activate.ps1
pip install -e ".[ingest,llm,retrieval,dev]"

# ---- infrastructure ----
docker start eraga-pg                       # PostgreSQL + pgvector on :55432
ollama serve                                # local models on :11434
python scripts/init_db.py                   # apply schema

# ---- data ----
python scripts/ingest.py data/samples/*.md --department HR --roles "admin,HR"
python scripts/search.py "leave policy" --roles admin,HR
python scripts/search.py "leave policy" --roles admin,HR --answer

# ---- run ----
uvicorn app.main:app --reload --port 8000

# ---- quality ----
pytest
ruff check . && ruff format .
mypy app

# ---- git ----
git add -A
git commit -m "feat(phase-1): add ingestion, embeddings and pgvector retrieval"
```

---

## 12. Troubleshooting (real issues hit)

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | Docker container **exited 255**, no error | local PostgreSQL already owns `:5432` | publish on `55432` instead: `-p 55432:5432` |
| 2 | `password authentication failed for user "eraga"` | app talking to the *wrong* Postgres on 5432 | point `DATABASE_URL` at `:55432` |
| 3 | `cannot insert multiple commands into a prepared statement` | asyncpg rejects multi-statement SQL | split `schema.sql` and execute one statement at a time (`scripts/init_db.py`) |
| 4 | `cannot import name 'TEXT_ARRAY'` | that type does not exist in SQLAlchemy | use `postgresql.ARRAY(Text)` |
| 5 | `dimension mismatch`, expected 768 got 1536 | model vs `embedding_dim` | set `EMBEDDING_DIM=768`; `ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768);` and re-embed |
| 6 | `RuntimeError: Event loop is closed` in DB tests | pytest-asyncio gives fixtures/tests different loops; asyncpg pool reused across loops | set `asyncio_default_fixture_loop_scope = "session"` + `asyncio_default_test_loop_scope = "session"` |
| 7 | DB tests deadlock when using `TestClient` | sync client runs the app on its own loop | use the `async_client` (httpx `ASGITransport`) fixture for DB tests |
| 8 | `X-Roles` header silently ignored, everyone is admin | FastAPI maps header name from the param name (`x_roles`) | `Annotated[str \| None, Header(alias="X-Roles")]` |
| 9 | `Invalid args for response field` on `dict \| JSONResponse` | FastAPI tries to build a response model | add `response_model=None` to the route |
| 10 | ruff reformats Python inside `docs/*.md` code blocks | ruff scans markdown | `extend-exclude = ["docs", "data", ".venv", "alembic"]` |
| 11 | `Multiple top-level packages discovered in flat layout` | missing `[build-system]` | add `[build-system]` + `[tool.setuptools.packages.find] include = ["app*", "workers*"]` |
| 12 | `ZeroDivisionError` in `rank_bm25` | empty corpus | guard: `BM25Okapi(corpus) if corpus else None` |
| 13 | `no text extracted` on an empty file | loader returned a block with empty text | filter blank blocks and raise a clear `ValueError` |
| 14 | `B008` lint errors in every route file | `Depends(...)` in defaults is required by FastAPI | per-file ignore for `app/api/routes/*.py` |
| 15 | Ollama `model not pulled` | model missing locally | `ollama pull <model>`; check `/health/models` |
| 16 | HNSW index build very slow | index built before bulk load | create index **after** bulk ingestion |
| 17 | PowerShell blocks venv activation | execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## 📌 Related Documents

- [`ERAGA.md`](./ERAGA.md) — full architecture, DB design, security model, resume blurb
- [`ERAGA1.md`](./ERAGA1.md) — research notes and references
- [`../README.md`](../README.md) — project overview and feature list

---

<div align="center">

**ERAGA — Development Roadmap**

*Free stack · local models · grounded answers.*

</div>