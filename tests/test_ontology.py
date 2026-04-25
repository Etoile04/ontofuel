"""Tests for ontofuel.core.ontology module."""

import json
import tempfile
from pathlib import Path
import pytest

from ontofuel.core.ontology import (
    load_ontology, get_classes, get_object_properties,
    get_datatype_properties, get_individuals, get_stats,
)


@pytest.fixture
def sample_ontology():
    """Create a minimal sample ontology for testing."""
    return {
        "classes": {
            "TestClass": {
                "uri": "http://example.org/TestClass",
                "type": "owl:Class",
                "comment": "A test class",
                "parent": "Entity",
            },
            "SubClass": {
                "uri": "http://example.org/SubClass",
                "type": "owl:Class",
                "comment": "A subclass",
                "parent": "TestClass",
            },
        },
        "objectProperties": {
            "hasPart": {
                "uri": "http://example.org/hasPart",
                "domain": "TestClass",
                "range": "TestClass",
            },
        },
        "datatypeProperties": {
            "density": {
                "uri": "http://example.org/density",
                "domain": "TestClass",
                "range": "xsd:float",
            },
        },
        "individuals": {
            "TestMat1": {
                "uri": "http://example.org/TestMat1",
                "type": "http://example.org/TestClass",
                "prop_density": 19.1,
            },
            "TestMat2": {
                "uri": "http://example.org/TestMat2",
                "class": "TestClass",
            },
        },
    }


@pytest.fixture
def ontology_file(sample_ontology):
    """Write sample ontology to a temp file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_ontology, f)
        return Path(f.name)


class TestLoadOntology:
    def test_load_from_file(self, ontology_file):
        ont = load_ontology(ontology_file)
        assert "classes" in ont
        assert len(ont["classes"]) == 2

    def test_classes_normalized_to_list(self, ontology_file):
        ont = load_ontology(ontology_file)
        assert isinstance(ont["classes"], list)
        assert isinstance(ont["individuals"], list)

    def test_classes_have_name_field(self, ontology_file):
        ont = load_ontology(ontology_file)
        names = [c["name"] for c in ont["classes"]]
        assert "TestClass" in names
        assert "SubClass" in names

    def test_individuals_have_name_field(self, ontology_file):
        ont = load_ontology(ontology_file)
        names = [i["name"] for i in ont["individuals"]]
        assert "TestMat1" in names
        assert "TestMat2" in names

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_ontology("/nonexistent/path.json")


class TestGetFunctions:
    def test_get_classes(self, ontology_file):
        ont = load_ontology(ontology_file)
        classes = get_classes(ont)
        assert len(classes) == 2

    def test_get_object_properties(self, ontology_file):
        ont = load_ontology(ontology_file)
        props = get_object_properties(ont)
        assert len(props) == 1
        assert props[0]["name"] == "hasPart"

    def test_get_datatype_properties(self, ontology_file):
        ont = load_ontology(ontology_file)
        props = get_datatype_properties(ont)
        assert len(props) == 1

    def test_get_individuals(self, ontology_file):
        ont = load_ontology(ontology_file)
        inds = get_individuals(ont)
        assert len(inds) == 2

    def test_get_stats(self, ontology_file):
        ont = load_ontology(ontology_file)
        stats = get_stats(ont)
        assert stats["classes"] == 2
        assert stats["object_properties"] == 1
        assert stats["datatype_properties"] == 1
        assert stats["individuals"] == 2
