"""Core publisher (NFM-251 Task 5): convert -> validate -> drift -> idempotent atomic publish."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ontofuel.viz_corpus.converter import validate
from ontofuel.viz_corpus.publisher import (
    FreshnessState,
    PublishStatus,
    check_freshness,
    publish_corpus,
)

REPO = Path(__file__).resolve().parents[1]
ONTO = REPO / "data" / "material_ontology_enhanced.json"


def test_idempotent_same_digest_is_noop(tmp_path):
    # first publish
    r1 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r1.status == PublishStatus.PUBLISHED
    manifest_path = tmp_path / "ontofuel" / "manifest.json"
    assert manifest_path.exists()
    mtime1 = manifest_path.stat().st_mtime
    # second publish, same source -> skipped, files untouched
    r2 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r2.status == PublishStatus.SKIPPED
    assert manifest_path.stat().st_mtime == mtime1


def test_publish_writes_both_files_and_valid_manifest(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    d = tmp_path / "ontofuel"
    nvl = json.loads((d / "ontology.nvl.json").read_text())
    man = json.loads((d / "manifest.json").read_text())
    assert nvl["source_digest"] == man["source_digest"]
    assert man["asset_url"] == "ontology.nvl.json"
    assert validate(nvl) == []


def test_drift_failure_blocks_publish(tmp_path, monkeypatch):
    monkeypatch.setattr("ontofuel.viz_corpus.publisher.drift_check_ok", lambda: False)
    r = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r.status == PublishStatus.BLOCKED
    assert not (tmp_path / "ontofuel" / "manifest.json").exists()


def test_skip_drift_flag_allows_publish_when_gate_disabled(tmp_path, monkeypatch):
    # even if drift gate would fail, skip_drift=True bypasses the provenance gate
    monkeypatch.setattr("ontofuel.viz_corpus.publisher.drift_check_ok", lambda: False)
    r = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path, skip_drift=True)
    assert r.status == PublishStatus.PUBLISHED


def test_publish_records_canonical_digest(tmp_path):
    r = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r.source_digest == "0d986d21a5a2b230"


def test_publish_is_atomic_no_tmp_leftover(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    d = tmp_path / "ontofuel"
    leftovers = [p.name for p in d.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [], f"atomic write left temp files: {leftovers}"


def test_freshness_fresh_after_publish(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert check_freshness("ontofuel", corpus_root=tmp_path) is FreshnessState.FRESH


def test_freshness_stale_after_15min(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    # backdate manifest generated_at by 20 min
    mpath = tmp_path / "ontofuel" / "manifest.json"
    m = json.loads(mpath.read_text())
    old = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    m["generated_at"] = old
    mpath.write_text(json.dumps(m))
    assert check_freshness("ontofuel", corpus_root=tmp_path) is FreshnessState.STALE
    # alert heartbeat refreshed on stale
    assert (tmp_path / "_freshness.json").exists()


def test_freshness_missing_when_no_corpus(tmp_path):
    assert check_freshness("ontofuel", corpus_root=tmp_path) is FreshnessState.MISSING
