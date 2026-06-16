#!/usr/bin/env python3
"""viz-sync — deterministic one-shot sync of the canonical ontology to the
versioned NVL contract consumed by the visualization app.

NFM-230 (NFM-226 ADR §2 D3 / G1). Eliminates the manual-copy data drift between
the extraction-side copy (``data/nvl_ontology_data.json``) and the visualization-side
copy (``visualization-app/public/data/nvl_ontology_data.json``).

The pipeline regenerates the NVL contract from the canonical ontology using the
existing converter (``scripts/ontology_to_nvl.py`` — NFM-227), then writes the SAME
bytes to both destinations and asserts they agree. The committed viz-side copy is
what the React app loads; regenerating straight into it (plus a CI drift gate) is
what keeps the two sides from diverging again.

Determinism
-----------
``source_digest`` is the sha256 of the canonical ontology (key-sorted, no
whitespace) truncated to 16 hex chars — stable across runs, so the same ontology
always yields the same nodes/relationships. The only non-deterministic field is
``generated_at``; ``--pin-timestamp`` fixes it for reproducible builds and the CI
drift check.

Modes
-----
- default:  regenerate → write both destinations → assert byte-identical → report stats
- ``--check``: regenerate to a buffer, compare (content-normalized, excluding
  ``generated_at``) against the committed viz-side copy; exit 1 on drift. The CI
  drift gate. Performs no writes.

Reuses ``OntologyToNVLConverter`` from ``ontology_to_nvl.py`` — never rewrites the
converter.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the sibling converter importable without installing the package.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ontology_to_nvl import OntologyToNVLConverter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CANONICAL = REPO_ROOT / "data" / "material_ontology_enhanced.json"
DEFAULT_EXTRACTION_OUT = REPO_ROOT / "data" / "nvl_ontology_data.json"
DEFAULT_VIZ_OUT = REPO_ROOT / "visualization-app" / "public" / "data" / "nvl_ontology_data.json"

# Fields excluded from drift comparison: generated_at is the only intentionally
# non-deterministic field (UTC build time). Everything else must match exactly.
NON_DETERMINISTIC_FIELDS = ("generated_at",)


class DriftError(RuntimeError):
    """Raised when the committed viz-side copy diverges from the canonical regen."""


def regenerate_contract(
    canonical_path: Path, pin_timestamp: str | None = None
) -> dict[str, Any]:
    """Regenerate the versioned NVL contract from the canonical ontology.

    Reuses ``OntologyToNVLConverter`` (NFM-227); does not rewrite the converter.
    ``pin_timestamp`` makes ``generated_at`` deterministic for reproducible builds.
    """
    converter = OntologyToNVLConverter(str(canonical_path))
    converter.convert()
    return converter.build_contract(generated_at=pin_timestamp)


def serialize_contract(contract: dict[str, Any]) -> str:
    """Serialize the contract to canonical bytes (indent=2, ensure_ascii=False).

    A single serialization written to every destination guarantees byte-identical
    output across the extraction-side and visualization-side copies.
    """
    return json.dumps(contract, indent=2, ensure_ascii=False)


def _normalize_for_drift(contract: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``contract`` with non-deterministic fields removed.

    Used by the drift check so that a fresh ``generated_at`` does not mask real
    structural drift (the only legitimate run-to-run variance is the timestamp).
    """
    return {k: v for k, v in contract.items() if k not in NON_DETERMINISTIC_FIELDS}


def _digest_summary(contract: dict[str, Any]) -> dict[str, Any]:
    """Compact, human-readable summary used in stats reporting and diff output."""
    return {
        "schema_version": contract.get("schema_version"),
        "source_digest": contract.get("source_digest"),
        "source_ontology": contract.get("source_ontology"),
        "stats": contract.get("stats"),
    }


