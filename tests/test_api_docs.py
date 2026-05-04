import pathlib
import subprocess

import pytest


def test_api_docs_index_exists():
    assert pathlib.Path("docs/api/index.rst").exists()


def test_api_docs_conf_exists():
    assert pathlib.Path("docs/api/conf.py").exists()


def test_api_docs_builds():
    """API docs should build without errors."""
    result = subprocess.run(
        ["sphinx-build", "-b", "html", "docs/api", "docs/api/_build/html"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"sphinx-build failed:\n{result.stderr}\n{result.stdout}"
