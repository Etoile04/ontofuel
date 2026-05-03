"""Tests for docker/scripts/restore.sh — Task 4: Data Restore Automation Script"""

import pathlib
import stat

SCRIPT_PATH = pathlib.Path(
    "/Users/lwj04/.openclaw/workspace-extractor/.worktrees/o3-docker/docker/scripts/restore.sh"
)


def test_restore_script_exists():
    assert SCRIPT_PATH.exists(), f"restore.sh not found at {SCRIPT_PATH}"


def test_restore_script_executable():
    assert SCRIPT_PATH.exists(), "restore.sh does not exist"
    assert SCRIPT_PATH.stat().st_mode & stat.S_IXUSR, "restore.sh is not executable"


def test_restore_script_uses_strict_mode():
    content = SCRIPT_PATH.read_text()
    assert "set -euo pipefail" in content, "Missing strict mode (set -euo pipefail)"


def test_restore_script_waits_for_db():
    content = SCRIPT_PATH.read_text()
    assert "pg_isready" in content, "Missing pg_isready check"
    assert "60" in content, "Missing 60s timeout"


def test_restore_script_has_materials_restore():
    content = SCRIPT_PATH.read_text()
    assert "materials" in content
    assert "INSERT" in content.upper() or "insert" in content.lower()


def test_restore_script_is_idempotent():
    content = SCRIPT_PATH.read_text()
    assert "DELETE" in content.upper() or "TRUNCATE" in content.upper(), (
        "Missing idempotent cleanup (DELETE or TRUNCATE)"
    )


def test_restore_script_has_python_inline():
    content = SCRIPT_PATH.read_text()
    assert "python3" in content, "Missing python3 invocation"
    assert "psycopg2" in content or "DATABASE_URL" in content, (
        "Missing psycopg2 or DATABASE_URL"
    )


def test_restore_script_has_summary_output():
    content = SCRIPT_PATH.read_text()
    # Should report counts of materials and properties
    assert "materials" in content and ("properties" in content or "property" in content), (
        "Missing summary output for materials/properties"
    )


def test_restore_script_handles_ontology_json():
    content = SCRIPT_PATH.read_text()
    assert "ontology" in content.lower() or "json" in content.lower(), (
        "Missing ontology JSON handling"
    )


def test_restore_script_has_env_defaults():
    content = SCRIPT_PATH.read_text()
    # Should have DB_HOST, DB_PORT etc with defaults
    assert "DB_HOST" in content or "DATABASE_URL" in content, "Missing DB env var handling"


def test_restore_script_uses_schema_sql():
    content = SCRIPT_PATH.read_text()
    assert "schema" in content.lower() or "01_schema" in content or "init" in content.lower(), (
        "Missing schema SQL execution"
    )


def test_restore_script_has_exit_codes():
    content = SCRIPT_PATH.read_text()
    assert "exit 1" in content, "Missing error exit code"
