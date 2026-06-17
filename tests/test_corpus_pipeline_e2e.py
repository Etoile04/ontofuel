"""End-to-end corpus publish pipeline (NFM-251 Task 10).

Full chain on the canonical ontology: convert -> validate -> viz-sync drift-gate
-> atomic publish. Asserts both files exist, manifest == ADR §2 schema, NVL
validates, source_digest == canonical, idempotent SKIPPED on rerun, and same-origin
HTTP servability (NFMD Tier-A static manifest).
"""

from __future__ import annotations

import json
import socket
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

from ontofuel.viz_corpus.converter import validate
from ontofuel.viz_corpus.publisher import PublishStatus, publish_corpus

REPO = Path(__file__).resolve().parents[1]
ONTO = REPO / "data" / "material_ontology_enhanced.json"
CANONICAL_DIGEST = "0d986d21a5a2b230"

ADR2_FIELDS = {
    "corpus_id",
    "asset_url",
    "source_digest",
    "schema_version",
    "pinned",
    "generated_at",
    "stats",
}


def test_e2e_full_chain_publish_on_canonical(tmp_path):
    r = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r.status == PublishStatus.PUBLISHED

    d = tmp_path / "ontofuel"
    nvl = json.loads((d / "ontology.nvl.json").read_text(encoding="utf-8"))
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))

    # NVL validates against the Draft 2020-12 schema
    assert validate(nvl) == []
    # canonical provenance digest (proves converter reused, not hand-built)
    assert nvl["source_digest"] == CANONICAL_DIGEST
    assert man["source_digest"] == CANONICAL_DIGEST
    # manifest == NFM-226 ADR §2 schema exactly
    assert set(man) == ADR2_FIELDS
    assert man["asset_url"] == "ontology.nvl.json"
    assert man["corpus_id"] == "ontofuel"
    assert man["pinned"] is True
    assert set(man["stats"]) == {"nodes", "edges"}
    assert man["stats"]["nodes"] == len(nvl["nodes"])
    assert man["stats"]["edges"] == len(nvl["relationships"])


def test_e2e_idempotent_second_run_skipped(tmp_path):
    r1 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r1.status == PublishStatus.PUBLISHED
    r2 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r2.status == PublishStatus.SKIPPED


def test_e2e_same_origin_servable(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)

    # bind a free port, serve the corpus root same-origin, fetch the artifacts
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(tmp_path), **kw)

        def log_message(self, *a):  # silence test stderr
            pass

    httpd = HTTPServer(("127.0.0.1", port), Handler)
    Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/ontofuel/manifest.json", timeout=5
        ) as resp:
            man = json.loads(resp.read())
        assert man["source_digest"] == CANONICAL_DIGEST
        assert man["asset_url"] == "ontology.nvl.json"

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/ontofuel/ontology.nvl.json", timeout=5
        ) as resp:
            nvl = json.loads(resp.read())
        assert nvl["source_digest"] == CANONICAL_DIGEST
        assert validate(nvl) == []
    finally:
        httpd.shutdown()
        httpd.server_close()
