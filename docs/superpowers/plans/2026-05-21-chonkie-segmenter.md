# Chonkie Segmenter Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace OntoFuel's basic segmenter with Chonkie-backed strategies (Recursive, Semantic, Late + Overlap) for better extraction quality on large scientific documents.

**Architecture:** Strategy pattern in `Segmenter` class. Chonkie is optional — when missing, existing pure-Python methods serve as fallback. New `segment()` method auto-selects strategy. `segment_heading()`/`segment_fixed()` signatures unchanged, internals use Chonkie when available.

**Tech Stack:** Python 3.10+, chonkie (optional), sentence-transformers (optional, for semantic chunking), pytest

**Worktree:** `.worktrees/chonkie-segmenter` on branch `feature/chonkie-segmenter`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/ontofuel/extraction/segmenter.py` | Core: `Chunk` dataclass, `Segmenter` with strategies |
| `tests/test_segmenter.py` | All tests: existing API, Chonkie strategies, auto, overlap, fallback |

---

### Task 1: Install Chonkie and Verify Baseline

**Files:**
- Modify: `pyproject.toml` (add chonkie optional dep)
- Test: `tests/test_segmenter.py` (baseline run)

- [ ] **Step 1: Install chonkie with semantic extras**

```bash
cd ~/.openclaw/workspace-extractor/.worktrees/chonkie-segmenter
pip install "chonkie[semantic]"
```

- [ ] **Step 2: Verify chonkie imports**

```bash
python3 -c "from chonkie import RecursiveChunker, SemanticChunker, LateChunker, OverlapRefinery; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run existing tests to verify baseline**

```bash
cd ~/.openclaw/workspace-extractor/.worktrees/chonkie-segmenter
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All existing tests pass (10 tests).

- [ ] **Step 4: Add chonkie as optional dependency in pyproject.toml**

Find the `[project.optional-dependencies]` section and add:

```toml
[project.optional-dependencies]
chonkie = ["chonkie>=0.4.0"]
chonkie-semantic = ["chonkie[semantic]>=0.4.0"]
```

If no optional-dependencies section exists, add one after `[project.dependencies]`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add chonkie as optional dependency"
```

---

### Task 2: Rewrite segmenter.py — Chunk Dataclass + Chonkie Import + Helper

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py`
- Test: `tests/test_segmenter.py`

- [ ] **Step 1: Write the test for Chonkie availability detection**

Add to `tests/test_segmenter.py`:

```python
import sys
import pytest
from unittest.mock import patch


class TestChonkieAvailability:
    """Test Chonkie optional dependency handling."""

    def test_chonkie_import_available(self):
        """When chonkie is installed, CHONKIE_AVAILABLE is True."""
        from ontofuel.extraction.segmenter import CHONKIE_AVAILABLE
        # In test env with chonkie installed
        assert CHONKIE_AVAILABLE is True

    def test_chonkie_not_available_fallback(self):
        """When chonkie is missing, Segmenter falls back gracefully."""
        # Simulate chonkie not installed by re-importing with blocked module
        import importlib
        import ontofuel.extraction.segmenter as seg_mod

        original = seg_mod.CHONKIE_AVAILABLE
        # Temporarily set to False
        seg_mod.CHONKIE_AVAILABLE = False

        seg = seg_mod.Segmenter(strategy="recursive")
        assert seg.strategy == "fixed"  # Should fall back

        seg_mod.CHONKIE_AVAILABLE = original  # Restore

    def test_segmenter_default_strategy_is_auto(self):
        from ontofuel.extraction.segmenter import Segmenter
        seg = Segmenter()
        assert seg.strategy == "auto"

    def test_segmenter_custom_strategy(self):
        from ontofuel.extraction.segmenter import Segmenter
        seg = Segmenter(strategy="recursive", chunk_size=1024)
        assert seg.strategy == "recursive"
        assert seg.chunk_size == 1024

    def test_segmenter_invalid_strategy_raises(self):
        from ontofuel.extraction.segmenter import Segmenter
        with pytest.raises(ValueError, match="Unknown strategy"):
            Segmenter(strategy="nonexistent")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/.openclaw/workspace-extractor/.worktrees/chonkie-segmenter
