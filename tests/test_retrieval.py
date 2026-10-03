"""Tests for embedding providers, BM25 fusion and ACL logic — no DB required."""

from types import SimpleNamespace

import pytest

from app.retrieval.embeddings import HashEmbedder, JinaEmbedder, tokenize
from app.retrieval.keyword_search import BM25Index, reciprocal_rank_fusion


class TestHashEmbedder:
    async def test_deterministic_for_same_input(self):
        embedder = HashEmbedder(dimension=768)
        assert await embedder.embed_query("leave policy") == await embedder.embed_query(
            "leave policy"
        )

    async def test_dimension_matches_schema(self):
        embedder = HashEmbedder(dimension=768)
        assert len(await embedder.embed_query("anything")) == 768

    async def test_unit_length_normalisation(self):
        import math

        vector = await HashEmbedder(dimension=768).embed_query("annual leave entitlement")
        assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-6)

    async def test_overlapping_text_scores_higher_than_unrelated(self):
        embedder = HashEmbedder(dimension=768)
        query = await embedder.embed_query("annual leave entitlement policy")
        related = await embedder.embed_query("annual leave entitlement for employees")
        unrelated = await embedder.embed_query("kubernetes pod autoscaling tuning")
        assert _cosine(query, related) > _cosine(query, unrelated)

    async def test_empty_text_returns_zero_vector(self):
        assert set(await HashEmbedder(64).embed_query("!!! ???")) == {0.0}

    async def test_embed_documents_matches_batch_size(self):
        texts = ["one", "two", "three"]
        assert len(await HashEmbedder(64).embed_documents(texts)) == 3

    async def test_embed_documents_empty_list(self):
        assert await HashEmbedder(64).embed_documents([]) == []


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class TestJinaEmbedderGuardrails:
    def _embedder(self) -> JinaEmbedder:
        return JinaEmbedder(
            api_key="test-key",
            model="jina-embeddings-v3",
            base_url="http://x",
            dimension=768,
        )

    def test_missing_api_key_is_rejected(self):
        with pytest.raises(ValueError, match="JINA_API_KEY"):
            JinaEmbedder(
                api_key="", model="jina-embeddings-v3", base_url="http://x", dimension=768
            )

    def test_dimension_mismatch_raises_actionable_error(self):
        with pytest.raises(ValueError, match="embedding dimension mismatch"):
            self._embedder()._validate([[0.0] * 384])

    def test_model_name_is_prefixed(self):
        assert self._embedder().model_name == "jina/jina-embeddings-v3"


class TestReciprocalRankFusion:
    def test_document_top_of_both_lists_wins(self):
        fused = reciprocal_rank_fusion([[0, 1, 2], [0, 2, 1]])
        assert max(fused, key=lambda key: fused[key]) == 0

    def test_scores_are_positive_and_finite(self):
        fused = reciprocal_rank_fusion([[0, 1], [1, 0]])
        assert all(score > 0 for score in fused.values())

    def test_single_list_still_scores(self):
        assert reciprocal_rank_fusion([[5, 6]]) == pytest.approx({5: 1 / 61, 6: 1 / 62}, rel=1e-6)

    def test_empty_input(self):
        assert reciprocal_rank_fusion([]) == {}


class TestBM25Index:
    def _chunk(self, content: str):
        return SimpleNamespace(content=content)

    def test_ranks_exact_term_match_first(self):
        chunks = [
            self._chunk("kubernetes autoscaling configuration"),
            self._chunk("annual leave entitlement table"),
            self._chunk("annual leave policy for employees"),
        ]
        hits = BM25Index(chunks).search("annual leave", top_k=3)
        assert hits
        assert "annual" in hits[0].chunk.content

    def test_returns_nothing_for_unmatched_query(self):
        chunks = [self._chunk("annual leave policy")]
        assert BM25Index(chunks).search("quantum tunneling", top_k=3) == []

    def test_empty_corpus(self):
        assert BM25Index([]).search("anything") == []


class TestTokenize:
    def test_lowercases_and_splits_on_punctuation(self):
        assert tokenize("Leave-Policy, v4.1!") == ["leave", "policy", "v4", "1"]
