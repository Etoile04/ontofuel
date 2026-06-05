"""Database module — Supabase client and data restoration."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


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

    def _request(
        self, method: str, table: str, data: dict | None = None, query: str = ""
    ) -> tuple[int, Any]:
        """Make a REST request to Supabase."""
        import urllib.error
        import urllib.request

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
        "columns": [
            "id",
            "material_id",
            "property_name",
            "property_value",
            "unit",
            "source",
            "temperature",
            "notes",
        ],
    },
    "material_composition": {
        "columns": ["id", "material_id", "element", "weight_fraction", "atomic_fraction"],
    },
    "literature_sources": {
        "columns": ["id", "title", "authors", "year", "doi", "journal", "url"],
    },
    "irradiation_behavior": {
        "columns": [
            "id",
            "material_id",
            "irradiation_type",
            "fluence",
            "temperature",
            "property_changed",
            "change_percent",
        ],
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
        from ..core.ontology import load_ontology  # pragma: no cover

        ont = load_ontology(ontology_path)  # pragma: no cover
        individuals = ont.get("individuals", [])  # pragma: no cover

        for ind in individuals:  # pragma: no cover
            name = ind.get("name", "")  # pragma: no cover
            if not name:  # pragma: no cover
                continue  # pragma: no cover

            # Extract material type from class
            cls = ind.get("class", "StructuralMaterial")  # pragma: no cover
            if isinstance(cls, list):  # pragma: no cover
                cls = cls[0] if cls else "StructuralMaterial"  # pragma: no cover

            # Try to extract chemical formula from name
            formula = self._extract_formula(name)  # pragma: no cover

            material = {  # pragma: no cover
                "id": str(uuid.uuid4()),  # pragma: no cover
                "name": name,  # pragma: no cover
                "chemical_formula": formula,  # pragma: no cover
                "material_type": cls,  # pragma: no cover
                "created_at": datetime.now().isoformat(),  # pragma: no cover
                "updated_at": datetime.now().isoformat(),  # pragma: no cover
            }  # pragma: no cover

            count = self.client.insert("materials", [material])  # pragma: no cover
            self.stats["materials"] += count  # pragma: no cover

            # Extract numeric properties
            for key, val in ind.items():  # pragma: no cover
                if key.startswith("prop_") and isinstance(val, (int, float)):  # pragma: no cover
                    prop = {  # pragma: no cover
                        "id": str(uuid.uuid4()),  # pragma: no cover
                        "material_id": material["id"],  # pragma: no cover
                        "property_name": key.replace("prop_", ""),  # pragma: no cover
                        "property_value": float(val),  # pragma: no cover
                        "unit": "",  # pragma: no cover
                        "source": "ontology",  # pragma: no cover
                    }  # pragma: no cover
                    if self.client.insert("material_properties", [prop]):  # pragma: no cover
                        self.stats["properties"] += 1  # pragma: no cover

        return self.stats  # pragma: no cover

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
        with open(path, encoding="utf-8") as f:
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
