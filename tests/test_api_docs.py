"""Tests for Sphinx API documentation build."""

import pathlib
import subprocess

import pytest


def test_api_docs_index_exists():
    """API docs index should exist."""
    assert pathlib.Path("docs/api/index.rst").exists()


def test_api_docs_build():
    """API docs should build without errors."""
    result = subprocess.run(
        ["make", "html"],
        cwd="docs",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"make html failed:\n{result.stderr}\n{result.stdout}"
    assert pathlib.Path("docs/api/_build/html/index.html").exists()
