"""Tests for CLI module."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ontofuel.cli import main


class TestCLIStats:
    """Test 'ontofuel stats' command."""

    def test_stats_basic(self, capsys):
        main(["stats"])
        out = capsys.readouterr().out
        assert "Classes:" in out
        assert "Individuals:" in out

    def test_stats_verbose(self, capsys):
        main(["stats", "-v"])
        out = capsys.readouterr().out
        assert "Top classes" in out


class TestCLIQuery:
    """Test 'ontofuel query' command."""

    def test_query_search(self, capsys):
        main(["query", "U-10Mo"])
        out = capsys.readouterr().out
        assert "results" in out.lower()

    def test_query_by_class(self, capsys):
        main(["query", "--class", "NuclearFuel"])
        out = capsys.readouterr().out
        assert "NuclearFuel" in out or "Individuals" in out

    def test_query_hierarchy(self, capsys):
        main(["query", "--hierarchy", "NuclearFuel"])
        out = capsys.readouterr().out
        # Should show class info (even if not found, no crash)
        assert "Class" in out or "not found" in out

    def test_query_export(self, capsys, tmp_path):
        out_file = tmp_path / "results.json"
        main(["query", "U-10Mo", "--output", str(out_file)])
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)

    def test_query_empty(self, capsys):
        main(["query", "ZZZZNONEXISTENT"])
        out = capsys.readouterr().out
        assert "0 results" in out


class TestCLIExport:
    """Test 'ontofuel export' command."""

    def test_export_json(self, capsys, tmp_path):
        out_file = tmp_path / "export.json"
        main(["export", "json", str(out_file)])
        out = capsys.readouterr().out
        assert "Exported" in out
        assert out_file.exists()

    def test_export_csv_classes(self, capsys, tmp_path):
        out_file = tmp_path / "classes.csv"
        main(["export", "csv-classes", str(out_file)])
        content = out_file.read_text()
        assert "name" in content  # header

    def test_export_graphml(self, capsys, tmp_path):
        out_file = tmp_path / "graph.graphml"
        main(["export", "graphml", str(out_file)])
        content = out_file.read_text()
        assert "graphml" in content

    def test_export_markdown(self, capsys, tmp_path):
        out_file = tmp_path / "report.md"
        main(["export", "markdown", str(out_file)])
        content = out_file.read_text()
        assert "# OntoFuel Ontology Report" in content


class TestCLIValidate:
    """Test 'ontofuel validate' command."""

    def test_validate_full(self, capsys):
        main(["validate"])
        out = capsys.readouterr().out
        assert "Quality Report" in out
        assert "/100" in out

    def test_validate_quick(self, capsys):
        main(["validate", "--quick"])
        out = capsys.readouterr().out
        assert "Quick Health Check" in out

    def test_validate_with_output(self, capsys, tmp_path):
        out_file = tmp_path / "report.json"
        main(["validate", "--output", str(out_file)])
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "total_score" in data
        assert "dimension_scores" in data


class TestCLIEntryPoint:
    """Test the CLI entry point script."""

    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "ontofuel.cli", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "OntoFuel" in result.stdout

    def test_no_command_shows_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "ontofuel.cli"],
            capture_output=True, text=True,
        )
        # Should exit cleanly (0 from help)
        assert result.returncode == 0
