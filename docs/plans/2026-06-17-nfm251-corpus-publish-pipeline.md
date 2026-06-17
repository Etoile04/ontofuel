# NFM-251 — NFMD Corpus Publish Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the verified viz-sync pipeline into the extraction completion hook so every extraction end-to-end, unattended, produces a validated, digest-gated NVL corpus published to the NFMD Tier-A static corpus path.

**Architecture:** A standalone, idempotent `publish_corpus()` function (CLI `ontofuel publish-corpus`) orchestrates the proven chain — `OntologyToNVLConverter` → `validate_contract()` → `viz_sync --check` drift-gate → atomic publish of `{corpus_id}/ontology.nvl.json` + `manifest.json`. The extraction flow invokes it **fire-and-forget** (swallow + alert) so a publish failure can never fail an extraction. No daemon, no backend API (Tier A static manifest per [NFM-226 ADR](/NFM/issues/NFM-226) §2/§3).

**Tech Stack:** Python 3.11+, pytest, jsonschema (Draft 2020-12), existing `scripts/ontology_to_nvl.py` + `scripts/viz_sync.py`, stdlib `http.server` for same-origin serving.

**Authoritative sources:** [NFM-226 ADR](/NFM/issues/NFM-226) §2 (manifest schema) + §3 (flow + binding constraints); [NFM-248](/NFM/issues/NFM-248) §5 #1.

---

## Part A — Design Spec (CPO brainstorm output)

### A.1 What already exists (reuse, do NOT rewrite)

| Component | Location | Status |
|---|---|---|
| Versioned NVL converter + `source_digest` + `stats` + `validate_contract()` | `scripts/ontology_to_nvl.py` (`OntologyToNVLConverter`, `validate_contract`) | ✅ shipped (NFM-227) |
| NVL contract JSON Schema (Draft 2020-12) | `schemas/nvl_contract.schema.json` | ✅ shipped (NFM-227) |
| viz-sync drift-gate (cross-repo blob parity, `--check`) | `scripts/viz_sync.py` + `tests/test_viz_sync_drift.py` | ✅ verified (NFM-230 done, NFM-241 PASS) — **PREREQUISITE: not merged to `ontofuel-v0.1`** |
| Extraction pipeline step-runner | `src/ontofuel/extraction/pipeline.py` (`Pipeline`) | ✅ (no post-run hook today) |
| NFMD static serve | `com.ontofuel.http-server.plist` → `http.server:9999` from repo root, same-origin | ✅ running |
| Consumer corpus resolver | `visualization-app/src/utils/resolveDataUrl.ts` (`resolveCorpusId` stub) | ⛔ stub — **NFM-250 wires the read side** |

### A.2 Approaches considered (brainstorm)

**Hook mechanism — where "extraction complete" triggers publish:**
1. **Terminal `PipelineStep`** — REJECTED. `Pipeline._execute` sets `result.success=False` on any step failure; a publish step that errors would fail the extraction → violates the binding *non-blocking* constraint.
2. **File-watch daemon** — REJECTED (YAGNI). ADR §4: "ontology is a low-frequency batch artifact"; a resident daemon is unjustified infra.
3. **Standalone idempotent command + thin fire-and-forget call-site** — **CHOSEN.** `publish_corpus()` is a pure, testable, reusable function exposed as `ontofuel publish-corpus`. The extraction entrypoint calls it inside a `try/except` that logs + alerts and **never re-raises**. Non-blocking is structural (swallow), freshness is trivially <15 min (in-process, seconds), idempotency is a digest compare before write.

**Publish path + corpus_id (ADR §2 contract):**
- corpus_id = stable alias, default `ontofuel` (env `ONTOFUEL_CORPUS_ID` override).
- Publish root = `data/corpus/` under repo root (already served same-origin at `http://<host>:9999/data/corpus/...`).
- Files: `data/corpus/{corpus_id}/ontology.nvl.json` + `data/corpus/{corpus_id}/manifest.json`.
- `asset_url` = relative `"ontology.nvl.json"` (manifest is the mutable pointer; carries `source_digest` so consumers cache-bust/verify).
- Atomic write: temp file + `os.replace`.

> **DECISION POINT — coordinate with NFM-250 (consumer resolver).** The ADR fixes the path *shape* (`/{corpus_id}/...`) but not the absolute root or the alias value. This plan's default (`data/corpus/{corpus_id}/`, alias `ontofuel`) must match what NFM-250's `resolveCorpusId()` resolves `?corpus=<id>` to. **Action:** Lead Engineer posts the manifest URL convention on NFM-250 before merge; if NFM-250's owner disagrees with the root/alias, escalate to CTO. This is the ONE cross-issue seam.

