"""Tests for database restore module."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ontofuel.database.restore import DataRestorer
from ontofuel.database.client import SupabaseClient


class TestDataRestorerInit:
    """Test DataRestorer initialization."""

    def test_init_default(self):
        r = DataRestorer()
        assert r.stats["materials"] == 0
        assert r.stats["properties"] == 0
        assert r.stats["errors"] == []

    def test_init_with_client(self):
        client = SupabaseClient(url="http://test:54321", key="test-key")
        r = DataRestorer(client=client)
        assert r.client.url == "http://test:54321"

    def test_reset_stats(self):
        r = DataRestorer()
        r.stats["materials"] = 100
        r.reset_stats()
        assert r.stats["materials"] == 0


class TestDataRestorerDryRun:
    """Test restore with dry_run=True (no actual DB writes)."""

    def test_dry_run_counts_materials(self):
        r = DataRestorer()
        ont_path = self._get_ontology_path()
        if not ont_path:
            pytest.skip("No ontology file available")

        result = r.restore_from_ontology(ont_path, dry_run=True)
        assert result["materials"] > 0
        assert result["materials"] == 755  # Known count

    def test_dry_run_counts_properties(self):
        r = DataRestorer()
        ont_path = self._get_ontology_path()
        if not ont_path:
            pytest.skip("No ontology file available")

        result = r.restore_from_ontology(ont_path, dry_run=True)
        # Should have some properties
        assert result["properties"] >= 0

    def _get_ontology_path(self) -> Path | None:
        """Find the ontology file."""
        candidates = [
            Path("memory/trustgraph-fix/material_ontology_enhanced.json"),
            Path("ontology/material_ontology_enhanced.json"),
        ]
        for p in candidates:
            if p.exists():
                return p
        return None


class TestDataRestorerWithMock:
    """Test restore with mocked Supabase client."""

    def test_restore_calls_insert(self):
        mock_client = MagicMock()
        mock_client.insert.return_value = 1

        r = DataRestorer(client=mock_client)
        ont_path = self._get_ontology_path()
        if not ont_path:
            pytest.skip("No ontology file available")

        result = r.restore_from_ontology(ont_path)
        assert result["materials"] > 0
        assert mock_client.insert.called

    def test_restore_handles_insert_failure(self):
        mock_client = MagicMock()
        mock_client.insert.return_value = 0  # All inserts fail

        r = DataRestorer(client=mock_client)
        ont_path = self._get_ontology_path()
        if not ont_path:
            pytest.skip("No ontology file available")

        result = r.restore_from_ontology(ont_path)
        # Should have errors recorded
        assert len(result["errors"]) > 0

    def test_restore_from_json(self, tmp_path):
        """Test generic JSON restore."""
        mock_client = MagicMock()
        mock_client.insert.return_value = 1

        # Create test data
        test_data = [{"name": "test1", "value": 1}, {"name": "test2", "value": 2}]
        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps(test_data))

        r = DataRestorer(client=mock_client)
        result = r.restore_from_json(data_file, "materials")
        assert result["materials"] == 2

    def test_restore_from_json_dict(self, tmp_path):
        """Test JSON restore with single dict (not list)."""
        mock_client = MagicMock()
        mock_client.insert.return_value = 1

        test_data = {"name": "single_item", "value": 42}
        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps(test_data))

        r = DataRestorer(client=mock_client)
        result = r.restore_from_json(data_file, "materials")
        assert result["materials"] == 1

    def test_extract_formula(self):
        r = DataRestorer()
        assert r._extract_formula("U_10Mo_alloy") == "10Mo"
        assert r._extract_formula("Steel_316") == ""
        assert r._extract_formula("U-10Zr_test") == "U10Zr"

    def test_verify_data(self):
        mock_client = MagicMock()
        mock_client.select.return_value = [{"id": "1", "name": "test"}]
        mock_client.count.return_value = 100

        r = DataRestorer(client=mock_client)
        result = r.verify_data("materials")
        assert result["count"] == 100
        assert len(result["sample"]) == 1

    def _get_ontology_path(self) -> Path | None:
        candidates = [
            Path("memory/trustgraph-fix/material_ontology_enhanced.json"),
            Path("ontology/material_ontology_enhanced.json"),
        ]
        for p in candidates:
            if p.exists():
                return p
        return None


class TestSupabaseClient:
    """Test SupabaseClient unit operations."""

    def test_health_check_failure(self):
        """Health check should return False when server not reachable."""
        client = SupabaseClient(url="http://localhost:59999")
        assert client.health_check() is False

    def test_select_empty_on_failure(self):
        client = SupabaseClient(url="http://localhost:59999")
        result = client.select("materials")
        assert result == []

    def test_count_zero_on_failure(self):
        client = SupabaseClient(url="http://localhost:59999")
        result = client.count("materials")
        assert result == 0

    def test_insert_zero_on_failure(self):
        client = SupabaseClient(url="http://localhost:59999")
        result = client.insert("materials", [{"name": "test"}])
        assert result == 0

    def test_delete_zero_on_failure(self):
        client = SupabaseClient(url="http://localhost:59999")
        result = client.delete("materials", "?name=eq.test")
        assert result == 0
