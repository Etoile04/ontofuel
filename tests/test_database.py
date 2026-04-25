"""Tests for ontofuel.database module."""

import pytest
from ontofuel.database import SupabaseClient, DataRestorer, TABLES


class TestSupabaseClient:
    def test_init_defaults(self):
        client = SupabaseClient()
        assert client.url == "http://localhost:54321"

    def test_init_custom(self):
        client = SupabaseClient(url="http://custom:54321", key="secret")
        assert client.url == "http://custom:54321"
        assert client.key == "secret"


class TestDataRestorer:
    def test_init(self):
        r = DataRestorer()
        assert r.stats["materials"] == 0
        assert r.stats["properties"] == 0

    def test_extract_formula(self):
        r = DataRestorer()
        assert r._extract_formula("UMo_U-10Mo_fuel") == "U10Mo"


class TestSchema:
    def test_tables_defined(self):
        assert len(TABLES) == 5
        assert "materials" in TABLES
        assert "material_properties" in TABLES

    def test_tables_have_columns(self):
        for name, schema in TABLES.items():
            assert "columns" in schema
            assert len(schema["columns"]) > 0