### A.3 manifest.json schema (ADR §2, exact)

```json
{
  "corpus_id": "ontofuel",
  "asset_url": "ontology.nvl.json",
  "source_digest": "0d986d21a5a2b230",
  "schema_version": "1.0",
  "pinned": true,
  "generated_at": "2026-06-17T12:00:00+00:00",
  "stats": { "nodes": 927, "edges": 1061 }
}
```
`stats.edges` = converter `relationships` count; `source_digest` = converter `source_digest` (sha256[:16] of canonical ontology).

### A.4 How each acceptance criterion is met

| AC | Mechanism |
|---|---|
| Full chain hook → convert → validate → drift-check → publish | `publish_corpus()` orchestrates all 5 steps; CLI + hook both call it |
| Path `/{corpus_id}/ontology.nvl.json` + `manifest.json` | Atomic publish to `data/corpus/{corpus_id}/` |
| Idempotent + digest-gated (rerun = no-op) | Read existing `manifest.json`; if `source_digest` unchanged → return `skipped`, write nothing |
| Non-blocking (failure alerts, never fails extraction) | `maybe_publish_after_extraction()` wraps call in `try/except`; logs WARNING + records to `data/corpus/_publish_errors.jsonl`; never raises |
| Freshness <15 min + alert | In-process publish = seconds; `check_freshness(corpus_id, max_age_minutes=15)` compares `manifest.generated_at` to now; alert = WARNING log + `_freshness.json` heartbeat |
| Provenance gating (digest matches viz-sync output) | Publish proceeds ONLY after `viz_sync --check` exits 0 (artifact matches converter → not hand-edited); `manifest.source_digest` records it; NFM-250 may re-verify |

### A.5 Non-regression (binding)
- Must not break existing 46 jest + 9 playwright + viz-sync drift-gate.
- Auto-publish is **opt-in** via `ONTOFUEL_AUTO_PUBLISH=1` (default off) so extraction behavior is byte-identical until enabled.

---

## Part B — Implementation Plan (file-level TDD)

> **Branch from `nfm-230/viz-sync`** (which has the verified `viz_sync.py`) off `ontofuel-v0.1`, OR confirm Release Engineer merges `nfm-230/viz-sync` first. `viz_sync.py` MUST be present on the working tree.

### Task 1: Scaffold `viz_corpus` package + config

**Files:** Create `src/ontofuel/viz_corpus/__init__.py`, `src/ontofuel/viz_corpus/config.py`; Test `tests/test_corpus_config.py`.

1. **Write failing test** — env-driven config, no hardcoded paths:
```python
import os, pytest
from ontofuel.viz_corpus.config import CorpusPublishConfig

def test_default_config(monkeypatch):
    for k in ("ONTOFUEL_CORPUS_ROOT","ONTOFUEL_CORPUS_ID","ONTOFUEL_AUTO_PUBLISH"):
        monkeypatch.delenv(k, raising=False)
    cfg = CorpusPublishConfig.from_env()
    assert cfg.corpus_id == "ontofuel"
    assert cfg.corpus_root.name == "corpus"      # <repo>/data/corpus
    assert cfg.auto_publish is False             # opt-in (non-regressive)

def test_auto_publish_opt_in(monkeypatch):
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    assert CorpusPublishConfig.from_env().auto_publish is True
```
2. Run `pytest tests/test_corpus_config.py -v` → FAIL (module missing).
3. Implement `config.py`: `@dataclass(frozen=True) CorpusPublishConfig` with `from_env()` reading the three env vars; default `corpus_root = <repo>/data/corpus`.
4. Run → PASS. 5. `git add -A && git commit -m "feat(NFM-251): viz_corpus config scaffold"`.

### Task 2: Reuse converter + contract validation (import shim)

**Files:** Create `src/ontofuel/viz_corpus/converter.py`; Test `tests/test_corpus_converter.py`.

