"""Request/response schemas for the public API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    marker: str = Field(description="Inline marker used in the answer, e.g. [1]")
    chunk_id: UUID
    document_id: UUID
    document_title: str | None = None
    section: str | None = None
    page_number: int | None = None
    similarity: float | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    departments: list[str] | None = None
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    confidence: float = 0.0
    grounded: bool = False
    latency_ms: int = 0
    retrieval_ms: int = 0
    llm_ms: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    llm_model: str | None = None
    embedding_model: str | None = None


class DocumentResponse(BaseModel):
    id: UUID
    name: str
    doc_type: str
    department: str | None = None
    classification: str = "INTERNAL"
    allowed_roles: list[str] = []
    chunk_count: int = 0
    status: str
    error: str | None = None
    created_at: datetime | None = None
