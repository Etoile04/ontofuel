"""Integration tests for OntoCast modules in extraction pipeline.

Tests the four integration points:
1. Updater.save() triggers GraphUpdate + Versioning
2. Merger.merge() triggers Sublimation
3. OntologyCritic as quality gate
4. Full end-to-end pipeline
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontofuel.extraction.extractor import ExtractionResult
from ontofuel.extraction.merger import Merger
from ontofuel.extraction.updater import OntologyUpdater
from ontofuel.extraction.graph_update import OntologyDiff
from ontofuel.extraction.versioning import OntologyVersionControl, OntologyVersion
from ontofuel.extraction.sublimation import OntologySublimator, SeparationResult
from ontofuel.extraction.critic import OntologyCritic, CritiqueSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ontology_json(
    tmp_path: Path,
    name: str = "test_ont.json",
) -> Path:
    """Create a minimal ontology JSON file."""
    ont = {
        "classes": {},
        "objectProperties": {},
        "datatypeProperties": {},
        "individuals": [],
    }
    p = tmp_path / name
    p.write_text(json.dumps(ont), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: Updater.save() triggers GraphUpdate
# ---------------------------------------------------------------------------

class TestUpdaterGraphUpdate:
    """Integration point 1a: save() computes and persists OntologyDiff."""

    def test_updater_save_triggers_graph_update(self, tmp_path):
        ont_file = _make_ontology_json(tmp_path)

        updater = OntologyUpdater(
            ont_file,
            backup=True,
            enable_graph_update=True,
            enable_versioning=False,
            enable_critic=False,
        )
        updater.add_individuals([{"name": "chunk_1_Alloy", "type": "Alloy"}])
        saved = updater.save()

        # diffs/ directory should exist
        diffs_dir = saved.parent / "diffs"
        assert diffs_dir.exists(), "diffs/ directory should be created"

        diff_files = list(diffs_dir.glob("diff_*.json"))
        assert len(diff_files) >= 1, "At least one diff file should be created"

        # Diff content should have operations
        diff_data = json.loads(diff_files[0].read_text(encoding="utf-8"))
        assert "operations" in diff_data
        assert "old_hash" in diff_data
        assert "new_hash" in diff_data

        # Verify added individuals appear as insert operations
        ops = diff_data["operations"]
        inserts = [op for op in ops if op.get("operation") == "insert"]
        assert len(inserts) >= 1, "Should have at least one insert operation"


# ---------------------------------------------------------------------------
# Test 2: Updater.save() triggers Versioning
# ---------------------------------------------------------------------------

class TestUpdaterVersioning:
    """Integration point 1b: save() commits versions."""

    def test_updater_save_triggers_versioning(self, tmp_path):
        ont_file = _make_ontology_json(tmp_path)

        updater = OntologyUpdater(
            ont_file,
            backup=True,
            enable_graph_update=False,
            enable_versioning=True,
            enable_critic=False,
        )

        # First save (with individuals → should bump MINOR)
        updater.add_individuals([{"name": "chunk_1_Material", "type": "Material"}])
        updater.save()

        # Second save (add new individuals → should create another version)
        updater2 = OntologyUpdater(
            ont_file,
            backup=False,
            enable_graph_update=False,
            enable_versioning=True,
        )
        updater2.add_individuals([
            {"name": "chunk_2_Material", "type": "Material"},
            {"name": "chunk_3_Material", "type": "NewType"},
        ])
        updater2.save()

        # versions/versions.json should exist with entries
        versions_file = tmp_path / "versions" / "versions.json"
        assert versions_file.exists(), "versions.json should be created"

        version_data = json.loads(versions_file.read_text(encoding="utf-8"))
        assert len(version_data) >= 1, f"Expected >=1 versions, got {len(version_data)}"

        # Verify version numbers are present
        versions = [OntologyVersion(**v) for v in version_data.values()]
        version_strs = [v.version for v in versions]
        assert all("." in v for v in version_strs), "Versions should have semantic versioning"


# ---------------------------------------------------------------------------
# Test 3: Merger.merge() triggers Sublimation
# ---------------------------------------------------------------------------

class TestMergerSublimation:
    """Integration point 2: merge() runs sublimation when enabled."""

    def test_merger_triggers_sublimation(self, tmp_path):
        r1 = ExtractionResult(
            source="chunk_1",
            individuals=[
                {"name": "U-10Mo", "type": "Alloy", "density": "15.8 g/cm³"},
                {"name": "chunk_1_sample", "type": "Sample"},
            ],
        )
        r2 = ExtractionResult(
            source="chunk_2",
            individuals=[
                {"name": "U-10Zr", "type": "Alloy", "density": "6.5 g/cm³"},
                {"name": "chunk_2_sample", "type": "Sample"},
            ],
        )

        merger = Merger(enable_sublimation=True)
        merged = merger.merge([r1, r2])

        # sublimation field should exist
        assert merged.sublimation is not None, "sublimation should be populated"

        # Should contain ontology and facts keys
        assert "ontology" in merged.sublimation
        assert "facts" in merged.sublimation


# ---------------------------------------------------------------------------
# Test 4: OntologyCritic quality gate
# ---------------------------------------------------------------------------

class TestCriticQuality:
    """Integration point 3: critic evaluates ontology quality."""

    def test_critic_blocks_low_quality(self):
        # Low-quality ontology: no classes, no metadata
        bad_ontology = {
            "individuals": {},
            "objectProperties": {},
            "datatypeProperties": {},
        }

        critic = OntologyCritic()
        report = critic.critique_ontology(bad_ontology)

        # Should fail due to CRITICAL suggestion (no classes)
        assert report.success is False, "Low-quality ontology should not pass"
        assert any(
            s.severity == CritiqueSeverity.CRITICAL for s in report.suggestions
        ), "Should have at least one CRITICAL suggestion"

    def test_critic_passes_good_ontology(self):
        good_ontology = {
            "classes": {
                "Material": {"comment": "A type of material"},
                "Alloy": {"comment": "A metallic alloy"},
            },
            "objectProperties": {
                "hasComponent": {"domain": "Alloy", "range": "Material"},
            },
            "datatypeProperties": {
                "hasDensity": {"domain": "Material"},
            },
            "individuals": {
                "U-10Mo": {"type": "Alloy"},
            },
            "metadata": {"version": "1.0.0"},
        }

        critic = OntologyCritic()
        report = critic.critique_ontology(good_ontology)

        assert report.success is True, f"Good ontology should pass, score={report.score}"

    def test_critic_emits_warning_on_updater(self, tmp_path):
        """Critic in Updater should warn but not block."""
        # Create an ontology with no classes (list format, as load_ontology returns)
        ont = {
            "classes": [],
            "objectProperties": [],
            "datatypeProperties": [],
            "individuals": [],
        }
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont), encoding="utf-8")

        updater = OntologyUpdater(
            ont_file,
            backup=False,
            enable_critic=True,
            enable_graph_update=False,
            enable_versioning=False,
        )
        # Should not raise, just warn
        with pytest.warns(UserWarning, match="本体质量批判"):
            updater.add_individuals([{"name": "test_item", "type": "Thing"}])


# ---------------------------------------------------------------------------
# Test 5: Full end-to-end pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end: Extract → Merge (w/ sublimation) → Update (w/ critic + versioning + graph_update)."""

    def test_full_pipeline_with_ontocast(self, tmp_path):
        ont_file = _make_ontology_json(tmp_path)

        # --- Step 1: Create extraction results ---
        r1 = ExtractionResult(
            source="chunk_1",
            individuals=[
                {"name": "U-10Mo", "type": "Alloy", "density": "15.8 g/cm³"},
                {"name": "chunk_1_specimen", "type": "Specimen"},
            ],
        )
        r2 = ExtractionResult(
            source="chunk_2",
            individuals=[
                {"name": "U-10Zr", "type": "Alloy", "density": "6.5 g/cm³"},
                {"name": "chunk_2_specimen", "type": "Specimen"},
            ],
        )

        # --- Step 2: Merge with sublimation ---
        merger = Merger(enable_sublimation=True)
        merged = merger.merge([r1, r2])

        assert merged.sublimation is not None, "Sublimation result should exist"
        assert "ontology" in merged.sublimation
        assert "facts" in merged.sublimation

        # --- Step 3: Update with all integrations ---
        updater = OntologyUpdater(
            ont_file,
            backup=True,
            enable_graph_update=True,
            enable_versioning=True,
            enable_critic=True,
        )

        # This should warn (critic) but not block
        with pytest.warns(UserWarning):
            stats = updater.add_individuals(merged.individuals)

        assert stats.added_individuals >= 1, "Should add at least one individual"

        # Save triggers graph_update + versioning
        saved = updater.save()
        assert saved.exists()

        # --- Verify artifacts ---
        # Diff file
        diffs_dir = tmp_path / "diffs"
        assert diffs_dir.exists(), "diffs/ should exist"
        diff_files = list(diffs_dir.glob("diff_*.json"))
        assert len(diff_files) >= 1, "Should have diff files"

        # Version file
        versions_file = tmp_path / "versions" / "versions.json"
        assert versions_file.exists(), "versions.json should exist"
        version_data = json.loads(versions_file.read_text(encoding="utf-8"))
        assert len(version_data) >= 1, "Should have at least one version"

        # Sublimation result verified above

        # --- Verify saved ontology has the individuals ---
        saved_data = json.loads(saved.read_text(encoding="utf-8"))
        individuals = saved_data.get("individuals", [])
        if isinstance(individuals, dict):
            names = list(individuals.keys())
        else:
            names = [ind.get("name", "") for ind in individuals if isinstance(ind, dict)]
        assert "U-10Mo" in names
        assert "U-10Zr" in names


# ---------------------------------------------------------------------------
# Test: Module independence (graceful degradation)
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Modules should degrade gracefully when disabled."""

    def test_updater_no_graph_update(self, tmp_path):
        ont_file = _make_ontology_json(tmp_path)
        updater = OntologyUpdater(
            ont_file,
            backup=False,
            enable_graph_update=False,
            enable_versioning=False,
        )
        updater.add_individuals([{"name": "X"}])
        saved = updater.save()
        assert not (saved.parent / "diffs").exists()

    def test_updater_no_versioning(self, tmp_path):
        ont_file = _make_ontology_json(tmp_path)
        updater = OntologyUpdater(
            ont_file,
            backup=False,
            enable_graph_update=False,
            enable_versioning=False,
        )
        updater.add_individuals([{"name": "X"}])
        saved = updater.save()
        assert not (saved.parent / "versions").exists()

    def test_merger_no_sublimation(self):
        r1 = ExtractionResult(source="c0", individuals=[{"name": "A"}])
        merger = Merger(enable_sublimation=False)
        merged = merger.merge([r1])
        assert merged.sublimation is None
