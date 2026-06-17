"""Tests for CLI module."""

import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from ontofuel.cli import main
from ontofuel.visualization import start_viewer


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
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "OntoFuel" in result.stdout

    def test_no_command_shows_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "ontofuel.cli"],
            capture_output=True,
            text=True,
        )
        # Should exit cleanly (0 from help)
        assert result.returncode == 0


class TestCLIVizDeprecation:
    """'ontofuel viz' / start_viewer deprecation (NFM-231 / NFM-229 D2)."""

    def test_viz_cmd_prints_deprecation_notice_to_stderr(self, capsys):
        """cmd_viz must warn on stderr that the legacy viewer is deprecated."""
        with patch("ontofuel.visualization.start_viewer") as mock_start:
            main(["viz", "--no-browser", "--port", "8181"])
            # service is still started (backward compatible, not removed)
            mock_start.assert_called_once()
            assert mock_start.call_args[1]["port"] == 8181
        err = capsys.readouterr().err
        assert "DEPRECATED" in err
        assert "visualization-app" in err

    def test_start_viewer_emits_deprecation_warning(self):
        """start_viewer itself emits a DeprecationWarning on every call."""
        # Patch the blocking server so the call returns immediately.
        with patch("http.server.HTTPServer"), pytest.warns(DeprecationWarning, match="DEPRECATED"):
            start_viewer(port=8182, open_browser=False)
