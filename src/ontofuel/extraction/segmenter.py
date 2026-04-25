"""Segmenter — split markdown/text into sections or fixed-size chunks.

Supports two modes:
  1. Heading-based segmentation (uses ##/### markers)
  2. Fixed-size chunking (by character or line count)

Example:
    >>> seg = Segmenter()
    >>> chunks = seg.segment_heading(md_text)
    >>> chunks = seg.segment_fixed(md_text, chunk_size=4000)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


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
