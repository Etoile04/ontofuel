"""Drift gate + sync tests for viz-sync (NFM-230 / NFM-226 ADR §2 D3).

The drift gate is the CI guard that keeps the committed NVL contract aligned with
the canonical ontology. The headline gate runs against the extraction-side copy
(``data/nvl_ontology_data.json``), which is committed in this repo and available in
CI. It regenerates the versioned contract from ``data/material_ontology_enhanced.json``
and compares it — content-normalized, excluding the intentionally non-deterministic
``generated_at`` — against the committed copy. Any divergence fails the build until
someone runs ``ontofuel viz-sync``.

The visualization-side copy lives in a SEPARATE repo (``visualization-app``), so its
cross-repo mirror check runs only when the nested ``visualization-app`` checkout is
present (developer machines), and skips in CI. The sync itself writes the SAME bytes
to both destinations, so the two can never diverge once produced.

Also covers viz-sync determinism and idempotency: same ontology → same source_digest
and the same byte output across runs and across both destinations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from viz_sync import (  # noqa: E402
    check_drift,
    regenerate_contract,
    serialize_contract,
    sync,
    write_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "data" / "material_ontology_enhanced.json"
EXTRACTION_COPY = REPO_ROOT / "data" / "nvl_ontology_data.json"
VIZ_COPY = REPO_ROOT / "visualization-app" / "public" / "data" / "nvl_ontology_data.json"

PINNED_TS = "2026-06-17T00:00:00+00:00"
# NFM-227 / NFM-235 acceptance anchor: the current canonical's stable digest.
ANCHOR_DIGEST = "0d986d21a5a2b230"


# --------------------------------------------------------------------------- #
# CI drift gate — the headline test for NFM-230
# --------------------------------------------------------------------------- #
def test_extraction_copy_has_no_drift():
    """Committed extraction-side copy must match a fresh canonical regeneration.

    This is the gate that breaks the build when the ontology changes but nobody
    runs ``ontofuel viz-sync``. ``generated_at`` is excluded so a fresh timestamp
    alone is not considered drift. Runs in CI (copy is committed in this repo).
    """
    if not EXTRACTION_COPY.exists():
        pytest.fail(f"extraction-side copy missing: {EXTRACTION_COPY}")
    result = check_drift(
        canonical_path=CANONICAL, copy_path=EXTRACTION_COPY, pin_timestamp=PINNED_TS
    )
    assert not result["drifted"], (
        "DATA DRIFT detected — the committed extraction-side copy does not match "
        "the canonical ontology.\n"
        f"  fresh regen: {result['expected']}\n"
        f"  committed:   {result['committed']}\n"
        "  Fix: run `ontofuel viz-sync` and commit the regenerated copy."
    )


def test_viz_copy_matches_extraction_copy_when_present():
    """Cross-repo mirror check: viz-side copy must be byte-identical to extraction-side.

    The visualization-side copy lives in the separate ``visualization-app`` repo and
    is absent from a plain workspace-extractor clone (e.g. CI), so this check runs
    only when the nested checkout is present (developer machines). The sync writes
    the same bytes to both, so divergence here means someone hand-edited one copy.
    """
    if not VIZ_COPY.exists() or not EXTRACTION_COPY.exists():
        pytest.skip("visualization-app checkout not present (CI); cross-repo mirror skipped")
    assert VIZ_COPY.read_bytes() == EXTRACTION_COPY.read_bytes(), (
        "extraction-side and viz-side NVL copies diverged — run `ontofuel viz-sync`."
    )


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_source_digest_is_stable_across_runs():
    a = regenerate_contract(CANONICAL, pin_timestamp=PINNED_TS)
    b = regenerate_contract(CANONICAL, pin_timestamp=PINNED_TS)
    assert a["source_digest"] == b["source_digest"]
    # Pinned timestamp → fully byte-identical serialization
    assert serialize_contract(a) == serialize_contract(b)


def test_source_digest_matches_nfm227_anchor():
    """Digest anchored to NFM-227 / NFM-235 acceptance (sha256 short, 16 hex)."""
    contract = regenerate_contract(CANONICAL, pin_timestamp=PINNED_TS)
    assert contract["source_digest"] == ANCHOR_DIGEST
    assert contract["schema_version"] == "1.0"


def test_drift_check_detects_real_drift(tmp_path):
    """Sanity: check_drift must report drift when the committed copy is stale."""
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps({"nodes": [], "relationships": []}), encoding="utf-8")
    result = check_drift(canonical_path=CANONICAL, copy_path=stale, pin_timestamp=PINNED_TS)
    assert result["drifted"] is True


# --------------------------------------------------------------------------- #
# Idempotency — syncing twice yields identical bytes across both destinations
# --------------------------------------------------------------------------- #
def test_sync_is_idempotent_and_identical(tmp_path):
    ext_a = tmp_path / "ext_a.json"
    viz_a = tmp_path / "viz_a.json"
    ext_b = tmp_path / "ext_b.json"
    viz_b = tmp_path / "viz_b.json"

    sync(
        canonical_path=CANONICAL,
        extraction_out=ext_a,
        viz_out=viz_a,
        pin_timestamp=PINNED_TS,
        backup_viz=False,
    )
    sync(
        canonical_path=CANONICAL,
        extraction_out=ext_b,
        viz_out=viz_b,
        pin_timestamp=PINNED_TS,
        backup_viz=False,
    )

    assert ext_a.read_bytes() == viz_a.read_bytes(), "extraction != viz after sync"
    assert ext_a.read_bytes() == ext_b.read_bytes(), "sync not idempotent across runs"
    assert ext_a.read_bytes() == viz_b.read_bytes()


def test_sync_reports_consistent_stats(tmp_path):
    ext = tmp_path / "ext.json"
    viz = tmp_path / "viz.json"
    report = sync(
        canonical_path=CANONICAL,
        extraction_out=ext,
        viz_out=viz,
        pin_timestamp=PINNED_TS,
        backup_viz=False,
    )
    assert report["identical"] is True
    assert report["extraction_bytes"] == report["viz_bytes"]
    assert report["source_digest"] == ANCHOR_DIGEST
    stats = report["stats"]
    assert stats["nodes"] == 927 and stats["relationships"] == 1061


def test_write_contract_round_trips_envelope(tmp_path):
    contract = regenerate_contract(CANONICAL, pin_timestamp=PINNED_TS)
    dest = tmp_path / "out.json"
    size = write_contract(contract, dest)
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert size == dest.stat().st_size
    assert {k: v for k, v in loaded.items() if k != "generated_at"} == {
        k: v for k, v in contract.items() if k != "generated_at"
    }
    for key in ("schema_version", "source_digest", "stats", "nodes", "relationships"):
        assert key in loaded
