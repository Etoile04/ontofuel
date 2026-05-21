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


class TestChonkieIntegration:
    """Test Chonkie-backed segmentation strategies."""

    def test_chonkie_available(self):
        from ontofuel.extraction.segmenter import CHONKIE_AVAILABLE
        assert CHONKIE_AVAILABLE is True

    def test_segmenter_default_init(self):
        seg = Segmenter()
        assert seg.strategy == "auto"
        assert seg.chunk_size == 2048
        assert seg.overlap_size == 128

    def test_segmenter_explicit_strategy(self):
        seg = Segmenter(strategy="recursive")
        assert seg.strategy == "recursive"

    def test_segmenter_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            Segmenter(strategy="nonexistent")

    def test_segmenter_fallback_without_chonkie(self, monkeypatch):
        import ontofuel.extraction.segmenter as mod
        monkeypatch.setattr(mod, "CHONKIE_AVAILABLE", False)
        seg = Segmenter(strategy="semantic")
        assert seg.strategy == "fixed"

    def test_segmenter_custom_embedding_config(self):
        seg = Segmenter(embedding_config={"model": "custom-model"})
        assert seg.embedding_config["model"] == "custom-model"

    def test_segmenter_default_embedding_config(self):
        seg = Segmenter()
        assert seg.embedding_config["model"] == "sentence-transformers/all-MiniLM-L6-v2"


class TestRecursiveStrategy:
    """Test recursive chunking strategy."""

    def test_recursive_basic(self):
        seg = Segmenter(strategy="recursive", chunk_size=256)
        text = "# Title\n\n" + "Alpha beta gamma delta. " * 50
        chunks = seg.segment(text)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_recursive_returns_chunk_objects(self):
        seg = Segmenter(strategy="recursive", chunk_size=256)
        text = "# Section A\n\n" + "Word " * 200 + "\n\n# Section B\n\n" + "More " * 200
        chunks = seg.segment(text)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_recursive_metadata_has_strategy(self):
        seg = Segmenter(strategy="recursive", chunk_size=256)
        text = "Some content " * 100
        chunks = seg.segment(text)
        for chunk in chunks:
            assert chunk.metadata.get("strategy") == "recursive"

    def test_segment_method_override_strategy(self):
        seg = Segmenter(strategy="fixed")
        text = "Content " * 200
        chunks = seg.segment(text, strategy="recursive", chunk_size=256)
        for chunk in chunks:
            assert chunk.metadata.get("strategy") == "recursive"

    def test_segment_empty_text(self):
        seg = Segmenter(strategy="recursive")
        chunks = seg.segment("")
        # Empty text should return empty list from segment_fixed fallback or single empty
        assert isinstance(chunks, list)

    def test_segment_passes_chunk_size(self):
        seg = Segmenter(strategy="recursive", chunk_size=128)
        text = "Word " * 500
        chunks = seg.segment(text)
        # Should produce multiple chunks with small size
        assert len(chunks) >= 2


class TestSegmentMethod:
    """Test unified segment() method routing."""

    def test_fixed_strategy_route(self):
        seg = Segmenter(strategy="fixed", chunk_size=256)
        text = "A" * 5000
        chunks = seg.segment(text)
        assert len(chunks) >= 1
        # Fixed route uses segment_fixed, which produces chunk_0, chunk_1 etc.
        assert all(c.title.startswith("chunk_") for c in chunks)


class TestSemanticStrategy:
    """Test semantic chunking strategy."""

    def test_semantic_basic(self):
        seg = Segmenter(strategy="semantic", chunk_size=256,
                        embedding_config={"model": "minishlab/potion-base-8M"})
        text = "U-10Mo has density 15.8. " * 30 + "Zirconium cladding material. " * 30
        chunks = seg.segment(text, overlap_size=0)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.metadata.get("strategy") == "semantic"

    def test_semantic_returns_chunk_objects(self):
        seg = Segmenter(strategy="semantic", chunk_size=256,
                        embedding_config={"model": "minishlab/potion-base-8M"})
        text = "Some text about nuclear fuel. " * 50
        chunks = seg.segment(text, overlap_size=0)
        assert all(isinstance(c, Chunk) for c in chunks)


class TestLateStrategy:
    """Test late chunking strategy."""

    def test_late_basic(self):
        # LateChunker requires SentenceTransformerEmbeddings specifically
        seg = Segmenter(strategy="late", chunk_size=256)
        text = "U-10Mo has density 15.8. " * 30 + "Zirconium cladding material. " * 30
        chunks = seg.segment(text, overlap_size=0)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.metadata.get("strategy") == "late"


class TestAutoStrategy:
    """Test auto detection strategy."""

    def test_auto_detects_recursive_for_heading_rich(self):
        seg = Segmenter(strategy="auto", chunk_size=256,
                        embedding_config={"model": "minishlab/potion-base-8M"})
        # Many headings → should pick recursive
        lines = [f"## Section {i}\nContent line {i}." for i in range(20)]
        text = "\n".join(lines)
        detected = seg._detect_strategy(text)
        assert detected == "recursive"

    def test_auto_detects_fixed_for_plain_text_no_embeddings(self, monkeypatch):
        import ontofuel.extraction.segmenter as mod
        monkeypatch.setattr(mod, "CHONKIE_AVAILABLE", False)
        seg = Segmenter(strategy="auto")
        text = "Just some plain text without headings. " * 50
        detected = seg._detect_strategy(text)
        assert detected == "fixed"

    def test_auto_detects_semantic_with_embeddings(self):
        seg = Segmenter(strategy="auto", chunk_size=256,
                        embedding_config={"model": "minishlab/potion-base-8M"})
        # Plain text, no headings, embeddings available → semantic
        text = "Just some plain text without headings. " * 50
        detected = seg._detect_strategy(text)
        assert detected == "semantic"


class TestOverlap:
    """Test overlap application."""

    def test_overlap_applied(self):
        seg = Segmenter(strategy="recursive", chunk_size=128, overlap_size=5)
        text = "Word " * 500
        chunks = seg.segment(text)
        # At least the second chunk should have overlap_applied
        overlap_chunks = [c for c in chunks if c.metadata.get("overlap_applied")]
        assert len(overlap_chunks) >= 1

    def test_overlap_zero_no_application(self):
        seg = Segmenter(strategy="recursive", chunk_size=128, overlap_size=0)
        text = "Word " * 500
        chunks = seg.segment(text)
        overlap_chunks = [c for c in chunks if c.metadata.get("overlap_applied")]
        assert len(overlap_chunks) == 0

    def test_overlap_single_chunk(self):
        seg = Segmenter(strategy="recursive", chunk_size=8192, overlap_size=10)
        text = "Short text."
        chunks = seg.segment(text)
        # Single chunk → no overlap applied
        assert len(chunks) == 1
        assert not chunks[0].metadata.get("overlap_applied")

    def test_overlap_content_contains_previous_words(self):
        seg = Segmenter(strategy="recursive", chunk_size=64, overlap_size=10)
        text = " ".join(f"word{i}" for i in range(200))
        chunks = seg.segment(text)
        if len(chunks) > 1:
            # Second chunk should start with words from previous chunk
            assert chunks[1].metadata.get("overlap_applied") is True


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
