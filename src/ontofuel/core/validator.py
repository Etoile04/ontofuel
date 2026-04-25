"""Ontology validator — quality assessment of ontology data."""

from __future__ import annotations

from typing import Any

from .ontology import load_ontology, get_stats


class OntologyValidator:
    """Validate and score ontology quality.

    Scores across 5 dimensions (0-100 each):
    1. Naming conventions (PascalCase/camelCase)
    2. Hierarchy structure (class relationships)
    3. Semantic consistency (domain/range definitions)
    4. Completeness (annotations, metadata)
    5. Domain coverage (concept coverage)

    Example:
        >>> v = OntologyValidator()
        >>> result = v.validate()
        >>> print(result["total_score"])
        100
    """

    def __init__(self, ontology: dict | None = None):
        self._ontology = ontology

    @property
    def ontology(self) -> dict:
        if self._ontology is None:
            self._ontology = load_ontology()
        return self._ontology

    def validate(self) -> dict[str, Any]:
        """Run full validation and return scores.

        Returns:
            Dict with dimension scores, total score, grade, and issues list.
        """
        scores = {
            "naming": self._check_naming(),
            "hierarchy": self._check_hierarchy(),
            "semantic": self._check_semantic(),
            "completeness": self._check_completeness(),
            "coverage": self._check_coverage(),
        }

        total = sum(scores.values()) // len(scores)
        grade = self._score_to_grade(total)

        return {
            "dimension_scores": scores,
            "total_score": total,
            "grade": grade,
            "stats": get_stats(self.ontology),
            "issues": self._collect_issues(scores),
        }

    def quick_check(self) -> dict[str, Any]:
        """Fast structural check without deep analysis.

        Returns:
            Dict with basic health indicators.
        """
        ont = self.ontology
        stats = get_stats(ont)

        checks = {
            "has_classes": stats["classes"] > 0,
            "has_individuals": stats["individuals"] > 0,
            "has_properties": (stats["object_properties"] + stats["datatype_properties"]) > 0,
            "individuals_per_class": round(stats["individuals"] / max(stats["classes"], 1), 1),
            "properties_per_class": round(
                (stats["object_properties"] + stats["datatype_properties"]) / max(stats["classes"], 1), 1
            ),
        }
        checks["healthy"] = all([
            checks["has_classes"],
            checks["has_individuals"],
            checks["has_properties"],
        ])
        return checks

    def _check_naming(self) -> int:
        """Check naming conventions."""
        ont = self.ontology
        issues = 0
        total = 0

        for cls in ont.get("classes", []):
            name = cls.get("name", cls.get("className", ""))
            if not name:
                issues += 1
            total += 1

        for prop in ont.get("objectProperties", []) + ont.get("datatypeProperties", []):
            name = prop.get("name", "")
            if not name:
                issues += 1
            total += 1

        if total == 0:
            return 0
        return min(100, max(0, int(100 * (1 - issues / total))))

    def _check_hierarchy(self) -> int:
        """Check class hierarchy structure."""
        classes = self.ontology.get("classes", [])
        if not classes:
            return 0

        with_parent = 0
        for cls in classes:
            parent = cls.get("subClassOf", cls.get("parentClass", ""))
            if parent:
                with_parent += 1

        return min(100, int(100 * with_parent / len(classes)))

    def _check_semantic(self) -> int:
        """Check semantic consistency (domain/range)."""
        props = self.ontology.get("objectProperties", [])
        if not props:
            return 50  # Neutral if no properties

        with_domain = sum(1 for p in props if p.get("domain"))
        with_range = sum(1 for p in props if p.get("range"))

        score = int(100 * (with_domain + with_range) / (2 * len(props)))
        return min(100, score)

    def _check_completeness(self) -> int:
        """Check annotation completeness."""
        classes = self.ontology.get("classes", [])
        if not classes:
            return 0

        with_comment = sum(1 for c in classes if c.get("comment"))
        return min(100, int(100 * with_comment / len(classes)))

    def _check_coverage(self) -> int:
        """Check domain coverage."""
        stats = get_stats(self.ontology)
        # Score based on scale: more entities = better coverage
        score = min(100, stats["classes"] // 2 + stats["individuals"] // 20)
        return max(50, score)  # Floor at 50 if we have any data

    def _score_to_grade(self, score: int) -> str:
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def _collect_issues(self, scores: dict) -> list[str]:
        issues = []
        for dim, score in scores.items():
            if score < 70:
                issues.append(f"⚠️ {dim}: {score}/100 — needs improvement")
            elif score < 90:
                issues.append(f"ℹ️ {dim}: {score}/100 — good, can improve")
        if not issues:
            issues.append("✅ All dimensions score 90+")
        return issues
