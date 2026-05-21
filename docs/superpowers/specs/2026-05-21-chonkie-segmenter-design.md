# Chonkie Segmenter Integration — Design Spec

**Date**: 2026-05-21
**Status**: Approved
**Scope**: `src/ontofuel/extraction/segmenter.py` only

## Goal

Replace OntoFuel's basic text segmenter with Chonkie-backed strategies (Recursive, Semantic, Late chunking + Overlap refinery) to improve extraction quality for large scientific documents (200-2000 pages).

## Architecture

Strategy pattern: `Segmenter` accepts a `strategy` parameter selecting the chunking backend. Chonkie is an optional dependency — when absent, the existing pure-Python implementation is used as fallback. The `Chunk` dataclass and all existing method signatures (`segment_heading`, `segment_fixed`, `segment_by_keywords`) remain unchanged.

## Decisions

1. **Chonkie is optional** — `import chonkie` wrapped in try/except; missing → fallback + warning
2. **Backward compatible** — `segment_heading()` and `segment_fixed()` signatures unchanged; internals rewritten with Chonkie when available
3. **New unified entry** — `segment(text, strategy, chunk_size, overlap_size)` auto-selects best strategy
4. **Auto detection** — has headings → recursive; no headings → semantic (if embedding ready) or fixed
5. **Embedding config** — dict with `provider`/`model`/`api_key`; defaults to `sentence-transformers/all-MiniLM-L6-v2`
6. **Overlap** — `OverlapRefinery` applied as post-processing when `overlap_size > 0`
7. **Strategy pattern** — strategies: `"recursive"`, `"semantic"`, `"late"`, `"auto"`, `"fixed"`

## Scope

### In Scope
- Rewrite `segmenter.py` with strategy pattern
- RecursiveChunker (markdown recipe) for structured documents
- SemanticChunker for unstructured documents (optional dependency)
- LateChunker for context-preserving chunking (optional dependency)
- OverlapRefinery for cross-chunk context preservation
- Auto strategy detection
- Embedding model configuration
- Full test coverage (with and without Chonkie)

### Out of Scope
- FastChunker (speed not a bottleneck)
- EmbeddingsRefinery (no vector retrieval)
- SlumberChunker (LLM cost too high)
- Chonkie Pipeline / Handshakes
- Changes to extractor.py, merger.py, updater.py, __init__.py

## File Changes

| File | Action |
|------|--------|
| `src/ontofuel/extraction/segmenter.py` | Rewrite with Chonkie integration |
| `tests/test_segmenter.py` | Expand with strategy/overlap/auto tests |

## Chunk Adaptation

Chonkie chunk objects (`text`, `token_count`, `start_index`, `end_index`) → OntoFuel `Chunk` via `_chonkie_to_chunk()` helper. Title extracted from first non-empty line (truncated 80 chars). Metadata includes `strategy` and `token_count`.

## Error Handling

| Scenario | Response |
|----------|----------|
| Chonkie not installed | `warnings.warn` + fallback to pure-Python |
| Embedding model fails to load | `warnings.warn` + fallback to `"fixed"` strategy |
| Empty / very short text (<100 chars) | Return single chunk, no splitting |
| Unknown strategy name | Raise `ValueError` |

## Test Plan

| Category | Tests | Requires Chonkie |
|----------|-------|-------------------|
| Existing API | `segment_heading`, `segment_fixed`, `segment_by_keywords`, `Chunk` | No |
| Fallback | No Chonkie → warning + fallback works | No (mock) |
| Recursive | `segment(strategy="recursive")` respects markdown structure | Yes |
| Semantic | `segment(strategy="semantic")` splits by semantics | Yes |
| Late | `segment(strategy="late")` context-preserving | Yes |
| Auto | Heading text → recursive; plain text → semantic/fixed | Yes |
| Overlap | Adjacent chunks have overlapping content | Yes |
| Backward compat | Old methods return `list[Chunk]` with all fields | Both |