1. **Write failing test** — reuse, don't rewrite; produces versioned contract + validates clean:
```python
from pathlib import Path
from ontofuel.viz_corpus.converter import build_nvl_contract, validate
REPO = Path(__file__).resolve().parents[1]
ONTO = REPO / "data" / "material_ontology_enhanced.json"

def test_build_contract_has_provenance():
    contract = build_nvl_contract(ONTO)
    assert contract["schema_version"] == "1.0"
    assert len(contract["source_digest"]) == 16
    assert "nodes" in contract and "relationships" in contract

def test_contract_validates_against_schema():
    assert validate(build_nvl_contract(ONTO)) == []
```
2. Run → FAIL. 3. Implement `converter.py`: import `OntologyToNVLConverter` + `validate_contract` from `scripts.ontology_to_nvl` (add `scripts/` to `sys.path` like `viz_sync.py` does — match its import pattern exactly). Expose `build_nvl_contract(ontology_path)` (calls `.convert()`) and `validate(contract)` (delegates to `validate_contract`).
4. Run → PASS. 5. Commit `feat(NFM-251): reuse converter+schema via import shim`.

### Task 3: Drift-gate wrapper (reuse viz_sync --check)

**Files:** Create `src/ontofuel/viz_corpus/drift.py`; Test `tests/test_corpus_drift.py`.

