"""TDD tests for extraction/updater.py — covering missing lines.

Following TDD: write failing test FIRST, then implement/fix to pass.
"""

import json

import pytest

from ontofuel.extraction.updater import OntologyUpdater, UpdateStats

# ─── Fixture: minimal ontology ─────────────────────────────────────────


@pytest.fixture
def mini_ontology(tmp_path):
    """Create a minimal ontology file for testing."""
    ont = {
        "classes": [{"name": "NuclearFuel"}],
        "objectProperties": [],
        "datatypeProperties": [],
        "individuals": [
            {"name": "U10Mo", "type": "NuclearFuel"},
            {"name": "U10Zr", "type": "NuclearFuel"},
        ],
    }
    path = tmp_path / "test_ontology.json"
    path.write_text(json.dumps(ont), encoding="utf-8")
    return str(path)


@pytest.fixture
def dict_keyed_ontology(tmp_path):
    """Create an ontology where individuals is a dict (not a list)."""
    ont = {
        "classes": [],
        "objectProperties": [],
        "datatypeProperties": [],
        "individuals": {
            "U10Mo": {"name": "U10Mo", "type": "NuclearFuel"},
            "U10Zr": {"name": "U10Zr", "type": "NuclearFuel"},
        },
    }
    path = tmp_path / "dict_ontology.json"
    path.write_text(json.dumps(ont), encoding="utf-8")
    return str(path)


# ─── RED: add_properties ───────────────────────────────────────────────


class TestAddProperties:
    """Tests for OntologyUpdater.add_properties (lines 145-168)."""

    def test_add_property_to_named_individual(self, mini_ontology):
        """Should add a property to a specific named individual."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8", "unit": "g/cm³"},
            ],
            target_individual="U10Mo",
        )
        assert stats.added_properties == 1

    def test_add_property_with_individual_in_prop(self, mini_ontology):
        """Should use prop['individual'] when no target_individual."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8", "individual": "U10Mo"},
            ],
        )
        assert stats.added_properties == 1

    def test_add_property_with_source_as_fallback(self, mini_ontology):
        """Should fall back to prop['source'] if no 'individual' key."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8", "source": "U10Mo"},
            ],
        )
        assert stats.added_properties == 1

    def test_add_property_skips_no_individual(self, mini_ontology):
        """Should skip properties with no individual reference."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8"},
            ],
        )
        assert stats.skipped_individuals >= 1
        assert stats.added_properties == 0

    def test_add_property_to_nonexistent_individual(self, mini_ontology):
        """Should skip when individual doesn't exist in ontology."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8", "individual": "NonExistent"},
            ],
        )
        assert stats.skipped_individuals >= 1
        assert stats.added_properties == 0

    def test_add_multiple_properties(self, mini_ontology):
        """Should track multiple property additions."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.add_properties(
            properties=[
                {"name": "density", "value": "15.8", "individual": "U10Mo"},
                {"name": "melting_point", "value": "1132", "individual": "U10Mo"},
                {"name": "density", "value": "16.3", "individual": "U10Zr"},
            ],
        )
        assert stats.added_properties == 3


# ─── RED: dict-keyed individuals ───────────────────────────────────────


