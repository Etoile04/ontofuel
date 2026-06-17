"""Wire the auto-publish hook into the extraction finalization point (NFM-251 Task 9).

OntologyUpdater.save() is where the enhanced ontology is finalized to disk; the
fire-and-forget hook fires there (opt-in via ONTOFUEL_AUTO_PUBLISH). Non-regression:
when unset, save() is byte-level unchanged (hook is a no-op); when set and publish
raises, save() still succeeds.
"""
from __future__ import annotations

import json
from pathlib import Path


def _make_onto(tmp_path: Path) -> Path:
    p = tmp_path / "ontology.json"
    p.write_text(json.dumps({"classes": [], "individuals": []}), encoding="utf-8")
    return p


def test_extraction_save_triggers_publish_when_opted_in(tmp_path, monkeypatch):
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    calls: list[dict] = []
    monkeypatch.setattr(
        "ontofuel.viz_corpus.hook.publish_corpus", lambda **kw: calls.append(kw)
    )
    from ontofuel.extraction.updater import OntologyUpdater

    onto = _make_onto(tmp_path)
    OntologyUpdater(onto, backup=False).save()
    assert len(calls) == 1  # exactly one publish trigger
    assert Path(calls[0]["ontology_path"]) == onto


def test_extraction_save_unaffected_when_publish_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    errlog = tmp_path / "_publish_errors.jsonl"
    monkeypatch.setattr("ontofuel.viz_corpus.hook._error_log", lambda: errlog)

    def boom(**kw):
        raise RuntimeError("publish boom")

    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus", boom)
    from ontofuel.extraction.updater import OntologyUpdater

    onto = _make_onto(tmp_path)
    saved = OntologyUpdater(onto, backup=False).save()
    assert Path(saved).exists()  # ontology save still succeeds (non-blocking)
    entries = [json.loads(line) for line in errlog.read_text().splitlines() if line.strip()]
    assert any("boom" in e["error"] for e in entries)


def test_extraction_save_noop_when_opt_out(tmp_path, monkeypatch):
    monkeypatch.delenv("ONTOFUEL_AUTO_PUBLISH", raising=False)
    called = {"v": False}
    monkeypatch.setattr(
        "ontofuel.viz_corpus.hook.publish_corpus", lambda **kw: called.__setitem__("v", True)
    )
    from ontofuel.extraction.updater import OntologyUpdater

    onto = _make_onto(tmp_path)
    OntologyUpdater(onto, backup=False).save()
    assert called["v"] is False  # byte-level unchanged: hook is a no-op
