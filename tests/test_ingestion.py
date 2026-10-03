"""Tests for cleaning, chunking and loading — all offline, no DB or models needed."""

from pathlib import Path

import pytest

from app.ingestion.chunker import chunk_blocks
from app.ingestion.cleaner import clean, clean_blocks
from app.ingestion.loaders import DocumentBlock, load


class TestCleaner:
    def test_collapses_excess_whitespace(self):
        assert clean("a   b\n\n\n\nc") == "a b\n\nc"

    def test_repairs_hyphenated_line_breaks(self):
        assert clean("deploy-\nment policy") == "deployment policy"

    def test_removes_running_page_headers(self):
        raw = "Section 2 Overview\nPage 3\nSection 2 Overview\nThe actual content here."
        assert "Page 3" not in clean(raw)

    def test_drops_consecutive_duplicate_lines(self):
        assert clean("Repeated header\nUnique body text") == "Repeated header\nUnique body text"

    def test_empty_input(self):
        assert clean("") == ""

    def test_clean_blocks_drops_empty_results(self):
        blocks = [
            DocumentBlock(text="   ", page_number=1),
            DocumentBlock(text="real text", page_number=2),
        ]
        cleaned = clean_blocks(blocks)
        assert len(cleaned) == 1
        assert cleaned[0].page_number == 2


class TestChunker:
    def test_splits_long_text_and_respects_size(self):
        blocks = [DocumentBlock(text="x" * 3000, page_number=1)]
        chunks = chunk_blocks(blocks, chunk_size=900, chunk_overlap=120)
        assert len(chunks) > 1
        assert all(chunk.char_count <= 900 for chunk in chunks)

    def test_preserves_page_and_section_metadata(self):
        blocks = [DocumentBlock(text="content " * 100, page_number=7, section="3.2 Leave")]
        chunks = chunk_blocks(blocks)
        assert all(chunk.page_number == 7 for chunk in chunks)
        assert all(chunk.section == "3.2 Leave" for chunk in chunks)

    def test_drops_tiny_fragments(self):
        blocks = [DocumentBlock(text="ok " * 40, page_number=1)]
        chunks = chunk_blocks(blocks, min_chunk_chars=40)
        assert all(chunk.char_count >= 40 for chunk in chunks)

    def test_rejects_overlap_larger_than_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_blocks([DocumentBlock(text="x" * 100)], chunk_size=100, chunk_overlap=100)

    def test_empty_input_yields_no_chunks(self):
        assert chunk_blocks([DocumentBlock(text="   ")]) == []


class TestLoaders:
    def test_loads_markdown_with_sections(self, tmp_path: Path):
        source = tmp_path / "policy.md"
        source.write_text("# Leave Policy\n\nIntro text.\n\n## Accrual\n\nAccrual details here.\n")
        blocks = load(source)
        assert len(blocks) >= 2
        assert any(block.section == "Leave Policy" for block in blocks)

    def test_loads_plain_text(self, tmp_path: Path):
        source = tmp_path / "notes.txt"
        source.write_text("Just some plain text content.")
        assert load(source)[0].text.startswith("Just some plain text")

    def test_loads_html_and_strips_scripts(self, tmp_path: Path):
        source = tmp_path / "page.html"
        source.write_text(
            "<html><body><script>evil()</script>"
            "<h1>Policy</h1><p>Visible body text.</p></body></html>"
        )
        combined = " ".join(block.text for block in load(source))
        assert "Visible body text" in combined
        assert "evil()" not in combined

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load("does-not-exist.pdf")

    def test_unsupported_type_raises(self, tmp_path: Path):
        source = tmp_path / "data.xlsx"
        source.write_text("binary-ish")
        with pytest.raises(ValueError, match="unsupported document type"):
            load(source)

    def test_empty_file_raises(self, tmp_path: Path):
        source = tmp_path / "empty.txt"
        source.write_text("")
        with pytest.raises(ValueError, match="no text extracted"):
            load(source)
