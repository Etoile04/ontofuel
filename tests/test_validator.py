"""Tests for ontofuel.core.validator module."""

import json
import tempfile
import pytest

from ontofuel.core.ontology import load_ontology
from ontofuel.core.validator import OntologyValidator


@pytest.fixture
def validator():
    sample = {
        "classes": {
            "TestClass": {"uri": "http://example.org/TestClass", "comment": "Test", "parent": "Entity"},
        },
        "objectProperties": {
            "hasPart": {"uri": "http://example.org/hasPart", "domain": "TestClass", "range": "TestClass"},
        },
        "datatypeProperties": {
            "density": {"uri": "http://example.org/density", "domain": "TestClass", "range": "xsd:float"},
        },
        "individuals": {
            "Mat1": {"uri": "http://example.org/Mat1", "class": "TestClass"},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample, f)
        fname = f.name
    ont = load_ontology(fname)
    return OntologyValidator(ont)


class TestValidate:
    def test_returns_scores(self, validator):
        result = validator.validate()
        assert "total_score" in result
        assert "grade" in result
        assert "dimension_scores" in result
        assert "issues" in result

    def test_score_range(self, validator):
        result = validator.validate()
        assert 0 <= result["total_score"] <= 100

    def test_dimensions_present(self, validator):
        result = validator.validate()
        dims = result["dimension_scores"]
        for d in ["naming", "hierarchy", "semantic", "completeness", "coverage"]:
            assert d in dims
            assert 0 <= dims[d] <= 100


class TestQuickCheck:
    def test_quick_check(self, validator):
        result = validator.quick_check()
        assert "healthy" in result
        assert "has_classes" in result
        assert "has_individuals" in result
