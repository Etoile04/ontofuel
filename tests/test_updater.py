"""Tests for extraction updater module."""

import json
import pytest
from pathlib import Path

from ontofuel.extraction.updater import OntologyUpdater, UpdateStats


class TestUpdateStats:
    """Test UpdateStats."""

    def test_default(self):
        stats = UpdateStats()
        assert stats.added_individuals == 0
        assert stats.errors == []

    def test_to_dict(self):
        stats = UpdateStats()
        stats.added_individuals = 5
        d = stats.to_dict()
        assert d["added_individuals"] == 5


class TestOntologyUpdaterAddIndividuals:
    """Test adding individuals."""

    def test_add_new_individual(self, tmp_path):
        # Create a minimal ontology
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        stats = updater.add_individuals([{"name": "U-10Mo", "type": "Alloy"}])
        assert stats.added_individuals == 1

    def test_add_duplicate_skipped(self, tmp_path):
        ont = {
            "classes": {},
            "objectProperties": {},
            "datatypeProperties": {},
            "individuals": [{"name": "U-10Mo", "type": "Alloy"}],
        }
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        stats = updater.add_individuals([{"name": "U-10Mo", "type": "Alloy"}])
        assert stats.skipped_individuals == 1
        assert stats.added_individuals == 0

    def test_add_updates_existing(self, tmp_path):
        ont = {
            "classes": {},
            "objectProperties": {},
            "datatypeProperties": {},
            "individuals": [{"name": "U-10Mo", "type": "Alloy"}],
        }
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        stats = updater.add_individuals([{"name": "U-10Mo", "density": 15.8}])
        assert stats.updated_individuals == 1

    def test_add_empty_name_skipped(self, tmp_path):
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        stats = updater.add_individuals([{"name": "", "type": "X"}, {"type": "Y"}])
        assert stats.skipped_individuals == 2


class TestOntologyUpdaterSave:
    """Test saving ontology."""

    def test_save(self, tmp_path):
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        updater.add_individuals([{"name": "Test", "type": "X"}])
        saved = updater.save()

        # Verify saved file
        with open(saved) as f:
            data = json.load(f)
        assert len(data["individuals"]) == 1

    def test_save_with_backup(self, tmp_path):
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=True)
        updater.add_individuals([{"name": "Test"}])
        updater.save()

        # Check backup was created
        backups = list(tmp_path.glob("*.backup_*.json"))
        assert len(backups) == 1

    def test_save_to_different_path(self, tmp_path):
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        output = tmp_path / "output.json"
        updater = OntologyUpdater(ont_file, backup=False)
        updater.save(output)

        assert output.exists()


class TestOntologyUpdaterChanges:
    """Test change tracking."""

    def test_changes_tracked(self, tmp_path):
        ont = {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": []}
        ont_file = tmp_path / "test_ont.json"
        ont_file.write_text(json.dumps(ont))

        updater = OntologyUpdater(ont_file, backup=False)
        updater.add_individuals([{"name": "A"}, {"name": "B"}])

        changes = updater.get_changes()
        assert len(changes) == 2
        assert all(c["action"] == "add" for c in changes)
        assert all("timestamp" in c for c in changes)
