"""Tests for elastic constant ontology extensions (C11/C12/C44/C33)."""

import json
from pathlib import Path


def _get_ontology():
    """Load the main ontology JSON directly for class/property checks."""
    from ontofuel.core.ontology import get_default_ontology_path

    with open(get_default_ontology_path(), encoding="utf-8") as f:
        return json.load(f)


def _class_names(ontology):
    """Get set of class names from ontology."""
    classes = ontology.get("classes", {})
    if isinstance(classes, dict):
        return set(classes.keys())
    return {c.get("name", "") for c in classes}


def _dp_names(ontology):
    """Get set of datatype property names."""
    dp = ontology.get("datatypeProperties", {})
    if isinstance(dp, dict):
        return set(dp.keys())
    return {p.get("name", "") for p in dp}


class TestElasticConstantClasses:
    def test_elastic_constant_class_exists(self):
        ont = _get_ontology()
        names = _class_names(ont)
        assert "ElasticConstant" in names

    def test_elastic_constant_parent_is_mechanical(self):
        ont = _get_ontology()
        ec = ont["classes"]["ElasticConstant"]
        assert ec.get("parent") == "MechanicalProperty"

    def test_c11_subclass_exists(self):
        ont = _get_ontology()
        names = _class_names(ont)
        assert "ElasticConstantC11" in names

    def test_c12_subclass_exists(self):
        ont = _get_ontology()
        names = _class_names(ont)
        assert "ElasticConstantC12" in names

    def test_c44_subclass_exists(self):
        ont = _get_ontology()
        names = _class_names(ont)
        assert "ElasticConstantC44" in names

    def test_c33_subclass_exists(self):
        ont = _get_ontology()
        names = _class_names(ont)
        assert "ElasticConstantC33" in names

    def test_subclasses_parent_is_elastic_constant(self):
        ont = _get_ontology()
        for name in [
            "ElasticConstantC11",
            "ElasticConstantC12",
            "ElasticConstantC44",
            "ElasticConstantC33",
        ]:
            assert ont["classes"][name].get("parent") == "ElasticConstant", (
                f"{name} parent mismatch"
            )


class TestElasticConstantDatatypeProperties:
    def test_elastic_constant_c11_property_exists(self):
        ont = _get_ontology()
        names = _dp_names(ont)
        assert "elasticConstantC11" in names

    def test_elastic_constant_c12_property_exists(self):
        ont = _get_ontology()
        names = _dp_names(ont)
        assert "elasticConstantC12" in names

    def test_elastic_constant_c44_property_exists(self):
        ont = _get_ontology()
        names = _dp_names(ont)
        assert "elasticConstantC44" in names

    def test_elastic_constant_c33_property_exists(self):
        ont = _get_ontology()
        names = _dp_names(ont)
        assert "elasticConstantC33" in names

    def test_properties_are_functional_decimal(self):
        ont = _get_ontology()
        for name in [
            "elasticConstantC11",
            "elasticConstantC12",
            "elasticConstantC44",
            "elasticConstantC33",
        ]:
            prop = ont["datatypeProperties"][name]
            assert prop.get("owl:functionalProperty") is True, f"{name} not functional"
            assert prop.get("rdfs:range") == "xsd:decimal", f"{name} range mismatch"


class TestAdapterElasticConstants:
    """Verify adapter_ontology maps C11/C12/C44/C33 via property-mapping.json."""

    def test_adapter_maps_c11(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "workspace" / "scripts"))
        from adapter_ontology import _load_ontofuel_key_map

        key_map = _load_ontofuel_key_map()
        assert "hasElasticConstantC11" in key_map
        assert key_map["hasElasticConstantC11"]["ref_property"] == "C11"

    def test_adapter_maps_c12(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "workspace" / "scripts"))
        from adapter_ontology import _load_ontofuel_key_map

        key_map = _load_ontofuel_key_map()
        assert "hasElasticConstantC12" in key_map
        assert key_map["hasElasticConstantC12"]["ref_property"] == "C12"

    def test_adapter_maps_c44(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "workspace" / "scripts"))
        from adapter_ontology import _load_ontofuel_key_map

        key_map = _load_ontofuel_key_map()
        assert "hasElasticConstantC44" in key_map

    def test_adapter_maps_c33(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "workspace" / "scripts"))
        from adapter_ontology import _load_ontofuel_key_map

        key_map = _load_ontofuel_key_map()
        assert "hasElasticConstantC33" in key_map

    def test_adapter_adapts_c11_individual(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "workspace" / "scripts"))
        from adapter_ontology import adapt_ontology_individual

        individual = {
            "class": "Uranium",
            "properties": {
                "hasElasticConstantC11": {"value": 206.0, "unit": "GPa"},
            },
            "source": "test",
        }
        results = adapt_ontology_individual(individual)
        assert results is not None
        assert len(results) == 1
        assert results[0]["property"] == "C11"
        assert results[0]["value"] == 206.0
