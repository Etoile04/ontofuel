"""Env-driven configuration for the NFMD corpus publish pipeline.

No hardcoded absolute paths. Auto-publish is opt-in via ``ONTOFUEL_AUTO_PUBLISH``
(default off) so extraction behavior is byte-identical until enabled — this is the
binding non-regression constraint (NFM-226 ADR §3).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# config.py lives at <repo>/src/ontofuel/viz_corpus/config.py
#   parents[0]=viz_corpus, [1]=ontofuel, [2]=src, [3]=<repo root>
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CORPUS_ROOT = _REPO_ROOT / "data" / "corpus"

# Conventional truthy opt-in values (case-insensitive).
_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CorpusPublishConfig:
    """Immutable publish configuration resolved from the environment."""

    corpus_id: str
    corpus_root: Path
    auto_publish: bool

    @classmethod
    def from_env(cls) -> CorpusPublishConfig:
        """Resolve config from environment with non-regressive defaults."""
        corpus_root = Path(
            os.environ.get("ONTOFUEL_CORPUS_ROOT", str(_DEFAULT_CORPUS_ROOT))
        )
        corpus_id = os.environ.get("ONTOFUEL_CORPUS_ID", "ontofuel")
        auto_publish = os.environ.get("ONTOFUEL_AUTO_PUBLISH", "").lower() in _TRUTHY
        return cls(
            corpus_id=corpus_id,
            corpus_root=corpus_root,
            auto_publish=auto_publish,
        )