1. **Write failing test** — provenance gate; exit 0 = drift-free = publishable:
```python
import pytest
from ontofuel.viz_corpus.drift import drift_check_ok

def test_drift_check_passes_on_canonical():
    # canonical ontology is drift-free by construction
    assert drift_check_ok() is True
```
2. Run → FAIL. 3. Implement `drift.py`: `drift_check_ok() -> bool` runs `ontofuel viz-sync --check` (or imports viz_sync's check fn) in a subprocess, returns `True` iff exit 0; raises/returns `False` otherwise with the captured stderr. (Reuse viz_sync — zero reimplementation, per NFM-241 focus #4.)
4. Run → PASS. 5. Commit `feat(NFM-251): viz_sync drift-gate wrapper`.

### Task 4: Manifest builder (ADR §2 schema)

**Files:** Create `src/ontofuel/viz_corpus/manifest.py`; Test `tests/test_corpus_manifest.py`.

1. **Write failing test** — exact ADR §2 field set + types:
```python
from ontofuel.viz_corpus.manifest import build_manifest
def test_manifest_schema():
    m = build_manifest(corpus_id="ontofuel", asset_url="ontology.nvl.json",
                       source_digest="0d986d21a5a2b230", schema_version="1.0",
                       generated_at="2026-06-17T12:00:00+00:00",
                       stats={"nodes": 927, "edges": 1061})
    assert set(m) == {"corpus_id","asset_url","source_digest","schema_version",
                      "pinned","generated_at","stats"}
    assert m["pinned"] is True
    assert set(m["stats"]) == {"nodes","edges"}
```
2. Run → FAIL. 3. Implement `manifest.py`: frozen `build_manifest(...)` returning the exact dict; default `pinned=True`.
4. Run → PASS. 5. Commit `feat(NFM-251): manifest builder`.

### Task 5: Core publisher — convert → validate → drift → idempotent atomic publish

**Files:** Create `src/ontofuel/viz_corpus/publisher.py`; Test `tests/test_corpus_publisher.py`.

1. **Write failing tests** (idempotency + full chain + provenance gate + atomicity):
```python
import json
from ontofuel.viz_corpus.publisher import publish_corpus, PublishResult, PublishStatus

def test_idempotent_same_digest_is_noop(tmp_path, monkeypatch):
    # first publish
    r1 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r1.status == PublishStatus.PUBLISHED
    manifest_path = tmp_path/"ontofuel"/"manifest.json"
    mtime1 = manifest_path.stat().st_mtime
    # second publish, same source → skipped, files untouched
    r2 = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r2.status == PublishStatus.SKIPPED
    assert manifest_path.stat().st_mtime == mtime1

def test_publish_writes_both_files_and_valid_manifest(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    d = tmp_path/"ontofuel"
    nvl = json.loads((d/"ontology.nvl.json").read_text())
    man = json.loads((d/"manifest.json").read_text())
    assert nvl["source_digest"] == man["source_digest"]
    assert man["asset_url"] == "ontology.nvl.json"
    assert validate(nvl) == []

def test_drift_failure_blocks_publish(tmp_path, monkeypatch):
    monkeypatch.setattr("ontofuel.viz_corpus.publisher.drift_check_ok", lambda: False)
    r = publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    assert r.status == PublishStatus.BLOCKED  # provenance gate
    assert not (tmp_path/"ontofuel"/"manifest.json").exists()
```
2. Run → FAIL. 3. Implement `publisher.py`:
   - `PublishStatus = Enum(PUBLISHED, SKIPPED, BLOCKED)`, `@dataclass(frozen=True) PublishResult`.
   - `publish_corpus(ontology_path, corpus_id=None, corpus_root=None, skip_drift=False) -> PublishResult`:
     1. `contract = build_nvl_contract(ontology_path)`; assert `validate(contract) == []`.
     2. Idempotency: if `{corpus_id}/manifest.json` exists and its `source_digest == contract.source_digest` → return `SKIPPED`.
     3. Provenance: if not `skip_drift` and not `drift_check_ok()` → return `BLOCKED`.
     4. Atomic write: write `ontology.nvl.json.tmp` → `os.replace`; write `manifest.json` (via `build_manifest`, `generated_at=contract.generated_at`, `stats={nodes, edges=len(relationships)}`).
     5. Return `PUBLISHED`.
4. Run → PASS. 5. Commit `feat(NFM-251): core digest-gated publisher`.

### Task 6: Non-blocking fire-and-forget hook wrapper

**Files:** Create `src/ontofuel/viz_corpus/hook.py`; Test `tests/test_corpus_hook.py`.

1. **Write failing tests** (never raises; records errors; respects opt-in):
```python
import json
from ontofuel.viz_corpus import hook

def test_hook_never_raises_even_when_publish_fails(monkeypatch):
    def boom(*a, **k): raise RuntimeError("boom")
    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus", boom)
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    # must NOT raise
    hook.maybe_publish_after_extraction(ONTO)
    # error recorded for alerting
    errs = json.loads((hook._error_log()).read_text())
    assert any("boom" in e["error"] for e in errs)

def test_hook_noop_when_opt_out(monkeypatch):
    monkeypatch.delenv("ONTOFUEL_AUTO_PUBLISH", raising=False)
    called = {"v": False}
    monkeypatch.setattr("ontofuel.viz_corpus.hook.publish_corpus",
                        lambda *a, **k: called.__setitem__("v", True))
    hook.maybe_publish_after_extraction(ONTO)
    assert called["v"] is False
```
2. Run → FAIL. 3. Implement `hook.py`: `maybe_publish_after_extraction(ontology_path)` — if not `config.auto_publish` → return; else `try: publish_corpus(...) except Exception as e: logger.warning(...); append {ts, error} to data/corpus/_publish_errors.jsonl`. Never re-raises.
4. Run → PASS. 5. Commit `feat(NFM-251): non-blocking post-extraction hook`.

### Task 7: Freshness check + alert

**Files:** Add `check_freshness()` to `publisher.py`; Test in `tests/test_corpus_publisher.py`.

1. **Write failing test**:
```python
from datetime import datetime, timezone, timedelta
from ontofuel.viz_corpus.publisher import check_freshness, FreshnessState
def test_freshness_stale_after_15min(tmp_path):
    publish_corpus(ontology_path=ONTO, corpus_root=tmp_path)
    # backdate manifest generated_at by 20 min
    m = json.loads((tmp_path/"ontofuel"/"manifest.json").read_text())
    old = (datetime.now(timezone.utc)-timedelta(minutes=20)).isoformat()
    m["generated_at"] = old
    (tmp_path/"ontofuel"/"manifest.json").write_text(json.dumps(m))
    assert check_freshness("ontofuel", corpus_root=tmp_path) is FreshnessState.STALE
```
2. Run → FAIL. 3. Implement `check_freshness(corpus_id, max_age_minutes=15) -> FreshnessState {FRESH, STALE, MISSING}`; STALE/MISSING → WARNING log + refresh `data/corpus/_freshness.json`.
4. Run → PASS. 5. Commit `feat(NFM-251): freshness check + alert`.

### Task 8: CLI subcommand `ontofuel publish-corpus`

**Files:** Modify `src/ontofuel/cli.py` (add subparser); Test `tests/test_cli_publish_corpus.py`.

1. **Write failing test** (CLI smoke):
```python
def test_cli_publish_corpus(tmp_path):
    from ontofuel.cli import main
    rc = main(["publish-corpus","--ontology",str(ONTO),
               "--corpus-root",str(tmp_path)])
    assert rc == 0
    assert (tmp_path/"ontofuel"/"manifest.json").exists()
```
2. Run → FAIL. 3. Add `publish-corpus` subparser in `cli.py` (flags `--ontology`, `--corpus-id`, `--corpus-root`, `--skip-drift`); calls `publish_corpus()`; exit 0 PUBLISHED/SKIPPED, exit 1 BLOCKED.
4. Run → PASS. 5. Commit `feat(NFM-251): publish-corpus CLI`.

### Task 9: Wire the hook into the extraction completion point

**Files:** Modify the extraction orchestration that finalizes `data/material_ontology_enhanced.json` (Lead Eng locates exact call-site — likely `cli.py` extract command end / a run script); guarded by `ONTOFUEL_AUTO_PUBLISH`.

1. **Write failing test** that an extraction run with `ONTOFUEL_AUTO_PUBLISH=1` triggers exactly one `publish_corpus` call (mock) and extraction result is still `success=True` even when publish raises.
2. Run → FAIL. 3. Insert `hook.maybe_publish_after_extraction(ontology_path)` immediately after the ontology is written/finalized.
4. Run → PASS. 5. Commit `feat(NFM-251): wire post-extraction auto-publish hook`.

### Task 10: Integration test — full chain end-to-end + same-origin servability

**Files:** `tests/test_corpus_pipeline_e2e.py`.

1. **Write test**: run `publish_corpus` on canonical ontology → assert `{corpus_id}/ontology.nvl.json` + `manifest.json` exist, manifest matches ADR §2 schema, NVL validates, `source_digest == 0d986d21a5a2b230` (canonical), and a second run is SKIPPED. Optionally `http.server`-serve `data/corpus/` and `urllib`-fetch the manifest (proves same-origin servability).
2. Run → PASS. 3. Commit `test(NFM-251): corpus publish e2e`.

### Task 11: Non-regression + docs

1. Run full suite: `pytest tests/ -q` (all prior green) + `ruff check src/ scripts/ tests/`.
2. Confirm `ONTOFUEL_AUTO_PUBLISH` unset → extraction behavior unchanged.
3. Add `docs/nfmd_corpus_publish.md` (one-pager: AC map, env vars, manifest schema, ops/alert).
4. Commit `docs(NFM-251): corpus publish runbook`.

### Task 12: Coordination gate before merge

> **⚠️ CORRECTION (2026-06-18, CPO):** "NFM-250 (viewer resolver)" referenced below does **not exist as a resolver** — NFM-250 is a *cancelled concurrent-run duplicate*, not a viewer-resolver issue (repo-wide search = 0 hits). The real consumer read side is the visualization-app resolver (`resolveCorpusId` stub in `src/utils/resolveDataUrl.ts`, owned by NFM-229 `done`, ADR D4). **Do not try to ack on cancelled NFM-250.** Coordinate the manifest URL convention against that read side; if it needs its own wiring child, **escalate to CTO** (don't silently diverge).

- Post the manifest URL convention (`/data/corpus/{corpus_id}/manifest.json`, default alias `ontofuel`) against the **visualization-app consumer resolver** (NFM-229 read side) and request ack. If the consumer's resolver convention differs → escalate to CTO (don't silently diverge).
- Hand to Code Reviewer (review issue) → on APPROVE, Release Engineer per-repo commit + PR (NFM-218/227/235 pattern).

---

## Verification (acceptance)
- [ ] `pytest tests/test_corpus_*.py tests/test_cli_publish_corpus.py tests/test_corpus_pipeline_e2e.py -v` all green
- [ ] Existing `pytest tests/ -q` + `ruff check` green (non-regression)
- [ ] `python -m ontofuel.cli publish-corpus --ontology data/material_ontology_enhanced.json` writes `data/corpus/ontofuel/{ontology.nvl.json,manifest.json}`; rerun = SKIPPED no-op
- [ ] manifest.json fields == ADR §2; NVL validates; `source_digest=0d986d21a5a2b230`
- [ ] Hook with `ONTOFUEL_AUTO_PUBLISH=1` publishes post-extraction; with publish forced to raise, extraction still `success=True` + error logged
- [ ] NFM-250 manifest-URL convention acked (or escalated)

## Out of scope (YAGNI / deferred)
- Tier-B dynamic NVL API (held option, ADR §2 graduation criteria only).
- Per-digest immutable archive dir (`_digests/{digest}/`) — provenance already guaranteed by the drift-gate + recorded `source_digest`; add only if NFM-250 needs historical pinning.
- Resident freshness-monitor daemon — `check_freshness()` + log alert is sufficient for Tier A; wire to a scheduler only if a cron owner is assigned.
