# ERAGA — Development Roadmap & Step-by-Step Build Guide

> **E**nterprise **R**etrieval-**A**ugmented **G**eneration **A**ssistant
> Companion to [`ERAGA.md`](./ERAGA.md) (architecture) and [`ERAGA1.md`](./ERAGA1.md) (notes).
> This document is the **executable** version: every phase lists the exact files to create, the
> commands to run, and the tests to prove the phase works.

---

## 📑 Table of Contents

- [0. Current Status](#0-current-status)
- [1. Prerequisites & Toolchain](#1-prerequisites--toolchain)
- [2. Phase 0 — Project Scaffolding](#2-phase-0--project-scaffolding)
- [3. Phase 1 — RAG Foundation (Ingestion + Embeddings)](#3-phase-1--rag-foundation)
- [4. Phase 2 — Retrieval + RAG API](#4-phase-2--retrieval--rag-api)
- [5. Phase 3 — Enterprise Features (Auth, ACL, Audit)](#5-phase-3--enterprise-features)
- [6. Phase 4 — Retrieval Quality + Evaluation](#6-phase-4--retrieval-quality--evaluation)
- [7. Phase 5 — Production Engineering](#7-phase-5--production-engineering)
- [8. Phase 6 — Advanced GenAI (Agentic RAG)](#8-phase-6--advanced-genai)
- [9. Phase 7 — Frontend & DevOps](#9-phase-7--frontend--devops)
- [10. Definition of Done (per phase)](#10-definition-of-done)
- [11. Continuous Commands Cheat Sheet](#11-continuous-commands-cheat-sheet)
- [12. Troubleshooting](#12-troubleshooting)

---

## 0. Current Status

| Item | Status |
|---|---|
| Repo initialised + docs written | ✅ Done |
| `app/main.py` FastAPI app with `GET /welcome` | ✅ Done |
| Virtualenv / dependencies file | ⬜ Not started |
| `pyproject.toml` | ⬜ Not started |
| Database schema | ⬜ Not started |
| Tests | ⬜ Not started |
| Docker / CI | ⬜ Not started |

**Next action →** complete [Phase 0](#2-phase-0--project-scaffolding).

---

## 1. Prerequisites & Toolchain

| Tool | Version | Why |
|---|---|---|
| Python | 3.11+ (3.13 works) | Async, modern typing |
| Git | any | Version control |
| PostgreSQL | 15+ with **pgvector** | Metadata + vectors in one DB |
| Docker Desktop | latest | Postgres/Redis without local install |
| uv *or* pip | latest | Dependency management |
| An LLM API key | Gemini / OpenAI / Anthropic | Generation step |

### 1.1 Verify the toolchain

```bash
python --version          # expect 3.11+
git --version
docker --version
uv --version              # optional but recommended
```

### 1.2 Bring up PostgreSQL + pgvector with Docker

```bash
docker run -d --name eraga-pg `
  -e POSTGRES_USER=eraga `
  -e POSTGRES_PASSWORD=eraga `
  -e POSTGRES_DB=eraga `
  -p 5432:5432 `
  -pgvector/pgvector:pg16
```

Verify the extension is available:

```bash
docker exec -it eraga-pg psql -U eraga -d eraga -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"
```

> If `docker` is unavailable, install PostgreSQL locally and run
> `CREATE EXTENSION vector;` after installing the pgvector package.

### 1.3 Environment variables

```bash
# PowerShell (Windows)
$env:DATABASE_URL = "postgresql+asyncpg://eraga:eraga@localhost:5432/eraga"
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "<your-key>"
$env:EMBEDDING_PROVIDER = "openai"
$env:OPENAI_API_KEY = "<your-key>"
$env:ADMIN_ROLES = "admin,HR,LEGAL,ENGINEERING"
```

> **Tip:** after Phase 0 you will copy these into `.env` (git-ignored) and
> `.env.example` (committed).

---

## 2. Phase 0 — Project Scaffolding

**Goal:** reproducible dev environment, config loading, app skeleton, health endpoint, first tests.

**Estimated time:** half a day.

### Step 0.1 — Create the virtual environment

```bash
cd eraga
python -m venv .venv
```

Activate:

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

### Step 0.2 — Create `pyproject.toml`

```toml
[project]
name = "eraga"
version = "0.1.0"
description = "Enterprise RAG Assistant"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pgvector>=0.3.6",
    "python-multipart>=0.0.9",
    "httpx>=0.27",
]

[project.optional-dependencies]
ingest = [
    "pymupdf>=1.24",       # PDF
    "python-docx>=1.1",    # DOCX
    "beautifulsoup4>=4.12",# HTML
    "unstructured>=0.15",  # fallback parser
    "langchain>=0.2",
    "langchain-community>=0.2",
    "langchain-text-splitters>=0.2",
]
llm = [
    "langchain-google-genai>=2.0",
    "langchain-openai>=0.2",
    "tiktoken>=0.7",
]
retrieval = [
    "rank-bm25>=0.2.2",
    "langchain-cohere>=0.2",
    "sentence-transformers>=3.0",
]
queue = ["celery>=5.4", "redis>=5.0"]
security = ["python-jose[cryptography]>=3.3", "passlib[bcrypt]>=1.7", "python-multipart"]
eval = ["ragas>=0.1", "datasets>=2.20"]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.11",
]
all = [
    "eraga[ingest,llm,retrieval,queue,security,eval,dev]",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-q --cov=app --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
```

### Step 0.3 — Install dependencies

```bash
pip install -e ".[all]"
# or with uv
uv pip install -e ".[all]"
```

### Step 0.4 — Add `.env.example` and `.gitignore`

```bash
# .env.example  ->  commit this
DATABASE_URL=postgresql+asyncpg://eraga:eraga@localhost:5432/eraga
LLM_PROVIDER=gemini
GEMINI_API_KEY=
OPENAI_API_KEY=
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
COHERE_API_KEY=
REDIS_URL=redis://localhost:6379/0
ADMIN_ROLES=admin
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

```gitignore
# .gitignore
.venv/
__pycache__/
*.py[cod]
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
data/
```

### Step 0.5 — Create `app/config.py`

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ERAGA"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://eraga:eraga@localhost:5432/eraga"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    cohere_api_key: str = ""

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    top_k: int = 8
    rerank_top_n: int = 5
    admin_roles: str = "admin"

    @property
    def admin_role_list(self) -> list[str]:
        return [r.strip() for r in self.admin_roles.split(",") if r.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Step 0.6 — Create the package skeleton

```bash
mkdir app
mkdir app\api app\api\routes app\ingestion app\retrieval app\rag
mkdir app\security app\models app\evaluation app\core
mkdir workers tests infra\infra\k8s eval_data data\samples
```

Empty `__init__.py` in every folder:

```powershell
Get-ChildItem -Recurse -Directory app, tests | ForEach-Object { New-Item -Item "$($_.FullName)\__init__.py" -Force }
```

### Step 0.7 — Upgrade `app/main.py`

```python
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("eraga")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ERAGA starting in %s mode", settings.environment)
    yield
    logger.info("ERAGA shutting down")


app = FastAPI(
    title="ERAGA — Enterprise RAG Assistant",
    description="Production-grade Retrieval-Augmented Generation platform for enterprises.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    return response


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok", "version": "0.1.0", "environment": settings.environment}


@app.get("/welcome", tags=["ops"])
def welcome():
    return {
        "message": "Welcome to ERAGA — Enterprise RAG Assistant 🧠",
        "version": "0.1.0",
        "status": "running",
    }
```

### Step 0.8 — Run the app

```bash
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> (Swagger) and <http://localhost:8000/health>.

### Step 0.9 — Write the first tests

`tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
```

`tests/test_api.py`:

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_welcome(client):
    r = client.get("/welcome")
    assert r.status_code == 200
    assert "ERAGA" in r.json()["message"]


def test_openapi(client):
    assert client.get("/openapi.json").status_code == 200
```

### Step 0.10 — Verify & commit

```bash
pytest -v
ruff check .
ruff format .
mypy app
git add -A
git commit -m "chore: scaffold project with config, app skeleton and first tests"
```

### ✅ Phase 0 Definition of Done

- [ ] `.venv` created and `.env`/`.env.example` present
- [ ] `pyproject.toml` installs with `pip install -e ".[all]"`
- [ ] `GET /health` returns 200
- [ ] `pytest` green
- [ ] `ruff check .` and `mypy app` clean

---

## 3. Phase 1 — RAG Foundation

**Goal:** ingest real documents → clean → chunk → embed → store in pgvector → similarity search works.

**Estimated time:** 1 week.

### Step 1.1 — Database schema

Create `app/models/base.py` (SQLAlchemy declarative base), then
`app/models/document.py` and `app/models/chunk.py`:

```python
# app/models/chunk.py
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TEXT_ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Chunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536))
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_ = mapped_column("metadata", JSONB, default=dict)
    allowed_roles = mapped_column(TEXT_ARRAY, default=list)
```

`app/models/document.py`:

```python
class Document(Base):
    __tablename__ = "documents"

    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512))
    doc_type: Mapped[str] = mapped_column(String(32))          # pdf | docx | html | txt
    source_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), default="INTERNAL")
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allowed_roles = mapped_column(TEXT_ARRAY, default=list)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Apply the schema. Two options — pick one:

**Option A — Alembic (recommended for real projects)**

```bash
alembic init alembic
# edit alembic/env.py to read settings.database_url (replace +asyncpg with +psycopg)
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**Option B — raw SQL for the first iteration**

Save `infra/schema.sql` (copy the DDL from [`ERAGA.md` § Database Design](./ERAGA.md#-database-design-postgresql--pgvector)) and run:

```bash
psql -U eraga -d eraga -f infra\schema.sql
```

Create the vector index **after** bulk loading (HNSW/IVFFlat build is slow on tiny data):

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
  ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### Step 1.2 — DB engine + session (`app/core/database.py`, `app/dependencies.py`)

```python
# app/core/database.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

Add a connectivity test endpoint and run it:

```python
from sqlalchemy import text

@app.get("/health/db", tags=["ops"])
async def health_db():
    async with engine.connect() as conn:
        version = (await conn.execute(text("SELECT version()"))).scalar_one()
    return {"status": "ok", "postgres": version.split(",")[0]}
```

```bash
pytest tests/test_db.py -v      # test that SELECT 1 works
```

### Step 1.3 — Document loaders (`app/ingestion/loaders.py`)

```python
from pathlib import Path
from typing import Protocol


class DocumentBlock(Protocol):
    text: str
    page_number: int | None
    section: str | None


def load_pdf(path: str | Path) -> list[DocumentBlock]:
    import fitz  # PyMuPDF

    blocks = []
    with fitz.open(path) as doc:
        for page_no, page in enumerate(doc, start=1):
            blocks.append(DocumentBlock(text=page.get_text(), page_number=page_no, section=None))
    return blocks


def load_docx(path: str | Path) -> list[DocumentBlock]:
    import docx

    document = docx.Document(path)
    return [DocumentBlock(text=p.text, page_number=None, section=None) for p in document.paragraphs if p.text.strip()]


def load_html(path: str | Path) -> list[DocumentBlock]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    return [DocumentBlock(text=soup.get_text("\n"), page_number=None, section=None)]


def load_txt(path: str | Path) -> list[DocumentBlock]:
    return [DocumentBlock(text=Path(path).read_text(encoding="utf-8"), page_number=None, section=None)]


LOADERS = {"pdf": load_pdf, "docx": load_docx, "html": load_html, "txt": load_txt}


def load(path: str | Path, doc_type: str | None = None) -> list[DocumentBlock]:
    doc_type = doc_type or Path(path).suffix.lstrip(".").lower()
    return LOADERS[doc_type](path)
```

### Step 1.4 — Cleaner (`app/ingestion/cleaner.py`)

```python
import re

_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\u00a0", " ")
    text = _WS.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()
```

### Step 1.5 — Structure-aware chunker (`app/ingestion/chunker.py`)

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS = [("#", "# 1"), ("##", "# 2"), ("###", "# 3")]


def chunk_blocks(blocks, chunk_size: int = 900, chunk_overlap: int = 120) -> list[dict]:
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks: list[dict] = []
    for block in blocks:
        for section_doc in md_splitter.split_text(block.text):
            header = (section_doc.metadata or {}).get("Header 1") or ""
            for piece in char_splitter.split_text(section_doc.page_content):
                chunks.append(
                    {
                        "content": piece,
                        "page_number": block.page_number,
                        "section": header or None,
                    }
                )
    return chunks
```

### Step 1.6 — Embeddings (`app/retrieval/embeddings.py`)

```python
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_embeddings():
    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await get_embeddings().aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await get_embeddings().aembed_query(text)
```

> **No API key?** Use the HuggingFace fallback above — fully offline, 768-dim, so set
> `embedding_model` and the `Vector(...)` dimension to `768` accordingly.

### Step 1.7 — Vector store (`app/retrieval/vector_store.py`)

```python
import uuid

from sqlalchemy import select

from app.models.chunk import Chunk


async def add_chunks(session, document_id: uuid.UUID, chunks: list[dict], embeddings: list[list[float]], allowed_roles: list[str]) -> None:
    rows = [
        Chunk(
            document_id=document_id,
            chunk_index=i,
            content=c["content"],
            page_number=c.get("page_number"),
            section=c.get("section"),
            metadata_=c.get("metadata", {}),
            allowed_roles=allowed_roles,
            embedding=emb,
        )
        for i, (c, emb) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    session.add_all(rows)
    await session.commit()


async def similarity_search(session, vector: list[float], top_k: int = 8, roles: list[str] | None = None) -> list[Chunk]:
    stmt = select(Chunk).order_by(Chunk.embedding.l2_distance(vector)).limit(top_k)
    if roles is not None:                       # ACL enforced in SQL, not in Python
        stmt = stmt.where(Chunk.allowed_roles.overlap(roles))
    result = await session.execute(stmt)
    return list(result.scalars())
```

### Step 1.8 — Ingestion orchestrator (`app/ingestion/pipeline.py`)

```python
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.chunker import chunk_blocks
from app.ingestion.cleaner import clean
from app.ingestion.loaders import load
from app.models.document import Document
from app.retrieval.embeddings import embed_texts
from app.retrieval.vector_store import add_chunks

settings = get_settings()


async def ingest_file(
    session: AsyncSession,
    path: str | Path,
    department: str | None = None,
    allowed_roles: list[str] | None = None,
) -> Document:
    path = Path(path)
    blocks = load(path)
    cleaned = [type(b)(text=clean(b.text), page_number=b.page_number, section=b.section) for b in blocks]
    chunks = chunk_blocks(cleaned)

    doc = Document(
        name=path.name,
        doc_type=path.suffix.lstrip(".").lower(),
        department=department,
        allowed_roles=allowed_roles or settings.admin_role_list,
        status="processing",
    )
    session.add(doc)
    await session.flush()

    embeddings = await embed_texts([c["content"] for c in chunks])
    await add_chunks(session, doc.id, chunks, embeddings, doc.allowed_roles)

    doc.status = "ready"
    await session.commit()
    return doc
```

### Step 1.9 — CLI to ingest + query (fast feedback loop)

```python
# scripts/ingest.py
import asyncio
import sys

from app.core.database import SessionLocal
from app.ingestion.pipeline import ingest_file


async def main(paths: list[str]) -> None:
    async with SessionLocal() as session:
        for p in paths:
            doc = await ingest_file(session, p, allowed_roles=["admin", "HR"])
            print(f"ingested {doc.name} status={doc.status}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
```

```bash
python scripts\ingest.py data\samples\leave_policy.pdf data\samples\deployment_policy.pdf
```

```python
# scripts/search.py
import asyncio
import sys

from app.core.database import SessionLocal
from app.retrieval.embeddings import embed_query
from app.retrieval.vector_store import similarity_search


async def main(query: str) -> None:
    async with SessionLocal() as session:
        vec = await embed_query(query)
        for chunk in await similarity_search(session, vec, top_k=5, roles=["admin"]):
            print(f"[{chunk.section or '-'}] p{chunk.page_number}: {chunk.content[:160]}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:])))
```

```bash
python scripts\search.py "leave policy for new joiners"
```

### Step 1.10 — Tests for Phase 1

```python
# tests/test_ingestion.py
from app.ingestion.cleaner import clean
from app.ingestion.chunker import chunk_blocks


class B:
    def __init__(self, text, page_number=None, section=None):
        self.text, self.page_number, self.section = text, page_number, section


def test_clean_collapses_whitespace():
    assert clean("a   b\n\n\n\nc") == "a b\n\nc"


def test_chunker_respects_chunk_size():
    text = "# Leave Policy\n\n" + ("Employees accrue 2 days per month. " * 300)
    chunks = chunk_blocks([B(text, page_number=1)])
    assert len(chunks) > 1
    assert all(len(c["content"]) <= 900 for c in chunks)
    assert chunks[0]["section"] == "Leave Policy"
```

```python
# tests/test_retrieval_db.py  (requires DB)
import pytest

from app.core.database import SessionLocal
from app.retrieval.embeddings import embed_query
from app.retrieval.vector_store import similarity_search


@pytest.mark.asyncio
async def test_similarity_search_returns_authorized_only():
    async with SessionLocal() as session:
        vec = await embed_query("leave policy")
        hits = await similarity_search(session, vec, top_k=5, roles=["admin"])
        assert all("admin" in h.allowed_roles for h in hits)
```

```bash
pytest tests/test_ingestion.py -v        # offline, no DB
pytest tests/test_retrieval_db.py -v     # needs Postgres
```

### Step 1.11 — Commit

```bash
git add -A
git commit -m "feat(ingestion): pdf/docx/html loaders, cleaning, chunking, embeddings, pgvector store"
```

### ✅ Phase 1 Definition of Done

- [ ] `python scripts/ingest.py data/samples/*.pdf` produces `status=ready`
- [ ] `python scripts/search.py "..."` returns ranked chunks with section/page
- [ ] ACL filter is applied inside the SQL query
- [ ] `pytest` green

---

## 4. Phase 2 — Retrieval + RAG API

**Goal:** expose `POST /api/v1/chat/query` returning a grounded answer with citations.

**Estimated time:** 1 week.

### Step 2.1 — LLM client (`app/rag/llm_client.py`)

```python
from app.config import get_settings

settings = get_settings()


def get_llm():
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=settings.gemini_api_key, temperature=0)
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key, temperature=0)
```

### Step 2.2 — Prompts (`app/rag/prompt_templates.py`)

```python
SYSTEM_PROMPT = """You are an enterprise knowledge assistant.
Rules:
1. Answer ONLY from the supplied CONTEXT.
2. Never invent, extrapolate, or use prior knowledge.
3. Cite the document title and section for every claim.
4. If the context is insufficient, reply exactly:
   "I don't have enough information to answer this."
"""

USER_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{question}

ANSWER (with inline citations like [1], [2]):"""


def format_context(chunks: list) -> str:
    return "\n\n".join(
        f"[{i}] Source: {c.section or 'unknown'} | page {c.page_number}\n{c.content}"
        for i, c in enumerate(chunks, start=1)
    )


def build_prompt(question: str, chunks: list) -> str:
    return USER_TEMPLATE.format(context=format_context(chunks), question=question)
```

### Step 2.3 — Context builder + pipeline (`app/rag/context_builder.py`, `app/rag/pipeline.py`)

```python
from app.config import get_settings
from app.rag.llm_client import get_llm
from app.rag.prompt_templates import SYSTEM_PROMPT, build_prompt

settings = get_settings()


async def answer(question: str, chunks: list) -> tuple[str, float]:
    llm = get_llm()
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", build_prompt(question, chunks)),
    ]
    result = await llm.ainvoke(messages)
    text = result.content if isinstance(result.content, str) else str(result.content)
    usage = getattr(result, "usage_metadata", {}) or {}
    cost = estimate_cost(usage)
    return text, cost


def estimate_cost(usage: dict) -> float:
    # update numbers to match current provider pricing
    return (usage.get("input_tokens", 0) / 1_000_000) * 0.15 + (usage.get("output_tokens", 0) / 1_000_000) * 0.60
```

### Step 2.4 — Schemas (`app/schemas.py`)

```python
from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str
    document_title: str | None = None
    section: str | None = None
    page_number: int | None = None
    score: float | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=50)


class RAGResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    confidence: float
    latency_ms: int
    cost_usd: float = 0.0
```

### Step 2.5 — Hybrid retrieval (`app/retrieval/keyword_search.py`, `hybrid_retriever.py`)

```python
# keyword_search.py
from rank_bm25 import BM25Okapi

_TOKEN = __import__("re").compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.content) for c in chunks])

    def search(self, query: str, top_k: int = 8) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, float(s)) for i, s in ranked[:top_k] if s > 0]
```

```python
# hybrid_retriever.py
def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1 / (k + rank)
    return scores


async def hybrid_retrieve(session, question: str, roles: list[str], top_k: int = 8, top_n: int = 5):
    vec = await embed_query(question)
    vector_hits = await similarity_search(session, vec, top_k=top_k * 2, roles=roles)
    idx = BM25Index(vector_hits)
    keyword_ids = [vector_hits[i] for i, _ in idx.search(question, top_k=top_k)]

    fused = reciprocal_rank_fusion([list(range(len(vector_hits))), [vector_hits.index(c) for c in keyword_ids]])
    ordered = [vector_hits[i] for i, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)]
    return ordered[:top_n]
```

### Step 2.6 — Routes (`app/api/routes/chat.py`)

```python
import time
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.rag.pipeline import answer
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.schemas import Citation, QueryRequest, RAGResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/query", response_model=RAGResponse)
async def query(req: QueryRequest, session: AsyncSession = Depends(get_db)):
    started = time.perf_counter()
    chunks = await hybrid_retrieve(session, req.question, roles=["admin"], top_k=req.top_k)
    text, cost = await answer(req.question, chunks) if chunks else ("I don't have enough information to answer this.", 0.0)
    citations = [
        Citation(chunk_id=str(c.id), section=c.section, page_number=c.page_number) for c in chunks
    ]
    return RAGResponse(
        answer=text,
        citations=citations,
        confidence=min(1.0, len(chunks) / 5),
        latency_ms=int((time.perf_counter() - started) * 1000),
        cost_usd=cost,
    )
```

Register in `app/main.py`:

```python
from app.api.routes import chat

app.include_router(chat.router, prefix="/api")
```

### Step 2.7 — Streaming

```python
@router.post("/query/stream")
async def query_stream(req: QueryRequest, session: AsyncSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse

    async def gen():
        chunks = await hybrid_retrieve(session, req.question, roles=["admin"])
        async for token in stream_answer(req.question, chunks):
            yield token

    return StreamingResponse(gen(), media_type="text/event-stream")
```

### Step 2.8 — Tests

```python
# tests/test_rag_pipeline.py
def test_prompt_contains_citations_marker():
    from app.rag.prompt_templates import build_prompt

    class C:
        content = "Policy text"
        section = "3.2"
        page_number = 5

    p = build_prompt("How much leave?", [C()])
    assert "Policy text" in p and "[1]" in p and "How much leave?" in p


def test_rrf_orders_by_combined_score():
    from app.retrieval.hybrid_retriever import reciprocal_rank_fusion

    fused = reciprocal_rank_fusion([[0, 1, 2], [2, 0, 1]])
    assert max(fused, key=fused.get) in (0, 1, 2)  # sanity, no crash
    assert fused[0] > 0
```

```bash
pytest -v
pytest --cov=app --cov-report=html   # then open htmlcov\index.html
```

### ✅ Phase 2 Definition of Done

- [ ] `POST /api/v1/chat/query` returns answer + citations
- [ ] Insufficient context triggers the "no information" fallback
- [ ] Streaming endpoint emits tokens
- [ ] `pytest --cov` green

---

## 5. Phase 3 — Enterprise Features

**Goal:** JWT auth, RBAC, chunk-level ACL, conversations, audit logs, feedback.

**Estimated time:** 1 week.

### Step 3.1 — Auth models + password hashing

- `app/models/user.py` → `users`, `roles`, `user_roles`
- `app/security/auth.py` → `hash_password`, `verify_password` (bcrypt via passlib),
  `create_access_token`, `decode_access_token` (python-jose)

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

ALGORITHM = "HS256"
SECRET = "change-me"
ACCESS_TTL = timedelta(minutes=30)


def create_access_token(subject: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "roles": roles, "iat": now, "exp": now + ACCESS_TTL},
        SECRET,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
```

### Step 3.2 — RBAC dependency (`app/security/rbac.py`, `app/security/acl_filter.py`)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.auth import decode_access_token

bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return decode_access_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad token")


def is_authorized(chunk, user_roles: list[str]) -> bool:
    return bool(set(chunk.allowed_roles) & set(user_roles))
```

### Step 3.3 — Wire roles into the query route

```python
@router.post("/query", response_model=RAGResponse)
async def query(req: QueryRequest, user: dict = Depends(current_user), session=Depends(get_db)):
    chunks = await hybrid_retrieve(session, req.question, roles=user["roles"])
    ...
```

**Security test (must exist):**

```python
# tests/test_acl.py
class C:
    allowed_roles = ["HR"]


def test_acl_blocks_unauthorized():
    from app.security.acl_filter import is_authorized

    assert is_authorized(C(), ["HR"]) is True
    assert is_authorized(C(), ["ENGINEERING"]) is False


def test_acl_empty_roles_denied():
    from app.security.acl_filter import is_authorized

    assert is_authorized(C(), []) is False
```

### Step 3.4 — Conversations & memory

- `app/models/conversation.py` → `conversations`, `messages`
- `app/rag/memory.py`:

```python
async def build_conversation_context(session, session_id, new_query, max_history: int = 5) -> str:
    history = await recent_messages(session, session_id, limit=max_history)
    if len(history) <= max_history:
        return "\n".join(f"{m.role}: {m.content}" for m in history)
    summary = await summarize("\n".join(f"{m.role}: {m.content}" for m in history))
    return f"Conversation summary:\n{summary}"
```

### Step 3.5 — Audit logging

`app/models/audit.py` + `app/rag/pipeline.py` writes a row per query:

```python
session.add(
    AuditLog(
        user_id=user_id,
        query=question,
        chunks_retrieved=len(chunks),
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        total_ms=total_ms,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cost_usd=cost,
    )
)
await session.commit()
```

### Step 3.6 — Feedback endpoint

```python
# app/api/routes/feedback.py
@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, session=Depends(get_db)):
    session.add(Feedback(message_id=payload.message_id, rating=payload.rating, comment=payload.comment))
    await session.commit()
    return {"status": "recorded"}
```

### Step 3.7 — Tests

```bash
pytest tests/test_security.py -v      # token create/decode, expiry, bad token
pytest tests/test_acl.py -v            # authorization matrix
pytest tests/test_api.py -v            # 401 without token, 200 with token
```

### ✅ Phase 3 Definition of Done

- [ ] Unauthenticated requests to `/api/v1/chat/query` return `401`
- [ ] A `ENGINEERING` user never receives an `HR`-only chunk (verified by test)
- [ ] Every query writes an `audit_logs` row
- [ ] Feedback endpoint persists

---

## 6. Phase 4 — Retrieval Quality + Evaluation

**Goal:** measurable quality — query rewriting, re-ranking, metadata filters, RAGAS suite.

**Estimated time:** 1 week.

### Step 4.1 — Golden dataset (`eval_data/golden.jsonl`)

```json
{"question": "What is the leave policy for employees with < 1 year service?", "answer": "18 days per year", "sources": ["Employee Leave Policy v4.1"], "department": "HR"}
```

Target 30–50 hand-verified questions across departments. This dataset is the single most
valuable asset in the repo — build it before optimising anything.

### Step 4.2 — Evaluation runner (`app/evaluation/runner.py`)

```python
import json

from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness


def load_golden(path: str = "eval_data/golden.jsonl") -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


async def build_samples(golden: list[dict]) -> list[dict]:
    samples = []
    for item in golden:
        chunks = await retrieve_for_eval(item["question"])
        answer_text, _ = await answer(item["question"], chunks)
        samples.append(
            {
                "user_input": item["question"],
                "response": answer_text,
                "retrieved_contexts": [c.content for c in chunks],
                "reference": item["answer"],
            }
        )
    return samples


def run_eval(samples: list[dict]):
    return evaluate(
        dataset=samples,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
```

```bash
python -m app.evaluation.runner            # prints a pandas table
pytest tests/test_evaluation.py -v         # asserts faithfulness > 0.8
```

### Step 4.3 — Query rewriting (`app/rag/query_rewriter.py`)

```python
REWRITE_PROMPT = """Rewrite the query to be retrieval-friendly.
Expand acronyms, add synonyms, keep named entities intact. Output only the rewritten query.

Query: {query}
Rewritten:"""


async def rewrite_query(query: str) -> str:
    if not settings.enable_query_rewrite:
        return query
    result = await get_llm().ainvoke(REWRITE_PROMPT.format(query=query))
    return (result.content if isinstance(result.content, str) else "").strip() or query
```

### Step 4.4 — Re-ranking (`app/retrieval/reranker.py`)

```python
from langchain_cohere import CohereRerank

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None and settings.cohere_api_key:
        _reranker = CohereRerank(model="rerank-english-v3.0", cohere_api_key=settings.cohere_api_key)
    return _reranker


async def rerank(query: str, chunks: list, top_n: int = 5) -> list:
    r = get_reranker()
    if r is None:
        return chunks[:top_n]
    compressed = r.compress_documents(chunks, query=query)
    return compressed[:top_n]
```

### Step 4.5 — Metadata filtering

```python
stmt = stmt.where(Chunk.document_id.in_(select(Document.id).where(Document.department.in_(departments))))
```

### Step 4.6 — Measure the delta

| Change | Run | Record |
|---|---|---|
| baseline (vector only) | `python -m app.evaluation.runner` | paste table in PR |
| + BM25 hybrid | " | " |
| + reranker | " | " |
| + query rewrite | " | " |

> Never merge a retrieval change without before/after RAGAS numbers in the PR description.

### ✅ Phase 4 Definition of Done

- [ ] `eval_data/golden.jsonl` with ≥30 items
- [ ] Eval command runs in CI and fails if faithfulness drops > 5%
- [ ] At least 3 documented retrieval experiments with measured deltas

---

## 7. Phase 5 — Production Engineering

**Goal:** caching, async ingestion, containers, monitoring, tracing, CI.

### Step 5.1 — Redis cache

```python
# app/core/cache.py
import hashlib
import json

import redis.asyncio as aioredis

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def cached_json(key: str, producer):
    r = await get_redis()
    full_key = f"eraga:{key}"
    hit = await r.get(full_key)
    if hit:
        return json.loads(hit)
    value = await producer()
    await r.setex(full_key, 3600, json.dumps(value))
    return value
```

Cache embedding lookups for identical questions, and cache answers keyed by
`hash(question + sorted(chunk_ids))`.

```bash
docker run -d --name eraga-redis -p 6379:6379 redis:7-alpine
pytest tests/test_cache.py -v
```

### Step 5.2 — Celery ingestion workers

```python
# workers/ingestion_worker.py
from celery import Celery

from app.ingestion.pipeline import ingest_file
from app.core.database import SessionLocal

celery_app = Celery("eraga", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.update(task_serializer="json", accept_content=["json"], timezone="UTC")


@celery_app.task(name="eraga.ingest", bind=True, max_retries=3, autoretry_for=(Exception,))
def ingest(self, path: str, department: str | None = None, roles: list[str] | None = None):
    async def run():
        async with SessionLocal() as session:
            return str((await ingest_file(session, path, department, roles)).id)

    return asyncio.run(run())
```

```bash
celery -A workers.ingestion_worker.celery_app worker --loglevel=info
```

Route ingestion through the worker when a document exceeds ~2 MB or the file count > 20.

### Step 5.3 — Docker

`infra/Dockerfile`:

```dockerfile
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir ".[all]"

EXPOSE 8000
HEALTHCHECK --interval=30s CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`infra/docker-compose.yml`:

```yaml
services:
  api:
    build: { context: .., dockerfile: infra/Dockerfile }
    env_file: [../.env]
    ports: ["8000:8000"]
    depends_on: [postgres, redis]

  worker:
    build: { context: .., dockerfile: infra/Dockerfile }
    command: celery -A workers.ingestion_worker.celery_app worker --loglevel=info
    env_file: [../.env]
    depends_on: [redis, postgres]

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: eraga
      POSTGRES_PASSWORD: eraga
      POSTGRES_DB: eraga
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

```bash
docker compose -f infra\docker-compose.yml up --build
curl http://localhost:8000/health
```

### Step 5.4 — Observability

- **Metrics:** `prometheus-client` + `/metrics` — request count, latency histogram, tokens, cost.
- **Tracing:** OpenTelemetry spans for `retrieve`, `rerank`, `llm`, with `user.id` and `query.length`.
- **Dashboards:** Grafana panels for latency P50/P95, retrieval success rate, cost per 1K queries.

```bash
pytest tests/test_observability.py -v
```

### Step 5.5 — CI/CD (`.github/workflows/ci.yml`)

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_USER: eraga, POSTGRES_PASSWORD: eraga, POSTGRES_DB: eraga }
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s
          --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[all]"
      - run: ruff check .
      - run: mypy app
      - run: pytest --cov=app --cov-fail-under=70
        env:
          DATABASE_URL: postgresql+asyncpg://eraga:eraga@localhost:5432/eraga
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### ✅ Phase 5 Definition of Done

- [ ] `docker compose up` yields a healthy API
- [ ] Identical question served from cache on 2nd call (< 200 ms)
- [ ] Celery ingests a 50-page PDF without blocking the API
- [ ] CI green on every PR with coverage gate ≥ 70%

---

## 8. Phase 6 — Advanced GenAI

**Goal:** agentic RAG, SQL agent, guardrails, cost optimisation, multi-tenancy.

### Step 6.1 — Query router (`app/rag/router.py`)

```python
ROUTE_PROMPT = """Classify the question into one of: policy | howto | analytics | general.
Return only the label.

Question: {q}
Label:"""


async def route(question: str) -> str:
    res = await get_llm().ainvoke(ROUTE_PROMPT.format(q=question))
    label = (res.content or "").strip().lower()
    return label if label in {"policy", "howto", "analytics", "general"} else "general"
```

### Step 6.2 — Tools + agent

```python
# app/rag/agent.py
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool


@tool
def vector_search_tool(query: str) -> str:
    """Search enterprise policy and documentation."""
    return run_sync(_vector_search, query, top_k=5)


@tool
def sql_tool(question: str) -> str:
    """Query the incident/analytics database (read-only)."""
    return run_sync(_sql_query, question)


AGENT_SYSTEM = """You are ERAGA. Route questions to the right tool, then answer using
ONLY the tool output. Always cite sources. If tools return nothing relevant, say so."""


def build_agent(llm):
    tools = [vector_search_tool, sql_tool]
    prompt = ChatPromptTemplate.from_messages([("system", AGENT_SYSTEM), ("human", "{input}"), agent_scratchpad])
    return AgentExecutor(agent=create_tool_calling_agent(llm, tools, prompt), tools=tools, verbose=False)
```

> **SQL safety:** use a read-only DB role, `LIMIT` injection, and an allow-list of tables.
> Never let the model emit DDL/DML.

### Step 6.3 — Guardrails

- Input guard: prompt-injection detection (e.g. NeMo Guardrails `self_check_input`).
- Output guard: reject answers that cite a `chunk_id` not present in the retrieved set.
- PII masking on both stored chunks and returned answers.

```python
def validate_citations(answer: str, chunks: list) -> bool:
    cited = set(re.findall(r"\[(\d+)\]", answer))
    allowed = {str(i) for i in range(1, len(chunks) + 1)}
    return cited <= allowed
```

```python
def test_citation_validator_rejects_invented_source():
    from app.rag.guardrails import validate_citations

    assert validate_citations("Per [1] policy...", chunks=["a", "b"]) is True
    assert validate_citations("Per [7] policy...", chunks=["a", "b"]) is False
```

### Step 6.4 — Multi-tenancy

Add `tenant_id` to `documents`, `document_chunks`, `users`; include it in **every** query
predicate; add it to the JWT; add a composite index `(tenant_id, document_id)`.
Add a test that tenant A's token cannot retrieve tenant B's chunk.

### Step 6.5 — Cost optimisation

| Technique | Expected saving |
|---|---|
| Cache identical questions | 15–25% |
| Reduce `top_k` after reranking (20 → 5) | 40–60% tokens |
| Small model for rewriting/routing, large for answering | 20–30% |
| Prompt caching / shorter system prompt | 10% |

### ✅ Phase 6 Definition of Done

- [ ] Router selects the correct tool for ≥ 90% of golden questions
- [ ] Fabricated-citation test passes
- [ ] Cross-tenant access test passes
- [ ] Cost dashboard shows $/1K queries

---

## 9. Phase 7 — Frontend & DevOps

**Goal:** usable chat UI, admin panel, cloud deployment.

### Step 7.1 — Minimal Next.js chat UI

```bash
npx create-next-app@latest web --typescript --tailwind --app --src-dir
cd web
npm i -D tailwindcss postcss autoprefixer
```

Key pieces:

- `src/app/page.tsx` — chat view with streaming (`EventSource`/`fetch` + `ReadableStream`).
- `src/app/admin/page.tsx` — upload documents, see ingestion status, assign `allowed_roles`.
- `src/lib/api.ts` — typed client: `query()`, `upload()`, `feedback()`.

```bash
npm run dev            # http://localhost:3000
npm run build && npm run start
npm run lint && npx tsc --noEmit
```

Wire the token: `Authorization: Bearer <jwt>` on every call; refresh on 401.

### Step 7.2 — Kubernetes (`infra/k8s/`)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eraga-api
spec:
  replicas: 3
  selector: { matchLabels: { app: eraga-api } }
  template:
    metadata: { labels: { app: eraga-api } }
    spec:
      containers:
        - name: api
          image: ghcr.io/<you>/eraga:latest
          ports: [{ containerPort: 8000 }]
          envFrom:
            - secretRef: { name: eraga-secrets }
            - configMapRef: { name: eraga-config }
          resources:
            requests: { cpu: "250m", memory: "512Mi" }
            limits: { cpu: "1", memory: "1Gi" }
          readinessProbe: { httpGet: { path: /health, port: 8000 }, initialDelaySeconds: 5 }
          livenessProbe: { httpGet: { path: /health, port: 8000 }, periodSeconds: 20 }
---
apiVersion: v1
kind: Service
metadata:
  name: eraga-api
spec:
  selector: { app: eraga-api }
  ports: [{ port: 80, targetPort: 8000 }]
```

```bash
kubectl apply -f infra\k8s\deployment.yaml
kubectl get pods -w
kubectl port-forward svc/eraga-api 8080:80
```

Add HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: eraga-api }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: eraga-api }
  minReplicas: 3
  maxReplicas: 12
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

### Step 7.3 — Release pipeline

1. PR → CI (lint, typecheck, unit + integration tests, RAGAS gate)
2. Merge to `main` → build image, push to GHCR, tag with git SHA
3. `staging` deploy → smoke test (`curl /health`, one golden question)
4. Manual approval → `prod` deploy → post-deploy golden-question canary

### ✅ Phase 7 Definition of Done

- [ ] Chat UI streams answers with clickable citations
- [ ] Admin can upload a PDF and restrict roles
- [ ] HPA scales under load test (k6 or Locust, 50 RPS)
- [ ] Canary passes before prod rollout

---

## 10. Definition of Done (per phase)

Every phase is only complete when **all** boxes are ticked:

- [ ] Code formatted (`ruff format`) and lint-clean (`ruff check`)
- [ ] Types checked (`mypy app`)
- [ ] Tests added for new behaviour; `pytest` green; coverage not decreased
- [ ] No secrets committed (`.env` ignored; `.env.example` updated)
- [ ] README/ERAGA.md updated if public behaviour changed
- [ ] For retrieval changes: before/after RAGAS numbers attached
- [ ] Commit message follows Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`)
- [ ] Phase checklist ticked in this document

---

## 11. Continuous Commands Cheat Sheet

```bash
# ---- environment ----
.\.venv\Scripts\Activate.ps1              # activate venv (PowerShell)
pip install -e ".[all]"                  # install/sync deps

# ---- run ----
uvicorn app.main:app --reload --port 8000 # dev server with hot reload
celery -A workers.ingestion_worker.celery_app worker --loglevel=info
docker compose -f infra\docker-compose.yml up --build

# ---- data ----
python scripts\ingest.py data\samples\leave_policy.pdf
python scripts\search.py "leave policy for new joiners"
alembic upgrade head                     # apply migrations

# ---- quality ----
pytest -v                                 # all tests
pytest -v --cov=app --cov-report=term-missing
pytest tests/test_acl.py -v               # single file
pytest -k "acl or retrieval" -v           # by keyword
ruff check . && ruff format .             # lint + format
mypy app                                 # typecheck
python -m app.evaluation.runner           # RAGAS quality report

# ---- git ----
git status
git add -A
git commit -m "feat: add hybrid retrieval with RRF fusion"
```

### Test strategy cheat sheet

| Layer | What to test | Tool | Needs services? |
|---|---|---|---|
| Unit | cleaner, chunker, RRF, ACL logic, prompt build | pytest | No |
| Integration | DB queries, Alembic, ACL in SQL | pytest + asyncpg | Postgres |
| Contract | `POST /query` shape, auth codes | pytest + TestClient | No |
| Evaluation | RAGAS on golden set | ragas | Postgres + LLM key |
| E2E | UI → API → answer | Playwright | Full stack |
| Load | 50 RPS latency P95 | k6 / Locust | Full stack |

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: app` | wrong working directory / not installed | run from repo root, `pip install -e .` |
| `dimension mismatch` in pgvector | model changed dim (1536 ↔ 768) | alter column: `ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768);` and re-embed |
| `operator does not exist: embedding <=> unknown` | extension missing | `CREATE EXTENSION vector;` |
| `embedding column does not exist` | model not migrated | `alembic revision --autogenerate -m "add embedding"` |
| `Connection refused localhost:5432` | Postgres not running | `docker ps -a` then `docker start eraga-pg` |
| HNSW index build is very slow | index created on empty/small table | drop index, bulk load, then recreate |
| `401` from `/api/v1/chat/query` | missing/expired JWT | pass `Authorization: Bearer <token>` |
| Answers ignore ACL | filtering in Python after fetch | move `allowed_roles.overlap(roles)` into the SQL `WHERE` |
| Streaming returns nothing | missing `media_type` / wrong router mount | verify `StreamingResponse` and route prefix |
| RAGAS scores near 0 | reference answers ungrounded or empty context | validate `golden.jsonl` manually first |
| `pytest` hangs on DB tests | no `asyncio_mode = "auto"` | add to `pyproject.toml` `[tool.pytest.ini_options]` |
| Windows `ExecutionPolicy` blocks venv | PowerShell policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## 📌 Related Documents

- [`ERAGA.md`](./ERAGA.md) — full architecture, DB design, security model, resume blurb
- [`ERAGA1.md`](./ERAGA1.md) — research notes and references
- [`../README.md`](../README.md) — project overview and feature list

---

<div align="center">

**ERAGA — Development Roadmap**
*Build → Measure → Harden → Ship.*

</div>