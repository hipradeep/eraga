"""End-to-end RAG orchestrator: retrieve -> build context -> generate -> cite -> audit."""

import logging
import re
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.audit import QueryAudit
from app.rag.llm_client import get_llm
from app.rag.prompt_templates import NO_CONTEXT_ANSWER, SYSTEM_PROMPT, build_prompt
from app.retrieval.hybrid_retriever import RetrievedChunk, hybrid_retrieve
from app.schemas import Citation, QueryRequest, QueryResponse

logger = logging.getLogger("eraga.rag")
settings = get_settings()

_CITATION = re.compile(r"\[(\d+)\]")
MARKERS = "123456789"

_MODEL_COSTS: dict[str, tuple[float, float]] = {}


def build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for index, item in enumerate(chunks, start=1):
        chunk = item.chunk
        metadata = chunk.extra_metadata or {}
        citations.append(
            Citation(
                marker=f"[{index}]",
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=metadata.get("source"),
                section=chunk.section,
                page_number=chunk.page_number,
                similarity=round(item.score, 4),
            )
        )
    return citations


def strip_markers(text: str) -> str:
    """Remove [1]-style markers for downstream display; citations travel separately."""
    return _CITATION.sub("", text)


def calculate_confidence(chunks: list[RetrievedChunk], answer: str) -> float:
    """Heuristic 0-1 score: retrieval quality gated by actual citation usage."""
    if not chunks:
        return 0.0
    top_score = max(item.score for item in chunks)
    cited = set(_CITATION.findall(answer))
    citation_ratio = len(cited) / max(1, len(chunks))
    refusal = answer.strip().lower().startswith("i don't have enough information")
    if refusal:
        return 0.0
    return round(min(1.0, 0.5 * top_score + 0.5 * citation_ratio), 4)


def validate_citations(answer: str, chunks: list[RetrievedChunk]) -> list[str]:
    """Return any citation markers that reference a non-existent source."""
    allowed = {str(index) for index in range(1, len(chunks) + 1)}
    return sorted(set(_CITATION.findall(answer)) - allowed)


async def answer_question(
    session: AsyncSession,
    request: QueryRequest,
    roles: list[str],
    user_id: str | None = None,
) -> QueryResponse:
    overall_started = time.perf_counter()

    chunks, retrieval_ms = await _timed_retrieve(session, request, roles)
    if not chunks:
        await _audit(
            session,
            request.question,
            roles,
            user_id,
            top_k=request.top_k or settings.top_k,
            chunks=0,
            retrieval_ms=retrieval_ms,
            llm_ms=0,
            total_ms=int((time.perf_counter() - overall_started) * 1000),
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
        )
        return QueryResponse(
            answer=NO_CONTEXT_ANSWER,
            citations=[],
            confidence=0.0,
            grounded=False,
            latency_ms=int((time.perf_counter() - overall_started) * 1000),
            retrieval_ms=retrieval_ms,
            llm_model=get_llm().model_name,
            embedding_model=settings.embedding_model,
        )

    llm = get_llm()
    llm_started = time.perf_counter()
    result = await llm.complete(SYSTEM_PROMPT, build_prompt(request.question, chunks))
    llm_ms = int((time.perf_counter() - llm_started) * 1000)

    answer = result.text.strip() or NO_CONTEXT_ANSWER
    hallucinated = validate_citations(answer, chunks)
    if hallucinated:
        logger.warning("dropping answer with invalid citation markers: %s", hallucinated)
        answer = NO_CONTEXT_ANSWER

    cost = llm.estimate_cost(result)
    total_ms = int((time.perf_counter() - overall_started) * 1000)

    await _audit(
        session,
        request.question,
        roles,
        user_id,
        top_k=request.top_k or settings.top_k,
        chunks=len(chunks),
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        total_ms=total_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost=cost,
    )

    return QueryResponse(
        answer=answer,
        citations=build_citations(chunks),
        confidence=calculate_confidence(chunks, answer),
        grounded=answer != NO_CONTEXT_ANSWER,
        latency_ms=total_ms,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        tokens=result.total_tokens,
        cost_usd=round(cost, 6),
        llm_model=llm.model_name,
        embedding_model=settings.embedding_model,
    )


async def _timed_retrieve(
    session: AsyncSession, request: QueryRequest, roles: list[str]
) -> tuple[list[RetrievedChunk], int]:
    started = time.perf_counter()
    chunks = await hybrid_retrieve(
        session,
        request.question,
        roles=roles,
        top_k=request.top_k,
        departments=request.departments,
    )
    if request.similarity_threshold is not None:
        chunks = [c for c in chunks if c.score >= request.similarity_threshold]
    return chunks, int((time.perf_counter() - started) * 1000)


async def _audit(
    session: AsyncSession,
    question: str,
    roles: list[str],
    user_id: str | None,
    *,
    top_k: int,
    chunks: int,
    retrieval_ms: int,
    llm_ms: int,
    total_ms: int,
    input_tokens: int,
    output_tokens: int,
    cost: float,
) -> None:
    """Audit writes must never break a user's answer."""
    try:
        session.add(
            QueryAudit(
                user_id=user_id,
                roles=",".join(roles),
                query=question,
                chunks_retrieved=chunks,
                top_k=top_k,
                retrieval_ms=retrieval_ms,
                llm_ms=llm_ms,
                total_ms=total_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                llm_model=get_llm().model_name,
                embedding_model=settings.embedding_model,
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("failed to write audit log")
        await session.rollback()
