"""Tests for ontofuel.extraction.versioning — Git-style ontology version control."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ontofuel.extraction.versioning import OntologyVersionControl


def _make_onto(
    classes: dict | None = None,
    object_properties: dict | None = None,
    datatype_properties: dict | None = None,
    individuals: dict | None = None,
) -> dict:
    return {
        "classes": classes or {},
        "objectProperties": object_properties or {},
        "datatypeProperties": datatype_properties or {},
        "individuals": individuals or {},
    }


# ── helpers for creating a VCS instance in a temp dir ───────────────────────


def _vc(tmp_path: Path, name: str = "ontology.json") -> OntologyVersionControl:
    onto_path = tmp_path / name
    onto_path.write_text(json.dumps(_make_onto()), encoding="utf-8")
    versions_dir = tmp_path / "versions"
    return OntologyVersionControl(onto_path, versions_dir)


# ── _compute_hash ─────────────────────────────────────────────────────────


class TestComputeHash:
    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        onto = _make_onto(classes={"A": {}})
        h1 = vc._compute_hash(onto)
        h2 = vc._compute_hash(onto)
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        h1 = vc._compute_hash(_make_onto(classes={"A": {}}))
        h2 = vc._compute_hash(_make_onto(classes={"B": {}}))
        assert h1 != h2


# ── commit ──────────────────────────────────────────────────────────────────


class TestCommit:
    def test_initial_commit(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        onto = _make_onto(classes={"Animal": {}})
        v = vc.commit("initial", ontology_data=onto)
        assert v.version == "1.0.0"
        assert v.hash in vc.versions_history

    def test_append_commit(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        v1 = vc.commit("v1", ontology_data=_make_onto(classes={"Animal": {}}))
        v2 = vc.commit("v2", ontology_data=_make_onto(classes={"Animal": {}, "Person": {}}))
        assert v2.version == "1.1.0"  # MINOR — class added
        assert v2.parent_hashes == [v1.hash]

    def test_duplicate_commit_skipped(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        v1 = vc.commit("first", ontology_data=_make_onto(classes={"A": {}}))
        # Same logical content — commit mutates in place, so pass a fresh copy
        v2 = vc.commit("duplicate", ontology_data=_make_onto(classes={"A": {}}))
        assert v1.hash == v2.hash
        assert v2 is v1  # same object returned

    def test_version_bump_minor_on_class_added(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        v2 = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        assert v2.version == "1.1.0"

    def test_version_bump_major_on_class_removed(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        v2 = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}}))
        assert v2.version == "2.0.0"

    def test_version_bump_patch_on_individual_only(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        v2 = vc.commit(
            "v2",
            ontology_data=_make_onto(classes={"A": {}}, individuals={"x": {}}),
        )
        assert v2.version == "1.0.1"

    def test_snapshot_file_created(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        onto = _make_onto(classes={"A": {}})
        v = vc.commit("snap", ontology_data=onto)
        snapshot = vc.versions_dir / f"{v.hash}.json"
        assert snapshot.exists()

    def test_versions_json_updated(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        assert vc.versions_file.exists()
        data = json.loads(vc.versions_file.read_text(encoding="utf-8"))
        assert len(data) == 1


# ── log ────────────────────────────────────────────────────────────────────


class TestLog:
    def test_returns_correct_count(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("1", ontology_data=_make_onto(classes={"A": {}}))
        vc.commit("2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        vc.commit("3", ontology_data=_make_onto(classes={"A": {}, "B": {}, "C": {}}))
        assert len(vc.log(limit=10)) == 3

    def test_sorted_newest_first(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("first", ontology_data=_make_onto(classes={"A": {}}))
        time.sleep(0.01)
        vc.commit("second", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        entries = vc.log(limit=2)
        assert entries[0].message == "second"
        assert entries[1].message == "first"

    def test_limit_respected(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        for i in range(5):
            vc.commit(f"commit {i}", ontology_data=_make_onto(classes={f"C{i}": {}}))
        assert len(vc.log(limit=2)) == 2


# ── diff ───────────────────────────────────────────────────────────────────


class TestDiff:
    def test_diff_between_two_versions(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        v1 = vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        v2 = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))

        report = vc.diff(v1.hash, v2.hash)
        assert report["changes"]["classes_added"] == 1
        assert report["changes"]["classes_removed"] == 0
        assert report["version1"]["hash"] == v1.hash
        assert report["version2"]["hash"] == v2.hash

    def test_diff_raises_on_missing_version(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        with pytest.raises(ValueError, match="版本不存在"):
            vc.diff("deadbeef12345678", "deadbeef87654321")


# ── checkout ────────────────────────────────────────────────────────────────


class TestCheckout:
    def test_checkout_restores_old_version(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        v1 = vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        vc.commit("v2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))

        restored = vc.checkout(v1.hash)
        assert "B" not in restored.get("classes", {})

    def test_checkout_raises_on_missing_hash(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        with pytest.raises(ValueError, match="版本"):
            vc.checkout("deadbeef12345678")

    def test_checkout_updates_current_version(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        v1 = vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        _ = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        vc.checkout(v1.hash)
        # Current ontology should have only A
        assert "B" not in vc.current_version.get("classes", {})


# ── version upgrade rules ──────────────────────────────────────────────────


class TestVersionUpgradeRules:
    def test_new_class_minor(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        v = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        assert v.version == "1.1.0"

    def test_deleted_class_major(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}, "B": {}}))
        v = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}}))
        assert v.version == "2.0.0"

    def test_only_individuals_patch(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        v = vc.commit("v2", ontology_data=_make_onto(classes={"A": {}}, individuals={"x": {}}))
        assert v.version == "1.0.1"

    def test_new_property_minor(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(object_properties={"p1": {}}))
        v = vc.commit(
            "v2",
            ontology_data=_make_onto(object_properties={"p1": {}, "p2": {}}),
        )
        assert v.version == "1.1.0"


# ── branch / merge ────────────────────────────────────────────────────────


class TestBranchMerge:
    def test_branch_creates_file(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        path = vc.branch("feature")
        assert Path(path).exists()

    def test_merge_union(self, tmp_path: Path) -> None:
        vc = _vc(tmp_path)
        vc.commit("v1", ontology_data=_make_onto(classes={"A": {}}))
        vc.branch("feature")
        # Simulate branch work by directly writing branch file
        branch_path = vc.versions_dir / "branch_feature.json"
        branch_data = _make_onto(classes={"B": {}})
        branch_path.write_text(json.dumps(branch_data), encoding="utf-8")

        _ = vc.merge("feature", "merge feature")
        assert "A" in vc.current_version.get("classes", {})
        assert "B" in vc.current_version.get("classes", {})


# pytest import for raises
import pytest  # noqa: E402
