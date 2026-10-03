"""Hybrid retrieval: dense (pgvector) + sparse (BM25) fused with RRF."""

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chunk import Chunk
from app.retrieval.embeddings import embed_query
from app.retrieval.keyword_search import BM25Index, KeywordHit, reciprocal_rank_fusion
from app.retrieval.rerank import get_reranker, rerank_enabled
from app.retrieval.vector_store import similarity_search

logger = logging.getLogger("eraga.retrieval")
settings = get_settings()


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    dense_score: float = 0.0
    keyword_score: float = 0.0

    @property
    def content(self) -> str:
        return self.chunk.content

    @property
    def section(self) -> str | None:
        return self.chunk.section

    @property
    def page_number(self) -> int | None:
        return self.chunk.page_number

    @property
    def document_id(self):
        return self.chunk.document_id


async def hybrid_retrieve(
    session: AsyncSession,
    question: str,
    roles: list[str],
    top_k: int | None = None,
    top_n: int | None = None,
    departments: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Retrieve ACL-authorised chunks using both dense and keyword search."""
    top_k = top_k or settings.top_k
    top_n = top_n or settings.rerank_top_n

    vector = await embed_query(question)
    dense_pairs = await similarity_search(
        session, vector, roles=roles, top_k=top_k * 2, departments=departments
    )
    dense_hits = {hit.chunk.id: hit for hit in dense_pairs}
    dense_order = [hit.chunk.id for hit in dense_pairs]

    # BM25 index over the dense candidate set keeps the keyword stage in-process
    # and guarantees both stages see the same ACL-filtered pool.
    candidates = list(dense_hits.keys())
    keyword_hits: list[KeywordHit] = []
    if candidates:
        keyword_candidates = await load_chunks_by_ids(session, candidates)
        index = BM25Index(keyword_candidates)
        keyword_hits = index.search(question, top_k=top_k)

    keyword_scores = {hit.chunk.id: hit.score for hit in keyword_hits}
    keyword_order = [hit.chunk.id for hit in keyword_hits]

    # Fused keys need to be positional indices to align the two ranked lists.
    ordered_ids = list(dict.fromkeys(dense_order + keyword_order))
    id_to_position = {chunk_id: position for position, chunk_id in enumerate(ordered_ids)}
    dense_positions = [id_to_position[cid] for cid in dense_order if cid in id_to_position]
    keyword_positions = [id_to_position[cid] for cid in keyword_order if cid in id_to_position]

    fused = reciprocal_rank_fusion([dense_positions, keyword_positions])

    retrieved = [
        RetrievedChunk(
            chunk=dense_hits[ordered_ids[position]].chunk,
            score=score,
            dense_score=dense_hits[ordered_ids[position]].similarity,
            keyword_score=keyword_scores.get(ordered_ids[position], 0.0),
        )
        for position, score in sorted(fused.items(), key=lambda item: item[1], reverse=True)
        if ordered_ids[position] in dense_hits
    ]

    logger.info(
        "hybrid_retrieve q=%r dense=%d keyword=%d fused=%d returned=%d",
        question[:60],
        len(dense_order),
        len(keyword_order),
        len(retrieved),
        min(top_n, len(retrieved)),
    )

    if rerank_enabled() and len(retrieved) > 1:
        reranker = get_reranker()
        candidates = retrieved[:top_k]
        order = await reranker.rerank(
            question, [item.content for item in candidates], top_n=top_n
        )
        if order:
            reranked = [
                candidates[index] for index, _ in order if index < len(candidates)
            ]
            for item, (_, score) in zip(reranked, order, strict=False):
                item.score = score
            logger.info(
                "rerank provider=%s pool=%d -> %d",
                reranker.model_name,
                len(candidates),
                len(reranked),
            )
            return reranked[:top_n]

    return retrieved[:top_n]


async def load_chunks_by_ids(session: AsyncSession, chunk_ids: list) -> list[Chunk]:
    from app.models.chunk import Chunk

    if not chunk_ids:
        return []
    result = await session.execute(select(Chunk).where(Chunk.id.in_(chunk_ids)))
    return list(result.scalars())


async def timed_retrieve(session: AsyncSession, question: str, roles: list[str], **kwargs):
    """Wrap `hybrid_retrieve` and return `(results, elapsed_ms)`."""
    started = time.perf_counter()
    results = await hybrid_retrieve(session, question, roles, **kwargs)
    return results, int((time.perf_counter() - started) * 1000)
