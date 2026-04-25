"""Updater — incrementally update an ontology with extracted data.

Supports:
  - Adding new individuals
  - Adding new property values
  - Updating existing individuals
  - Backup before modification
  - Change tracking with statistics

Example:
    >>> updater = OntologyUpdater("ontology.json")
    >>> stats = updater.add_individuals(merged_result.individuals)
    >>> updater.save("ontology_updated.json")
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.ontology import load_ontology, get_stats


class UpdateStats:
    """Statistics from an ontology update operation."""

    def __init__(self):
        self.added_individuals: int = 0
        self.updated_individuals: int = 0
        self.skipped_individuals: int = 0
        self.added_properties: int = 0
        self.added_relationships: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_individuals": self.added_individuals,
            "updated_individuals": self.updated_individuals,
            "skipped_individuals": self.skipped_individuals,
            "added_properties": self.added_properties,
            "added_relationships": self.added_relationships,
            "errors": self.errors,
        }


class OntologyUpdater:
    """Incrementally update an ontology with extraction results.

    Example:
        >>> updater = OntologyUpdater("ontology.json")
        >>> stats = updater.add_individuals([{"name": "U-10Mo", "type": "Alloy"}])
        >>> updater.save()
    """

    def __init__(
        self,
        ontology_path: str | Path | None = None,
        backup: bool = True,
    ):
        """Initialize updater.

        Args:
            ontology_path: Path to ontology JSON. None for auto-detect.
            backup: Whether to create backup before saving.
        """
        self._path = Path(ontology_path) if ontology_path else None
        self._ontology: dict | None = None
        self._backup = backup
        self._stats = UpdateStats()
        self._changes: list[dict[str, Any]] = []

    @property
    def ontology(self) -> dict:
        if self._ontology is None:
            self._ontology = load_ontology(self._path)
        return self._ontology

    @property
    def stats(self) -> UpdateStats:
        return self._stats

    def add_individuals(
        self,
        individuals: list[dict[str, Any]],
        dedup: bool = True,
    ) -> UpdateStats:
        """Add new individuals to the ontology.

        Args:
            individuals: List of individual dicts with at least "name" field.
            dedup: Whether to skip individuals that already exist.

        Returns:
            UpdateStats with counts.
        """
        stats = UpdateStats()
        existing_names = self._get_existing_names()

        for ind in individuals:
            name = ind.get("name", "")
            if not name:
                stats.skipped_individuals += 1
                continue

            if dedup and name in existing_names:
                # Try to update existing individual with new properties
                updated = self._update_existing(name, ind)
                if updated:
                    stats.updated_individuals += 1
                else:
                    stats.skipped_individuals += 1
                continue

            # Add new individual
            self._add_individual(ind)
            stats.added_individuals += 1
            self._changes.append({
                "action": "add",
                "type": "individual",
                "name": name,
                "timestamp": datetime.now().isoformat(),
            })

        # Merge stats
        self._merge_stats(stats)
        return stats

    def add_properties(
        self,
        properties: list[dict[str, Any]],
        target_individual: str | None = None,
    ) -> UpdateStats:
        """Add property values to individuals.

        Args:
            properties: List of property dicts.
            target_individual: If set, add all properties to this individual.

        Returns:
            UpdateStats with counts.
        """
        stats = UpdateStats()

        for prop in properties:
            prop_name = prop.get("name", "")
            prop_value = prop.get("value", "")

            if target_individual:
                ind_name = target_individual
            else:
                # Try to find individual from property context
                ind_name = prop.get("individual", prop.get("source", ""))

            if not ind_name:
                stats.skipped_individuals += 1
                continue

            added = self._add_property_to_individual(ind_name, prop_name, prop_value, prop.get("unit", ""))
            if added:
                stats.added_properties += 1
            else:
                stats.skipped_individuals += 1

        self._merge_stats(stats)
        return stats

    def save(
        self,
        output_path: str | Path | None = None,
    ) -> Path:
        """Save the updated ontology.

        Args:
            output_path: Output path. Defaults to original path.

        Returns:
            Path to saved file.
        """
        path = Path(output_path) if output_path else self._path
        if path is None:
            raise ValueError("No output path specified and no original path")

        # Backup
        if self._backup and path.exists():
            backup_path = path.with_suffix(
                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(path, backup_path)

        # Save
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._ontology, f, ensure_ascii=False, indent=2)

        return path

    def get_changes(self) -> list[dict[str, Any]]:
        """Get list of all changes made."""
        return self._changes

    def get_before_stats(self) -> dict[str, int]:
        """Get ontology stats before changes (recomputed from current state)."""
        return get_stats(self.ontology)

    def _get_existing_names(self) -> set[str]:
        """Get set of existing individual names."""
        individuals = self.ontology.get("individuals", [])
        if isinstance(individuals, dict):
            return set(individuals.keys())
        return {ind.get("name", "") for ind in individuals if isinstance(ind, dict)}

    def _add_individual(self, ind: dict[str, Any]) -> None:
        """Add an individual to the ontology."""
        individuals = self.ontology.get("individuals", [])

        # Normalize to list if dict-keyed
        if isinstance(individuals, dict):
            name = ind.get("name", "")
            individuals[name] = ind
            self._ontology["individuals"] = individuals
        else:
            individuals.append(ind)

    def _update_existing(self, name: str, new_data: dict[str, Any]) -> bool:
        """Update an existing individual with new data.

        Returns True if any new data was added.
        """
        individuals = self.ontology.get("individuals", [])
        updated = False

        if isinstance(individuals, dict):
            if name in individuals:
                existing = individuals[name]
                for key, val in new_data.items():
                    if key == "name":
                        continue
                    if key not in existing:
                        existing[key] = val
                        updated = True
        else:
            for ind in individuals:
                if isinstance(ind, dict) and ind.get("name") == name:
                    for key, val in new_data.items():
                        if key == "name":
                            continue
                        if key not in ind:
                            ind[key] = val
                            updated = True
                    break

        return updated

    def _add_property_to_individual(
        self,
        ind_name: str,
        prop_name: str,
        prop_value: Any,
        unit: str = "",
    ) -> bool:
        """Add a property to an individual.

        Returns True if property was added.
        """
        individuals = self.ontology.get("individuals", [])
        prop_key = f"prop_{prop_name}"

        if isinstance(individuals, dict):
            if ind_name in individuals:
                individuals[ind_name][prop_key] = prop_value
                return True
        else:
            for ind in individuals:
                if isinstance(ind, dict) and ind.get("name") == ind_name:
                    ind[prop_key] = prop_value
                    return True

        return False

    def _merge_stats(self, other: UpdateStats) -> None:
        """Merge another stats into this one."""
        self._stats.added_individuals += other.added_individuals
        self._stats.updated_individuals += other.updated_individuals
        self._stats.skipped_individuals += other.skipped_individuals
        self._stats.added_properties += other.added_properties
        self._stats.added_relationships += other.added_relationships
        self._stats.errors.extend(other.errors)
