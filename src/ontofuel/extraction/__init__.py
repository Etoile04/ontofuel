"""Extraction module — ontology extraction from documents.

Pipeline:
  PDF → Markdown → Segments → Extract → Merge → Update Ontology

Core classes:
  - Segmenter: Split markdown into sections/chunks
  - Extractor: Extract structured knowledge from text
  - Merger: Merge extraction results with deduplication
  - Updater: Incrementally update the ontology
"""

from .segmenter import Segmenter
from .extractor import Extractor, ExtractionResult
from .merger import Merger
from .updater import OntologyUpdater

__all__ = [
    "Segmenter",
    "Extractor",
    "ExtractionResult",
    "Merger",
    "OntologyUpdater",
]
