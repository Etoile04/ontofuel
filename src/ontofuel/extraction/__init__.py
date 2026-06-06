"""Extraction module — ontology extraction from documents.

Pipeline:
  PDF → Markdown → Segments → Extract → Merge → Update Ontology

Core classes:
  - Segmenter: Split markdown into sections/chunks
  - Extractor: Extract structured knowledge from text
  - Merger: Merge extraction results with deduplication
  - Updater: Incrementally update the ontology
"""

from .extractor import ExtractionResult, Extractor
from .graph_update import GraphUpdate, OntologyDiff
from .merger import Merger
from .segmenter import Segmenter
from .sublimation import OntologySublimator, SeparationResult
from .updater import OntologyUpdater
from .versioning import OntologyVersionControl, OntologyVersion
from .critic import OntologyCritic, OntologyCritiqueReport, CritiqueSeverity, Suggestion

__all__ = [
    "Segmenter",
    "Extractor",
    "ExtractionResult",
    "Merger",
    "OntologyUpdater",
    "GraphUpdate",
    "OntologyDiff",
    "OntologySublimator",
    "SeparationResult",
    "OntologyVersionControl",
    "OntologyVersion",
    "OntologyCritic",
    "OntologyCritiqueReport",
    "CritiqueSeverity",
    "Suggestion",
]
