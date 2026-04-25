"""Ontology exporter — export to multiple formats."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .ontology import load_ontology, get_classes, get_individuals, get_object_properties


class OntologyExporter:
    """Export ontology data to various formats.

    Example:
        >>> exp = OntologyExporter()
        >>> exp.export_json("output.json")
        >>> exp.export_csv_classes("classes.csv")
    """

    def __init__(self, ontology: dict | None = None):
        self._ontology = ontology

    @property
    def ontology(self) -> dict:
        if self._ontology is None:
            self._ontology = load_ontology()
        return self._ontology

    def export_json(self, path: str | Path, indent: int = 2) -> Path:
        """Export full ontology as JSON."""
        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.ontology, f, ensure_ascii=False, indent=indent)
        return path

    def export_csv_classes(self, path: str | Path) -> Path:
        """Export classes to CSV."""
        classes = get_classes(self.ontology)
        return self._write_csv(path, classes, ["name", "comment"])

    def export_csv_individuals(self, path: str | Path) -> Path:
        """Export individuals to CSV."""
        individuals = get_individuals(self.ontology)
        return self._write_csv(path, individuals, ["name", "class", "type"])

    def export_csv_properties(self, path: str | Path) -> Path:
        """Export object properties to CSV."""
        props = get_object_properties(self.ontology)
        return self._write_csv(path, props, ["name", "domain", "range"])

    def export_graphml(self, path: str | Path) -> Path:
        """Export as GraphML for Gephi/Cytoscape."""
        path = Path(path)
        ont = self.ontology
        classes = {c.get("name", f"cls_{i}"): c for i, c in enumerate(ont.get("classes", []))}

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphstruct.org/graphml">',
            '<key id="label" for="node" attr.name="label" attr.type="string"/>',
            '<key id="type" for="node" attr.name="type" attr.type="string"/>',
            '<graph id="OntoFuel" edgedefault="directed">',
        ]

        # Nodes for classes
        for name in classes:
            safe_id = name.replace(" ", "_").replace("/", "_")
            lines.append(f'<node id="{safe_id}"><data key="label">{name}</data><data key="type">class</data></node>')

        # Nodes for individuals
        for ind in ont.get("individuals", []):
            name = ind.get("name", "unknown")
            cls = ind.get("class", "")
            safe_id = name.replace(" ", "_").replace("/", "_")
            lines.append(f'<node id="{safe_id}"><data key="label">{name}</data><data key="type">individual</data></node>')
            if cls and cls in classes:
                cls_safe = cls.replace(" ", "_").replace("/", "_")
                lines.append(f'<edge source="{safe_id}" target="{cls_safe}"/>')

        lines.append("</graph>")
        lines.append("</graphml>")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    def export_markdown_report(self, path: str | Path) -> Path:
        """Export a markdown summary report."""
        from .ontology import get_stats
        path = Path(path)
        stats = get_stats(self.ontology)

        lines = [
            "# OntoFuel Ontology Report",
            "",
            f"**Classes**: {stats['classes']}",
            f"**Object Properties**: {stats['object_properties']}",
            f"**Datatype Properties**: {stats['datatype_properties']}",
            f"**Individuals**: {stats['individuals']}",
            "",
            "## Classes",
            "",
        ]

        for cls in get_classes(self.ontology):
            name = cls.get("name", cls.get("className", "?"))
            comment = cls.get("comment", "")
            lines.append(f"- **{name}**: {comment}" if comment else f"- **{name}**")

        lines.extend(["", "## Individuals", ""])
        for ind in get_individuals(self.ontology)[:50]:  # First 50
            name = ind.get("name", "?")
            cls = ind.get("class", "")
            lines.append(f"- **{name}** → {cls}" if cls else f"- **{name}**")

        remaining = stats["individuals"] - 50
        if remaining > 0:
            lines.append(f"- ... and {remaining} more")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    def _write_csv(self, path: str | Path, items: list[dict], columns: list[str]) -> Path:
        path = Path(path)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({k: item.get(k, "") for k in columns})
        return path
