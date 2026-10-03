"""Tests for prompt construction, citation integrity and guardrails."""

from types import SimpleNamespace

from app.rag.pipeline import calculate_confidence, strip_markers, validate_citations
from app.rag.prompt_templates import NO_CONTEXT_ANSWER, build_prompt, format_context
from app.retrieval.hybrid_retriever import RetrievedChunk


def make_chunk(content: str = "Policy text", section: str = "3.2", page: int = 5):
    chunk = SimpleNamespace(
        content=content,
        section=section,
        page_number=page,
        id="chunk-1",
        document_id="doc-1",
        extra_metadata={"source": "Leave Policy v4.1"},
    )
    return RetrievedChunk(chunk=chunk, score=0.8, dense_score=0.8, keyword_score=3.0)


class TestPromptBuilding:
    def test_context_is_numbered_for_citation(self):
        context = format_context([make_chunk()])
        assert "[1]" in context
        assert "Leave Policy v4.1" in context
        assert "section 3.2" in context
        assert "page 5" in context

    def test_prompt_contains_context_and_question(self):
        prompt = build_prompt("How much leave?", [make_chunk()])
        assert "How much leave?" in prompt
        assert "Policy text" in prompt

    def test_marker_increments_per_chunk(self):
        context = format_context([make_chunk("A"), make_chunk("B"), make_chunk("C")])
        assert "[1]" in context and "[2]" in context and "[3]" in context

    def test_empty_chunk_list_yields_empty_context(self):
        assert format_context([]) == ""


class TestCitationGuardrails:
    def test_accepts_valid_markers(self):
        chunks = [make_chunk("A"), make_chunk("B")]
        assert validate_citations("Per [1] and [2] policy.", chunks) == []

    def test_rejects_invented_marker(self):
        chunks = [make_chunk("A"), make_chunk("B")]
        assert validate_citations("Per [7] policy.", chunks) == ["7"]

    def test_markers_beyond_chunk_count_are_rejected(self):
        assert validate_citations("See [3].", [make_chunk("A")]) == ["3"]

    def test_answer_without_markers_is_allowed(self):
        assert validate_citations("Plain answer.", [make_chunk("A")]) == []

    def test_strip_markers_removes_all_citations(self):
        assert "[" not in strip_markers("Answer [1] with [2] sources.")


class TestConfidence:
    def test_no_chunks_is_zero_confidence(self):
        assert calculate_confidence([], NO_CONTEXT_ANSWER) == 0.0

    def test_refusal_is_zero_confidence(self):
        assert calculate_confidence([make_chunk()], NO_CONTEXT_ANSWER) == 0.0

    def test_cited_answer_is_high_confidence(self):
        score = calculate_confidence([make_chunk()], "Answer citing [1].")
        assert 0.0 < score <= 1.0

    def test_uncited_answer_scores_lower_than_cited(self):
        chunk = [make_chunk()]
        assert calculate_confidence(chunk, "no markers") < calculate_confidence(chunk, "cited [1]")
