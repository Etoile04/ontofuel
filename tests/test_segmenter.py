"""Tests for extraction segmenter module."""

import pytest

from ontofuel.extraction.segmenter import Segmenter, Chunk


class TestSegmentHeading:
    """Test heading-based segmentation."""

    def test_single_heading(self):
        text = "# Title\nSome content here."
        seg = Segmenter()
        chunks = seg.segment_heading(text)
        assert len(chunks) == 1
        assert chunks[0].title == "Title"
        assert "content" in chunks[0].content

    def test_multiple_headings(self):
        text = "# Title\n## Section 1\n" + "X" * 200 + "\n## Section 2\n" + "Y" * 200
        seg = Segmenter()
        chunks = seg.segment_heading(text)
        assert len(chunks) == 2
        assert chunks[0].title == "Section 1"
        assert chunks[1].title == "Section 2"

    def test_no_headings(self):
        text = "Just some plain text without any headings."
        seg = Segmenter()
        chunks = seg.segment_heading(text)
        assert len(chunks) == 1
        assert chunks[0].title == "full_document"

    def test_preamble(self):
        text = "Preamble text\n# First Section\nContent"
        seg = Segmenter()
        chunks = seg.segment_heading(text)
        # Preamble + first section
        assert len(chunks) >= 1
        # First chunk should be preamble or first section

    def test_heading_levels(self):
        text = "# H1\n" + "X" * 200 + "\n## H2\n" + "Y" * 200 + "\n### H3\n" + "Z" * 200
        seg = Segmenter()
        chunks = seg.segment_heading(text, min_size=50)
        assert len(chunks) >= 2
        levels = [c.level for c in chunks]
        assert 1 in levels or 2 in levels

    def test_empty_text(self):
        seg = Segmenter()
        chunks = seg.segment_heading("")
        assert len(chunks) == 1
        assert chunks[0].content == ""

    def test_chunk_has_indices(self):
        text = "## A\nX\n## B\nY\n## C\nZ"
        seg = Segmenter()
        chunks = seg.segment_heading(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i


class TestSegmentFixed:
    """Test fixed-size segmentation."""

    def test_basic_chunking(self):
        text = "A" * 10000
        seg = Segmenter()
        chunks = seg.segment_fixed(text, chunk_size=4000, overlap=0)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.char_count <= 4000

    def test_short_text(self):
        text = "Short text"
        seg = Segmenter()
        chunks = seg.segment_fixed(text, chunk_size=4000)
        assert len(chunks) == 1

    def test_empty_text(self):
        seg = Segmenter()
        chunks = seg.segment_fixed("")
        assert len(chunks) == 0

    def test_overlap(self):
        text = "A" * 8000
        seg = Segmenter()
        chunks = seg.segment_fixed(text, chunk_size=4000, overlap=200)
        assert len(chunks) >= 2

    def test_chunk_titles(self):
        text = "A" * 6000
        seg = Segmenter()
        chunks = seg.segment_fixed(text, chunk_size=4000)
        for i, chunk in enumerate(chunks):
            assert chunk.title == f"chunk_{i}"


class TestSegmentByKeywords:
    """Test keyword-based segmentation."""

    def test_keyword_match(self):
        text = "The U-10Mo alloy is used in nuclear fuel. It has excellent properties."
        seg = Segmenter()
        chunks = seg.segment_by_keywords(text, ["U-10Mo"], window=50)
        assert len(chunks) >= 1
        assert "U-10Mo" in chunks[0].content

    def test_no_match(self):
        text = "Nothing relevant here."
        seg = Segmenter()
        chunks = seg.segment_by_keywords(text, ["U-10Mo"])
        assert len(chunks) == 0

    def test_multiple_keywords(self):
        text = "U-10Mo has density 15.8 g/cm³. " + "X" * 200 + ". U-10Zr has density 16.3 g/cm³."
        seg = Segmenter()
        chunks = seg.segment_by_keywords(text, ["U-10Mo", "U-10Zr"], window=50)
        assert len(chunks) >= 2


class TestChunk:
    """Test Chunk dataclass."""

    def test_char_count(self):
        chunk = Chunk(index=0, title="test", content="Hello World")
        assert chunk.char_count == 11

    def test_line_count(self):
        chunk = Chunk(index=0, title="test", content="Line 1\nLine 2\nLine 3")
        assert chunk.line_count == 3

    def test_to_dict(self):
        chunk = Chunk(index=0, title="test", content="Hello")
        d = chunk.to_dict()
        assert d["index"] == 0
        assert d["title"] == "test"
        assert d["char_count"] == 5
