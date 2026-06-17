# viz-sync — Ontology → NVL Contract Sync

> NFM-230 (NFM-226 ADR §2 D3 / G1). The deterministic one-shot pipeline that keeps
> the visualization app's NVL data aligned with the canonical ontology, eliminating
> the manual-copy drift between the extraction-side and visualization-side copies.

## Why

The React NVL visualization app (`visualization-app/`) loads
`public/data/nvl_ontology_data.json`. That file was maintained by **manual copy**
from the extraction-side `data/nvl_ontology_data.json`, which itself had to be
regenerated from the canonical ontology `data/material_ontology_enhanced.json`. With
no automation, the three copies drifted: at NFM-230 the viz-side copy was a stale
`nodes`/`relationships` blob (915 nodes / 1048 rels) while the canonical regen
produced a versioned contract of 927 nodes / 1061 rels. `viz-sync` removes the
manual step and adds a CI gate so drift can never be merged again.

## The command

```bash
ontofuel viz-sync
# or, equivalently:
python scripts/viz_sync.py
```

Regenerates the versioned NVL contract (NFM-227) from the canonical ontology and
writes the **same bytes** to both destinations, asserting they are byte-identical:

| Destination | Default path |
| --- | --- |
| Canonical ontology (input) | `data/material_ontology_enhanced.json` |
| Extraction-side copy | `data/nvl_ontology_data.json` |
| Visualization-side copy | `visualization-app/public/data/nvl_ontology_data.json` |

### Flags

| Flag | Purpose |
| --- | --- |
| `--canonical PATH` | Override the canonical ontology input. |
| `--extraction-out PATH` | Override the extraction-side output. |
| `--viz-out PATH` | Override the visualization-side output. |
| `--pin-timestamp ISO` | Fix `generated_at` for reproducible/deterministic builds. |
| `--check` | **CI drift gate** — compare the committed viz copy against a fresh regen; exit `1` on drift. Performs **no writes**. |
| `--no-backup` | Do not take a `.bak` of the viz copy before overwriting. |

## Determinism

`source_digest` is the sha256 of the canonical ontology (key-sorted, no
whitespace) truncated to 16 hex chars. It is stable across runs, so **the same
ontology always yields the same nodes/relationships**. The only non-deterministic
field is `generated_at` (UTC build time); `--pin-timestamp` fixes it for
reproducible builds, and the drift gate excludes it so a fresh timestamp alone is
never treated as drift.

Current anchor (NFM-227 / NFM-235 acceptance):

```
schema_version = 1.0
source_digest  = 0d986d21a5a2b230
stats          = nodes 927 · relationships 1061 · classes 172 · individuals 755
```

## CI drift gate

`tests/test_viz_sync_drift.py::test_extraction_copy_has_no_drift` regenerates the
contract from the canonical ontology and compares it (content-normalized, excluding
`generated_at`) against the committed extraction-side copy. If someone edits the
ontology but forgets to run `ontofuel viz-sync`, **the build fails** until the copy
is regenerated and committed.

The visualization-side copy lives in a separate repo (`visualization-app`); its
cross-repo mirror check (`test_viz_copy_matches_extraction_copy_when_present`) runs
on developer machines where the nested checkout is present and skips in CI.

## Workflow

After changing the canonical ontology:

```bash
ontofuel viz-sync            # regenerate + write both copies
git add data/nvl_ontology_data.json \
        visualization-app/public/data/nvl_ontology_data.json
git commit                   # commit the regenerated copies together
```

Verify locally before pushing:

```bash
ontofuel viz-sync --check    # exit 0 = no drift
```

## Architecture

- **Reuses** `scripts/ontology_to_nvl.py` (NFM-227) — `viz-sync` never rewrites the
  converter, only calls `OntologyToNVLConverter.build_contract()`.
- The output is the NFM-227 **versioned contract** (`schema_version`,
  `generated_at`, `source_ontology`, `source_digest`, `stats`, `nodes`,
  `relationships`) and validates against `schemas/nvl_contract.schema.json`.
- `viz-sync` writes one serialization to every destination, guaranteeing the two
  copies can never diverge once produced.

## Prerequisites

- Python 3.10+ (stdlib only for the sync itself; `jsonschema` only for full contract
  validation, with a structural fallback).
- The canonical ontology at `data/material_ontology_enhanced.json`.
- For the visualization-side write: the `visualization-app/` checkout present (it is
  a separate repo, nested in development).