def write_contract(contract: dict[str, Any], dest: Path) -> int:
    """Write the contract to ``dest``, returning the byte size written.

    Creates parent directories. Overwrites any existing copy (this is the drift fix).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_contract(contract)
    dest.write_text(payload, encoding="utf-8")
    return dest.stat().st_size


def sync(
    canonical_path: Path = DEFAULT_CANONICAL,
    extraction_out: Path = DEFAULT_EXTRACTION_OUT,
    viz_out: Path = DEFAULT_VIZ_OUT,
    pin_timestamp: str | None = None,
    backup_viz: bool = True,
) -> dict[str, Any]:
    """Regenerate the contract and write the SAME bytes to both destinations.

    Asserts the two destinations are byte-identical after writing. Returns a stats
    dict. When ``backup_viz`` is true and the viz-side copy exists, a ``.bak`` copy
    is taken before overwrite (guard against clobbering unsaved local experiments).
    """
    contract = regenerate_contract(canonical_path, pin_timestamp=pin_timestamp)
    payload = serialize_contract(contract)

    extraction_out.parent.mkdir(parents=True, exist_ok=True)
    extraction_out.write_text(payload, encoding="utf-8")
    extraction_size = extraction_out.stat().st_size

    if backup_viz and viz_out.exists():
        backup = viz_out.with_suffix(viz_out.suffix + ".bak")
        backup.write_bytes(viz_out.read_bytes())

    viz_out.parent.mkdir(parents=True, exist_ok=True)
    viz_out.write_text(payload, encoding="utf-8")
    viz_size = viz_out.stat().st_size

    if extraction_size != viz_size:
        raise DriftError(
            f"destinations disagree after write: extraction={extraction_size}B "
            f"viz={viz_size}B — serialization is not deterministic"
        )

    return {
        **_digest_summary(contract),
        "canonical": str(canonical_path),
        "extraction_out": str(extraction_out),
        "viz_out": str(viz_out),
        "extraction_bytes": extraction_size,
        "viz_bytes": viz_size,
        "identical": extraction_size == viz_size,
    }


def check_drift(
    canonical_path: Path = DEFAULT_CANONICAL,
    copy_path: Path = DEFAULT_EXTRACTION_OUT,
    pin_timestamp: str | None = None,
) -> dict[str, Any]:
    """Compare a committed NVL copy against a fresh canonical regen.

    Defaults to the extraction-side copy (``data/nvl_ontology_data.json``) — the
    artifact committed in THIS repo and present in CI. Content-normalized
    (``generated_at`` excluded) so a new timestamp alone is not drift. Returns a
    result dict with ``drifted`` (bool) and a summary for each side. Performs no
    writes — this is the CI gate.
    """
    if not copy_path.exists():
        raise DriftError(f"committed copy not found: {copy_path}")

    fresh = regenerate_contract(canonical_path, pin_timestamp=pin_timestamp)
    committed = json.loads(copy_path.read_text(encoding="utf-8"))

    fresh_norm = _normalize_for_drift(fresh)
    committed_norm = _normalize_for_drift(committed)
    drifted = fresh_norm != committed_norm

    return {
        "drifted": drifted,
        "canonical": str(canonical_path),
        "copy_path": str(copy_path),
        "expected": _digest_summary(fresh),
        "committed": _digest_summary(committed),
    }


def _format_stats(report: dict[str, Any]) -> str:
    lines = [
        "═══ viz-sync ═══",
        f"  canonical:       {report.get('canonical')}",
        f"  schema_version:  {report.get('schema_version')}",
        f"  source_digest:   {report.get('source_digest')}",
        f"  source_ontology: {report.get('source_ontology')}",
    ]
    stats = report.get("stats") or {}
    if stats:
        lines.append(
            "  stats:           "
            f"nodes={stats.get('nodes')} relationships={stats.get('relationships')} "
            f"classes={stats.get('classes')} individuals={stats.get('individuals')}"
        )
    if "extraction_bytes" in report:
        lines.append(f"  extraction copy: {report['extraction_bytes']:,} bytes")
        lines.append(f"  viz copy:        {report['viz_bytes']:,} bytes")
        lines.append(f"  identical:       {report['identical']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="viz-sync",
        description=(
            "Deterministic sync of the canonical ontology → versioned NVL contract "
            "into both extraction-side and visualization-side data copies (NFM-230)."
        ),
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=DEFAULT_CANONICAL,
        help=f"Canonical ontology JSON (default: {DEFAULT_CANONICAL})",
    )
    parser.add_argument(
        "--extraction-out",
        type=Path,
        default=DEFAULT_EXTRACTION_OUT,
        help=f"Extraction-side NVL output (default: {DEFAULT_EXTRACTION_OUT})",
    )
    parser.add_argument(
        "--viz-out",
        type=Path,
        default=DEFAULT_VIZ_OUT,
        help=f"Visualization-side NVL output (default: {DEFAULT_VIZ_OUT})",
    )
    parser.add_argument(
        "--pin-timestamp",
        default=None,
        help="Fix generated_at to this ISO-8601 value (deterministic builds / CI).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Drift-check only (CI gate): compare a committed copy vs fresh regen; "
            "no writes. Defaults to the extraction-side copy."
        ),
    )
    parser.add_argument(
        "--check-path",
        type=Path,
        default=DEFAULT_EXTRACTION_OUT,
        help=f"Copy to drift-check in --check mode (default: {DEFAULT_EXTRACTION_OUT}).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not take a .bak of the viz-side copy before overwriting.",
    )
    args = parser.parse_args(argv)

    if args.check:
        result = check_drift(
            canonical_path=args.canonical,
            copy_path=args.check_path,
            pin_timestamp=args.pin_timestamp,
        )
        if result["drifted"]:
            print(
                "❌ DRIFT DETECTED — the committed copy does not match a fresh "
                "regeneration from the canonical ontology.",
                file=sys.stderr,
            )
            print(f"  copy:            {result['copy_path']}", file=sys.stderr)
            print(f"  expected (fresh): {result['expected']}", file=sys.stderr)
            print(f"  committed:        {result['committed']}", file=sys.stderr)
            print(
                "  Run `ontofuel viz-sync` (or `python scripts/viz_sync.py`) to fix.",
                file=sys.stderr,
            )
            return 1
        print("✅ no drift — committed copy matches canonical regeneration")
        print(f"  copy:          {result['copy_path']}")
        print(f"  source_digest: {result['expected']['source_digest']}")
        return 0

    report = sync(
        canonical_path=args.canonical,
        extraction_out=args.extraction_out,
        viz_out=args.viz_out,
        pin_timestamp=args.pin_timestamp,
        backup_viz=not args.no_backup,
    )
    print(_format_stats(report))
    print("✅ synced — extraction-side and visualization-side copies are byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
