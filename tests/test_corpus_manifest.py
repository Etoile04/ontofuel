"""Manifest builder (NFM-251 Task 4) — exact NFM-226 ADR §2 schema."""

from __future__ import annotations

from ontofuel.viz_corpus.manifest import build_manifest


def test_manifest_schema():
    m = build_manifest(
        corpus_id="ontofuel",
        asset_url="ontology.nvl.json",
        source_digest="0d986d21a5a2b230",
        schema_version="1.0",
        generated_at="2026-06-17T12:00:00+00:00",
        stats={"nodes": 927, "edges": 1061},
    )
    assert set(m) == {
        "corpus_id",
        "asset_url",
        "source_digest",
        "schema_version",
        "pinned",
        "generated_at",
        "stats",
    }
    assert m["pinned"] is True
    assert set(m["stats"]) == {"nodes", "edges"}
    assert m["stats"]["nodes"] == 927
    assert m["stats"]["edges"] == 1061
    assert m["source_digest"] == "0d986d21a5a2b230"


def test_manifest_pinned_defaults_true():
    m = build_manifest(
        corpus_id="ontofuel",
        asset_url="ontology.nvl.json",
        source_digest="0d986d21a5a2b230",
        schema_version="1.0",
        generated_at="2026-06-17T12:00:00+00:00",
        stats={"nodes": 1, "edges": 2},
    )
    assert m["pinned"] is True
