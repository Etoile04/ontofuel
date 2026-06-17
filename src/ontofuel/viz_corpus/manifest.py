"""Manifest builder — exact NFM-226 ADR §2 schema.

The manifest is the mutable pointer consumers fetch. It carries ``source_digest``
so consumers can cache-bust/verify. Field set is fixed by the ADR:

    corpus_id, asset_url, source_digest, schema_version, pinned,
    generated_at, stats{nodes, edges}
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_manifest(
    *,
    corpus_id: str,
    asset_url: str,
    source_digest: str,
    schema_version: str,
    generated_at: str,
    stats: Mapping[str, int],
    pinned: bool = True,
) -> dict[str, Any]:
    """Build the ADR §2 manifest dict (pinned defaults True)."""
    return {
        "corpus_id": corpus_id,
        "asset_url": asset_url,
        "source_digest": source_digest,
        "schema_version": schema_version,
        "pinned": pinned,
        "generated_at": generated_at,
        "stats": {"nodes": stats["nodes"], "edges": stats["edges"]},
    }