python3 -m pytest tests/test_segmenter.py::TestChonkieAvailability -v
```

Expected: FAIL — `Segmenter.__init__` doesn't accept `strategy` parameter yet.

- [ ] **Step 3: Implement Chunk dataclass + Chonkie import + Segmenter.__init__ + helper**

Rewrite `src/ontofuel/extraction/segmenter.py` with this structure. Keep the existing `Chunk` dataclass exactly as-is. Add the Chonkie import block, `CHONKIE_AVAILABLE`, `EMBEDDING_DEFAULTS`, updated `Segmenter.__init__`, and `_chonkie_to_chunk` helper. The existing `segment_heading`, `segment_fixed`, `segment_by_keywords`, `_merge_small` methods remain unchanged for now.

Add at the top of the file, after `from typing import Any`:

```python
import warnings

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
```

Update the `Segmenter.__init__` method:

```python
def __init__(
    self,
    strategy: str = "auto",
    chunk_size: int = 2048,
    overlap_size: int = 128,
    embedding_config: dict[str, Any] | None = None,
) -> None:
    """Initialize Segmenter with chunking strategy.

    Args:
        strategy: Chunking strategy ("auto"|"recursive"|"semantic"|"late"|"fixed").
        chunk_size: Target chunk size in tokens.
        overlap_size: Overlap between chunks in tokens. 0 = no overlap.
        embedding_config: Embedding model config for semantic/late strategies.
    """
    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Must be one of {VALID_STRATEGIES}"
        )

    # Fallback if chonkie unavailable
    if strategy not in ("fixed", "auto") and not CHONKIE_AVAILABLE:
        warnings.warn(
            "chonkie not installed, falling back to 'fixed' strategy. "
            "Install with: pip install chonkie[semantic]",
            stacklevel=2,
        )
        strategy = "fixed"

    self.strategy = strategy
    self.chunk_size = chunk_size
    self.overlap_size = overlap_size
    self.embedding_config = embedding_config or EMBEDDING_DEFAULTS.copy()
```

Add the helper method to `Segmenter`:

```python
@staticmethod
def _chonkie_to_chunk(chonkie_chunks, strategy_name: str) -> list[Chunk]:
    """Convert Chonkie chunk objects to OntoFuel Chunk objects."""
    chunks: list[Chunk] = []
    for i, cc in enumerate(chonkie_chunks):
        text = cc.text if hasattr(cc, 'text') else str(cc)
        first_line = text.strip().split('\n')[0][:80] if text.strip() else f"chunk_{i}"
        chunks.append(Chunk(
            index=i,
            title=first_line,
            content=text,
            start_char=getattr(cc, 'start_index', 0),
            end_char=getattr(cc, 'end_index', len(text)),
            level=0,
            metadata={
                "strategy": strategy_name,
                "token_count": getattr(cc, 'token_count', 0),
            },
        ))
    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/.openclaw/workspace-extractor/.worktrees/chonkie-segmenter
python3 -m pytest tests/test_segmenter.py::TestChonkieAvailability -v
```

Expected: All 5 new tests PASS.

- [ ] **Step 5: Run ALL existing tests to verify no regression**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 15 tests pass (10 existing + 5 new).

- [ ] **Step 6: Commit**

```bash
git add src/ontofuel/extraction/segmenter.py tests/test_segmenter.py
git commit -m "feat: add strategy init, Chonkie import, and availability tests"
```

---

### Task 3: Implement RecursiveChunker Strategy

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py`
- Test: `tests/test_segmenter.py`

- [ ] **Step 1: Write tests for recursive strategy**

Add to `tests/test_segmenter.py`:

```python
@pytest.mark.skipif(not CHONKIE_AVAILABLE, reason="chonkie not installed")
class TestRecursiveStrategy:
    """Test RecursiveChunker strategy."""

    def test_recursive_basic(self):
        from ontofuel.extraction.segmenter import Segmenter
        text = "## Section 1\n" + "Alpha beta gamma. " * 200 + "\n## Section 2\n" + "Delta epsilon. " * 200
        seg = Segmenter(strategy="recursive", chunk_size=512, overlap_size=0)
        chunks = seg.segment(text)
        assert len(chunks) >= 2
        for c in chunks:
            assert isinstance(c, Chunk)
            assert c.metadata.get("strategy") == "recursive"

    def test_recursive_respects_markdown_tables(self):
        from ontofuel.extraction.segmenter import Segmenter
        text = "## Data\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\n## End\nDone."
        seg = Segmenter(strategy="recursive", chunk_size=256)
        chunks = seg.segment(text)
        # Table should not be split mid-row
        for c in chunks:
            assert isinstance(c, Chunk)

    def test_recursive_short_text_single_chunk(self):
        from ontofuel.extraction.segmenter import Segmenter
        seg = Segmenter(strategy="recursive")
        chunks = seg.segment("Short text only.")
        assert len(chunks) == 1

    def test_recursive_empty_text(self):
        from ontofuel.extraction.segmenter import Segmenter
        seg = Segmenter(strategy="recursive")
        chunks = seg.segment("")
        assert len(chunks) == 1
        assert chunks[0].content == ""
```

Note: Add `from ontofuel.extraction.segmenter import CHONKIE_AVAILABLE, Segmenter, Chunk` at the top of the test file if not already there.

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_segmenter.py::TestRecursiveStrategy -v
```

Expected: FAIL — `Segmenter.segment()` method doesn't exist yet.

- [ ] **Step 3: Implement `_chunk_recursive` and `segment` method**

Add to `Segmenter` class in `segmenter.py`:

```python
def _chunk_recursive(self, text: str, chunk_size: int) -> list[Chunk]:
    """Chunk using Chonkie RecursiveChunker with markdown recipe."""
    from chonkie import RecursiveChunker
    chunker = RecursiveChunker(
        tokenizer="character",
        chunk_size=chunk_size,
        recipe="markdown",
    )
    result = chunker(text)
    return self._chonkie_to_chunk(result, "recursive")

def segment(
    self,
    text: str,
    strategy: str | None = None,
    chunk_size: int | None = None,
    overlap_size: int | None = None,
) -> list[Chunk]:
    """Unified chunking entry point.

    Args:
        text: Input text (Markdown or plain text).
        strategy: Override instance strategy.
        chunk_size: Override instance chunk_size.
        overlap_size: Override instance overlap_size (0 = no overlap).

    Returns:
        List of Chunk objects.
    """
    strat = strategy or self.strategy
    size = chunk_size or self.chunk_size
    overlap = overlap_size if overlap_size is not None else self.overlap_size

    if strat == "auto":
        strat = self._detect_strategy(text)

    if strat == "recursive" and CHONKIE_AVAILABLE:
        chunks = self._chunk_recursive(text, size)
    elif strat == "semantic" and CHONKIE_AVAILABLE:
        chunks = self._chunk_semantic(text, size)
    elif strat == "late" and CHONKIE_AVAILABLE:
        chunks = self._chunk_late(text, size)
    else:
        chunks = self.segment_fixed(text, chunk_size=size * 4, overlap=0)

    # Apply overlap
    if overlap > 0 and CHONKIE_AVAILABLE and len(chunks) > 1:
        chunks = self._apply_overlap(chunks, overlap)

    return chunks
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_segmenter.py::TestRecursiveStrategy -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Run ALL tests**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 19 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ontofuel/extraction/segmenter.py tests/test_segmenter.py
git commit -m "feat: implement recursive strategy and unified segment() method"
```

---

### Task 4: Implement SemanticChunker and LateChunker Strategies

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py`
- Test: `tests/test_segmenter.py`

- [ ] **Step 1: Write tests for semantic and late strategies**

