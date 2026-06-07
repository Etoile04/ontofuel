"""Tests for ontofuel.extraction.graph_update.

All fixtures are in-memory — no external files required.
"""

from __future__ import annotations

from ontofuel.extraction.graph_update import GraphUpdate, OntologyDiff

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _empty_onto() -> dict:
    return {"classes": {}, "objectProperties": {}, "datatypeProperties": {}, "individuals": {}}


def _base_onto() -> dict:
    return {
        "classes": {
            "Person": {"comment": "A human being"},
            "Organization": {},
        },
        "objectProperties": {
            "worksFor": {},
            "memberOf": {},
        },
        "datatypeProperties": {
            "name": {},
            "age": {},
        },
        "individuals": {
            "Alice": {"type": "Person"},
            "Acme": {"type": "Organization"},
        },
    }


# ===========================================================================
# GraphUpdate
# ===========================================================================


class TestGraphUpdate:
    # -- construction --------------------------------------------------------

    def test_default_operation_type_is_update(self) -> None:
        gu = GraphUpdate()
        assert gu.operation_type == "update"
        assert gu.operations == []
        assert gu.tokens_saved == 0

    def test_custom_operation_type(self) -> None:
        gu = GraphUpdate(operation_type="fresh")
        assert gu.operation_type == "fresh"

    # -- add_insert / add_delete --------------------------------------------

    def test_add_insert(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "rdf:type", "owl:Class")
        assert len(gu.operations) == 1
        assert gu.operations[0]["operation"] == "insert"
        assert gu.operations[0]["triple"] == ("ex:A", "rdf:type", "owl:Class")

    def test_add_delete(self) -> None:
        gu = GraphUpdate()
        gu.add_delete("ex:A", "rdf:type", "owl:Class")
        assert len(gu.operations) == 1
        assert gu.operations[0]["operation"] == "delete"

    def test_multiple_operations_preserve_order(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "p1", "o1")
        gu.add_delete("ex:B", "p2", "o2")
        gu.add_insert("ex:C", "p3", "o3")
        assert len(gu.operations) == 3
        assert gu.operations[0]["operation"] == "insert"
        assert gu.operations[1]["operation"] == "delete"
        assert gu.operations[2]["operation"] == "insert"

    # -- to_sparql -----------------------------------------------------------

    def test_to_sparql_empty(self) -> None:
        gu = GraphUpdate()
        assert gu.to_sparql() == ""

    def test_to_sparql_insert_only(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:Cat", "rdf:type", "owl:Class")
        sparql = gu.to_sparql()
        assert "INSERT DATA" in sparql
        assert '<ex:Cat> <rdf:type> "owl:Class" .' in sparql
        assert "DELETE" not in sparql

    def test_to_sparql_delete_only(self) -> None:
        gu = GraphUpdate()
        gu.add_delete("ex:Dog", "rdf:type", "owl:Class")
        sparql = gu.to_sparql()
        assert "DELETE DATA" in sparql
        assert '<ex:Dog> <rdf:type> "owl:Class" .' in sparql
        assert "INSERT" not in sparql

    def test_to_sparql_mixed(self) -> None:
        gu = GraphUpdate()
        gu.add_delete("ex:A", "rdf:type", "owl:Class")
        gu.add_insert("ex:B", "rdf:type", "owl:Class")
        sparql = gu.to_sparql()
        assert "DELETE DATA" in sparql
        assert "INSERT DATA" in sparql
        # semicolon between DELETE and INSERT
        assert ";" in sparql

    def test_to_sparql_formats_string_object(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "rdfs:comment", "a comment")
        assert '"a comment"' in gu.to_sparql()

    def test_to_sparql_formats_uri_object(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "rdf:type", "http://example.org/Thing")
        assert "<http://example.org/Thing>" in gu.to_sparql()

    def test_to_sparql_formats_int_object(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "ex:age", 25)
        assert '"25"^^<http://www.w3.org/2001/XMLSchema#int>' in gu.to_sparql()

    def test_to_sparql_formats_float_object(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "ex:score", 3.14)
        assert '"3.14"^^<http://www.w3.org/2001/XMLSchema#float>' in gu.to_sparql()

    # -- estimate_tokens -----------------------------------------------------

    def test_estimate_tokens_empty(self) -> None:
        assert GraphUpdate().estimate_tokens() == 0

    def test_estimate_tokens_nonzero(self) -> None:
        gu = GraphUpdate()
        gu.add_insert("ex:A", "p", "o")
        gu.add_insert("ex:B", "p", "o")
        assert gu.estimate_tokens() == 20


# ===========================================================================
# OntologyDiff
# ===========================================================================


class TestOntologyDiff:
    # -- compute_hash --------------------------------------------------------

    def test_compute_hash_deterministic(self) -> None:
        onto = {"classes": {"A": {}}}
        h1 = OntologyDiff.compute_hash(onto)
        h2 = OntologyDiff.compute_hash(onto)
        assert h1 == h2
        assert len(h1) == 16

    def test_compute_hash_differs_for_different_ontos(self) -> None:
        onto_a = {"classes": {"A": {}}}
        onto_b = {"classes": {"B": {}}}
        assert OntologyDiff.compute_hash(onto_a) != OntologyDiff.compute_hash(onto_b)

    def test_compute_hash_key_sorted(self) -> None:
        # Same content, different insertion order
        onto_a = {"classes": {"B": {}, "A": {}}}
        onto_b = {"classes": {"A": {}, "B": {}}}
        assert OntologyDiff.compute_hash(onto_a) == OntologyDiff.compute_hash(onto_b)

    # -- diff_ontologies ----------------------------------------------------

    def test_diff_identical_ontos_empty(self) -> None:
        onto = _base_onto()
        diff = OntologyDiff.diff_ontologies(onto, onto)
        assert len(diff.operations) == 0
        assert diff.to_sparql() == ""

    # -- new classes ---------------------------------------------------------

    def test_diff_new_class(self) -> None:
        old = _empty_onto()
        new: dict = {
            **_empty_onto(),
            "classes": {"Robot": {"comment": "A machine"}},
        }
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 2  # rdf:type + rdfs:comment
        ops = [op["triple"] for op in diff.operations]
        assert ("ex:Robot", "rdf:type", "owl:Class") in ops
        assert ("ex:Robot", "rdfs:comment", "A machine") in ops

    def test_diff_new_class_without_comment(self) -> None:
        old = _empty_onto()
        new: dict = {**_empty_onto(), "classes": {"Thing": {}}}
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1

    def test_diff_deleted_class(self) -> None:
        old: dict = {**_empty_onto(), "classes": {"Ghost": {}}}
        new = _empty_onto()
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["operation"] == "delete"

    # -- new individuals -----------------------------------------------------

    def test_diff_new_individual(self) -> None:
        old = _empty_onto()
        new: dict = {
            **_empty_onto(),
            "individuals": {"Bob": {"type": "Person"}},
        }
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["triple"] == ("ex:Bob", "rdf:type", "ex:Person")

    def test_diff_new_individual_default_type(self) -> None:
        old = _empty_onto()
        new: dict = {**_empty_onto(), "individuals": {"X": {}}}
        diff = OntologyDiff.diff_ontologies(old, new)
        # type defaults to "Individual"
        assert diff.operations[0]["triple"] == ("ex:X", "rdf:type", "ex:Individual")

    def test_diff_deleted_individual(self) -> None:
        old: dict = {**_empty_onto(), "individuals": {"OldOne": {"type": "Thing"}}}
        new = _empty_onto()
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        # Deleted individuals always use owl:NamedIndividual
        assert diff.operations[0]["triple"] == ("ex:OldOne", "rdf:type", "owl:NamedIndividual")

    # -- new object properties ----------------------------------------------

    def test_diff_new_object_property(self) -> None:
        old = _empty_onto()
        new: dict = {**_empty_onto(), "objectProperties": {"likes": {}}}
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["triple"] == ("ex:likes", "rdf:type", "owl:ObjectProperty")

    def test_diff_deleted_object_property(self) -> None:
        old: dict = {**_empty_onto(), "objectProperties": {"hates": {}}}
        new = _empty_onto()
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["operation"] == "delete"

    # -- new datatype properties (was MISSING in original PoC) ---------------

    def test_diff_new_datatype_property(self) -> None:
        old = _empty_onto()
        new: dict = {**_empty_onto(), "datatypeProperties": {"email": {}}}
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["triple"] == ("ex:email", "rdf:type", "owl:DatatypeProperty")

    def test_diff_deleted_datatype_property(self) -> None:
        old: dict = {**_empty_onto(), "datatypeProperties": {"phone": {}}}
        new = _empty_onto()
        diff = OntologyDiff.diff_ontologies(old, new)
        assert len(diff.operations) == 1
        assert diff.operations[0]["operation"] == "delete"

    # -- combined diff ------------------------------------------------------

    def test_diff_combined_changes(self) -> None:
        old = _base_onto()
        new = {
            "classes": {
                "Person": {"comment": "A human being"},
                "Organization": {},
                "Robot": {"comment": "A machine"},  # new
            },
            "objectProperties": {
                "worksFor": {},
                # "memberOf" removed
            },
            "datatypeProperties": {
                "name": {},
                "age": {},
                "email": {},  # new
            },
            "individuals": {
                "Alice": {"type": "Person"},
                "Acme": {"type": "Organization"},
                "Robo1": {"type": "Robot"},  # new
            },
        }
        diff = OntologyDiff.diff_ontologies(old, new)
        sparql = diff.to_sparql()

        # Should contain both DELETE and INSERT
        assert "DELETE DATA" in sparql
        assert "INSERT DATA" in sparql

        # Count: +Robot(2 ops) +email(1) +Robo1(1) -memberOf(1) = 5
        assert len(diff.operations) == 5

        # Verify specific triples
        triples = [op["triple"] for op in diff.operations]
        assert ("ex:Robot", "rdf:type", "owl:Class") in triples
        assert ("ex:email", "rdf:type", "owl:DatatypeProperty") in triples
        assert ("ex:Robo1", "rdf:type", "ex:Robot") in triples
        assert ("ex:memberOf", "rdf:type", "owl:ObjectProperty") in triples  # delete

    # -- estimate_tokens on diff ---------------------------------------------

    def test_diff_estimate_tokens(self) -> None:
        old = _empty_onto()
        new: dict = {**_empty_onto(), "classes": {"A": {}}}
        diff = OntologyDiff.diff_ontologies(old, new)
        assert diff.estimate_tokens() == 10  # 1 operation × 10
