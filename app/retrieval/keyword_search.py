"""In-process BM25 keyword search (rank-bm25).

Complements dense retrieval: catches exact identifiers, policy numbers and acronyms
that embeddings routinely blur together.
"""

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.models.chunk import Chunk
from app.retrieval.embeddings import tokenize

MIN_CORPUS_SIZE = 1


@dataclass(slots=True)
class KeywordHit:
    chunk: Chunk
    score: float


class BM25Index:
    """Keyword index over an ACL-filtered candidate set."""

    def __init__(self, chunks: list) -> None:
        self.chunks = chunks
        # rank_bm25 divides by corpus_size, so an empty corpus must never be built.
        corpus = [tokenize(chunk.content) or ["<empty>"] for chunk in chunks]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 8) -> list[KeywordHit]:
        if not self.chunks or self.bm25 is None:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return [
            KeywordHit(chunk=self.chunks[index], score=float(score))
            for index, score in ranked[:top_k]
            if score > 0
        ]


def reciprocal_rank_fusion(rankings: list[list], k: int = 60) -> dict[int, float]:
    """RRF merges ranked lists without needing comparable scores.

    Each document contributes `1 / (k + rank)` to the fused score, so a document
    ranked highly by both retrievers beats one ranked highly by only a single one.
    """
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
    return fused
