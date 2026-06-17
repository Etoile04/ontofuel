"""Non-blocking fire-and-forget hook (NFM-251 Task 6).

Guarantees: never raises; records failures to data/corpus/_publish_errors.jsonl;
respects opt-in (ONTOFUEL_AUTO_PUBLISH).
"""

from __future__ import annotations

import json
from pathlib import Path

from ontofuel.viz_corpus import hook

REPO = Path(__file__).resolve().parents[1]
ONTO = REPO / "data" / "material_ontology_enhanced.json"


def test_hook_never_raises_even_when_publish_fails(tmp_path, monkeypatch):
    errlog = tmp_path / "_publish_errors.jsonl"
    monkeypatch.setattr("ontofuel.viz_corpus.hook._error_log", lambda: errlog)

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus", boom)
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")

    # must NOT raise
    hook.maybe_publish_after_extraction(ONTO)

    # error recorded for alerting (JSONL: one entry per line)
    entries = [json.loads(line) for line in errlog.read_text().splitlines() if line.strip()]
    assert any("boom" in e["error"] for e in entries)


def test_hook_noop_when_opt_out(tmp_path, monkeypatch):
    monkeypatch.delenv("ONTOFUEL_AUTO_PUBLISH", raising=False)
    called = {"v": False}

    def spy(*a, **k):
        called["v"] = True

    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus", spy)
    hook.maybe_publish_after_extraction(ONTO)
    assert called["v"] is False


def test_hook_no_error_recorded_on_success(tmp_path, monkeypatch):
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    errlog = tmp_path / "_publish_errors.jsonl"
    monkeypatch.setattr("ontofuel.viz_corpus.hook._error_log", lambda: errlog)
    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus", lambda *a, **k: None)
    hook.maybe_publish_after_extraction(ONTO)
    assert not errlog.exists() or errlog.read_text().strip() == ""
