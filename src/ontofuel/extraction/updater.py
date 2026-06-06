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

from ..core.ontology import get_stats, load_ontology


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
        enable_graph_update: bool = True,
        enable_versioning: bool = True,
        enable_critic: bool = False,
    ):
        """Initialize updater.

        Args:
            ontology_path: Path to ontology JSON. None for auto-detect.
            backup: Whether to create backup before saving.
            enable_graph_update: Compute and save OntologyDiff on save().
            enable_versioning: Commit new version on save().
            enable_critic: Run quality critique before add_individuals().
        """
        self._path = Path(ontology_path) if ontology_path else None
        self._ontology: dict | None = None
        self._backup = backup
        self._stats = UpdateStats()
        self._changes: list[dict[str, Any]] = []
        self.enable_graph_update = enable_graph_update
        self.enable_versioning = enable_versioning
        self.enable_critic = enable_critic

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
        # Quality gate: critic before adding (warning only, never blocks)
        if self.enable_critic:
            try:
                from .critic import OntologyCritic

                # Ensure ontology is loaded for critique
                _ = self.ontology
                critic = OntologyCritic()
                # Critic expects dict-keyed sections; convert from list format
                crit_data = self._to_dict_keyed(self._ontology)
                report = critic.critique_ontology(crit_data)
                if report.score < 50 or any(
                    s.severity.value == "critical" for s in report.suggestions
                ):
                    import warnings
                    warnings.warn(
                        f"本体质量批判: score={report.score}, "
                        f"success={report.success}. 继续更新。",
                        stacklevel=2,
                    )
            except Exception:
                pass  # critic module unavailable or error

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
            self._changes.append(
                {
                    "action": "add",
                    "type": "individual",
                    "name": name,
                    "timestamp": datetime.now().isoformat(),
                }
            )

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

            # Try to find individual from property context
            ind_name = target_individual or prop.get("individual", prop.get("source", ""))

            if not ind_name:
                stats.skipped_individuals += 1
                continue

            added = self._add_property_to_individual(
                ind_name, prop_name, prop_value, prop.get("unit", "")
            )
            if added:
                stats.added_properties += 1
                self._changes.append(
                    {
                        "action": "add",
                        "type": "property",
                        "name": prop_name,
                        "individual": ind_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
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

        # --- Integration: graph_update (OntologyDiff) ---
        if self.enable_graph_update:
            try:
                from .graph_update import OntologyDiff

                old_onto: dict | None = None
                # Try to find the most recent backup for diff
                backups = sorted(
                    path.parent.glob(path.stem + ".backup_*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if backups:
                    old_onto = json.loads(backups[0].read_text(encoding="utf-8"))

                if old_onto is not None:
                    # Convert list-based ontology to dict-keyed for diff
                    old_dict = self._to_dict_keyed(old_onto)
                    new_dict = self._to_dict_keyed(self._ontology)
                    diff = OntologyDiff.diff_ontologies(old_dict, new_dict)
                    diffs_dir = path.parent / "diffs"
                    diffs_dir.mkdir(parents=True, exist_ok=True)
                    diff_path = diffs_dir / f"diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    diff_data = {
                        "old_hash": OntologyDiff.compute_hash(old_onto),
                        "new_hash": OntologyDiff.compute_hash(self._ontology),
                        "operations": diff.operations,
                        "operation_type": diff.operation_type,
                        "tokens_saved": diff.estimate_tokens(),
                    }
                    with open(diff_path, "w", encoding="utf-8") as f:
                        json.dump(diff_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # graph_update module unavailable or error

        # --- Integration: versioning (OntologyVersionControl) ---
        if self.enable_versioning:
            try:
                from .versioning import OntologyVersionControl

                vc = OntologyVersionControl(
                    ontology_path=path,
                )
                # Convert to dict-keyed for versioning
                vc_data = self._to_dict_keyed(self._ontology)
                vc.commit(
                    message=f"OntologyUpdater save — {datetime.now().isoformat()}",
                    author="OntologyUpdater",
                    ontology_data=vc_data,
                )
            except Exception:
                pass  # versioning module unavailable or error

        return path

    def get_changes(self) -> list[dict[str, Any]]:
        """Get list of all changes made."""
        return self._changes

    def get_stats(self) -> UpdateStats:
        """Get accumulated update statistics."""
        return self._stats

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

    @staticmethod
    def _to_dict_keyed(ontology: dict[str, Any]) -> dict[str, Any]:
        """Convert list-based ontology sections to dict-keyed format.

        OntoFuel's load_ontology() normalizes sections to list-of-dicts.
        graph_update and versioning expect dict-keyed sections.
        """
        result: dict[str, Any] = {}
        for key in ("classes", "objectProperties", "datatypeProperties", "individuals"):
            section = ontology.get(key, [])
            if isinstance(section, list):
                result[key] = {
                    item.get("name", ""): {k: v for k, v in item.items() if k != "name"}
                    for item in section
                    if isinstance(item, dict)
                }
            else:
                result[key] = dict(section) if section else {}
        # Carry metadata
        if "metadata" in ontology:
            result["metadata"] = ontology["metadata"]
        return result