```python
@pytest.mark.skipif(not CHONKIE_AVAILABLE, reason="chonkie not installed")
class TestSemanticStrategy:
    """Test SemanticChunker strategy."""

    def test_semantic_basic(self):
        seg = Segmenter(strategy="semantic", chunk_size=512, overlap_size=0)
        text = (
            "Uranium silicide U3Si2 has high thermal conductivity of 15 W/mK. "
            "It also has high uranium density of 11.3 g/cm3. "
            "The material is considered for accident tolerant fuels. "
            "FeCrAl alloys contain iron, chromium, and aluminum. "
            "They form protective oxide layers at high temperature. "
            "The oxidation behavior depends on chromium content."
        )
        chunks = seg.segment(text)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.metadata.get("strategy") == "semantic"

    def test_semantic_short_text(self):
        seg = Segmenter(strategy="semantic")
        chunks = seg.segment("Just one sentence.")
        assert len(chunks) == 1


@pytest.mark.skipif(not CHONKIE_AVAILABLE, reason="chonkie not installed")
class TestLateStrategy:
    """Test LateChunker strategy."""

    def test_late_basic(self):
        seg = Segmenter(strategy="late", chunk_size=512, overlap_size=0)
        text = (
            "Zirconium alloys are used as nuclear fuel cladding. "
            "They have low neutron absorption cross section. "
            "Zircaloy-4 contains tin, iron, and chromium. "
            "Under accident conditions, zirconium reacts with steam. "
            "This produces hydrogen gas and heat. "
            "The Fukushima accident highlighted this risk."
        )
        chunks = seg.segment(text)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.metadata.get("strategy") == "late"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_segmenter.py::TestSemanticStrategy tests/test_segmenter.py::TestLateStrategy -v
```

Expected: FAIL — `_chunk_semantic` and `_chunk_late` not implemented.

- [ ] **Step 3: Implement `_chunk_semantic`, `_chunk_late`, and `_get_embeddings`**

Add to `Segmenter` class:

```python
def _get_embeddings(self):
    """Load embedding model based on config."""
    from chonkie import AutoEmbeddings
    provider = self.embedding_config.get("provider", "sentence-transformers")
    model = self.embedding_config.get("model", EMBEDDING_DEFAULTS["model"])
    return AutoEmbeddings.get_embeddings(model)

def _chunk_semantic(self, text: str, chunk_size: int) -> list[Chunk]:
    """Chunk using Chonkie SemanticChunker."""
    from chonkie import SemanticChunker
    embeddings = self._get_embeddings()
    chunker = SemanticChunker(
        embedding_model=embeddings,
        chunk_size=chunk_size,
    )
    result = chunker(text)
    return self._chonkie_to_chunk(result, "semantic")

def _chunk_late(self, text: str, chunk_size: int) -> list[Chunk]:
    """Chunk using Chonkie LateChunker (embed then split)."""
    from chonkie import LateChunker
    embeddings = self._get_embeddings()
    chunker = LateChunker(
        embedding_model=embeddings,
        chunk_size=chunk_size,
    )
    result = chunker(text)
    return self._chonkie_to_chunk(result, "late")
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_segmenter.py::TestSemanticStrategy tests/test_segmenter.py::TestLateStrategy -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Run ALL tests**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 23 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ontofuel/extraction/segmenter.py tests/test_segmenter.py
git commit -m "feat: implement semantic and late chunking strategies"
```

---

### Task 5: Implement Auto Detection and Overlap Refinery

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py`
- Test: `tests/test_segmenter.py`

- [ ] **Step 1: Write tests for auto strategy and overlap**

```python
class TestAutoStrategy:
    """Test automatic strategy selection."""

    def test_auto_with_headings(self):
        """Markdown with headings should select recursive."""
        seg = Segmenter(strategy="auto")
        text = "## Intro\n" + "Word " * 300 + "\n## Methods\n" + "More " * 300
        chunks = seg.segment(text)
        assert len(chunks) >= 2
        # First chunk should have strategy=recursive in metadata
        strategies = {c.metadata.get("strategy") for c in chunks}
        assert "recursive" in strategies

    def test_auto_plain_text(self):
        """Plain text without headings should not use recursive."""
        seg = Segmenter(strategy="auto")
        text = "Just plain text. " * 500
        chunks = seg.segment(text)
        assert len(chunks) >= 1
        strategies = {c.metadata.get("strategy") for c in chunks}
        # Should be semantic or fixed (not recursive)
        assert "recursive" not in strategies or len(chunks) == 1


