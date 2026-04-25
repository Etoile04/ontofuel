"""Ontology query engine — search and filter ontology data."""

from __future__ import annotations

from typing import Any

from .ontology import load_ontology, get_classes, get_individuals


class OntologyQuery:
    """Query engine for ontology data.

    Example:
        >>> q = OntologyQuery()
        >>> results = q.search("U-10Mo")
        >>> print(len(results))
        >>> results = q.by_class("NuclearFuel")
    """

    def __init__(self, ontology: dict | None = None):
        """Initialize with optional pre-loaded ontology.

        Args:
            ontology: Pre-loaded ontology dict. If None, loads default.
        """
        self._ontology = ontology
        self._classes: list[dict] | None = None
        self._individuals: list[dict] | None = None
        self._class_index: dict[str, dict] | None = None
        self._individual_index: dict[str, dict] | None = None

    @property
    def ontology(self) -> dict:
        if self._ontology is None:
            self._ontology = load_ontology()
        return self._ontology

    @property
    def classes(self) -> list[dict]:
        if self._classes is None:
            self._classes = get_classes(self.ontology)
        return self._classes

    @property
    def individuals(self) -> list[dict]:
        if self._individuals is None:
            self._individuals = get_individuals(self.ontology)
        return self._individuals

    def _build_class_index(self) -> dict[str, dict]:
        if self._class_index is None:
            self._class_index = {}
            for cls in self.classes:
                name = cls.get("name", cls.get("className", ""))
                if name:
                    self._class_index[name.lower()] = cls
        return self._class_index

    def _build_individual_index(self) -> dict[str, dict]:
        if self._individual_index is None:
            self._individual_index = {}
            for ind in self.individuals:
                name = ind.get("name", "")
                if name:
                    self._individual_index[name.lower()] = ind
        return self._individual_index

    def search(self, query: str, category: str = "all") -> list[dict]:
        """Search ontology by name (case-insensitive substring match).

        Args:
            query: Search string.
            category: "classes", "individuals", or "all".

        Returns:
            List of matching items with a "_match_type" field added.
        """
        q = query.lower()
        results = []

        if category in ("all", "classes"):
            for cls in self.classes:
                name = cls.get("name", cls.get("className", ""))
                comment = cls.get("comment", "")
                if q in name.lower() or q in str(comment).lower():
                    results.append({**cls, "_match_type": "class"})

        if category in ("all", "individuals"):
            for ind in self.individuals:
                name = ind.get("name", "")
                if q in name.lower():
                    results.append({**ind, "_match_type": "individual"})

        return results

    def by_class(self, class_name: str) -> list[dict]:
        """Get all individuals of a given class.

        Args:
            class_name: Class name (exact or case-insensitive).

        Returns:
            List of individuals belonging to the class.
        """
        results = []
        target = class_name.lower()

        for ind in self.individuals:
            # Check "class" field (direct class reference)
            ind_class = ind.get("class", "")
            if ind_class.lower() == target:
                results.append(ind)
                continue

            # Check "type" field
            ind_type = ind.get("type", "")
            if isinstance(ind_type, str) and ind_type.lower() == target:
                results.append(ind)
                continue
            elif isinstance(ind_type, list):
                for t in ind_type:
                    if isinstance(t, str) and t.lower() == target:
                        results.append(ind)
                        break
                else:
                    continue

            # Check "classes" list
            ind_classes = ind.get("classes", [])
            if isinstance(ind_classes, list):
                for c in ind_classes:
                    if isinstance(c, str) and c.lower() == target:
                        results.append(ind)
                        break

        return results

    def by_property(self, prop_name: str, prop_value: str | None = None) -> list[dict]:
        """Search individuals by property name and optional value.

        Args:
            prop_name: Property name prefix (e.g., "density" matches "prop_density")
            prop_value: Optional value to match (substring).

        Returns:
            List of individuals with matching properties.
        """
        results = []
        prop_key = f"prop_{prop_name}" if not prop_name.startswith("prop_") else prop_name

        for ind in self.individuals:
            # Check exact prop key
            if prop_key in ind:
                if prop_value is None:
                    results.append(ind)
                elif str(prop_value).lower() in str(ind[prop_key]).lower():
                    results.append(ind)
                continue

            # Check all prop_ keys for substring match
            for key, val in ind.items():
                if key.startswith("prop_") and prop_name.lower() in key.lower():
                    if prop_value is None or str(prop_value).lower() in str(val).lower():
                        results.append(ind)
                        break

        return results

    def get_class_hierarchy(self, class_name: str) -> dict[str, Any]:
        """Get a class and its direct children.

        Args:
            class_name: Parent class name.

        Returns:
            Dict with "class" and "children" keys.
        """
        target = class_name.lower()
        parent = None
        children = []

        for cls in self.classes:
            name = cls.get("name", cls.get("className", ""))
            if name.lower() == target:
                parent = cls
            else:
                # Check subclassOf
                parent_ref = cls.get("subClassOf", cls.get("parentClass", ""))
                if isinstance(parent_ref, str) and parent_ref.lower() == target:
                    children.append(cls)
                elif isinstance(parent_ref, list):
                    for p in parent_ref:
                        if isinstance(p, str) and p.lower() == target:
                            children.append(cls)
                            break

        return {"class": parent, "children": children}

    def stats(self) -> dict[str, int]:
        """Return ontology statistics."""
        from .ontology import get_stats
        return get_stats(self.ontology)
