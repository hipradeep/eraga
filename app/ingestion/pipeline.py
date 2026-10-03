"""Offline ingestion orchestrator: file -> parse -> clean -> chunk -> embed -> store."""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.chunker import chunk_blocks, chunk_to_dicts
from app.ingestion.cleaner import clean_blocks
from app.ingestion.loaders import detect_doc_type, load
from app.models.document import Document
from app.retrieval.embeddings import embed_documents, get_embedder
from app.retrieval.vector_store import replace_chunks

logger = logging.getLogger("eraga.ingestion")
settings = get_settings()

MAX_EMBED_CHARS = 8_000_000  # guard against pathological inputs


@dataclass(slots=True)
class IngestionResult:
    document_id: uuid.UUID
    name: str
    chunk_count: int
    status: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ready"


def file_checksum(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


async def ingest_file(
    session: AsyncSession,
    path: str | Path,
    *,
    department: str | None = None,
    allowed_roles: list[str] | None = None,
    classification: str = "INTERNAL",
    version: str | None = None,
    source_uri: str | None = None,
) -> IngestionResult:
    """Ingest one file end to end. Never raises — failures land on the document row."""
    path = Path(path)
    roles = allowed_roles or settings.admin_role_list
    embedder = get_embedder()

    document = Document(
        name=path.name,
        doc_type=detect_doc_type(path),
        department=department,
        classification=classification,
        version=version,
        source_uri=source_uri,
        allowed_roles=roles,
        checksum=file_checksum(path) if path.is_file() else None,
        status="processing",
    )
    session.add(document)

    try:
        await session.flush()

        blocks = clean_blocks(load(path))
        chunks = chunk_blocks(
            blocks,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise ValueError("no usable text after cleaning (scanned image or empty file?)")

        total_chars = sum(chunk.char_count for chunk in chunks)
        if total_chars > MAX_EMBED_CHARS:
            raise ValueError(f"document too large to embed in one pass ({total_chars} chars)")

        payloads = chunk_to_dicts(chunks)
        embeddings = await embed_documents([chunk["content"] for chunk in payloads])

        await replace_chunks(session, document, payloads, embeddings)
        await session.commit()

        logger.info("ingested %s -> %d chunks (%s)", path.name, len(payloads), embedder.model_name)
        return IngestionResult(document.id, document.name, len(payloads), "ready")

    except Exception as exc:  # noqa: BLE001
        logger.exception("ingestion failed for %s", path.name)
        document.status = "failed"
        document.error = str(exc)[:1000]
        await session.commit()
        return IngestionResult(document.id, document.name, 0, "failed", str(exc)[:1000])


async def ingest_many(
    session: AsyncSession, paths: list[str | Path], **kwargs
) -> list[IngestionResult]:
    return [await ingest_file(session, path, **kwargs) for path in paths]
