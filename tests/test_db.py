"""Database + end-to-end API tests.

Skipped automatically when PostgreSQL is unreachable so `pytest` still works on a
machine without Docker.
"""

from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.core.database import SessionLocal, engine
from app.ingestion.pipeline import ingest_file
from app.models.chunk import Chunk
from app.models.document import Document
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.retrieval.vector_store import count_chunks, ensure_vector_index, similarity_search


async def _db_ready() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="session")
async def db_available():
    ready = await _db_ready()
    if not ready:
        pytest.skip("PostgreSQL unreachable - start it with: docker start eraga-pg")
    async with engine.begin() as conn:
        from app.models import Base

        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await ensure_vector_index(session)


@pytest.fixture
async def sample_doc(db_available):
    """Ingest a small markdown policy scoped to the ADMIN_ONLY role."""
    content = (
        "# Widget Retirement Policy\n\n"
        "## 1. Scope\n\nThis policy governs the retirement of legacy widgets.\n\n"
        "## 2. Notice Period\n\nEngineers receive 60 days notice before a widget is retired.\n"
    )
    path = Path("data/samples/_test_widget_policy.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    async with SessionLocal() as session:
        result = await ingest_file(session, path, department="QA", allowed_roles=["ADMIN_ONLY"])
        assert result.ok, result.error
        yield result

        doc = await session.get(Document, result.document_id)
        if doc is not None:
            for chunk in (
                await session.execute(select(Chunk).where(Chunk.document_id == doc.id))
            ).scalars():
                await session.delete(chunk)
            await session.delete(doc)
            await session.commit()
    path.unlink(missing_ok=True)


class TestDatabase:
    async def test_connection(self, db_available):
        async with SessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

    async def test_pgvector_extension_present(self, db_available):
        async with SessionLocal() as session:
            result = await session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname='vector'")
            )
            assert result.scalar_one() == 1

    async def test_hnsw_index_present(self, db_available):
        async with SessionLocal() as session:
            result = await session.execute(
                text("SELECT count(*) FROM pg_indexes WHERE indexname='idx_chunks_embedding_hnsw'")
            )
            assert result.scalar_one() == 1

    async def test_embedding_column_is_768_dim(self, db_available):
        async with SessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                    "WHERE attrelid='document_chunks'::regclass AND attname='embedding'"
                )
            )
            assert result.scalar_one() == "vector(768)"


class TestIngestionEndToEnd:
    async def test_document_marked_ready(self, sample_doc):
        assert sample_doc.status == "ready"
        assert sample_doc.chunk_count > 0

    async def test_chunks_stored_with_metadata(self, sample_doc):
        async with SessionLocal() as session:
            chunks = (
                await session.execute(
                    select(Chunk).where(Chunk.document_id == sample_doc.document_id)
                )
            ).scalars()
            chunks = list(chunks)
            assert len(chunks) == sample_doc.chunk_count
            assert all(chunk.embedding is not None for chunk in chunks)
            assert all(chunk.char_count > 0 for chunk in chunks)

    async def test_reingest_replaces_chunks(self, sample_doc):
        async with SessionLocal() as session:
            before = await count_chunks(session)
            result = await ingest_file(
                session, "data/samples/_test_widget_policy.md", allowed_roles=["ADMIN_ONLY"]
            )
            after = await count_chunks(session)
            assert result.ok
            assert after >= before


class TestACLEnforcement:
    async def test_authorised_role_sees_chunks(self, sample_doc):
        async with SessionLocal() as session:
            chunks = await hybrid_retrieve(session, "notice period widgets", roles=["ADMIN_ONLY"])
            assert len(chunks) > 0

    async def test_unauthorised_role_sees_nothing(self, sample_doc):
        async with SessionLocal() as session:
            chunks = await hybrid_retrieve(session, "notice period widgets", roles=["INTRUDER"])
            assert chunks == []

    async def test_similarity_search_filters_in_sql(self, sample_doc):
        from app.retrieval.embeddings import embed_query

        vector = await embed_query("widget retirement")
        async with SessionLocal() as session:
            allowed = await similarity_search(session, vector, roles=["ADMIN_ONLY"], top_k=10)
            denied = await similarity_search(session, vector, roles=["INTRUDER"], top_k=10)
        assert allowed
        assert denied == []
        assert all("ADMIN_ONLY" in hit.chunk.allowed_roles for hit in allowed)

    async def test_empty_role_list_denied(self, sample_doc):
        async with SessionLocal() as session:
            assert await hybrid_retrieve(session, "widget", roles=[]) == []


