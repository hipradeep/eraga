import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("eraga")

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("ERAGA starting in %s mode", settings.environment)
    yield
    logger.info("ERAGA shutting down")


app = FastAPI(
    title="ERAGA — Enterprise RAG Assistant",
    description="Production-grade Retrieval-Augmented Generation platform for enterprises.",
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
    if request.url.path not in {"/health", "/metrics"}:
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
    return {"status": "ok", "version": VERSION, "environment": settings.environment}


@app.get("/welcome", tags=["ops"])
def welcome() -> dict:
    return {
        "message": "Welcome to ERAGA — Enterprise RAG Assistant 🧠",
        "version": VERSION,
        "status": "running",
    }
