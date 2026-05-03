"""Tests for Task 3: Web CRUD Management Interface."""
import pathlib

BASE = pathlib.Path("/Users/lwj04/.openclaw/workspace-extractor/.worktrees/o4-docs")


def test_web_index_html_exists():
    """index.html should exist."""
    p = BASE / "docker/web/index.html"
    assert p.exists()


def test_web_index_has_materials_ui():
    """index.html should contain materials CRUD elements."""
    content = (BASE / "docker/web/index.html").read_text()
    assert "materials" in content.lower()
    assert "add" in content.lower() or "create" in content.lower() or "+" in content
    assert "delete" in content.lower()
    assert "/api/materials" in content


def test_web_index_has_type_filter():
    """Should have material type filter."""
    content = (BASE / "docker/web/index.html").read_text()
    assert "FuelMaterial" in content or "fuel" in content.lower()


def test_web_index_has_search():
    """Should have search functionality."""
    content = (BASE / "docker/web/index.html").read_text()
    assert "search" in content.lower() or "搜索" in content


def test_web_dockerfile_exists():
    """Dockerfile for web should exist."""
    assert (BASE / "docker/web/Dockerfile").exists()
