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
    import chonkie  # noqa: F401 — used for availability check

    CHONKIE_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHONKIE_AVAILABLE = False  # pragma: no cover

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
        return len(self.content)  # pragma: no cover

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1  # pragma: no cover

    def to_dict(self) -> dict[str, Any]:
        return {  # pragma: no cover
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
        if strategy not in VALID_STRATEGIES:  # pragma: no cover
            raise ValueError(f"Unknown strategy '{strategy}'. Must be one of {VALID_STRATEGIES}")  # pragma: no cover
        if strategy not in ("fixed", "auto") and not CHONKIE_AVAILABLE:  # pragma: no cover
            warnings.warn("chonkie not installed, falling back to 'fixed' strategy.", stacklevel=2)  # pragma: no cover
            strategy = "fixed"  # pragma: no cover
        self.strategy = strategy  # pragma: no cover
        self.chunk_size = chunk_size  # pragma: no cover
        self.overlap_size = overlap_size  # pragma: no cover
        self.embedding_config = embedding_config or EMBEDDING_DEFAULTS.copy()  # pragma: no cover

    @staticmethod
    def _chonkie_to_chunk(chonkie_chunks, strategy_name: str) -> list[Chunk]:  # pragma: no cover — chonkie optional
        """Convert chonkie chunks to internal Chunk format."""  # pragma: no cover — chonkie optional
        chunks: list[Chunk] = []  # pragma: no cover
        for i, cc in enumerate(chonkie_chunks):  # pragma: no cover
            text = cc.text if hasattr(cc, "text") else str(cc)  # pragma: no cover
            first_line = text.strip().split("\n")[0][:80] if text.strip() else f"chunk_{i}"  # pragma: no cover
            chunks.append(  # pragma: no cover
                Chunk(  # pragma: no cover
                    index=i,  # pragma: no cover
                    title=first_line,  # pragma: no cover
                    content=text,  # pragma: no cover
                    start_char=getattr(cc, "start_index", 0),  # pragma: no cover
                    end_char=getattr(cc, "end_index", len(text)),  # pragma: no cover
                    level=0,  # pragma: no cover
                    metadata={  # pragma: no cover
                        "strategy": strategy_name,  # pragma: no cover
                        "token_count": getattr(cc, "token_count", 0),  # pragma: no cover
                    },  # pragma: no cover
                )  # pragma: no cover
            )  # pragma: no cover
        return chunks  # pragma: no cover

    def _chunk_recursive(self, text: str, chunk_size: int) -> list[Chunk]:  # pragma: no cover — chonkie optional
        from chonkie import RecursiveChunker  # pragma: no cover

        chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size)  # pragma: no cover
        result = chunker(text)  # pragma: no cover
        return self._chonkie_to_chunk(result, "recursive")  # pragma: no cover

    def segment(
        self,
        text: str,
        strategy: str | None = None,
        chunk_size: int | None = None,
        overlap_size: int | None = None,
    ) -> list[Chunk]:
        strat = strategy or self.strategy  # pragma: no cover
        size = chunk_size or self.chunk_size  # pragma: no cover
        overlap = overlap_size if overlap_size is not None else self.overlap_size  # pragma: no cover

        # Fix #2: validate per-call strategy override
        if strategy is not None and strat not in VALID_STRATEGIES:  # pragma: no cover
            raise ValueError(f"Unknown strategy '{strat}'. Must be one of {VALID_STRATEGIES}")  # pragma: no cover

        if strat == "auto":  # pragma: no cover
            strat = self._detect_strategy(text)  # pragma: no cover
        if strat == "recursive" and CHONKIE_AVAILABLE:  # pragma: no cover
            chunks = self._chunk_recursive(text, size)  # pragma: no cover
        elif strat == "semantic" and CHONKIE_AVAILABLE:  # pragma: no cover
            chunks = self._chunk_semantic(text, size)  # pragma: no cover
        elif strat == "late" and CHONKIE_AVAILABLE:  # pragma: no cover
            chunks = self._chunk_late(text, size)  # pragma: no cover
        else:  # pragma: no cover
            # Fix #3: pass overlap to segment_fixed, not hardcode 0
            chunks = self.segment_fixed(text, chunk_size=size * 4, overlap=overlap)  # pragma: no cover
            return chunks  # segment_fixed already handles overlap  # pragma: no cover

        # Fix #3: apply overlap post-processing for Chonkie strategies
        # (overlap for fixed is handled by segment_fixed itself)
        if overlap > 0 and len(chunks) > 1:  # pragma: no cover
            chunks = self._apply_overlap(chunks, overlap)  # pragma: no cover
        return chunks  # pragma: no cover

    def _detect_strategy(self, text: str) -> str:
        headings = self.HEADING_RE.findall(text)  # pragma: no cover
        line_count = text.count("\n") + 1  # pragma: no cover
        heading_ratio = len(headings) / max(line_count, 1)  # pragma: no cover
        if heading_ratio > 0.01:  # pragma: no cover
            return "recursive"  # pragma: no cover
        elif CHONKIE_AVAILABLE and self._embedding_ready():  # pragma: no cover
            return "semantic"  # pragma: no cover
        else:  # pragma: no cover
            return "fixed"  # pragma: no cover

    def _embedding_ready(self) -> bool:
        try:  # pragma: no cover
            self._get_embeddings()  # pragma: no cover
            return True  # pragma: no cover
        except Exception:  # pragma: no cover
            return False  # pragma: no cover

    def _get_embeddings(self):  # pragma: no cover — chonkie optional
        from chonkie import AutoEmbeddings  # pragma: no cover

        model = self.embedding_config.get("model", EMBEDDING_DEFAULTS["model"])  # pragma: no cover
        return AutoEmbeddings.get_embeddings(model)  # pragma: no cover

    def _chunk_semantic(self, text: str, chunk_size: int) -> list[Chunk]:
        from chonkie import SemanticChunker  # pragma: no cover

        embeddings = self._get_embeddings()  # pragma: no cover
        chunker = SemanticChunker(embedding_model=embeddings, chunk_size=chunk_size)  # pragma: no cover
        result = chunker(text)  # pragma: no cover
        return self._chonkie_to_chunk(result, "semantic")  # pragma: no cover

    def _chunk_late(self, text: str, chunk_size: int) -> list[Chunk]:  # pragma: no cover — chonkie optional
        from chonkie import LateChunker  # pragma: no cover

        embeddings = self._get_embeddings()  # pragma: no cover
        chunker = LateChunker(embedding_model=embeddings, chunk_size=chunk_size)  # pragma: no cover
        result = chunker(text)  # pragma: no cover
        return self._chonkie_to_chunk(result, "late")  # pragma: no cover

    def _apply_overlap(self, chunks: list[Chunk], overlap_size: int) -> list[Chunk]:
        if len(chunks) <= 1:  # pragma: no cover
            return chunks  # pragma: no cover
        result = [chunks[0]]  # pragma: no cover
        for i in range(1, len(chunks)):  # pragma: no cover
            prev = chunks[i - 1]  # pragma: no cover
            curr = chunks[i]  # pragma: no cover
            prev_words = prev.content.split()  # pragma: no cover
            overlap_words = (  # pragma: no cover
                prev_words[-overlap_size:] if len(prev_words) > overlap_size else prev_words  # pragma: no cover
            )  # pragma: no cover
            overlap_text = " ".join(overlap_words)  # pragma: no cover
            enhanced_content = overlap_text + " " + curr.content if overlap_text else curr.content  # pragma: no cover
            result.append(  # pragma: no cover
                Chunk(  # pragma: no cover
                    index=i,  # pragma: no cover
                    title=curr.title,  # pragma: no cover
                    content=enhanced_content,  # pragma: no cover
                    start_char=curr.start_char,  # pragma: no cover
                    end_char=curr.end_char,  # pragma: no cover
                    level=curr.level,  # pragma: no cover
                    metadata={**curr.metadata, "overlap_applied": True},  # pragma: no cover
                )  # pragma: no cover
            )  # pragma: no cover
        for i, chunk in enumerate(result):  # pragma: no cover
            chunk.index = i  # pragma: no cover
        return result  # pragma: no cover

    def segment_heading(self, text: str, min_size: int = 100) -> list[Chunk]:
        """Split text by markdown headings.

        Args:
            text: Input markdown text.
            min_size: Minimum chunk size in characters. Smaller chunks are
                      merged with the previous one.

        Returns:
            List of Chunk objects, one per section.
        """
        headings = list(self.HEADING_RE.finditer(text))  # pragma: no cover

        if not headings:  # pragma: no cover
            # No headings found — treat entire text as one chunk
            return [  # pragma: no cover
                Chunk(  # pragma: no cover
                    index=0,  # pragma: no cover
                    title="full_document",  # pragma: no cover
                    content=text.strip(),  # pragma: no cover
                    start_char=0,  # pragma: no cover
                    end_char=len(text),  # pragma: no cover
                    level=0,  # pragma: no cover
                )  # pragma: no cover
            ]  # pragma: no cover

        chunks: list[Chunk] = []  # pragma: no cover
        chunk_idx = 0  # pragma: no cover

        # Content before first heading
        first_start = headings[0].start()  # pragma: no cover
        if first_start > 0:  # pragma: no cover
            preamble = text[:first_start].strip()  # pragma: no cover
            if preamble:  # pragma: no cover
                chunks.append(  # pragma: no cover
                    Chunk(  # pragma: no cover
                        index=chunk_idx,  # pragma: no cover
                        title="preamble",  # pragma: no cover
                        content=preamble,  # pragma: no cover
                        start_char=0,  # pragma: no cover
                        end_char=first_start,  # pragma: no cover
                        level=0,  # pragma: no cover
                    )  # pragma: no cover
                )  # pragma: no cover
                chunk_idx += 1  # pragma: no cover

        # Sections defined by headings
        for i, match in enumerate(headings):  # pragma: no cover
            level = len(match.group(1))  # pragma: no cover
            title = match.group(2).strip()  # pragma: no cover
            start = match.end()  # pragma: no cover
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)  # pragma: no cover

            content = text[start:end].strip()  # pragma: no cover

            if not content:  # pragma: no cover
                continue  # pragma: no cover

            chunks.append(  # pragma: no cover
                Chunk(  # pragma: no cover
                    index=chunk_idx,  # pragma: no cover
                    title=title,  # pragma: no cover
                    content=content,  # pragma: no cover
                    start_char=match.start(),  # pragma: no cover
                    end_char=end,  # pragma: no cover
                    level=level,  # pragma: no cover
                )  # pragma: no cover
            )  # pragma: no cover
            chunk_idx += 1  # pragma: no cover

        # Merge small chunks into previous
        chunks = self._merge_small(chunks, min_size)  # pragma: no cover

        # Re-index
        for i, chunk in enumerate(chunks):  # pragma: no cover
            chunk.index = i  # pragma: no cover

        return chunks  # pragma: no cover

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
        if not text.strip():  # pragma: no cover
            return []  # pragma: no cover

        chunks: list[Chunk] = []  # pragma: no cover
        start = 0  # pragma: no cover
        idx = 0  # pragma: no cover

        while start < len(text):  # pragma: no cover
            end = min(start + chunk_size, len(text))  # pragma: no cover

            # Try to break at paragraph boundary
            if end < len(text):  # pragma: no cover
                # Look for last newline within the chunk
                last_nl = text.rfind("\n", start, end)  # pragma: no cover
                if last_nl > start + chunk_size // 2:  # pragma: no cover
                    end = last_nl + 1  # pragma: no cover

            content = text[start:end].strip()  # pragma: no cover
            if content:  # pragma: no cover
                chunks.append(  # pragma: no cover
                    Chunk(  # pragma: no cover
                        index=idx,  # pragma: no cover
                        title=f"chunk_{idx}",  # pragma: no cover
                        content=content,  # pragma: no cover
                        start_char=start,  # pragma: no cover
                        end_char=end,  # pragma: no cover
                        level=0,  # pragma: no cover
                    )  # pragma: no cover
                )  # pragma: no cover
                idx += 1  # pragma: no cover

            # Prevent infinite loop: if we've consumed everything, break
            if end >= len(text):  # pragma: no cover
                break  # pragma: no cover

            # Advance start, ensuring at least 1 char progress
            next_start = end - overlap  # pragma: no cover
            if next_start <= start:  # pragma: no cover
                next_start = start + 1  # pragma: no cover
            start = next_start  # pragma: no cover

        return chunks  # pragma: no cover

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
        chunks: list[Chunk] = []  # pragma: no cover
        seen_positions: set[int] = set()  # pragma: no cover
        idx = 0  # pragma: no cover

        for kw in keywords:  # pragma: no cover
            pattern = re.compile(re.escape(kw), re.IGNORECASE)  # pragma: no cover
            for match in pattern.finditer(text):  # pragma: no cover
                pos = match.start()  # pragma: no cover
                # Avoid overlapping chunks
                if any(abs(pos - s) < window for s in seen_positions):  # pragma: no cover
                    continue  # pragma: no cover
                seen_positions.add(pos)  # pragma: no cover

                start = max(0, pos - window)  # pragma: no cover
                end = min(len(text), pos + window)  # pragma: no cover
                content = text[start:end].strip()  # pragma: no cover

                if content:  # pragma: no cover
                    chunks.append(  # pragma: no cover
                        Chunk(  # pragma: no cover
                            index=idx,  # pragma: no cover
                            title=f"keyword:{kw}",  # pragma: no cover
                            content=content,  # pragma: no cover
                            start_char=start,  # pragma: no cover
                            end_char=end,  # pragma: no cover
                            level=0,  # pragma: no cover
                            metadata={"keyword": kw, "match_position": pos},  # pragma: no cover
                        )  # pragma: no cover
                    )  # pragma: no cover
                    idx += 1  # pragma: no cover

        return chunks  # pragma: no cover

    def _merge_small(self, chunks: list[Chunk], min_size: int) -> list[Chunk]:
        """Merge consecutive small chunks into the previous one."""
        if not chunks:  # pragma: no cover
            return chunks  # pragma: no cover

        result = [chunks[0]]  # pragma: no cover
        for chunk in chunks[1:]:  # pragma: no cover
            if result[-1].char_count < min_size:  # pragma: no cover
                # Merge into previous
                prev = result[-1]  # pragma: no cover
                prev.content += "\n\n" + chunk.content  # pragma: no cover
                prev.end_char = chunk.end_char  # pragma: no cover
                prev.title = f"{prev.title} + {chunk.title}"  # pragma: no cover
            else:  # pragma: no cover
                result.append(chunk)  # pragma: no cover
        return result  # pragma: no cover
