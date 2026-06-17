"""Core publisher: convert -> validate -> drift-gate -> idempotent atomic publish.

Standalone, idempotent ``publish_corpus()`` orchestrates the proven chain and
atomically writes ``{corpus_id}/ontology.nvl.json`` + ``manifest.json`` to the
NFMD Tier-A static corpus path (NFM-226 ADR §2/§3). Publish is:

* **Idempotent + digest-gated** — a rerun with an unchanged ``source_digest`` is
  a no-op (``SKIPPED``), leaving files untouched.
* **Provenance-gated** — proceeds ONLY after ``drift_check_ok()`` (the committed
  artifact provably matches a fresh canonical regen); otherwise ``BLOCKED``.
* **Atomic** — temp-file + ``os.replace`` so consumers never see a half-written
  artifact.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from ontofuel.viz_corpus.config import CorpusPublishConfig
from ontofuel.viz_corpus.converter import build_nvl_contract, validate
from ontofuel.viz_corpus.drift import drift_check_ok
from ontofuel.viz_corpus.manifest import build_manifest

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


class PublishStatus(str, Enum):
    """Outcome of a publish attempt."""

    PUBLISHED = "published"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PublishResult:
    """Immutable result of ``publish_corpus``."""

    status: PublishStatus
    corpus_id: str
    source_digest: str
    output_dir: Optional[Path] = None
    message: str = ""


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write JSON to ``path`` atomically via temp-file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def publish_corpus(
    ontology_path: PathLike,
    corpus_id: Optional[str] = None,
    corpus_root: Optional[PathLike] = None,
    skip_drift: bool = False,
) -> PublishResult:
    """Publish the validated, drift-gated NVL corpus for ``ontology_path``.

    Steps (NFM-226 ADR §3):
      1. convert -> versioned contract; validate against the NVL schema.
      2. idempotency: if the existing manifest carries the same source_digest,
         return ``SKIPPED`` without writing.
      3. provenance gate: unless ``skip_drift``, require ``drift_check_ok()``;
         otherwise return ``BLOCKED``.
      4. atomic publish of ``ontology.nvl.json`` + ``manifest.json``.
    """
    cfg = CorpusPublishConfig.from_env()
    corpus_id = corpus_id or cfg.corpus_id
    corpus_root = Path(corpus_root) if corpus_root else cfg.corpus_root
    out_dir = corpus_root / corpus_id
    manifest_path = out_dir / "manifest.json"

    # 1. convert + validate
    contract = build_nvl_contract(ontology_path)
    errors = validate(contract)
    if errors:
        digest = contract.get("source_digest", "")
        logger.warning("publish blocked: contract invalid (%d errors)", len(errors))
        return PublishResult(
            PublishStatus.BLOCKED,
            corpus_id,
            digest,
            message="contract invalid: " + "; ".join(errors[:3]),
        )
    source_digest = contract["source_digest"]

    # 2. idempotency (digest-gated)
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = {}
        if existing.get("source_digest") == source_digest:
            logger.info("publish skipped: source_digest unchanged (%s)", source_digest)
            return PublishResult(
                PublishStatus.SKIPPED, corpus_id, source_digest, out_dir,
                "source_digest unchanged",
            )

    # 3. provenance gate
    if not skip_drift and not drift_check_ok():
        logger.warning("publish blocked: drift-gate failed (artifact not provably derived)")
        return PublishResult(
            PublishStatus.BLOCKED,
            corpus_id,
            source_digest,
            message="drift-gate failed: artifact not provably derived",
        )

    # 4. atomic publish
    nvl_path = out_dir / "ontology.nvl.json"
    _atomic_write_json(nvl_path, contract)
    manifest = build_manifest(
        corpus_id=corpus_id,
        asset_url="ontology.nvl.json",
        source_digest=source_digest,
        schema_version=contract.get("schema_version", "1.0"),
        generated_at=contract.get("generated_at", ""),
        stats={
            "nodes": len(contract.get("nodes", [])),
            "edges": len(contract.get("relationships", [])),
        },
    )
    _atomic_write_json(manifest_path, manifest)
    logger.info("publish ok: %s (digest %s)", out_dir, source_digest)
    return PublishResult(
        PublishStatus.PUBLISHED, corpus_id, source_digest, out_dir, "published"
    )
