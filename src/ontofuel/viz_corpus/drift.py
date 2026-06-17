"""Drift-gate wrapper: provenance gate reusing viz_sync.check_drift (NFM-230).

``drift_check_ok()`` is True iff the committed NVL copy matches a fresh canonical
regeneration — i.e. the artifact is provably derived from the converter and not
hand-edited. Publish proceeds ONLY when this returns True (NFM-226 ADR §3
provenance gating). Zero reimplementation of viz_sync (NFM-241 focus #4). Fails
closed: a missing copy or any drift returns False.
"""

from __future__ import annotations

import sys
from pathlib import Path

# drift.py lives at <repo>/src/ontofuel/viz_corpus/drift.py
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from viz_sync import (  # noqa: E402
    DEFAULT_CANONICAL,
    DEFAULT_EXTRACTION_OUT,
    DriftError,
    check_drift,
)

PathLike = str | Path | None


def drift_check_ok(
    canonical_path: PathLike = None,
    copy_path: PathLike = None,
) -> bool:
    """Return True iff the committed NVL copy is drift-free vs a fresh canonical regen.

    Fails closed: a missing committed copy or any detected drift returns False, so
    the publisher blocks rather than shipping an unprovable artifact.
    """
    try:
        result = check_drift(
            canonical_path=Path(canonical_path) if canonical_path else DEFAULT_CANONICAL,
            copy_path=Path(copy_path) if copy_path else DEFAULT_EXTRACTION_OUT,
        )
    except DriftError:
        return False
    return not result.get("drifted", True)
