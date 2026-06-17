"""CLI subcommand `ontofuel publish-corpus` (NFM-251 Task 8)."""
from __future__ import annotations

from pathlib import Path

from ontofuel.cli import main

REPO = Path(__file__).resolve().parents[1]
ONTO = REPO / "data" / "material_ontology_enhanced.json"


def test_cli_publish_corpus(tmp_path):
    rc = main(
        ["publish-corpus", "--ontology", str(ONTO), "--corpus-root", str(tmp_path)]
    )
    assert rc == 0
    assert (tmp_path / "ontofuel" / "manifest.json").exists()
    assert (tmp_path / "ontofuel" / "ontology.nvl.json").exists()


def test_cli_publish_corpus_idempotent(tmp_path):
    rc1 = main(
        ["publish-corpus", "--ontology", str(ONTO), "--corpus-root", str(tmp_path)]
    )
    assert rc1 == 0
    # second run is SKIPPED (no-op) -> still success (rc 0)
    rc2 = main(
        ["publish-corpus", "--ontology", str(ONTO), "--corpus-root", str(tmp_path)]
    )
    assert rc2 == 0


def test_cli_publish_corpus_blocked_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr("ontofuel.viz_corpus.publisher.drift_check_ok", lambda: False)
    rc = main(
        ["publish-corpus", "--ontology", str(ONTO), "--corpus-root", str(tmp_path)]
    )
    assert rc == 1
    assert not (tmp_path / "ontofuel" / "manifest.json").exists()


def test_cli_publish_corpus_skip_drift_flag(tmp_path, monkeypatch):
    # --skip-drift bypasses the gate even when it would fail
    monkeypatch.setattr("ontofuel.viz_corpus.publisher.drift_check_ok", lambda: False)
    rc = main(
        [
            "publish-corpus", "--ontology", str(ONTO),
            "--corpus-root", str(tmp_path), "--skip-drift",
        ]
    )
    assert rc == 0
