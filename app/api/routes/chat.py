"""Chat endpoints: grounded question answering over the enterprise corpus."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.rag.llm_client import get_llm
from app.rag.pipeline import answer_question
from app.rag.prompt_templates import SYSTEM_PROMPT, build_prompt, format_context
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.schemas import QueryRequest, QueryResponse

logger = logging.getLogger("eraga.api.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# FastAPI derives the header name from the parameter name (`x_roles`), which never
# matches a real `X-Roles` header — the alias is mandatory, not cosmetic.
RolesHeader = Annotated[
    str | None, Header(alias="X-Roles", description="comma-separated ACL roles")
]


def resolve_roles(x_roles: str | None) -> list[str]:
    """Resolve caller roles from a comma-separated header.

    SECURITY: Phase 3 replaces this with verified JWT claims. Until then the header
    is intentionally unauthenticated and must not be treated as a security control.
    """
    raw = x_roles or "admin"
    return [role.strip() for role in raw.split(",") if role.strip()]


@router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    x_roles: RolesHeader = None,
    session: AsyncSession = Depends(get_db),
) -> QueryResponse:
    return await answer_question(session, payload, roles=resolve_roles(x_roles))


@router.post("/retrieve")
async def retrieve_only(
    payload: QueryRequest,
    x_roles: RolesHeader = None,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Expose raw retrieval scores — invaluable for tuning chunking and top_k."""
    roles = resolve_roles(x_roles)
    chunks = await hybrid_retrieve(
        session,
        payload.question,
        roles=roles,
        top_k=payload.top_k,
        departments=payload.departments,
    )
    return {
        "question": payload.question,
        "roles": roles,
        "count": len(chunks),
        "chunks": [
            {
                "chunk_id": str(item.chunk.id),
                "document_id": str(item.chunk.document_id),
                "section": item.chunk.section,
                "page_number": item.chunk.page_number,
                "fused_score": round(item.score, 6),
                "dense_score": round(item.dense_score, 6),
                "keyword_score": round(item.keyword_score, 6),
                "allowed_roles": item.chunk.allowed_roles,
                "preview": item.content[:240],
            }
            for item in chunks
        ],
    }


@router.post("/stream")
async def query_stream(
    payload: QueryRequest,
    x_roles: RolesHeader = None,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-sent events: answer tokens, then a final citations event."""
    roles = resolve_roles(x_roles)
    llm = get_llm()

    async def event_stream():
        chunks = await hybrid_retrieve(session, payload.question, roles=roles, top_k=payload.top_k)
        if not chunks:
            yield "event: answer\ndata: I don't have enough information to answer this.\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        citations = [
            {
                "marker": f"[{index}]",
                "chunk_id": str(item.chunk.id),
                "section": item.chunk.section,
                "page_number": item.chunk.page_number,
            }
            for index, item in enumerate(chunks, start=1)
        ]

        async for piece in llm.stream(SYSTEM_PROMPT, build_prompt(payload.question, chunks)):
            yield f"event: answer\ndata: {piece}\n\n"

        yield f"event: citations\ndata: {json.dumps(citations)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/context-preview")
async def context_preview(
    question: str,
    top_k: int = 5,
    x_roles: RolesHeader = None,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Render the exact prompt context — debug grounding issues without a full run."""
    roles = resolve_roles(x_roles)
    chunks = await hybrid_retrieve(session, question, roles=roles, top_k=top_k)
    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": build_prompt(question, chunks),
        "chunk_count": len(chunks),
        "context_chars": len(format_context(chunks)),
    }