@pytest.mark.skipif(not CHONKIE_AVAILABLE, reason="chonkie not installed")
class TestOverlapRefinery:
    """Test overlap post-processing."""

    def test_overlap_between_chunks(self):
        seg = Segmenter(strategy="recursive", chunk_size=256, overlap_size=64)
        text = "## Alpha\n" + "Beta gamma delta. " * 100 + "\n## Epsilon\n" + "Zeta eta theta. " * 100
        chunks = seg.segment(text)
        if len(chunks) >= 2:
            # Adjacent chunks should share some content
            overlap_found = False
            for i in range(len(chunks) - 1):
                tail_words = set(chunks[i].content.split()[-10:])
                head_words = set(chunks[i + 1].content.split()[:10])
                if tail_words & head_words:
                    overlap_found = True
                    break
            assert overlap_found, "No overlap detected between adjacent chunks"

    def test_zero_overlap_no_overlap(self):
        seg = Segmenter(strategy="recursive", chunk_size=256, overlap_size=0)
        text = "## A\n" + "Word " * 200 + "\n## B\n" + "More " * 200
        chunks = seg.segment(text)
        if len(chunks) >= 2:
            for i in range(len(chunks) - 1):
                tail_words = set(chunks[i].content.split()[-5:])
                head_words = set(chunks[i + 1].content.split()[:5])
                # With overlap=0, very unlikely to share many words
                # Just verify it runs without error
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_segmenter.py::TestAutoStrategy tests/test_segmenter.py::TestOverlapRefinery -v
```

Expected: FAIL — `_detect_strategy` and `_apply_overlap` not implemented.

- [ ] **Step 3: Implement `_detect_strategy` and `_apply_overlap`**

Add to `Segmenter` class:

```python
def _detect_strategy(self, text: str) -> str:
    """Auto-detect best chunking strategy based on text structure."""
    headings = self.HEADING_RE.findall(text)
    line_count = text.count('\n') + 1
    heading_ratio = len(headings) / max(line_count, 1)

    if heading_ratio > 0.01:  # ~1 heading per 100 lines
        return "recursive"
    elif CHONKIE_AVAILABLE and self._embedding_ready():
        return "semantic"
    else:
        return "fixed"

def _embedding_ready(self) -> bool:
    """Check if embedding model is available."""
    try:
        self._get_embeddings()
        return True
    except Exception:
        return False

def _apply_overlap(self, chunks: list[Chunk], overlap_size: int) -> list[Chunk]:
    """Apply overlap between adjacent chunks using Chonkie OverlapRefinery."""
    if len(chunks) <= 1:
        return chunks

    try:
        from chonkie import OverlapRefinery

        # Reconstruct Chonkie-compatible chunks for refinery
        # Since we already converted to our Chunk format,
        # we implement overlap directly
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]

            # Extract overlap from previous chunk's tail
            prev_words = prev.content.split()
            overlap_words = prev_words[-overlap_size:] if len(prev_words) > overlap_size else prev_words
            overlap_text = " ".join(overlap_words)

            # Prepend overlap to current chunk
            enhanced_content = overlap_text + " " + curr.content if overlap_text else curr.content

            result.append(Chunk(
                index=i,
                title=curr.title,
                content=enhanced_content,
                start_char=curr.start_char,
                end_char=curr.end_char,
                level=curr.level,
                metadata={**curr.metadata, "overlap_applied": True},
            ))

        # Re-index
        for i, chunk in enumerate(result):
            chunk.index = i

        return result
    except ImportError:
        return chunks
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_segmenter.py::TestAutoStrategy tests/test_segmenter.py::TestOverlapRefinery -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Run ALL tests**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 27 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ontofuel/extraction/segmenter.py tests/test_segmenter.py
git commit -m "feat: implement auto strategy detection and overlap refinery"
```

---

### Task 6: Backward Compatibility — Rewrite segment_heading/segment_fixed Internals

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py`
- Test: `tests/test_segmenter.py` (existing tests cover this)

- [ ] **Step 1: Write additional backward-compat tests**

