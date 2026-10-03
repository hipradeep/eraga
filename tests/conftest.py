import os

# Force offline providers for the whole test session, BEFORE any app module is
# imported. `app.config.get_settings()` is cached at import time, so this must
# happen first. Env vars take precedence over `.env`, so tests never touch the
# Groq/Jina network APIs regardless of local `.env` values.
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["RERANK_PROVIDER"] = "none"

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture
def client():
    """Sync client for tests that never touch the database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client():
    """Async client that shares the pytest event loop with the async engine.

    `TestClient` spins up its own loop on a worker thread, which breaks SQLAlchemy's
    asyncpg pool. Anything hitting the database must use this instead.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
