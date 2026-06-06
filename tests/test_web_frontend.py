"""Tests for Task 3: Web CRUD Management Interface."""

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_web_index_html_exists():
    """index.html should exist."""
    p = REPO_ROOT / "docker/web/index.html"
    assert p.exists()


def test_web_index_has_materials_ui():
    """index.html should contain materials CRUD elements."""
    content = (REPO_ROOT / "docker/web/index.html").read_text()
    assert "materials" in content.lower()
    assert "add" in content.lower() or "create" in content.lower() or "+" in content
    assert "delete" in content.lower()
    assert "/api/materials" in content


def test_web_index_has_type_filter():
    """Should have material type filter."""
    content = (REPO_ROOT / "docker/web/index.html").read_text()
    assert "FuelMaterial" in content or "fuel" in content.lower()


def test_web_index_has_search():
    """Should have search functionality."""
    content = (REPO_ROOT / "docker/web/index.html").read_text()
    assert "search" in content.lower() or "搜索" in content


def test_web_dockerfile_exists():
    """Dockerfile for web should exist."""
    assert (REPO_ROOT / "docker/web/Dockerfile").exists()
