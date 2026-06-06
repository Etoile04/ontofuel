"""OntoFuel Sublimation — Ontology / Fact Separation.

Inspired by OntoCast's schema-instance split, this module separates the
*ontology schema* (classes, object-properties, datatype-properties) from
*concrete facts* (individuals, property-assertions, relations) so that a
reusable ontology can be merged across chunks while facts remain chunk-local.

Key types
---------
SeparationResult : dataclass carrying ``ontology`` and ``facts`` dicts.

Classes
-------
OntologySublimator
    Core engine — classifies individuals via heuristic IRI patterns and
    splits an extraction payload into ontology / facts halves.

Design notes
------------
- Zero runtime dependencies (stdlib only).
- Python 3.12+ style annotations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SeparationResult:
    """Container for the two halves produced by ontology sublimation.

    Attributes
    ----------
    ontology :
        Schema-level dictionary with keys ``classes``, ``objectProperties``,
        ``datatypeProperties`` and ``metadata``.
    facts :
        Instance-level dictionary with keys ``individuals``,
        ``propertyValues``, ``relations`` and ``metadata``.
    statistics :
        Counts for each sub-category in both halves.
    """

    ontology: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

_CHUNK_IRI_RE = re.compile(r"chunk_\d+|cd:")


class OntologySublimator:
    """Separate ontology schema from instance-level facts.

    The classifier inspects the *subject IRI* of each individual and applies
    lightweight heuristics:

    * Subject contains ``chunk_`` or starts with ``cd:``  → fact
    * Subject contains digits (excluding semantic-version strings) → fact
    * Otherwise → ontology concept (promoted to ``owl:Class``)
    """

    def __init__(self) -> None:
        self.chunk_pattern: re.Pattern[str] = _CHUNK_IRI_RE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_fact_triple(self, subject: str) -> bool:
        """Return ``True`` when *subject* looks like a concrete instance.

        Rules
        -----
        1. Contains ``chunk_`` substring  → fact
        2. Starts with ``cd:`` prefix     → fact
        3. Contains digits but is **not** a version string (``v1.2.3``)
           → fact
        4. Otherwise                       → ontology
        """
        if "chunk_" in subject or subject.startswith("cd:"):
            return True

        if any(c.isdigit() for c in subject):
            if not re.search(r"v\d+\.\d+\.\d+", subject):
                return True

        return False

    def separate_ontology_facts(
        self, extraction_data: dict[str, Any]
    ) -> SeparationResult:
        """Split *extraction_data* into ontology and facts.

        Parameters
        ----------
        extraction_data :
            A dictionary with any combination of the keys ``classes``,
            ``objectProperties``, ``datatypeProperties``, ``individuals``.

        Returns
        -------
        SeparationResult
            ``ontology`` always contains ``classes``, ``objectProperties``,
            and ``datatypeProperties``.  ``facts`` contains ``individuals``
            and, if present in the source, ``propertyValues`` /
            ``relations``.
        """
        ontology: dict[str, Any] = {
            "classes": dict(extraction_data.get("classes", {})),
            "objectProperties": dict(
                extraction_data.get("objectProperties", {})
            ),
            "datatypeProperties": dict(
                extraction_data.get("datatypeProperties", {})
            ),
        }

        facts_individuals: dict[str, Any] = {}
        facts_other: dict[str, Any] = {}

        # Carry over fact-level keys that are *not* schema keys.
        schema_keys = {"classes", "objectProperties", "datatypeProperties"}
        for key in extraction_data:
            if key not in schema_keys and key != "individuals":
                facts_other[key] = extraction_data[key]

        for ind_name, ind_def in extraction_data.get("individuals", {}).items():
            if self.is_fact_triple(ind_name):
                facts_individuals[ind_name] = ind_def
            else:
                # Generic concept individual → promote to class
                ontology["classes"][ind_name] = {
                    "comment": ind_def.get("label", ""),
                    "type": "owl:Class",
                }

        facts: dict[str, Any] = {"individuals": facts_individuals}
        facts.update(facts_other)

        return SeparationResult(ontology=ontology, facts=facts)

    def sublimate(
        self,
        merged_data: dict[str, Any],
        source_chunks: list[str] | None = None,
    ) -> SeparationResult:
        """Full sublimation pipeline.

        1. Call :meth:`separate_ontology_facts`.
        2. Attach ``metadata`` to each half.
        3. Compute summary statistics.

        Parameters
        ----------
        merged_data :
            The merged extraction dictionary.
        source_chunks :
            Optional list of chunk identifiers for provenance.

        Returns
        -------
        SeparationResult
            Enriched with ``metadata`` on both halves and ``statistics``.
        """
        result = self.separate_ontology_facts(merged_data)
        chunks = source_chunks or []

        result.ontology["metadata"] = {
            "type": "ontology",
            "source": "sublimated",
            "reusable": True,
            "chunks": chunks,
        }
        result.facts["metadata"] = {
            "type": "facts",
            "source": "sublimated",
            "reusable": False,
            "chunks": chunks,
        }

        result.statistics = {
            "ontology": {
                "classes": len(result.ontology.get("classes", {})),
                "objectProperties": len(
                    result.ontology.get("objectProperties", {})
                ),
                "datatypeProperties": len(
                    result.ontology.get("datatypeProperties", {})
                ),
            },
            "facts": {
                "individuals": len(result.facts.get("individuals", {})),
                "propertyValues": len(result.facts.get("propertyValues", {})),
                "relations": len(result.facts.get("relations", {})),
            },
        }

        return result
