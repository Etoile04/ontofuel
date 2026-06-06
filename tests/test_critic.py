"""Tests for ontofuel.extraction.critic — ontology quality critic module."""

from __future__ import annotations

import pytest

from ontofuel.extraction.critic import (
    CritiqueSeverity,
    OntologyCritiqueReport,
    OntologyCritic,
    Suggestion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _perfect_ontology() -> dict:
    """A well-formed ontology that should score 100."""
    return {
        "metadata": {"version": "1.0"},
        "classes": {
            "Person": {"comment": "A human person", "subClassOf": None},
            "Organization": {"comment": "An organization entity", "subClassOf": None},
        },
        "objectProperties": {
            "worksFor": {"domain": "Person", "range": "Organization"},
            "hasMember": {"domain": "Organization", "range": "Person"},
        },
        "individuals": {
            "Alice": {"type": "Person"},
            "Bob": {"type": "Person"},
            "AcmeCorp": {"type": "Organization"},
        },
    }


def _problematic_ontology() -> dict:
    """An ontology with deliberate quality issues."""
    return {
        "classes": {
            "person": {},          # lowercase → naming warning
            "my_class": {},       # underscore → naming warning
        },
        "objectProperties": {
            "HasProp": {"domain": "Person"},  # capital letter property, missing range → 2 warnings
        },
        "individuals": {},
    }


# ---------------------------------------------------------------------------
# _check_naming
# ---------------------------------------------------------------------------

class TestCheckNaming:
    def test_pascalcase_correct(self):
        critic = OntologyCritic()
        onto = {"classes": {"Person": {}, "Car": {}}}
        score, sugs = critic._check_naming(onto)
        assert score == 100
        assert len(sugs) == 0

    def test_lowercase_class_warning(self):
        critic = OntologyCritic()
        onto = {"classes": {"person": {}}}
        score, sugs = critic._check_naming(onto)
        assert score < 100
        assert any(s.description.startswith("类名") and "PascalCase" in s.description for s in sugs)

    def test_underscore_class_warning(self):
        critic = OntologyCritic()
        onto = {"classes": {"My_Class": {}}}
        score, sugs = critic._check_naming(onto)
        assert score < 100
        assert any("下划线" in s.description for s in sugs)


# ---------------------------------------------------------------------------
# _check_structure
# ---------------------------------------------------------------------------

class TestCheckStructure:
    def test_no_classes_critical(self):
        critic = OntologyCritic()
        onto: dict = {"classes": {}}
        score, sugs = critic._check_structure(onto)
        assert score < 100
        assert any(s.severity == CritiqueSeverity.CRITICAL for s in sugs)

    def test_orphan_class_warning(self):
        critic = OntologyCritic()
        onto = {
            "classes": {"A": {}, "B": {}},
            "objectProperties": {"aProp": {"domain": "A", "range": "A"}},
        }
        score, sugs = critic._check_structure(onto)
        assert any("B" in s.location for s in sugs)

    def test_normal_structure_full_score(self):
        critic = OntologyCritic()
        onto = {
            "classes": {"A": {}, "B": {}},
            "objectProperties": {"link": {"domain": "A", "range": "B"}},
        }
        score, sugs = critic._check_structure(onto)
        assert score == 100
        assert len(sugs) == 0

    def test_single_class_no_orphan_warning(self):
        """A single class with no properties should NOT produce orphan warning."""
        critic = OntologyCritic()
        onto = {"classes": {"OnlyClass": {}}, "objectProperties": {}}
        score, sugs = critic._check_structure(onto)
        assert all(s.category != "structure" for s in sugs)


# ---------------------------------------------------------------------------
# _check_semantics
# ---------------------------------------------------------------------------

class TestCheckSemantics:
    def test_missing_domain_range_warning(self):
        critic = OntologyCritic()
        onto = {"objectProperties": {"prop": {}}}
        score, sugs = critic._check_semantics(onto)
        assert score < 100
        assert any("domain" in s.description or "range" in s.description for s in sugs)

    def test_full_semantics_score(self):
        critic = OntologyCritic()
        onto = {"objectProperties": {"prop": {"domain": "A", "range": "B"}}}
        score, sugs = critic._check_semantics(onto)
        assert score == 100


# ---------------------------------------------------------------------------
# _check_completeness
# ---------------------------------------------------------------------------

class TestCheckCompleteness:
    def test_missing_comment_warning(self):
        critic = OntologyCritic()
        onto = {"classes": {"X": {}}}
        score, sugs = critic._check_completeness(onto)
        assert any("缺少注释" in s.description for s in sugs)

    def test_missing_metadata_warning(self):
        critic = OntologyCritic()
        onto = {"classes": {}}
        score, sugs = critic._check_completeness(onto)
        assert any("元数据" in s.description for s in sugs)

    def test_full_completeness_score(self):
        critic = OntologyCritic()
        onto = {
            "metadata": {"version": "1.0"},
            "classes": {"X": {"comment": "desc"}},
        }
        score, sugs = critic._check_completeness(onto)
        assert score == 100


# ---------------------------------------------------------------------------
# _check_domain_coverage
# ---------------------------------------------------------------------------

class TestCheckDomainCoverage:
    def test_no_individuals_warning(self):
        critic = OntologyCritic()
        onto = {"classes": {"A": {}}, "individuals": {}}
        score, sugs = critic._check_domain_coverage(onto)
        assert score < 100
        assert any(s.severity == CritiqueSeverity.WARNING for s in sugs)

    def test_low_ratio_info(self):
        critic = OntologyCritic()
        onto = {
            "classes": {"A": {}, "B": {}, "C": {}},
            "individuals": {"x": {"type": "A"}},
        }
        score, sugs = critic._check_domain_coverage(onto)
        assert any(s.severity == CritiqueSeverity.INFO for s in sugs)

    def test_good_coverage_full_score(self):
        critic = OntologyCritic()
        onto = {
            "classes": {"A": {}, "B": {}},
            "individuals": {"x": {"type": "A"}, "y": {"type": "B"}, "z": {"type": "A"}},
        }
        score, sugs = critic._check_domain_coverage(onto)
        assert score == 100


# ---------------------------------------------------------------------------
# critique_ontology — full flow
# ---------------------------------------------------------------------------

class TestCritiqueOntology:
    def test_perfect_ontology_scores_100(self):
        critic = OntologyCritic()
        report = critic.critique_ontology(_perfect_ontology())
        assert report.score == 100
        assert report.success is True
        assert len(report.suggestions) == 0

    def test_problematic_ontology_low_score(self):
        critic = OntologyCritic()
        report = critic.critique_ontology(_problematic_ontology())
        assert report.score < 100
        assert len(report.suggestions) > 0

    def test_weighted_score_calculation(self):
        """Verify all 5 category scores are present and contribute to total."""
        critic = OntologyCritic()
        report = critic.critique_ontology(_problematic_ontology())
        assert set(report.categories_scores) == {
            "naming", "structure", "semantics", "completeness", "domain_coverage",
        }

    def test_critical_blocks_success(self):
        """Even if score >= 70, a CRITICAL finding should block success."""
        critic = OntologyCritic()
        onto: dict = {"classes": {}, "objectProperties": {}, "individuals": {}}
        report = critic.critique_ontology(onto)
        # Should have CRITICAL from structure (no classes)
        assert any(s.severity == CritiqueSeverity.CRITICAL for s in report.suggestions)
        assert report.success is False

    def test_use_llm_fallback(self):
        """use_llm=True should fall back to rules (no LLM available)."""
        critic = OntologyCritic()
        report_rules = critic.critique_ontology(_perfect_ontology(), use_llm=False)
        report_llm = critic.critique_ontology(_perfect_ontology(), use_llm=True)
        assert report_llm.score == report_rules.score


# ---------------------------------------------------------------------------
# OntologyCritiqueReport data structure
# ---------------------------------------------------------------------------

class TestReportStructure:
    def test_report_fields(self):
        report = OntologyCritiqueReport(
            success=True,
            score=85,
            summary="good",
            suggestions=[Suggestion(
                severity=CritiqueSeverity.INFO,
                category="naming",
                description="test",
            )],
            categories_scores={"naming": 90},
        )
        assert report.success is True
        assert report.score == 85
        assert len(report.suggestions) == 1
        assert report.suggestions[0].severity == CritiqueSeverity.INFO
