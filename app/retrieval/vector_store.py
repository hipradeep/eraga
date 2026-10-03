"""pgvector-backed chunk storage and similarity search.

The ACL filter (`allowed_roles && ARRAY[...]`) is applied inside the SQL query so
unauthorised chunks never leave the database — not even into the LLM prompt.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document


@dataclass(slots=True)
class VectorHit:
    """A chunk returned by dense search together with its cosine similarity."""

    chunk: Chunk
    similarity: float


async def replace_chunks(
    session: AsyncSession,
    document: Document,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> list[Chunk]:
    """Delete any previous chunks for the document and insert a fresh set."""
    await session.execute(delete(Chunk).where(Chunk.document_id == document.id))

    rows = [
        Chunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk["content"],
            embedding=embedding,
            page_number=chunk.get("page_number"),
            section=chunk.get("section"),
            char_count=chunk.get("char_count", len(chunk["content"])),
            extra_metadata={
                "page_number": chunk.get("page_number"),
                "section": chunk.get("section"),
                "source": document.name,
            },
            allowed_roles=document.allowed_roles,
        )
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
    ]

    session.add_all(rows)
    document.chunk_count = len(rows)
    document.status = "ready"
    document.error = None
    return rows


async def delete_document(session: AsyncSession, document_id: uuid.UUID) -> bool:
    result = await session.execute(delete(Document).where(Document.id == document_id))
    await session.commit()
    return bool(getattr(result, "rowcount", 0))


async def list_documents(
    session: AsyncSession, roles: list[str] | None = None, limit: int = 100
) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc()).limit(limit)
    if roles is not None:
        stmt = stmt.where(Document.allowed_roles.overlap(roles))
    result = await session.execute(stmt)
    return list(result.scalars())


async def similarity_search(
    session: AsyncSession,
    vector: list[float],
    roles: list[str],
    top_k: int = 8,
    departments: list[str] | None = None,
    similarity_threshold: float | None = None,
) -> list[VectorHit]:
    """Cosine-similarity search restricted to chunks the roles may read.

    Returns `VectorHit` records ordered by descending similarity.
    """
    distance = Chunk.embedding.cosine_distance(vector).label("distance")
    stmt = (
        select(Chunk, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.allowed_roles.overlap(roles))
    )

    if departments:
        stmt = stmt.where(Document.department.in_(departments))

    if similarity_threshold is not None:
        stmt = stmt.where(distance < (1 - similarity_threshold))

    stmt = stmt.order_by(distance).limit(top_k)

    result = await session.execute(stmt)
    return [VectorHit(chunk=chunk, similarity=1.0 - float(dist)) for chunk, dist in result.all()]


async def load_chunks_for_bm25(
    session: AsyncSession, roles: list[str], limit: int = 5000
) -> list[Chunk]:
    """Pull candidate chunks into memory to build a BM25 index.

    A single-process in-memory index keeps Phase 1 dependency-free; Phase 5 swaps
    this for Elasticsearch/OpenSearch once the corpus outgrows RAM.
    """
    stmt = select(Chunk).where(Chunk.allowed_roles.overlap(roles)).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars())


async def count_chunks(session: AsyncSession) -> int:
    result = await session.execute(text("SELECT count(*) FROM document_chunks"))
    return int(result.scalar_one())


async def ensure_vector_index(session: AsyncSession) -> None:
    """Create the pgvector extension and HNSW index if absent."""
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw "
            "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
        )
    )
    await session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_roles "
            "ON document_chunks USING gin (allowed_roles)"
        )
    )
    await session.commit()
