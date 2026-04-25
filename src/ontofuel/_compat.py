"""Path utilities for finding package data files."""

from pathlib import Path

# Package root (where this file lives)
PACKAGE_DIR = Path(__file__).parent

# Project root (repo root, 2 levels up from src/ontofuel/)
# Works for both installed package and development mode
def _find_project_root() -> Path:
    """Find the project root directory."""
    # Check if we're in development mode (src/ layout)
    current = PACKAGE_DIR
    for _ in range(5):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: package dir itself
    return PACKAGE_DIR


PROJECT_ROOT = _find_project_root()

# Ontology data directory
def get_ontology_dir() -> Path:
    """Get the ontology data directory."""
    # Check multiple locations
    candidates = [
        PROJECT_ROOT / "ontology",
        PACKAGE_DIR.parent.parent / "ontology",
        PACKAGE_DIR.parent.parent / "data",
        Path.cwd() / "ontology",
        Path.cwd() / "data",
    ]
    for p in candidates:
        if p.exists() and any(p.glob("*.json")):
            return p
    return PROJECT_ROOT / "ontology"
