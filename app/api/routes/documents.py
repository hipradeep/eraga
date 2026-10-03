"""Document management endpoints."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.ingestion.loaders import SUPPORTED_TYPES
from app.ingestion.pipeline import ingest_file
from app.models.document import Document
from app.retrieval.vector_store import delete_document, list_documents
from app.schemas import DocumentResponse

logger = logging.getLogger("eraga.api.documents")
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
settings = get_settings()

UPLOAD_DIR = Path("data/uploads")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

RolesHeader = Annotated[
    str | None, Header(alias="X-Roles", description="comma-separated ACL roles")
]


def resolve_roles(x_roles: str | None) -> list[str]:
    raw = x_roles or "admin"
    return [role.strip() for role in raw.split(",") if role.strip()]


@router.get("", response_model=list[DocumentResponse])
async def get_documents(
    x_roles: RolesHeader = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    documents = await list_documents(session, roles=resolve_roles(x_roles), limit=limit)
    return [DocumentResponse.model_validate(doc, from_attributes=True) for doc in documents]


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    department: str | None = Form(default=None),
    allowed_roles: str = Form(default=""),
    classification: str = Form(default="INTERNAL"),
    version: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    suffix = Path(file.filename or "").suffix.lstrip(".").lower()
    if suffix not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported file type '{suffix}'; allowed: {', '.join(SUPPORTED_TYPES)}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}.{suffix}"

    size = 0
    try:
        with open(destination, "wb") as handle:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="file exceeds 50 MB limit")
                handle.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise

    roles = [role.strip() for role in allowed_roles.split(",") if role.strip()]
    result = await ingest_file(
        session,
        destination,
        department=department,
        allowed_roles=roles or None,
        classification=classification,
        version=version,
        source_uri=file.filename,
    )

    document = await session.get(Document, result.document_id)
    if result.status != "ready" or document is None:
        raise HTTPException(status_code=422, detail=f"ingestion failed: {result.error}")

    logger.info("uploaded %s as %s (%d chunks)", file.filename, document.name, result.chunk_count)
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.delete("/{document_id}", status_code=204)
async def remove_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    if not await delete_document(session, document_id):
        raise HTTPException(status_code=404, detail="document not found")


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Re-chunk and re-embed an existing document after a pipeline change."""
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    if not document.source_uri or not Path(document.source_uri).is_file():
        raise HTTPException(status_code=409, detail="original file is no longer on disk")
    raise HTTPException(status_code=501, detail="reindex is scheduled for Phase 5")