class TestApiEndpoints:
    async def test_query_with_authorised_role(self, async_client, sample_doc):
        response = await async_client.post(
            "/api/v1/chat/query",
            json={"question": "How much notice before a widget is retired?"},
            headers={"X-Roles": "ADMIN_ONLY"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["grounded"] is True
        assert len(body["citations"]) > 0
        assert body["citations"][0]["document_title"] == "_test_widget_policy.md"

    async def test_query_with_unauthorised_role_is_refused(self, async_client, sample_doc):
        response = await async_client.post(
            "/api/v1/chat/query",
            json={"question": "How much notice before a widget is retired?"},
            headers={"X-Roles": "INTRUDER"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["grounded"] is False
        assert body["citations"] == []
        assert "don't have enough information" in body["answer"]

    async def test_missing_roles_header_defaults_to_admin_scope(self, async_client, sample_doc):
        """No X-Roles header means the default admin scope, not an empty one."""
        response = await async_client.post(
            "/api/v1/chat/query", json={"question": "notice period widgets"}
        )
        assert response.status_code == 200
        assert response.json()["grounded"] is True

    async def test_retrieve_endpoint_returns_scores(self, async_client, sample_doc):
        response = await async_client.post(
            "/api/v1/chat/retrieve",
            json={"question": "notice period"},
            headers={"X-Roles": "ADMIN_ONLY"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] > 0
        assert "fused_score" in body["chunks"][0]

    async def test_documents_list_is_acl_scoped(self, async_client, sample_doc):
        allowed = await async_client.get("/api/v1/documents", headers={"X-Roles": "ADMIN_ONLY"})
        denied = await async_client.get("/api/v1/documents", headers={"X-Roles": "INTRUDER"})
        assert any(d["name"] == "_test_widget_policy.md" for d in allowed.json())
        assert all(d["name"] != "_test_widget_policy.md" for d in denied.json())

    async def test_upload_rejects_unsupported_type(self, async_client):
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": ("data.xlsx", b"binary", "application/octet-stream")},
        )
        assert response.status_code == 415

    async def test_upload_ingests_markdown(self, async_client, tmp_path: Path):
        source = tmp_path / "uploaded.md"
        source.write_text(
            "# Upload Test\n\n## Section\n\nEmployees receive a stipend of 500 per month.\n",
            encoding="utf-8",
        )
        with open(source, "rb") as handle:
            response = await async_client.post(
                "/api/v1/documents",
                files={"file": ("uploaded.md", handle, "text/markdown")},
                data={"department": "FIN", "allowed_roles": "UPLOAD_ROLE"},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "ready"
        assert body["chunk_count"] > 0
        assert body["allowed_roles"] == ["UPLOAD_ROLE"]

    async def test_validation_rejects_short_question(self, async_client):
        response = await async_client.post("/api/v1/chat/query", json={"question": "hi"})
        assert response.status_code == 422

    async def test_stream_emits_sse_events(self, async_client, sample_doc):
        response = await async_client.post(
            "/api/v1/chat/stream",
            json={"question": "What notice period applies?"},
            headers={"X-Roles": "ADMIN_ONLY"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: citations" in response.text
        assert "event: done" in response.text

    async def test_audit_row_written(self, async_client, sample_doc):
        await async_client.post(
            "/api/v1/chat/query",
            json={"question": "notice period for widgets"},
            headers={"X-Roles": "ADMIN_ONLY"},
        )
        async with SessionLocal() as session:
            result = await session.execute(
                text("SELECT count(*) FROM query_audits WHERE chunks_retrieved > 0")
            )
            assert result.scalar_one() > 0

    async def test_audit_records_ungrounded_queries(self, async_client, sample_doc):
        await async_client.post(
            "/api/v1/chat/query",
            json={"question": "notice period for widgets"},
            headers={"X-Roles": "INTRUDER"},
        )
        async with SessionLocal() as session:
            result = await session.execute(
                text("SELECT count(*) FROM query_audits WHERE chunks_retrieved = 0")
            )
            assert result.scalar_one() > 0
