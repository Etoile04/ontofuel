"""Conformance tests for the versioned NVL data contract (NFM-227 / NFM-226 ADR D2).

Verifies that the ontology→NVL converter emits a versioned, provenance-bearing
contract that validates against the in-repo JSON Schema, that source-ontology
counts match the NFM-217 anchored truth (156/169/302/755), and that the
nodes/relationships element structure is preserved (backward compatible).
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# make scripts/ importable without installing the package
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ontology_to_nvl import (  # noqa: E402
    DIGEST_LENGTH,
    NVL_SCHEMA_VERSION,
    OntologyToNVLConverter,
    load_contract_schema,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = REPO_ROOT / "data" / "material_ontology_enhanced.json"
NVL_OUTPUT_PATH = REPO_ROOT / "data" / "nvl_ontology_data.json"

# NFM-217 锚定的本体真值
EXPECTED_SOURCE_COUNTS = {
    "classes": 156,
    "objectProperties": 169,
    "datatypeProperties": 302,
    "individuals": 755,
}

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402


@pytest.fixture(scope="module")
def converter() -> OntologyToNVLConverter:
    return OntologyToNVLConverter(str(ONTOLOGY_PATH))


@pytest.fixture(scope="module")
def contract(converter: OntologyToNVLConverter) -> dict:
    # 固定 generated_at 以保证可复现（不影响其余断言）
    return converter.build_contract(generated_at="2026-06-17T00:00:00+00:00")


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_contract_schema()


# --------------------------------------------------------------------------- #
# 1. 契约顶层结构
# --------------------------------------------------------------------------- #
CONTRACT_REQUIRED_KEYS = [
    "schema_version",
    "generated_at",
    "source_ontology",
    "source_digest",
    "stats",
    "nodes",
    "relationships",
]


def test_contract_has_required_envelope(contract: dict):
    for key in CONTRACT_REQUIRED_KEYS:
        assert key in contract, f"contract missing required key: {key}"


def test_schema_version_is_initial_value(contract: dict):
    assert contract["schema_version"] == NVL_SCHEMA_VERSION == "1.0"


def test_generated_at_is_iso8601(contract: dict):
    # datetime.fromisoformat 解析成功即视为 ISO-8601
    parsed = datetime.fromisoformat(contract["generated_at"])
    assert parsed.tzinfo is not None, "generated_at 必须带时区（UTC）"


def test_source_ontology_points_to_canonical(contract: dict):
    assert contract["source_ontology"].endswith("material_ontology_enhanced.json")


def test_stats_has_required_counts(contract: dict):
    stats = contract["stats"]
    for key in ("nodes", "relationships", "classes", "individuals"):
        assert key in stats, f"stats missing {key}"
        assert isinstance(stats[key], int) and stats[key] >= 0


def test_stats_counts_match_actual_elements(contract: dict):
    stats = contract["stats"]
    assert stats["nodes"] == len(contract["nodes"])
    assert stats["relationships"] == len(contract["relationships"])
    assert stats["classes"] == sum(1 for n in contract["nodes"] if n.get("type") == "class")
    assert stats["individuals"] == sum(
        1 for n in contract["nodes"] if n.get("type") == "individual"
    )


# --------------------------------------------------------------------------- #
# 2. source_digest 正确性与可复现
# --------------------------------------------------------------------------- #
def test_source_digest_format(contract: dict):
    digest = contract["source_digest"]
    assert len(digest) == DIGEST_LENGTH
    assert all(c in "0123456789abcdef" for c in digest)


def test_source_digest_matches_canonical_recompute(contract: dict):
    """source_digest 必须等于对规范本体确定性序列化的 sha256[:16]。"""
    with open(ONTOLOGY_PATH, encoding="utf-8") as f:
        ontology = json.load(f)
    canonical = json.dumps(ontology, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]
    assert contract["source_digest"] == expected


# --------------------------------------------------------------------------- #
# 3. JSON Schema 校验（核心 conformance 门）
# --------------------------------------------------------------------------- #
def test_contract_passes_json_schema(contract: dict, schema: dict):
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))
    assert not errors, "契约未通过 JSON Schema 校验:\n" + "\n".join(
        f"  - {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
    )


def test_validate_contract_helper_is_consistent(contract: dict):
    """模块级 validate_contract 助手必须与直接使用 jsonschema 一致。"""
    assert validate_contract(contract) == []


def test_schema_rejects_invalid_node_type(schema: dict):
    bad = {
        "schema_version": "1.0",
        "generated_at": "2026-06-17T00:00:00+00:00",
        "source_ontology": "x.json",
        "source_digest": "0" * DIGEST_LENGTH,
        "stats": {"nodes": 1, "relationships": 0, "classes": 1, "individuals": 0},
        "nodes": [{"id": "n1", "type": "bogus"}],
        "relationships": [],
    }
    errors = list(Draft202012Validator(schema).iter_errors(bad))
    assert errors, "schema 应拒绝非法节点 type"


def test_schema_accepts_domain_verb_relationship_type(schema: dict):
    """关系 type 必须接受 INSTANCE_OF / SUBCLASS_OF 与领域动词（对象属性名）。"""
    for rtype in ("INSTANCE_OF", "SUBCLASS_OF", "hasComposition", "undergoes"):
        doc = {
            "schema_version": "1.0",
            "generated_at": "2026-06-17T00:00:00+00:00",
            "source_ontology": "x.json",
            "source_digest": "0" * DIGEST_LENGTH,
            "stats": {"nodes": 2, "relationships": 1, "classes": 2, "individuals": 0},
            "nodes": [
                {"id": "a", "type": "class"},
                {"id": "b", "type": "class"},
            ],
            "relationships": [{"id": "r1", "from": "a", "to": "b", "type": rtype}],
        }
        errors = list(Draft202012Validator(schema).iter_errors(doc))
        assert not errors, f"schema 错误拒绝了合法关系 type {rtype!r}"


# --------------------------------------------------------------------------- #
# 4. NFM-217 本体真值锚定
# --------------------------------------------------------------------------- #
def test_source_ontology_counts_match_nfm217_truth():
    with open(ONTOLOGY_PATH, encoding="utf-8") as f:
        ontology = json.load(f)
    for key, expected in EXPECTED_SOURCE_COUNTS.items():
        assert len(ontology.get(key, {})) == expected, (
            f"source ontology {key} count drift: "
            f"expected {expected}, got {len(ontology.get(key, {}))}"
        )


# --------------------------------------------------------------------------- #
# 5. nodes/relationships 元素结构保持（向后兼容）
# --------------------------------------------------------------------------- #
def test_nodes_have_required_element_fields(contract: dict):
    for node in contract["nodes"]:
        assert "id" in node and "type" in node
        assert node["type"] in ("class", "individual")


def test_relationships_have_required_element_fields(contract: dict):
    node_ids = {n["id"] for n in contract["nodes"]}
    for rel in contract["relationships"]:
        for key in ("id", "from", "to", "type"):
            assert key in rel, f"relationship missing {key}"
        assert rel["from"] in node_ids, f"dangling relationship.from: {rel['from']}"
        assert rel["to"] in node_ids, f"dangling relationship.to: {rel['to']}"


# --------------------------------------------------------------------------- #
# 6. save_nvl_json 写出可被 schema 校验的契约（端到端）
# --------------------------------------------------------------------------- #
def test_save_nvl_json_writes_valid_contract(tmp_path: Path):
    converter = OntologyToNVLConverter(str(ONTOLOGY_PATH))
    converter.convert()
    out = tmp_path / "nvl.json"
    written = converter.save_nvl_json(str(out), generated_at="2026-06-17T00:00:00+00:00")
    assert validate_contract(written) == []
    with open(out, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["schema_version"] == "1.0"
    assert validate_contract(on_disk) == []


# --------------------------------------------------------------------------- #
# 7. 仓库内随附的 nvl_ontology_data.json 也是合规契约
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not NVL_OUTPUT_PATH.exists(), reason="canonical NVL artifact not present")
def test_checked_in_nvl_artifact_is_valid_contract():
    with open(NVL_OUTPUT_PATH, encoding="utf-8") as f:
        artifact = json.load(f)
    assert "schema_version" in artifact, "随附 NVL 仍是旧的无版本格式"
    assert validate_contract(artifact) == []