class TestDictKeyedIndividuals:
    """Tests for dict-keyed individuals (lines 205, 211, 220-222, 235-242, 267-280)."""

    def test_get_existing_names_dict(self, dict_keyed_ontology):
        """Should get names from dict-keyed individuals."""
        updater = OntologyUpdater(dict_keyed_ontology)
        names = updater._get_existing_names()
        assert "U10Mo" in names
        assert "U10Zr" in names

    def test_add_individual_to_dict(self, dict_keyed_ontology):
        """Should add individual to dict-keyed ontology."""
        updater = OntologyUpdater(dict_keyed_ontology)
        stats = updater.add_individuals(
            [
                {"name": "UNb", "type": "NuclearFuel"},
            ]
        )
        assert stats.added_individuals == 1
        names = updater._get_existing_names()
        assert "UNb" in names

    def test_update_existing_in_dict(self, dict_keyed_ontology):
        """Should update existing individual in dict-keyed ontology."""
        updater = OntologyUpdater(dict_keyed_ontology)
        stats = updater.add_individuals(
            [
                {"name": "U10Mo", "type": "NuclearFuel", "density": "15.8"},
            ]
        )
        # U10Mo already exists, so should update
        assert stats.updated_individuals >= 1

    def test_add_property_to_dict_individual(self, dict_keyed_ontology):
        """Should add property to individual in dict-keyed ontology."""
        updater = OntologyUpdater()
        # Set dict-keyed individuals directly (bypass load_ontology normalization)
        updater._ontology = {
            "classes": [],
            "objectProperties": [],
            "datatypeProperties": [],
            "individuals": {
                "U10Mo": {"name": "U10Mo", "type": "NuclearFuel"},
            },
        }
        result = updater._add_property_to_individual("U10Mo", "density", "15.8", "g/cm³")
        assert result is True
        ind = updater.ontology["individuals"]["U10Mo"]
        assert "prop_density" in ind

    def test_add_property_to_nonexistent_dict_individual(self, dict_keyed_ontology):
        """Should return False for nonexistent individual in dict."""
        updater = OntologyUpdater(dict_keyed_ontology)
        result = updater._add_property_to_individual("NonExistent", "density", "15.8")
        assert result is False


# ─── RED: get_before_stats ─────────────────────────────────────────────


class TestGetBeforeStats:
    """Tests for get_before_stats (line 184)."""

    def test_get_before_stats_returns_dict(self, mini_ontology):
        """Should return a dict with ontology stats."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.get_before_stats()
        assert isinstance(stats, dict)
        assert "individuals" in stats or "classes" in stats

    def test_get_before_stats_correct_counts(self, mini_ontology):
        """Should reflect the actual ontology content."""
        updater = OntologyUpdater(mini_ontology)
        stats = updater.get_before_stats()
        assert stats.get("individuals", 0) == 2
        assert stats.get("classes", 0) == 1


# ─── RED: _merge_stats ─────────────────────────────────────────────────


class TestMergeStats:
    """Tests for internal _merge_stats (line 267-280 coverage)."""

    def test_merge_accumulates_counts(self, mini_ontology):
        """Should accumulate stats from multiple operations."""
        updater = OntologyUpdater(mini_ontology)
        updater.add_individuals([{"name": "New1", "type": "NuclearFuel"}])
        updater.add_individuals([{"name": "New2", "type": "NuclearFuel"}])
        stats = updater.get_stats()
        assert stats.added_individuals == 2

    def test_merge_tracks_errors(self, mini_ontology):
        """Should accumulate errors across operations."""
        updater = OntologyUpdater(mini_ontology)
        stats1 = UpdateStats()
        stats1.errors.append("error 1")
        stats2 = UpdateStats()
        stats2.errors.append("error 2")
        updater._merge_stats(stats1)
        updater._merge_stats(stats2)
        assert len(updater.get_stats().errors) == 2


# ─── RED: edge cases ───────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases for full coverage."""

    def test_empty_ontology(self, tmp_path):
        """Should handle ontology with no individuals."""
        ont = {"classes": [], "objectProperties": [], "datatypeProperties": [], "individuals": []}
        path = tmp_path / "empty.json"
        path.write_text(json.dumps(ont), encoding="utf-8")
        updater = OntologyUpdater(str(path))
        stats = updater.add_individuals([{"name": "New", "type": "NuclearFuel"}])
        assert stats.added_individuals == 1

    def test_save_no_path_no_original(self):
        """Should raise ValueError when no path available."""
        updater = OntologyUpdater()
        updater._ontology = {
            "classes": [],
            "objectProperties": [],
            "datatypeProperties": [],
            "individuals": [],
        }
        with pytest.raises(ValueError, match="No output path"):
            updater.save()

    def test_changes_tracked_across_operations(self, mini_ontology):
        """Should track all changes across multiple operations."""
        updater = OntologyUpdater(mini_ontology)
        updater.add_individuals([{"name": "New1", "type": "NuclearFuel"}])
        updater.add_properties([{"name": "density", "value": "15.8", "individual": "U10Mo"}])
        changes = updater.get_changes()
        assert len(changes) >= 2
