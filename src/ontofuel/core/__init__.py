"""Core ontology modules."""

from .ontology import load_ontology, get_default_ontology_path, get_stats
from .query import OntologyQuery
from .exporter import OntologyExporter
from .validator import OntologyValidator

__all__ = [
    "load_ontology",
    "get_default_ontology_path",
    "get_stats",
    "OntologyQuery",
    "OntologyExporter",
    "OntologyValidator",
]
