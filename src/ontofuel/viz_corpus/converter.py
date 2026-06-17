"""Import shim: reuse the verified NVL converter + contract validation (NFM-227).

Reuses ``OntologyToNVLConverter`` + ``validate_contract`` from
``scripts/ontology_to_nvl.py`` — never rewrites them. Mirrors the ``sys.path``
import pattern used by ``scripts/viz_sync.py`` (NFM-241 focus #4: zero reimplementation).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# converter.py lives at <repo>/src/ontofuel/viz_corpus/converter.py
#   parents[0]=viz_corpus, [1]=ontofuel, [2]=src, [3]=<repo root>
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ontology_to_nvl import (  # noqa: E402
    OntologyToNVLConverter,
    validate_contract,
)


def build_nvl_contract(ontology_path: Path | str) -> dict[str, Any]:
    """Build the versioned NVL contract from the canonical ontology (reuse, not rewrite).

    Returns the contract dict carrying ``schema_version``, ``source_digest``
    (sha256[:16] of the canonical ontology), ``nodes``, ``relationships``,
    ``generated_at`` and ``stats``.
    """
    converter = OntologyToNVLConverter(str(ontology_path))
    return converter.convert()


def validate(contract: dict[str, Any]) -> list[str]:
    """Validate a contract against the NVL Draft 2020-12 schema.

    Returns a list of error messages; an empty list means the contract is valid.
    """
    return validate_contract(contract)
