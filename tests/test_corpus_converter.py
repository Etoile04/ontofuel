"""Converter import shim (NFM-251 Task 2).

Reuse the verified NVL converter + contract validation (NFM-227) — do NOT rewrite.
Produces the versioned contract and validates it clean against the Draft 2020-12
schema.
"""

from __future__ import annotations

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


def test_build_contract_is_deterministic():
    # same canonical ontology -> same source_digest (provenance anchor)
    c1 = build_nvl_contract(ONTO)
    c2 = build_nvl_contract(ONTO)
    assert c1["source_digest"] == c2["source_digest"]
    assert c1["source_digest"] == "0d986d21a5a2b230"
