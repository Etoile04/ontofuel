"""Tests for ontofuel.extraction.sublimation."""

from __future__ import annotations

from ontofuel.extraction.sublimation import OntologySublimator, SeparationResult

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_extraction(
    *,
    classes: dict | None = None,
    object_properties: dict | None = None,
    datatype_properties: dict | None = None,
    individuals: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """Build a realistic extraction-data dict in memory."""
    data: dict = {}
    if classes is not None:
        data["classes"] = classes
    if object_properties is not None:
        data["objectProperties"] = object_properties
    if datatype_properties is not None:
        data["datatypeProperties"] = datatype_properties
    if individuals is not None:
        data["individuals"] = individuals
    if extra is not None:
        data.update(extra)
    return data


def _standard_extraction() -> dict:
    """Full extraction payload with all keys."""
    return _make_extraction(
        classes={
            "Sensor": {"label": "传感器", "subClassOf": "Device"},
            "Device": {"label": "设备"},
        },
        object_properties={
            "hasComponent": {
                "label": "包含组件",
                "domain": "Device",
                "range": "Sensor",
            }
        },
        datatype_properties={
            "hasSerialNumber": {
                "label": "序列号",
                "domain": "Device",
                "range": "xsd:string",
            }
        },
        individuals={
            "Sensor": {"label": "传感器概念"},  # no chunk prefix → ontology
            "chunk_42_TemperatureSensor": {"label": "温度传感器实例42"},
            "cd:sensor_001": {"label": "传感器001"},
            "EngineRoom2": {"label": "2号机舱"},  # has digit → fact
        },
        extra={
            "propertyValues": {"chunk_42_TemperatureSensor": {"hasSerialNumber": "SN-001"}},
            "relations": {"chunk_42_TemperatureSensor": {"hasComponent": "EngineRoom2"}},
        },
    )


# ------------------------------------------------------------------
# OntologySublimator.is_fact_triple
# ------------------------------------------------------------------


class TestIsFactTriple:
    def setup_method(self) -> None:
        self.sub = OntologySublimator()

    def test_chunk_prefix(self) -> None:
        assert self.sub.is_fact_triple("chunk_42_Sensor") is True
        assert self.sub.is_fact_triple("chunk_0") is True

    def test_cd_prefix(self) -> None:
        assert self.sub.is_fact_triple("cd:sensor_001") is True
        assert self.sub.is_fact_triple("cd:anything") is True

    def test_contains_digits(self) -> None:
        assert self.sub.is_fact_triple("EngineRoom2") is True
        assert self.sub.is_fact_triple("Sensor_v3") is True  # digit, not semver

    def test_version_string_excluded(self) -> None:
        assert self.sub.is_fact_triple("Protocol_v1.2.3") is False
        assert self.sub.is_fact_triple("API_v10.0.0") is False

    def test_plain_text_is_ontology(self) -> None:
        assert self.sub.is_fact_triple("Sensor") is False
        assert self.sub.is_fact_triple("Device") is False
        assert self.sub.is_fact_triple("hasComponent") is False


# ------------------------------------------------------------------
# OntologySublimator.separate_ontology_facts
# ------------------------------------------------------------------


class TestSeparateOntologyFacts:
    def setup_method(self) -> None:
        self.sub = OntologySublimator()

    def test_standard_structure(self) -> None:
        data = _standard_extraction()
        result = self.sub.separate_ontology_facts(data)

        # Ontology
        assert "Sensor" in result.ontology["classes"]
        assert "Device" in result.ontology["classes"]
        # "Sensor" individual (plain text) gets promoted to class
        assert "Sensor" in result.ontology["classes"]
        assert len(result.ontology["objectProperties"]) == 1
        assert len(result.ontology["datatypeProperties"]) == 1

        # Facts
        assert "chunk_42_TemperatureSensor" in result.facts["individuals"]
        assert "cd:sensor_001" in result.facts["individuals"]
        assert "EngineRoom2" in result.facts["individuals"]
        # propertyValues and relations carried over
        assert "propertyValues" in result.facts
        assert "relations" in result.facts

    def test_schema_keys_only_go_to_ontology(self) -> None:
        data = _make_extraction(
            classes={"A": {}},
            object_properties={"p": {}},
            datatype_properties={"q": {}},
        )
        result = self.sub.separate_ontology_facts(data)
        assert result.ontology["classes"] == {"A": {}}
        assert result.ontology["objectProperties"] == {"p": {}}
        assert result.ontology["datatypeProperties"] == {"q": {}}
        assert result.facts["individuals"] == {}

    def test_individuals_split(self) -> None:
        data = _make_extraction(
            individuals={
                "Plain": {"label": "x"},
                "chunk_1_X": {"label": "y"},
            }
        )
        result = self.sub.separate_ontology_facts(data)
        # Plain promoted to class
        assert "Plain" in result.ontology["classes"]
        assert "Plain" not in result.facts["individuals"]
        # chunk individual stays in facts
        assert "chunk_1_X" in result.facts["individuals"]

    def test_return_type(self) -> None:
        result = self.sub.separate_ontology_facts({})
        assert isinstance(result, SeparationResult)


# ------------------------------------------------------------------
# OntologySublimator.sublimate  (full pipeline)
# ------------------------------------------------------------------


class TestSublimate:
    def setup_method(self) -> None:
        self.sub = OntologySublimator()

    def test_full_pipeline(self) -> None:
        data = _standard_extraction()
        result = self.sub.sublimate(data, source_chunks=["chunk_42", "chunk_7"])

        # Structure
        assert isinstance(result, SeparationResult)
        assert result.ontology["metadata"]["type"] == "ontology"
        assert result.facts["metadata"]["type"] == "facts"
        assert result.ontology["metadata"]["reusable"] is True
        assert result.facts["metadata"]["reusable"] is False
        assert result.ontology["metadata"]["chunks"] == ["chunk_42", "chunk_7"]

        # Stats
        stats = result.statistics
        assert stats["ontology"]["classes"] >= 2  # Sensor + Device + promoted
        assert stats["ontology"]["objectProperties"] == 1
        assert stats["facts"]["individuals"] == 3

    def test_no_source_chunks(self) -> None:
        result = self.sub.sublimate({"classes": {"A": {}}})
        assert result.ontology["metadata"]["chunks"] == []

    def test_empty_input(self) -> None:
        result = self.sub.sublimate({})
        assert result.ontology["classes"] == {}
        assert result.ontology["objectProperties"] == {}
        assert result.ontology["datatypeProperties"] == {}
        assert result.facts["individuals"] == {}
        assert result.statistics["ontology"]["classes"] == 0
        assert result.statistics["facts"]["individuals"] == 0

    def test_only_classes(self) -> None:
        data = _make_extraction(classes={"Sensor": {"label": "传感器"}})
        result = self.sub.sublimate(data)
        assert result.ontology["classes"] == {"Sensor": {"label": "传感器"}}
        assert result.facts["individuals"] == {}

    def test_only_individuals(self) -> None:
        data = _make_extraction(
            individuals={
                "chunk_5_X": {"label": "x"},
                "Plain": {"label": "y"},
            }
        )
        result = self.sub.sublimate(data)
        assert "chunk_5_X" in result.facts["individuals"]
        assert "Plain" in result.ontology["classes"]  # promoted
        assert result.facts["individuals"].get("Plain") is None
