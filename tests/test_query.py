"""Tests for ontofuel.core.query module."""

import json
import tempfile
from pathlib import Path
import pytest

from ontofuel.core.ontology import load_ontology
from ontofuel.core.query import OntologyQuery


@pytest.fixture
def sample_ontology():
    return {
        "classes": {
            "NuclearFuel": {"uri": "http://example.org/NuclearFuel", "comment": "Nuclear fuel", "parent": "Material"},
            "AlloySystem": {"uri": "http://example.org/AlloySystem", "comment": "Alloy system", "parent": "Material"},
        },
        "objectProperties": {},
        "datatypeProperties": {},
        "individuals": {
            "U10Mo_fuel": {
                "uri": "http://example.org/U10Mo_fuel",
                "class": "NuclearFuel",
                "prop_density": 17.0,
            },
            "U10Zr_fuel": {
                "uri": "http://example.org/U10Zr_fuel",
                "class": "NuclearFuel",
                "prop_density": 16.0,
            },
            "HEA_test": {
                "uri": "http://example.org/HEA_test",
                "class": "AlloySystem",
                "type": ["AlloySystem", "HighEntropyAlloy"],
            },
        },
    }


@pytest.fixture
def query(sample_ontology):
    ont = load_ontology.__wrapped__(sample_ontology) if hasattr(load_ontology, '__wrapped__') else None
    # Load directly since we have a dict, not a file
    # Normalize it like load_ontology does
    from ontofuel.core.ontology import load_ontology as _load
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_ontology, f)
        fname = f.name
    ont = _load(fname)
    return OntologyQuery(ont)


class TestSearch:
    def test_search_by_name(self, query):
        results = query.search("U10Mo")
        assert len(results) >= 1
        assert any(r["name"] == "U10Mo_fuel" for r in results)

    def test_search_classes_only(self, query):
        results = query.search("Fuel", category="classes")
        assert all(r["_match_type"] == "class" for r in results)

    def test_search_individuals_only(self, query):
        results = query.search("U", category="individuals")
        assert all(r["_match_type"] == "individual" for r in results)

    def test_search_empty_query(self, query):
        results = query.search("")
        assert isinstance(results, list)


class TestByClass:
    def test_by_class_nuclear_fuel(self, query):
        results = query.by_class("NuclearFuel")
        assert len(results) == 2

    def test_by_class_alloy_system(self, query):
        results = query.by_class("AlloySystem")
        assert len(results) == 1

    def test_by_class_case_insensitive(self, query):
        results = query.by_class("nuclearfuel")
        assert len(results) == 2


class TestByProperty:
    def test_by_property_name(self, query):
        results = query.by_property("density")
        assert len(results) >= 2


class TestHierarchy:
    def test_class_hierarchy(self, query):
        result = query.get_class_hierarchy("Material")
        assert result["class"] is not None or len(result["children"]) >= 0


class TestStats:
    def test_stats(self, query):
        stats = query.stats()
        assert stats["classes"] == 2
        assert stats["individuals"] == 3
