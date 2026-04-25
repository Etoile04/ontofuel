"""Merger — merge extraction results with deduplication and conflict resolution.

Supports:
  - Merging multiple ExtractionResults into one
  - Deduplication by name (exact and fuzzy)
  - Conflict resolution (latest wins, or priority-based)

Example:
    >>> merger = Merger()
    >>> merged = merger.merge([result1, result2, result3])
    >>> print(merged.stats)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


@dataclass
class MergeStats:
    """Statistics from a merge operation."""
    input_results: int = 0
    total_individuals_in: int = 0
    total_properties_in: int = 0
    total_relationships_in: int = 0
    duplicates_removed: int = 0
    conflicts_resolved: int = 0
    final_individuals: int = 0
    final_properties: int = 0
    final_relationships: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "input_results": self.input_results,
            "total_individuals_in": self.total_individuals_in,
            "duplicates_removed": self.duplicates_removed,
            "conflicts_resolved": self.conflicts_resolved,
            "final_individuals": self.final_individuals,
            "final_properties": self.final_properties,
            "dedup_rate": round(self.duplicates_removed / max(self.total_individuals_in, 1) * 100, 1),
        }


@dataclass
class MergedResult:
    """Merged extraction results.

    Attributes:
        individuals: Deduplicated individuals.
        properties: Merged properties.
        relationships: Merged relationships.
        stats: Merge statistics.
        sources: List of source identifiers.
    """
    individuals: list[dict[str, Any]] = field(default_factory=list)
    properties: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    stats: MergeStats = field(default_factory=MergeStats)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "individuals": self.individuals,
            "properties": self.properties,
            "relationships": self.relationships,
            "stats": self.stats.to_dict(),
            "sources": self.sources,
        }


class Merger:
    """Merge extraction results with deduplication.

    Strategies:
      - "exact": Exact name matching (default)
      - "fuzzy": Fuzzy matching with configurable threshold
      - "normalized": Normalize names before comparing

    Example:
        >>> from ontofuel.extraction.extractor import ExtractionResult
        >>> r1 = ExtractionResult(source="chunk_0", individuals=[{"name": "U-10Mo"}])
        >>> r2 = ExtractionResult(source="chunk_1", individuals=[{"name": "U-10Mo"}])
        >>> merger = Merger()
        >>> merged = merger.merge([r1, r2])
        >>> print(merged.stats.duplicates_removed)
        1
    """

    def __init__(
        self,
        strategy: str = "exact",
        fuzzy_threshold: float = 0.85,
        conflict_resolution: str = "latest",
    ):
        """Initialize merger.

        Args:
            strategy: Deduplication strategy ("exact", "fuzzy", "normalized").
            fuzzy_threshold: Similarity threshold for fuzzy matching (0-1).
            conflict_resolution: How to resolve conflicts ("latest", "priority", "merge").
        """
        self.strategy = strategy
        self.fuzzy_threshold = fuzzy_threshold
        self.conflict_resolution = conflict_resolution

    def merge(self, results: list) -> MergedResult:
        """Merge multiple ExtractionResults.

        Args:
            results: List of ExtractionResult objects.

        Returns:
            MergedResult with deduplicated data and merge statistics.
        """
        stats = MergeStats(input_results=len(results))

        all_individuals: list[dict] = []
        all_properties: list[dict] = []
        all_relationships: list[dict] = []
        sources: list[str] = []

        for r in results:
            all_individuals.extend(r.individuals)
            all_properties.extend(r.properties)
            all_relationships.extend(r.relationships)
            sources.append(r.source)
            stats.total_individuals_in += len(r.individuals)
            stats.total_properties_in += len(r.properties)
            stats.total_relationships_in += len(r.relationships)

        # Deduplicate
        deduped_individuals, dup_count = self._deduplicate(all_individuals)
        stats.duplicates_removed = dup_count

        # Merge properties by name
        merged_props = self._merge_properties(all_properties)

        # Deduplicate relationships
        deduped_rels, rel_dups = self._deduplicate(all_relationships, key="context")
        stats.duplicates_removed += rel_dups

        stats.final_individuals = len(deduped_individuals)
        stats.final_properties = len(merged_props)
        stats.final_relationships = len(deduped_rels)

        return MergedResult(
            individuals=deduped_individuals,
            properties=merged_props,
            relationships=deduped_rels,
            stats=stats,
            sources=sources,
        )

    def _deduplicate(
        self,
        items: list[dict],
        key: str = "name",
    ) -> tuple[list[dict], int]:
        """Deduplicate items by key.

        Returns:
            Tuple of (deduplicated items, duplicates removed count).
        """
        if not items:
            return [], 0

        seen: dict[str, dict] = {}
        result: list[dict] = []
        dups = 0

        for item in items:
            name = item.get(key, "")
            if not name:
                result.append(item)
                continue

            normalized = self._normalize(name)

            if self.strategy == "exact":
                match_key = normalized
            elif self.strategy == "fuzzy":
                match_key = self._fuzzy_match(normalized, seen)
            elif self.strategy == "normalized":
                match_key = re.sub(r"[\s\-_]", "", normalized.lower())
            else:
                match_key = normalized

            if match_key in seen:
                dups += 1
                # Resolve conflict
                if self.conflict_resolution == "latest":
                    # Replace in both seen and result
                    idx_to_replace = None
                    for i, r in enumerate(result):
                        r_key = self._normalize(r.get(key, ""))
                        if self.strategy == "fuzzy":
                            if SequenceMatcher(None, r_key, match_key).ratio() >= self.fuzzy_threshold:
                                idx_to_replace = i
                                break
                        elif r_key == match_key:
                            idx_to_replace = i
                            break
                    if idx_to_replace is not None:
                        result[idx_to_replace] = item
                    seen[match_key] = item
                elif self.conflict_resolution == "merge":
                    existing = seen[match_key]
                    for k, v in item.items():
                        if k not in existing:
                            existing[k] = v
            else:
                seen[match_key] = item
                result.append(item)

        return result, dups

    def _merge_properties(self, properties: list[dict]) -> list[dict]:
        """Merge properties, combining values for the same property name."""
        if not properties:
            return []

        grouped: dict[str, list[dict]] = {}
        for prop in properties:
            name = prop.get("name", "unknown")
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(prop)

        result = []
        for name, props in grouped.items():
            if len(props) == 1:
                result.append(props[0])
            else:
                # Keep unique values
                values_seen: set[str] = set()
                for p in props:
                    val_key = f"{p.get('value', '')}_{p.get('unit', '')}"
                    if val_key not in values_seen:
                        values_seen.add(val_key)
                        result.append(p)

        return result

    def _normalize(self, name: str) -> str:
        """Normalize a name for comparison."""
        return name.strip().lower()

    def _fuzzy_match(self, name: str, seen: dict[str, dict]) -> str:
        """Find fuzzy match in seen keys, or return original name."""
        for existing_key in seen:
            ratio = SequenceMatcher(None, name, existing_key).ratio()
            if ratio >= self.fuzzy_threshold:
                return existing_key
        return name
