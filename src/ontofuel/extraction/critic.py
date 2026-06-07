"""OntoFuel Ontology Quality Critic.

Zero-dependency ontology quality assessment module.
Evaluates ontologies across five dimensions (naming, structure, semantics,
completeness, domain_coverage) and produces actionable improvement suggestions.

Usage::

    from ontofuel.extraction.critic import OntologyCritic

    critic = OntologyCritic()
    report = critic.critique_ontology(my_ontology_data)
    print(report.score, report.success)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CritiqueSeverity(Enum):
    """Severity level for a critique finding."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Suggestion:
    """A single actionable improvement suggestion."""

    severity: CritiqueSeverity
    category: str
    description: str
    location: str | None = None
    fix_hint: str | None = None


@dataclass
class OntologyCritiqueReport:
    """Full critique report for an ontology."""

    success: bool
    score: int
    summary: str
    suggestions: list[Suggestion] = field(default_factory=list)
    categories_scores: dict[str, int] = field(default_factory=dict)


class OntologyCritic:
    """Rule-based ontology quality critic with optional LLM enhancement.

    The critic evaluates ontologies across five weighted dimensions:
        - naming          (0.20): PascalCase classes, camelCase properties
        - structure       (0.25): class hierarchy and property linkage
        - semantics       (0.25): domain/range completeness
        - completeness    (0.15): comments, metadata
        - domain_coverage(0.15): individual instance coverage
    """

    # Dimension weights (must sum to 1.0)
    _WEIGHTS: dict[str, float] = {
        "naming": 0.20,
        "structure": 0.25,
        "semantics": 0.25,
        "completeness": 0.15,
        "domain_coverage": 0.15,
    }

    _DIMENSION_DESCRIPTIONS: dict[str, str] = {
        "naming": "命名规范",
        "structure": "层次结构",
        "semantics": "语义一致性",
        "completeness": "完整性",
        "domain_coverage": "领域覆盖",
    }

    def critique_ontology(
        self,
        ontology: dict[str, Any],
        *,
        use_llm: bool = False,
    ) -> OntologyCritiqueReport:
        """Critique an ontology and return a structured report.

        Args:
            ontology: The ontology data as a dict with keys like
                ``classes``, ``objectProperties``, ``individuals``, ``metadata``.
            use_llm: If *True*, attempt LLM-based critique (falls back to rules).

        Returns:
            An :class:`OntologyCritiqueReport` with scores and suggestions.
        """
        if use_llm:
            # LLM interface reserved for future implementation
            return self._critique_with_rules(ontology)
        return self._critique_with_rules(ontology)

    # ------------------------------------------------------------------
    # Rule-based critique
    # ------------------------------------------------------------------

    def _critique_with_rules(self, ontology: dict[str, Any]) -> OntologyCritiqueReport:
        suggestions: list[Suggestion] = []
        categories_scores: dict[str, int] = {}

        naming_score, naming_sugs = self._check_naming(ontology)
        categories_scores["naming"] = naming_score
        suggestions.extend(naming_sugs)

        structure_score, structure_sugs = self._check_structure(ontology)
        categories_scores["structure"] = structure_score
        suggestions.extend(structure_sugs)

        semantics_score, semantics_sugs = self._check_semantics(ontology)
        categories_scores["semantics"] = semantics_score
        suggestions.extend(semantics_sugs)

        completeness_score, completeness_sugs = self._check_completeness(ontology)
        categories_scores["completeness"] = completeness_score
        suggestions.extend(completeness_sugs)

        coverage_score, coverage_sugs = self._check_domain_coverage(ontology)
        categories_scores["domain_coverage"] = coverage_score
        suggestions.extend(coverage_sugs)

        total_score = sum(categories_scores[cat] * self._WEIGHTS[cat] for cat in self._WEIGHTS)

        summary = self._generate_summary(total_score, categories_scores, suggestions)

        success = total_score >= 70 and not any(
            s.severity == CritiqueSeverity.CRITICAL for s in suggestions
        )

        return OntologyCritiqueReport(
            success=success,
            score=int(round(total_score)),
            summary=summary,
            suggestions=suggestions,
            categories_scores=categories_scores,
        )

    # ------------------------------------------------------------------
    # Dimension checkers  (each returns (score, suggestions))
    # ------------------------------------------------------------------

    def _check_naming(self, ontology: dict[str, Any]) -> tuple[int, list[Suggestion]]:
        suggestions: list[Suggestion] = []
        score = 100

        for name in ontology.get("classes", {}):
            if not name:
                continue
            if not name[0].isupper():
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="naming",
                        description=f"类名 '{name}' 应使用 PascalCase（首字母大写）",
                        location=name,
                        fix_hint=f"建议改为: {name[0].upper() + name[1:]}",
                    )
                )
                score -= 10
            if "_" in name:
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="naming",
                        description=f"类名 '{name}' 包含下划线，建议使用 PascalCase",
                        location=name,
                        fix_hint=f"建议改为: {name.replace('_', '')}",
                    )
                )
                score -= 8

        for name in ontology.get("objectProperties", {}):
            if name and name[0].isupper():
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="naming",
                        description=f"属性名 '{name}' 应使用 camelCase（首字母小写）",
                        location=name,
                        fix_hint=f"建议改为: {name[0].lower() + name[1:]}",
                    )
                )
                score -= 10

        return max(0, score), suggestions

    def _check_structure(self, ontology: dict[str, Any]) -> tuple[int, list[Suggestion]]:
        suggestions: list[Suggestion] = []
        score = 100

        classes = ontology.get("classes", {})
        props = ontology.get("objectProperties", {})

        if not classes:
            suggestions.append(
                Suggestion(
                    severity=CritiqueSeverity.CRITICAL,
                    category="structure",
                    description="本体没有定义任何类",
                    location=None,
                    fix_hint="至少需要定义一个顶层类",
                )
            )
            score -= 50
            return max(0, score), suggestions

        # Detect orphan classes (not referenced by any property)
        for class_name in classes:
            has_link = any(class_name in str(prop_def) for prop_def in props.values())
            if not has_link and len(classes) > 1:
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="structure",
                        description=f"类 '{class_name}' 没有关联任何属性",
                        location=class_name,
                        fix_hint="考虑添加相关属性或与其他类建立关系",
                    )
                )
                score -= 5

        return max(0, score), suggestions

    def _check_semantics(self, ontology: dict[str, Any]) -> tuple[int, list[Suggestion]]:
        suggestions: list[Suggestion] = []
        score = 100

        for prop_name, prop_def in ontology.get("objectProperties", {}).items():
            if "domain" not in prop_def and "range" not in prop_def:
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="semantics",
                        description=f"属性 '{prop_name}' 缺少 domain 或 range 定义",
                        location=prop_name,
                        fix_hint="建议添加 domain 和 range 定义",
                    )
                )
                score -= 10

        return max(0, score), suggestions

    def _check_completeness(self, ontology: dict[str, Any]) -> tuple[int, list[Suggestion]]:
        suggestions: list[Suggestion] = []
        score = 100

        for class_name, class_def in ontology.get("classes", {}).items():
            if "comment" not in class_def and "description" not in class_def:
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.WARNING,
                        category="completeness",
                        description=f"类 '{class_name}' 缺少注释或描述",
                        location=class_name,
                        fix_hint="建议添加 comment 字段说明类的用途",
                    )
                )
                score -= 8

        if "metadata" not in ontology:
            suggestions.append(
                Suggestion(
                    severity=CritiqueSeverity.WARNING,
                    category="completeness",
                    description="本体缺少元数据（metadata）",
                    location=None,
                    fix_hint="建议添加 metadata 字段，包含版本、创建时间等信息",
                )
            )
            score -= 15

        return max(0, score), suggestions

    def _check_domain_coverage(self, ontology: dict[str, Any]) -> tuple[int, list[Suggestion]]:
        suggestions: list[Suggestion] = []
        score = 100

        classes = ontology.get("classes", {})
        individuals = ontology.get("individuals", {})

        if classes and not individuals:
            suggestions.append(
                Suggestion(
                    severity=CritiqueSeverity.WARNING,
                    category="domain_coverage",
                    description="本体没有定义任何个体实例",
                    location=None,
                    fix_hint="建议添加一些具体的个体实例",
                )
            )
            score -= 15
            return max(0, score), suggestions

        if classes and individuals:
            ratio = len(individuals) / len(classes)
            if ratio < 0.5:
                suggestions.append(
                    Suggestion(
                        severity=CritiqueSeverity.INFO,
                        category="domain_coverage",
                        description=(
                            f"个体实例数量较少（{len(individuals)} 个，类 {len(classes)} 个）"
                        ),
                        location=None,
                        fix_hint="建议为每个类至少添加 1-2 个个体实例",
                    )
                )
                score -= 8

        return max(0, score), suggestions

    # ------------------------------------------------------------------
    # Summary generation
    # ------------------------------------------------------------------

    def _generate_summary(
        self,
        total_score: float,
        categories_scores: dict[str, int],
        suggestions: list[Suggestion],
    ) -> str:
        parts: list[str] = []

        if total_score >= 90:
            parts.append("✅ 本体质量优秀")
        elif total_score >= 70:
            parts.append("⚠️ 本体质量良好，但有改进空间")
        else:
            parts.append("❌ 本体质量需要改进")

        parts.append("\n各维度评分：")
        for cat, score in categories_scores.items():
            emoji = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            label = self._DIMENSION_DESCRIPTIONS.get(cat, cat)
            parts.append(f"  {emoji} {label}: {score}/100")

        critical = sum(1 for s in suggestions if s.severity == CritiqueSeverity.CRITICAL)
        warnings = sum(1 for s in suggestions if s.severity == CritiqueSeverity.WARNING)
        if critical:
            parts.append(f"\n🔴 严重问题: {critical} 个")
        if warnings:
            parts.append(f"🟡 警告: {warnings} 个")

        return "\n".join(parts)