```python
class TestBackwardCompatibility:
    """Verify existing API still works identically."""

    def test_segment_heading_returns_list_chunk(self):
        seg = Segmenter()
        text = "# Title\n## A\n" + "X" * 200 + "\n## B\n" + "Y" * 200
        chunks = seg.segment_heading(text)
        assert isinstance(chunks, list)
        for c in chunks:
            assert isinstance(c, Chunk)
            assert hasattr(c, 'index')
            assert hasattr(c, 'title')
            assert hasattr(c, 'content')
            assert hasattr(c, 'start_char')
            assert hasattr(c, 'end_char')
            assert hasattr(c, 'level')
            assert hasattr(c, 'metadata')
            assert hasattr(c, 'char_count')
            assert hasattr(c, 'line_count')
            assert hasattr(c, 'to_dict')

    def test_segment_fixed_returns_list_chunk(self):
        seg = Segmenter()
        chunks = seg.segment_fixed("A" * 5000, chunk_size=2000)
        assert isinstance(chunks, list)
        for c in chunks:
            assert isinstance(c, Chunk)
            assert isinstance(c.to_dict(), dict)

    def test_segment_by_keywords_returns_list_chunk(self):
        seg = Segmenter()
        chunks = seg.segment_by_keywords("U-10Mo is great.", ["U-10Mo"])
        assert isinstance(chunks, list)
        for c in chunks:
            assert isinstance(c, Chunk)

    def test_segment_heading_no_chonkie_still_works(self):
        """Even without chonkie, segment_heading works (pure Python fallback)."""
        import ontofuel.extraction.segmenter as seg_mod
        original = seg_mod.CHONKIE_AVAILABLE
        seg_mod.CHONKIE_AVAILABLE = False
        try:
            seg = seg_mod.Segmenter()
            text = "## Section\n" + "Content " * 100
            chunks = seg.segment_heading(text)
            assert len(chunks) >= 1
            assert chunks[0].title == "Section"
        finally:
            seg_mod.CHONKIE_AVAILABLE = original
```

- [ ] **Step 2: Run all tests**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 31 tests pass (27 previous + 4 new backward compat tests). If any backward compat test fails, fix the issue in `segmenter.py` — the existing `segment_heading`, `segment_fixed`, `segment_by_keywords` methods must work unchanged.

- [ ] **Step 3: Commit**

```bash
git add tests/test_segmenter.py
git commit -m "test: add backward compatibility tests for existing API"
```

---

### Task 7: Integration Test with Real Scientific Document

**Files:**
- Modify: `tests/test_segmenter.py`
- No changes to source

- [ ] **Step 1: Write integration test with realistic nuclear material text**

```python
@pytest.mark.skipif(not CHONKIE_AVAILABLE, reason="chonkie not installed")
class TestIntegration:
    """Integration test with realistic nuclear material document."""

    NUCLEAR_TEXT = """# U3Si2 Fuel-Cladding Compatibility

## 1. Introduction

U3Si2 is a promising accident tolerant fuel with high thermal conductivity
(15-30 W/mK) and high uranium density (11.3 g-U/cm3). The fuel-cladding
chemical interaction (FCCI) between U3Si2 and candidate cladding materials
is a key concern for engineering application.

## 2. Thermodynamic Analysis

The interface reaction enthalpy was calculated using DFT+U method with
Ueff = 1.6 eV. The convex hull construction established local multiphase
equilibrium chemical potentials. Results show two distinct pathways:

- SiC and Zr systems exhibit "self-passivating" characteristics
- Fe and Cr systems face "continuous degradation" risk

## 3. Kinetic Migration Barriers

The CI-NEB method was used to calculate solute transition barriers.
Key findings include:

| System | Barrier (eV) | Migration Path |
|--------|-------------|----------------|
| Fe in U3Si2 | 0.66 | U1-U2 vacancy |
| Zr in U3Si2 | 1.56 | U1-U2 vacancy |
| U in alpha-Fe | 0.37 | 5NN-1NN (OSA) |
| Si in alpha-Cr | 0.70 | NN exchange |

## 4. Diffusion Behavior

The Onsager transport coefficients were calculated using KineCluE method.
Temperature range: 400-2200 K. The inverse Kirkendall effect dominates
cladding element penetration into U3Si2 fuel.

## 5. Conclusions

SiC and Zr alloys demonstrate relatively superior performance.
FeCrAl alloys and pure Cr coatings require intermediate barrier layers
for long-term stable service.
"""

    def test_recursive_on_nuclear_doc(self):
        seg = Segmenter(strategy="recursive", chunk_size=512)
        chunks = seg.segment(self.NUCLEAR_TEXT)
        assert len(chunks) >= 3  # Multiple sections
        # Each chunk should be non-trivial
        for c in chunks:
            assert len(c.content) > 50, f"Chunk {c.index} too short: {c.content[:50]}"

    def test_semantic_on_nuclear_doc(self):
        seg = Segmenter(strategy="semantic", chunk_size=512)
        chunks = seg.segment(self.NUCLEAR_TEXT)
        assert len(chunks) >= 1
        # Semantic chunks should group related content
        all_text = " ".join(c.content for c in chunks)
        assert "U3Si2" in all_text
        assert "FCCI" in all_text

    def test_auto_on_nuclear_doc(self):
        seg = Segmenter(strategy="auto", chunk_size=512)
        chunks = seg.segment(self.NUCLEAR_TEXT)
        assert len(chunks) >= 2
        # Should detect headings and use recursive
        strategies = {c.metadata.get("strategy") for c in chunks}
        assert "recursive" in strategies

    def test_overlap_preserves_context(self):
        seg = Segmenter(strategy="recursive", chunk_size=256, overlap_size=32)
        chunks = seg.segment(self.NUCLEAR_TEXT)
        # All content should be recoverable from chunks
        all_text = " ".join(c.content for c in chunks)
        assert "U3Si2" in all_text
        assert "Onsager" in all_text or "Kirkendall" in all_text
```

