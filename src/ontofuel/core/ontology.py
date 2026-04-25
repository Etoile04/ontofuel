"""Ontology loader — load and access ontology data from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .._compat import get_ontology_dir


def get_default_ontology_path() -> Path:
    """Get the default ontology JSON file path."""
    ont_dir = get_ontology_dir()
    candidates = [
        ont_dir / "material_ontology_enhanced.json",
        ont_dir / "ontology.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Ontology file not found in {ont_dir}")


def get_default_nvl_path() -> Path:
    """Get the default NVL visualization data path."""
    ont_dir = get_ontology_dir()
    for p in [ont_dir / "nvl_ontology_data.json", ont_dir.parent / "data" / "nvl_ontology_data.json"]:
        if p.exists():
            return p
    raise FileNotFoundError("NVL data file not found")


def load_ontology(path: str | Path | None = None) -> dict[str, Any]:
    """Load ontology from JSON file.

    The ontology JSON has this structure:
    {
        "classes": {"ClassName": {...}, ...},  # dict keyed by name
        "objectProperties": {...},
        "datatypeProperties": {...},
        "individuals": {...},
        "metadata": {...}
    }

    This function normalizes all sections to lists of dicts with a "name" field.
    """
    if path is None:
        path = get_default_ontology_path()
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize: convert dict-keyed sections to list of dicts with "name" field
    normalized = {}
    for key in ("classes", "objectProperties", "datatypeProperties", "individuals"):
        section = raw.get(key, {})
        if isinstance(section, dict):
            normalized[key] = [
                {**v, "name": k} if isinstance(v, dict) else {"name": k, "value": v}
                for k, v in section.items()
            ]
        elif isinstance(section, list):
            normalized[key] = section
        else:
            normalized[key] = []

    # Copy metadata as-is
    if "metadata" in raw:
        normalized["metadata"] = raw["metadata"]

    return normalized


def load_nvl_data(path: str | Path | None = None) -> dict[str, Any]:
    """Load NVL visualization data."""
    if path is None:
        path = get_default_nvl_path()
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_classes(ontology: dict | None = None) -> list[dict]:
    """Get all classes as list of dicts with 'name' field."""
    if ontology is None:
        ontology = load_ontology()
    return ontology.get("classes", [])


def get_object_properties(ontology: dict | None = None) -> list[dict]:
    """Get all object properties."""
    if ontology is None:
        ontology = load_ontology()
    return ontology.get("objectProperties", [])


def get_datatype_properties(ontology: dict | None = None) -> list[dict]:
    """Get all datatype properties."""
    if ontology is None:
        ontology = load_ontology()
    return ontology.get("datatypeProperties", [])


def get_individuals(ontology: dict | None = None) -> list[dict]:
    """Get all individuals."""
    if ontology is None:
        ontology = load_ontology()
    return ontology.get("individuals", [])


def get_stats(ontology: dict | None = None) -> dict[str, int]:
    """Get ontology statistics."""
    if ontology is None:
        ontology = load_ontology()
    return {
        "classes": len(ontology.get("classes", [])),
        "object_properties": len(ontology.get("objectProperties", [])),
        "datatype_properties": len(ontology.get("datatypeProperties", [])),
        "individuals": len(ontology.get("individuals", [])),
    }
