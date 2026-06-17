# NFMD Corpus Publish Pipeline

> NFM-251 / NFM-253 — NFMD Tier-A static corpus publish. Authoritative design:
> [NFM-226 ADR](../issues/NFM-226) §2 (manifest schema) + §3 (flow + binding constraints).

Wires the verified **viz-sync** pipeline into the extraction completion hook so
every extraction, end-to-end and unattended, produces a **validated, digest-gated**
NVL corpus published to the NFMD Tier-A static path. No daemon, no backend API.

## Flow

```
extraction finalizes ontology (OntologyUpdater.save)
        │  (opt-in: ONTOFUEL_AUTO_PUBLISH=1, else no-op)
        ▼
maybe_publish_after_extraction()          ← fire-and-forget, never raises
        ▼
publish_corpus()                          ← standalone, idempotent
   1. OntologyToNVLConverter → versioned contract  (reuse, NFM-227)
   2. validate_contract()    → Draft 2020-12 schema
   3. idempotency            → same source_digest? SKIPPED (no write)
   4. viz_sync --check       → provenance drift-gate (exit 0 required)
   5. atomic publish         → {corpus_id}/ontology.nvl.json + manifest.json
```

A publish failure is swallowed, logged `WARNING`, and appended to
`data/corpus/_publish_errors.jsonl`. **Extraction success is never affected**
(NFM-226 ADR §3 non-blocking binding).

## Files

| Concern | Module |
|---|---|
| Config (env) | `src/ontofuel/viz_corpus/config.py` — `CorpusPublishConfig.from_env()` |
| Converter shim | `src/ontofuel/viz_corpus/converter.py` — `build_nvl_contract()`, `validate()` |
| Drift gate | `src/ontofuel/viz_corpus/drift.py` — `drift_check_ok()` (reuses `viz_sync.check_drift`) |
| Manifest | `src/ontofuel/viz_corpus/manifest.py` — `build_manifest()` (ADR §2 schema) |
| Publisher | `src/ontofuel/viz_corpus/publisher.py` — `publish_corpus()`, `check_freshness()` |
| Hook | `src/ontofuel/viz_corpus/hook.py` — `maybe_publish_after_extraction()` |
| CLI | `ontofuel publish-corpus` (`src/ontofuel/cli.py`) |
| Wiring | `src/ontofuel/extraction/updater.py` — `OntologyUpdater.save()` |

## Environment variables

| Var | Default | Meaning |
|---|---|---|
| `ONTOFUEL_AUTO_PUBLISH` | unset (`0`) | **Opt-in** auto-publish after extraction. Default off = byte-identical extraction behavior (non-regressive). |
| `ONTOFUEL_CORPUS_ID` | `ontofuel` | Corpus alias (path segment + manifest `corpus_id`). |
| `ONTOFUEL_CORPUS_ROOT` | `<repo>/data/corpus` | Publish root (same-origin served at `http://<host>:9999/data/corpus/...`). |

## Manifest schema (NFM-226 ADR §2)

`data/corpus/{corpus_id}/manifest.json`:

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

`source_digest` = sha256[:16] of the canonical ontology (provenance anchor; consumers
cache-bust/verify against it).

## Ops / alerting

- **Idempotency**: rerun with unchanged `source_digest` → `SKIPPED`, files untouched.
- **Provenance gate**: publish proceeds ONLY when `viz-sync --check` exits 0 (artifact
  provably derived, not hand-edited); otherwise `BLOCKED`.
- **Atomicity**: temp-file + `os.replace` — consumers never see a half-written artifact.
- **Freshness**: `check_freshness(corpus_id, max_age_minutes=15)` → `FRESH|STALE|MISSING`;
  STALE/MISSING emit `WARNING` + refresh `data/corpus/_freshness.json`.
- **Errors**: publish failures append to `data/corpus/_publish_errors.jsonl` (JSONL).

## CLI

```bash
# one-shot publish (drift-gated)
ontofuel publish-corpus --ontology data/material_ontology_enhanced.json
# exit 0 = PUBLISHED/SKIPPED, exit 1 = BLOCKED

# bypass the provenance gate (not recommended)
ontofuel publish-corpus --ontology ... --skip-drift

# custom corpus id / root
ontofuel publish-corpus --ontology ... --corpus-id experimental --corpus-root /tmp/corpus
```

## Acceptance-criteria map

| AC (NFM-253) | Mechanism |
|---|---|
| hook → convert → validate → drift-check → publish full chain | `publish_corpus()`; e2e `tests/test_corpus_pipeline_e2e.py` |
| `/{corpus_id}/ontology.nvl.json` + `/{corpus_id}/manifest.json` | atomic publish to `data/corpus/{corpus_id}/` |
| idempotent + digest-gated (rerun = no-op) | manifest `source_digest` compare → `SKIPPED` |
| non-blocking (failure alerts, never fails extraction) | `maybe_publish_after_extraction()` swallow + `_publish_errors.jsonl` |
| freshness <15 min + alert | in-process (seconds); `check_freshness()` + `_freshness.json` |
| provenance gating (`viz-sync --check` exit 0; `source_digest` recorded) | `drift_check_ok()` gate; `manifest.source_digest` |

## Out of scope (YAGNI)

- Tier-B dynamic NVL API (held option; ADR §2 graduation only).
- Per-digest immutable archive — provenance already guaranteed by drift-gate + recorded `source_digest`.
- Resident freshness daemon — `check_freshness()` + log alert suffices for Tier A.
