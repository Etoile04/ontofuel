"""Segmenter — split markdown/text into sections or chunks.

Supports multiple chunking strategies via Chonkie integration:
  1. "recursive" — RecursiveChunker (best for structured markdown docs)
  2. "semantic"  — SemanticChunker (best for unstructured text, needs embeddings)
  3. "late"      — LateChunker (embed-then-split for better context)
  4. "auto"      — Auto-detect best strategy based on document structure
  5. "fixed"     — Pure-Python fixed-size chunking (fallback, no dependencies)

Unified entry:
    >>> seg = Segmenter(strategy="auto")
    >>> chunks = seg.segment(text)

Legacy methods (backward compatible):
    >>> seg.segment_heading(md_text)
    >>> seg.segment_fixed(md_text, chunk_size=4000)
    >>> seg.segment_by_keywords(md_text, ["U3Si2"])

Requires: chonkie (optional, pip install ontofuel[chonkie-semantic])
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Any

try:
    import chonkie
    CHONKIE_AVAILABLE = True
except ImportError:
    CHONKIE_AVAILABLE = False

EMBEDDING_DEFAULTS: dict[str, Any] = {
    "provider": "sentence-transformers",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
}

VALID_STRATEGIES = {"auto", "recursive", "semantic", "late", "fixed"}


@dataclass
class Chunk:
    """A text chunk from segmentation.

    Attributes:
        index: Chunk sequence number (0-based).
        title: Section title (from heading) or "chunk_{index}".
        content: The text content.
        start_char: Start character offset in original text.
        end_char: End character offset in original text.
        level: Heading level (1-6), or 0 for fixed chunks.
        metadata: Optional metadata dict.
    """
    index: int
    title: str
    content: str
    start_char: int = 0
    end_char: int = 0
    level: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "content": self.content,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "level": self.level,
            "char_count": self.char_count,
            "line_count": self.line_count,
            "metadata": self.metadata,
        }


class Segmenter:
    """Split text into manageable chunks for extraction.

    Example:
        >>> seg = Segmenter()
        >>> chunks = seg.segment_heading("# Title\\n## Section 1\\nContent")
        >>> len(chunks)
        2
    """

    # Heading pattern: captures level and title
    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        strategy: str = "auto",
        chunk_size: int = 2048,
        overlap_size: int = 128,
        embedding_config: dict[str, Any] | None = None,
    ) -> None:
        if strategy not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Must be one of {VALID_STRATEGIES}")
        if strategy not in ("fixed", "auto") and not CHONKIE_AVAILABLE:
            warnings.warn("chonkie not installed, falling back to 'fixed' strategy.", stacklevel=2)
            strategy = "fixed"
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.embedding_config = embedding_config or EMBEDDING_DEFAULTS.copy()

    @staticmethod
    def _chonkie_to_chunk(chonkie_chunks, strategy_name: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for i, cc in enumerate(chonkie_chunks):
            text = cc.text if hasattr(cc, 'text') else str(cc)
            first_line = text.strip().split('\n')[0][:80] if text.strip() else f"chunk_{i}"
            chunks.append(Chunk(
                index=i, title=first_line, content=text,
                start_char=getattr(cc, 'start_index', 0),
                end_char=getattr(cc, 'end_index', len(text)),
                level=0,
                metadata={"strategy": strategy_name, "token_count": getattr(cc, 'token_count', 0)},
            ))
        return chunks

    def _chunk_recursive(self, text: str, chunk_size: int) -> list[Chunk]:
        from chonkie import RecursiveChunker
        chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size)
        result = chunker(text)
        return self._chonkie_to_chunk(result, "recursive")

    def segment(self, text: str, strategy: str | None = None, chunk_size: int | None = None, overlap_size: int | None = None) -> list[Chunk]:
        strat = strategy or self.strategy
        size = chunk_size or self.chunk_size
        overlap = overlap_size if overlap_size is not None else self.overlap_size

        # Fix #2: validate per-call strategy override
        if strategy is not None and strat not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy '{strat}'. Must be one of {VALID_STRATEGIES}")

        if strat == "auto":
            strat = self._detect_strategy(text)
        if strat == "recursive" and CHONKIE_AVAILABLE:
            chunks = self._chunk_recursive(text, size)
        elif strat == "semantic" and CHONKIE_AVAILABLE:
            chunks = self._chunk_semantic(text, size)
        elif strat == "late" and CHONKIE_AVAILABLE:
            chunks = self._chunk_late(text, size)
        else:
            # Fix #3: pass overlap to segment_fixed, not hardcode 0
            chunks = self.segment_fixed(text, chunk_size=size * 4, overlap=overlap)
            return chunks  # segment_fixed already handles overlap

        # Fix #3: apply overlap post-processing for Chonkie strategies
        # (overlap for fixed is handled by segment_fixed itself)
        if overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks, overlap)
        return chunks

    def _detect_strategy(self, text: str) -> str:
        headings = self.HEADING_RE.findall(text)
        line_count = text.count('\n') + 1
        heading_ratio = len(headings) / max(line_count, 1)
        if heading_ratio > 0.01:
            return "recursive"
        elif CHONKIE_AVAILABLE and self._embedding_ready():
            return "semantic"
        else:
            return "fixed"

    def _embedding_ready(self) -> bool:
        try:
            self._get_embeddings()
            return True
        except Exception:
            return False

    def _get_embeddings(self):
        from chonkie import AutoEmbeddings
        model = self.embedding_config.get("model", EMBEDDING_DEFAULTS["model"])
        return AutoEmbeddings.get_embeddings(model)

    def _chunk_semantic(self, text: str, chunk_size: int) -> list[Chunk]:
        from chonkie import SemanticChunker
        embeddings = self._get_embeddings()
        chunker = SemanticChunker(embedding_model=embeddings, chunk_size=chunk_size)
        result = chunker(text)
        return self._chonkie_to_chunk(result, "semantic")

    def _chunk_late(self, text: str, chunk_size: int) -> list[Chunk]:
        from chonkie import LateChunker
        embeddings = self._get_embeddings()
        chunker = LateChunker(embedding_model=embeddings, chunk_size=chunk_size)
        result = chunker(text)
        return self._chonkie_to_chunk(result, "late")

    def _apply_overlap(self, chunks: list[Chunk], overlap_size: int) -> list[Chunk]:
        if len(chunks) <= 1:
            return chunks
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]
            prev_words = prev.content.split()
            overlap_words = prev_words[-overlap_size:] if len(prev_words) > overlap_size else prev_words
            overlap_text = " ".join(overlap_words)
            enhanced_content = overlap_text + " " + curr.content if overlap_text else curr.content
            result.append(Chunk(
                index=i, title=curr.title, content=enhanced_content,
                start_char=curr.start_char, end_char=curr.end_char,
                level=curr.level,
                metadata={**curr.metadata, "overlap_applied": True},
            ))
        for i, chunk in enumerate(result):
            chunk.index = i
        return result

    def segment_heading(self, text: str, min_size: int = 100) -> list[Chunk]:
        """Split text by markdown headings.

        Args:
            text: Input markdown text.
            min_size: Minimum chunk size in characters. Smaller chunks are
                      merged with the previous one.

        Returns:
            List of Chunk objects, one per section.
        """
        headings = list(self.HEADING_RE.finditer(text))

        if not headings:
            # No headings found — treat entire text as one chunk
            return [Chunk(
                index=0,
                title="full_document",
                content=text.strip(),
                start_char=0,
                end_char=len(text),
                level=0,
            )]

        chunks: list[Chunk] = []
        chunk_idx = 0

        # Content before first heading
        first_start = headings[0].start()
        if first_start > 0:
            preamble = text[:first_start].strip()
            if preamble:
                chunks.append(Chunk(
                    index=chunk_idx,
                    title="preamble",
                    content=preamble,
                    start_char=0,
                    end_char=first_start,
                    level=0,
                ))
                chunk_idx += 1

        # Sections defined by headings
        for i, match in enumerate(headings):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)

            content = text[start:end].strip()

            if not content:
                continue

            chunks.append(Chunk(
                index=chunk_idx,
                title=title,
                content=content,
                start_char=match.start(),
                end_char=end,
                level=level,
            ))
            chunk_idx += 1

        # Merge small chunks into previous
        chunks = self._merge_small(chunks, min_size)

        # Re-index
        for i, chunk in enumerate(chunks):
            chunk.index = i

        return chunks

    def segment_fixed(
        self,
        text: str,
        chunk_size: int = 4000,
        overlap: int = 200,
    ) -> list[Chunk]:
        """Split text into fixed-size chunks with overlap.

        Args:
            text: Input text.
            chunk_size: Maximum characters per chunk.
            overlap: Number of overlapping characters between chunks.

        Returns:
            List of Chunk objects.
        """
        if not text.strip():
            return []

        chunks: list[Chunk] = []
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to break at paragraph boundary
            if end < len(text):
                # Look for last newline within the chunk
                last_nl = text.rfind("\n", start, end)
                if last_nl > start + chunk_size // 2:
                    end = last_nl + 1

            content = text[start:end].strip()
            if content:
                chunks.append(Chunk(
                    index=idx,
                    title=f"chunk_{idx}",
                    content=content,
                    start_char=start,
                    end_char=end,
                    level=0,
                ))
                idx += 1

            # Prevent infinite loop: if we've consumed everything, break
            if end >= len(text):
                break

            # Advance start, ensuring at least 1 char progress
            next_start = end - overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunks

    def segment_by_keywords(
        self,
        text: str,
        keywords: list[str],
        window: int = 500,
    ) -> list[Chunk]:
        """Extract chunks around keyword occurrences.

        Args:
            text: Input text.
            keywords: Keywords to search for.
            window: Characters to include before/after each match.

        Returns:
            List of Chunk objects centered on keyword matches.
        """
        chunks: list[Chunk] = []
        seen_positions: set[int] = set()
        idx = 0

        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            for match in pattern.finditer(text):
                pos = match.start()
                # Avoid overlapping chunks
                if any(abs(pos - s) < window for s in seen_positions):
                    continue
                seen_positions.add(pos)

                start = max(0, pos - window)
                end = min(len(text), pos + window)
                content = text[start:end].strip()

                if content:
                    chunks.append(Chunk(
                        index=idx,
                        title=f"keyword:{kw}",
                        content=content,
                        start_char=start,
                        end_char=end,
                        level=0,
                        metadata={"keyword": kw, "match_position": pos},
                    ))
                    idx += 1

        return chunks

    def _merge_small(self, chunks: list[Chunk], min_size: int) -> list[Chunk]:
        """Merge consecutive small chunks into the previous one."""
        if not chunks:
            return chunks

        result = [chunks[0]]
        for chunk in chunks[1:]:
            if result[-1].char_count < min_size:
                # Merge into previous
                prev = result[-1]
                prev.content += "\n\n" + chunk.content
                prev.end_char = chunk.end_char
                prev.title = f"{prev.title} + {chunk.title}"
            else:
                result.append(chunk)
        return result
