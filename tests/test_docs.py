"""Tests for documentation files."""

import pathlib


def test_user_manual_exists():
    """User manual file should exist at docs/user_manual.md."""
    assert pathlib.Path("docs/user_manual.md").exists()


def test_user_manual_has_sections():
    """User manual should contain key sections: install, quick start, CLI."""
    content = pathlib.Path("docs/user_manual.md").read_text()
    assert "安装" in content or "Install" in content
    assert "快速开始" in content or "Quick Start" in content
    assert "CLI" in content or "命令" in content


def test_user_manual_has_troubleshooting():
    """User manual should contain troubleshooting section."""
    content = pathlib.Path("docs/user_manual.md").read_text()
    assert "故障" in content or "troubleshoot" in content.lower()


# --- Deployment Guide Tests ---


def test_deployment_guide_exists():
    """Deployment guide should exist at docs/deployment.md."""
    assert pathlib.Path("docs/deployment.md").exists()


def test_deployment_guide_covers_docker():
    """Deployment guide should cover Docker and docker compose."""
    content = pathlib.Path("docs/deployment.md").read_text()
    assert "Docker" in content or "docker" in content.lower()
    assert "docker compose" in content.lower()


def test_deployment_guide_covers_env_vars():
    """Deployment guide should cover environment variables."""
    content = pathlib.Path("docs/deployment.md").read_text()
    assert "POSTGRES" in content or "DATABASE" in content or "环境变量" in content


# --- Contributing Guide Tests ---


def test_contributing_exists():
    assert pathlib.Path("CONTRIBUTING.md").exists()


def test_contributing_mentions_tests():
    content = pathlib.Path("CONTRIBUTING.md").read_text()
    assert "test" in content.lower()
    assert "pytest" in content
