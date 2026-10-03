import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, documents
from app.config import get_settings
from app.core.database import engine
from app.rag import llm_client
from app.retrieval import embeddings as embeddings_module
from app.retrieval import rerank as rerank_module

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("eraga")

VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.core.database import SessionLocal
    from app.models import Base  # noqa: F401  (registers tables on metadata)
    from app.retrieval.vector_store import ensure_vector_index

    logger.info("ERAGA %s starting in %s mode", VERSION, settings.environment)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as session:
            await ensure_vector_index(session)
        logger.info("database schema verified")
    except Exception:
        logger.exception(
            "database unavailable - API started but /api/v1/* will fail until Postgres is reachable"
        )
    yield
    await engine.dispose()
    logger.info("ERAGA shutting down")


app = FastAPI(
    title="ERAGA — Enterprise RAG Assistant",
    description=(
        "Production-grade Retrieval-Augmented Generation platform for enterprises. "
        "Stack: Groq (LLM) + Jina (embeddings & rerank) + PostgreSQL/pgvector."
    ),
    version=VERSION,
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
async def timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    if request.url.path not in {"/health", "/health/db", "/metrics"}:
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health", tags=["ops"])
async def health() -> dict:
    try:
        llm_name = llm_client.get_llm().model_name
    except Exception:  # noqa: BLE001 - missing/invalid credentials must not 500 health
        llm_name = f"{settings.llm_provider} (not configured)"
    try:
        embed_name = embeddings_module.get_embedder().model_name
    except Exception:  # noqa: BLE001
        embed_name = f"{settings.embedding_provider} (not configured)"
    return {
        "status": "ok",
        "version": VERSION,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "llm": llm_name,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": embed_name,
        "embedding_dim": settings.embedding_dim,
        "rerank_provider": settings.rerank_provider,
    }


@app.get("/health/db", tags=["ops"], response_model=None)
async def health_db() -> dict | JSONResponse:
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT version()"))).scalar_one()
            chunk_count = (
                await conn.execute(text("SELECT count(*) FROM document_chunks"))
            ).scalar_one()
        return {
            "status": "ok",
            "postgres": version.split(",")[0],
            "chunks": int(chunk_count),
        }
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": str(exc)},
        )


@app.get("/health/models", tags=["ops"])
async def health_models() -> dict:
    llm_ok, llm_detail = await llm_client.health()
    embed_ok, embed_detail = await embeddings_module.health()
    rerank_ok, rerank_detail = await rerank_module.health()
    return {
        "status": "ok" if (llm_ok and embed_ok and rerank_ok) else "degraded",
        "llm": {"ok": llm_ok, "detail": llm_detail},
        "embeddings": {"ok": embed_ok, "detail": embed_detail},
        "rerank": {"ok": rerank_ok, "detail": rerank_detail},
    }


@app.get("/welcome", tags=["ops"])
def welcome() -> dict:
    return {
        "message": "Welcome to ERAGA — Enterprise RAG Assistant",
        "version": VERSION,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "ask": "POST /api/v1/chat/query",
            "retrieve_only": "POST /api/v1/chat/retrieve",
            "stream": "POST /api/v1/chat/stream",
            "documents": "/api/v1/documents",
        },
    }


app.include_router(chat.router)
app.include_router(documents.router)
