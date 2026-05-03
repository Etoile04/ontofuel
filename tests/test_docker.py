# tests/test_docker.py
import subprocess
import pathlib
import pytest

WORKTREE = "/Users/lwj04/.openclaw/workspace-extractor/.worktrees/o3-docker"


def test_docker_compose_file_valid():
    """docker-compose.yml should be valid YAML with required services."""
    result = subprocess.run(
        ["docker", "compose", "-f", "docker/docker-compose.yml", "config"],
        capture_output=True, text=True, cwd=WORKTREE,
    )
    assert result.returncode == 0, f"docker compose config failed: {result.stderr}"
    output = result.stdout
    assert "db" in output or "supabase" in output
    assert "api" in output
    assert "web" in output


def test_schema_sql_exists_and_valid():
    """01_schema.sql should exist and contain CREATE TABLE statements."""
    p = pathlib.Path(f"{WORKTREE}/docker/supabase/init/01_schema.sql")
    assert p.exists()
    content = p.read_text()
    assert "CREATE TABLE" in content
    assert "materials" in content
    assert "material_properties" in content
    assert "material_composition" in content
    assert "literature_sources" in content
    assert "irradiation_behavior" in content


def test_env_example_exists():
    """docker/.env.example should exist with required variables."""
    p = pathlib.Path(f"{WORKTREE}/docker/.env.example")
    assert p.exists()
    content = p.read_text()
    assert "POSTGRES_PASSWORD" in content
    assert "POSTGRES_DB" in content
    assert "SUPABASE_SERVICE_KEY" in content