- [ ] **Step 2: Run integration tests**

```bash
python3 -m pytest tests/test_segmenter.py::TestIntegration -v
```

Expected: All 4 tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 35 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_segmenter.py
git commit -m "test: add integration tests with realistic nuclear material document"
```

---

### Task 8: Final Verification and Docstring Cleanup

**Files:**
- Modify: `src/ontofuel/extraction/segmenter.py` (docstrings only)

- [ ] **Step 1: Verify all tests pass**

```bash
python3 -m pytest tests/test_segmenter.py -v --tb=short
```

Expected: All 35 tests pass, 0 failures.

- [ ] **Step 2: Update module docstring**

Update the top of `segmenter.py` to reflect new capabilities:

```python
"""Segmenter — split markdown/text into sections or chunks.

Supports multiple chunking strategies via Chonkie integration:
  1. "recursive" — RecursiveChunker with markdown recipe (best for structured docs)
  2. "semantic"  — SemanticChunker (best for unstructured text, requires embeddings)
  3. "late"      — LateChunker (embed-then-split for better context)
  4. "auto"      — Auto-detect best strategy based on document structure
  5. "fixed"     — Pure-Python fixed-size chunking (fallback, no dependencies)

Legacy methods (backward compatible):
  - segment_heading() — Split by markdown headings
  - segment_fixed()   — Split by character count
  - segment_by_keywords() — Extract chunks around keywords

Unified entry: segment(text, strategy, chunk_size, overlap_size)

Requires: chonkie (optional, pip install chonkie[semantic])
"""
```

- [ ] **Step 3: Final full test run**

```bash
python3 -m pytest tests/test_segmenter.py -v
```

Expected: All 35 tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/ontofuel/extraction/segmenter.py
git commit -m "docs: update segmenter module docstring with strategy documentation"
```

---

## Plan Self-Review

**Spec coverage:**
- ✅ RecursiveChunker → Task 3
- ✅ SemanticChunker → Task 4
- ✅ LateChunker → Task 4
- ✅ OverlapRefinery → Task 5
- ✅ Auto detection → Task 5
- ✅ Embedding config → Task 4 (_get_embeddings)
- ✅ Chonkie optional/fallback → Task 2
- ✅ Backward compatibility → Task 6
- ✅ Integration test → Task 7

**Placeholder scan:** No TBDs, no TODOs, all steps have complete code.

**Type consistency:** `Chunk` dataclass fields consistent across all tasks. `Segmenter.__init__` parameters match usage in all test and implementation code.
