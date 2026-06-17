"""Non-blocking, fire-and-forget post-extraction publish hook.

``maybe_publish_after_extraction()`` is the thin call-site the extraction flow
invokes after finalizing the ontology. It is **structurally non-blocking**: a
publish failure is swallowed, logged as a WARNING, and appended to
``data/corpus/_publish_errors.jsonl`` for alerting — extraction success is never
affected (NFM-226 ADR §3 binding constraint). No-op unless
``ONTOFUEL_AUTO_PUBLISH`` is set (default off = non-regressive).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ontofuel.viz_corpus.config import CorpusPublishConfig
from ontofuel.viz_corpus.publisher import publish_corpus

logger = logging.getLogger(__name__)

PathLike = str | Path


def _error_log() -> Path:
    """Path to the publish-error JSONL log (under the configured corpus root)."""
    cfg = CorpusPublishConfig.from_env()
    return cfg.corpus_root / "_publish_errors.jsonl"


def _record_error(error_log: Path, message: str) -> None:
    """Append one JSON error entry (append-only JSONL; safe for concurrent writers)."""
    error_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "error": message}
    with error_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def maybe_publish_after_extraction(ontology_path: PathLike) -> None:
    """Publish the corpus after an extraction run. NEVER raises.

    Returns immediately when auto-publish is off. On any publish failure, logs a
    WARNING and records the error; the caller's extraction result is unaffected.
    """
    cfg = CorpusPublishConfig.from_env()
    if not cfg.auto_publish:
        return
    try:
        publish_corpus(
            ontology_path=ontology_path,
            corpus_id=cfg.corpus_id,
            corpus_root=cfg.corpus_root,
        )
    except Exception as exc:  # noqa: BLE001 — fire-and-forget must swallow everything
        logger.warning("post-extraction publish failed (non-blocking): %s", exc)
        _record_error(_error_log(), str(exc))
