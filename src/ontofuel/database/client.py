"""Database module — Supabase client and data restoration."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class SupabaseClient:
    """Lightweight Supabase REST client (stdlib only, uses urllib).

    Example:
        >>> client = SupabaseClient()
        >>> client.health_check()
    """

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
    ):
        self.url = url or os.environ.get("SUPABASE_URL", "http://localhost:54321")
        self.key = key or os.environ.get("SUPABASE_SERVICE_KEY", "")
        self._headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def _request(self, method: str, table: str, data: dict | None = None,
                 query: str = "") -> tuple[int, Any]:
        """Make a REST request to Supabase."""
        import urllib.request
        import urllib.error

        url = f"{self.url}/rest/v1/{table}{query}"
        body = json.dumps(data).encode() if data else None

        req = urllib.request.Request(url, data=body, headers=self._headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read().decode()
                return resp.status, json.loads(resp_data) if resp_data else None
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return e.code, body
        except Exception as e:
            return 0, str(e)

    def health_check(self) -> bool:
        """Check if Supabase is reachable."""
        code, _ = self._request("GET", "materials", query="?limit=1")
        return code in (200, 206)

    def select(self, table: str, query: str = "") -> list[dict]:
        """Select rows from a table."""
        code, data = self._request("GET", table, query=query)
        if code in (200, 206):
            return data if isinstance(data, list) else []
        return []

    def insert(self, table: str, rows: list[dict]) -> int:
        """Insert rows into a table. Returns count inserted."""
        code, _ = self._request("POST", table, data=rows if len(rows) > 1 else rows[0])
        return 1 if code in (200, 201) else 0

    def delete(self, table: str, query: str) -> int:
        """Delete rows matching query."""
        code, _ = self._request("DELETE", table, query=query)
        return 1 if code in (200, 204) else 0

    def count(self, table: str) -> int:
        """Count rows in a table."""
        code, data = self._request("GET", table, query="?select=count")
        if code == 200 and isinstance(data, list) and data:
            return data[0].get("count", 0)
        return 0


# ---- Schema definitions ----

TABLES = {
    "materials": {
        "columns": ["id", "name", "chemical_formula", "material_type", "created_at", "updated_at"],
    },
    "material_properties": {
        "columns": ["id", "material_id", "property_name", "property_value", "unit", "source", "temperature", "notes"],
    },
    "material_composition": {
        "columns": ["id", "material_id", "element", "weight_fraction", "atomic_fraction"],
    },
    "literature_sources": {
        "columns": ["id", "title", "authors", "year", "doi", "journal", "url"],
    },
    "irradiation_behavior": {
        "columns": ["id", "material_id", "irradiation_type", "fluence", "temperature", "property_changed", "change_percent"],
    },
}


class DataRestorer:
    """Restore ontology data into Supabase from JSON sources.

    Example:
        >>> r = DataRestorer(client)
        >>> r.restore_from_ontology("ontology/material_ontology_enhanced.json")
        >>> print(r.stats)
    """

    def __init__(self, client: SupabaseClient | None = None):
        self.client = client or SupabaseClient()
        self.stats = {"materials": 0, "properties": 0, "errors": []}

    def restore_from_ontology(self, ontology_path: str | Path) -> dict:
        """Restore individuals from ontology JSON to Supabase materials table.

        Returns:
            Stats dict with counts.
        """
        from ..core.ontology import load_ontology

        ont = load_ontology(ontology_path)
        individuals = ont.get("individuals", [])

        for ind in individuals:
            name = ind.get("name", "")
            if not name:
                continue

            # Extract material type from class
            cls = ind.get("class", "StructuralMaterial")
            if isinstance(cls, list):
                cls = cls[0] if cls else "StructuralMaterial"

            # Try to extract chemical formula from name
            formula = self._extract_formula(name)

            material = {
                "id": str(uuid.uuid4()),
                "name": name,
                "chemical_formula": formula,
                "material_type": cls,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            count = self.client.insert("materials", [material])
            self.stats["materials"] += count

            # Extract numeric properties
            for key, val in ind.items():
                if key.startswith("prop_") and isinstance(val, (int, float)):
                    prop = {
                        "id": str(uuid.uuid4()),
                        "material_id": material["id"],
                        "property_name": key.replace("prop_", ""),
                        "property_value": float(val),
                        "unit": "",
                        "source": "ontology",
                    }
                    if self.client.insert("material_properties", [prop]):
                        self.stats["properties"] += 1

        return self.stats

    def _extract_formula(self, name: str) -> str:
        """Try to extract chemical formula from individual name."""
        # Common patterns: U-10Mo, U10Zr, HEA_XXX
        parts = name.split("_")
        for p in parts:
            if any(c.isupper() for c in p) and any(c.isdigit() for c in p):
                return p.replace("-", "")
        return ""

    def restore_from_json(self, data_path: str | Path, table: str) -> dict:
        """Restore data from a generic JSON file to a table."""
        path = Path(data_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        count = 0
        for row in data:
            if "id" not in row:
                row["id"] = str(uuid.uuid4())
            if self.client.insert(table, [row]):
                count += 1

        self.stats[table] = count
        return self.stats
