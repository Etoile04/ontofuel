"""Drift-gate wrapper (NFM-251 Task 3).

Provenance gate reusing viz_sync.check_drift (NFM-230). Exit-0-equivalent =
drift-free = publishable. Fails closed.
"""

from __future__ import annotations

import json

from ontofuel.viz_corpus.drift import drift_check_ok


def test_drift_check_passes_on_canonical():
    # canonical ontology is drift-free by construction (committed copy == fresh regen)
    assert drift_check_ok() is True


def test_drift_check_detects_tampered_copy(tmp_path):
    # a tampered copy must NOT pass the gate (proves it is a real gate, not a stub)
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps({"nodes": [], "relationships": []}), encoding="utf-8")
    assert drift_check_ok(copy_path=tampered) is False


def test_drift_check_fails_closed_when_copy_missing(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    assert drift_check_ok(copy_path=missing) is False
