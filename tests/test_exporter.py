"""Tests for ontofuel.core.exporter module."""

import json
import tempfile
from pathlib import Path
import pytest

from ontofuel.core.ontology import load_ontology
from ontofuel.core.exporter import OntologyExporter


@pytest.fixture
def exporter():
    sample = {
        "classes": {
            "TestClass": {"uri": "http://example.org/TestClass", "comment": "Test"},
        },
        "objectProperties": {
            "hasPart": {"uri": "http://example.org/hasPart", "domain": "TestClass"},
        },
        "datatypeProperties": {},
        "individuals": {
            "Mat1": {"uri": "http://example.org/Mat1", "class": "TestClass"},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample, f)
        fname = f.name
    ont = load_ontology(fname)
    return OntologyExporter(ont)


class TestExport:
    def test_export_json(self, exporter):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = exporter.export_json(f.name)
            assert path.exists()
            data = json.loads(path.read_text())
            assert "classes" in data

    def test_export_csv_classes(self, exporter):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = exporter.export_csv_classes(f.name)
            assert path.exists()
            assert path.stat().st_size > 0

    def test_export_graphml(self, exporter):
        with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as f:
            path = exporter.export_graphml(f.name)
            assert path.exists()
            content = path.read_text()
            assert "<graphml" in content

    def test_export_markdown(self, exporter):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = exporter.export_markdown_report(f.name)
            assert path.exists()
            content = path.read_text()
            assert "# OntoFuel" in content
