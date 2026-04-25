"""Data restoration — load ontology data into Supabase."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .client import SupabaseClient
from .schema import get_column_names, get_table_names


class DataRestorer:
    """Restore ontology data into Supabase tables.

    Supports:
    - Restoring individuals as materials
    - Restoring properties as material_properties
    - Batch restoration with progress tracking
    - Dry-run mode for preview

    Example:
        >>> r = DataRestorer(client)
        >>> r.restore_from_ontology("ontology.json")
        >>> print(r.stats)
    """

    def __init__(self, client: SupabaseClient | None = None):
        self.client = client or SupabaseClient()
        self.stats: dict[str, Any] = {
            "materials": 0,
            "properties": 0,
            "compositions": 0,
            "errors": [],
            "skipped": 0,
        }
        self._dry_run = False

    def restore_from_ontology(
        self,
        ontology_path: str | Path,
        dry_run: bool = False,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        """Restore individuals from ontology JSON to Supabase.

        Args:
            ontology_path: Path to ontology JSON file.
            dry_run: If True, don't actually write to DB.
            batch_size: Number of records to insert per batch.

        Returns:
            Stats dict with counts and errors.
        """
        from ..core.ontology import load_ontology

        self._dry_run = dry_run
        ont = load_ontology(ontology_path)
        individuals = ont.get("individuals", [])

        print(f"Restoring {len(individuals)} individuals...")

        batch: list[dict] = []
        for i, ind in enumerate(individuals):
            name = ind.get("name", "")
            if not name:
                self.stats["skipped"] += 1
                continue

            # Extract material type from class
            cls = ind.get("class", "Unknown")
            if isinstance(cls, list):
                cls = cls[0] if cls else "Unknown"

            formula = self._extract_formula(name)

            material = {
                "id": str(uuid.uuid4()),
                "name": name,
                "chemical_formula": formula,
                "material_type": cls,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            if not dry_run:
                batch.append(material)

                # Insert batch
                if len(batch) >= batch_size:
                    self._insert_batch("materials", batch)
                    self.stats["materials"] += len(batch)
                    batch = []
            else:
                self.stats["materials"] += 1

            # Extract properties
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
                    if not dry_run:
                        self.client.insert("material_properties", [prop])
                    self.stats["properties"] += 1

        # Flush remaining batch
        if batch and not dry_run:
            self._insert_batch("materials", batch)
            self.stats["materials"] += len(batch)

        mode = " (dry run)" if dry_run else ""
        print(f"Done{mode}: {self.stats['materials']} materials, {self.stats['properties']} properties")

        return self.stats

    def restore_from_json(
        self,
        data_path: str | Path,
        table: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Restore data from a generic JSON file to a table.

        Args:
            data_path: Path to JSON data file.
            table: Target table name.
            dry_run: If True, don't actually write.

        Returns:
            Stats dict.
        """
        path = Path(data_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        count = 0
        for row in data:
            if "id" not in row:
                row["id"] = str(uuid.uuid4())
            if not dry_run:
                if self.client.insert(table, [row]):
                    count += 1
            else:
                count += 1

        self.stats[table] = count
        return self.stats

    def verify_data(self, table: str) -> dict[str, Any]:
        """Verify data in a table.

        Returns:
            Dict with count and sample data.
        """
        rows = self.client.select(table, query="?limit=5")
        total = self.client.count(table)
        return {"table": table, "count": total, "sample": rows}

    def _insert_batch(self, table: str, rows: list[dict]) -> int:
        """Insert a batch of rows."""
        count = 0
        for row in rows:
            if self.client.insert(table, [row]):
                count += 1
            else:
                self.stats["errors"].append(f"Failed to insert: {row.get('name', 'unknown')}")
        return count

    def _extract_formula(self, name: str) -> str:
        """Try to extract chemical formula from individual name."""
        # Common patterns: U-10Mo, U10Zr, HEA_XXX
        parts = name.split("_")
        for p in parts:
            if any(c.isupper() for c in p) and any(c.isdigit() for c in p):
                return p.replace("-", "")
        return ""

    def reset_stats(self) -> None:
        """Reset stats for a new run."""
        self.stats = {
            "materials": 0,
            "properties": 0,
            "compositions": 0,
            "errors": [],
            "skipped": 0,
        }
