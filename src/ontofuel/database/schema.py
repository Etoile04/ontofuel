"""Database schema definitions for Supabase tables."""

from __future__ import annotations

from typing import Any

# ---- Table definitions ----

TABLES: dict[str, dict[str, Any]] = {
    "materials": {
        "description": "Core materials table",
        "columns": [
            {"name": "id", "type": "uuid", "primary": True, "default": "gen_random_uuid()"},
            {"name": "name", "type": "text", "nullable": False},
            {"name": "chemical_formula", "type": "text", "nullable": True},
            {"name": "material_type", "type": "text", "nullable": True},
            {"name": "created_at", "type": "timestamptz", "default": "now()"},
            {"name": "updated_at", "type": "timestamptz", "default": "now()"},
        ],
        "indexes": ["name", "material_type"],
    },
    "material_properties": {
        "description": "Material properties with values and units",
        "columns": [
            {"name": "id", "type": "uuid", "primary": True, "default": "gen_random_uuid()"},
            {"name": "material_id", "type": "uuid", "nullable": False, "references": "materials(id)"},
            {"name": "property_name", "type": "text", "nullable": False},
            {"name": "property_value", "type": "float8", "nullable": True},
            {"name": "value_string", "type": "text", "nullable": True},
            {"name": "unit", "type": "text", "nullable": True},
            {"name": "source", "type": "text", "nullable": True},
            {"name": "temperature", "type": "float8", "nullable": True},
            {"name": "temperature_unit", "type": "text", "default": "'K'"},
            {"name": "notes", "type": "text", "nullable": True},
        ],
        "indexes": ["material_id", "property_name"],
    },
    "material_composition": {
        "description": "Elemental composition of materials",
        "columns": [
            {"name": "id", "type": "uuid", "primary": True, "default": "gen_random_uuid()"},
            {"name": "material_id", "type": "uuid", "nullable": False, "references": "materials(id)"},
            {"name": "element", "type": "text", "nullable": False},
            {"name": "weight_fraction", "type": "float8", "nullable": True},
            {"name": "atomic_fraction", "type": "float8", "nullable": True},
        ],
        "indexes": ["material_id", "element"],
    },
    "literature_sources": {
        "description": "Literature references",
        "columns": [
            {"name": "id", "type": "uuid", "primary": True, "default": "gen_random_uuid()"},
            {"name": "title", "type": "text", "nullable": False},
            {"name": "authors", "type": "text[]", "nullable": True},
            {"name": "year", "type": "int4", "nullable": True},
            {"name": "doi", "type": "text", "nullable": True},
            {"name": "journal", "type": "text", "nullable": True},
            {"name": "url", "type": "text", "nullable": True},
        ],
        "indexes": ["year", "doi"],
    },
    "irradiation_behavior": {
        "description": "Irradiation effects on material properties",
        "columns": [
            {"name": "id", "type": "uuid", "primary": True, "default": "gen_random_uuid()"},
            {"name": "material_id", "type": "uuid", "nullable": False, "references": "materials(id)"},
            {"name": "irradiation_type", "type": "text", "nullable": True},
            {"name": "fluence", "type": "float8", "nullable": True},
            {"name": "fluence_unit", "type": "text", "default": "'n/cm²'"},
            {"name": "temperature", "type": "float8", "nullable": True},
            {"name": "property_changed", "type": "text", "nullable": True},
            {"name": "change_percent", "type": "float8", "nullable": True},
        ],
        "indexes": ["material_id", "irradiation_type"],
    },
}


def get_table_names() -> list[str]:
    """Get all table names."""
    return list(TABLES.keys())


def get_table(name: str) -> dict[str, Any] | None:
    """Get a table definition by name."""
    return TABLES.get(name)


def get_column_names(table_name: str) -> list[str]:
    """Get column names for a table."""
    table = TABLES.get(table_name)
    if not table:
        return []
    return [col["name"] for col in table["columns"]]


def generate_create_sql(table_name: str) -> str:
    """Generate CREATE TABLE SQL for a table.

    Args:
        table_name: Table name.

    Returns:
        SQL CREATE TABLE statement.
    """
    table = TABLES.get(table_name)
    if not table:
        raise ValueError(f"Unknown table: {table_name}")

    lines = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]
    col_defs = []
    constraints = []

    for col in table["columns"]:
        parts = [f'  "{col["name"]}"', col["type"]]
        if col.get("primary"):
            parts.append("PRIMARY KEY")
        if not col.get("nullable", True) and not col.get("primary"):
            parts.append("NOT NULL")
        if "default" in col:
            parts.append(f"DEFAULT {col['default']}")
        if "references" in col:
            constraints.append(
                f'  FOREIGN KEY ("{col["name"]}") REFERENCES {col["references"]}'
            )
        col_defs.append(" ".join(parts))

    all_defs = col_defs + constraints
    lines.append(",\n".join(all_defs))
    lines.append(");")

    # Indexes
    for idx in table.get("indexes", []):
        lines.append(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{idx} ON {table_name}("{idx}");')

    return "\n".join(lines)


def generate_all_sql() -> str:
    """Generate SQL for all tables.

    Returns:
        Complete SQL script.
    """
    parts = ["-- OntoFuel Database Schema", "-- Auto-generated", ""]
    for name in TABLES:
        parts.append(generate_create_sql(name))
        parts.append("")
    return "\n".join(parts)
