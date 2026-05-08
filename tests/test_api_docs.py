"""Tests for Sphinx API documentation build."""

import os
import pathlib
import subprocess

import pytest

# Resolve paths relative to this test file (not cwd)
HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DOCS_DIR = PROJECT_ROOT / "docs"
API_BUILD_HTML = DOCS_DIR / "api" / "_build" / "html"

# Discover sphinx-build: prefer the project venv, fall back to PATH
_VENV_SPHINX = PROJECT_ROOT / ".venv" / "bin" / "sphinx-build"
SPHINXBUILD = str(_VENV_SPHINX) if _VENV_SPHINX.exists() else "sphinx-build"


def _sphinx_env():
    """Return an env dict that ensures the project venv is on PATH."""
    env = os.environ.copy()
    venv_bin = str(PROJECT_ROOT / ".venv" / "bin")
    if pathlib.Path(venv_bin).exists():
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    return env


def test_api_docs_index_exists():
    """API docs index should exist."""
    assert (DOCS_DIR / "api" / "index.rst").exists()


def test_api_docs_build():
    """API docs should build without errors."""
    result = subprocess.run(
        ["make", "html"],
        cwd=str(DOCS_DIR),
        capture_output=True,
        text=True,
        env=_sphinx_env(),
    )
    assert result.returncode == 0, f"make html failed:\n{result.stderr}\n{result.stdout}"
    assert API_BUILD_HTML.exists()


def test_api_docs_no_warnings():
    """API docs build should produce no warnings."""
    result = subprocess.run(
        ["make", "html"],
        cwd=str(DOCS_DIR),
        capture_output=True,
        text=True,
        env=_sphinx_env(),
    )
    combined = result.stdout + result.stderr
    # Sphinx warnings always contain "WARNING:" (with colon)
    warnings = [
        line for line in combined.splitlines()
        if "WARNING:" in line
    ]
    assert len(warnings) == 0, (
        f"Found {len(warnings)} warning(s) in docs build:\n"
        + "\n".join(warnings)
    )
