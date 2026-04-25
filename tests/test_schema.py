"""Tests for database schema module."""

import pytest

from ontofuel.database.schema import (
    TABLES,
    generate_all_sql,
    generate_create_sql,
    get_column_names,
    get_table_names,
    get_table,
)


class TestSchemaDefinitions:
    """Test schema structure."""

    def test_tables_defined(self):
        names = get_table_names()
        assert len(names) == 5
        assert "materials" in names
        assert "material_properties" in names
        assert "material_composition" in names
        assert "literature_sources" in names
        assert "irradiation_behavior" in names

    def test_get_table(self):
        mat = get_table("materials")
        assert mat is not None
        assert "columns" in mat
        assert "indexes" in mat

    def test_get_table_unknown(self):
        assert get_table("nonexistent") is None

    def test_columns_have_required_fields(self):
        for name in get_table_names():
            table = get_table(name)
            for col in table["columns"]:
                assert "name" in col, f"{name}.{col} missing 'name'"
                assert "type" in col, f"{name}.{col.get('name')} missing 'type'"

    def test_materials_has_name_column(self):
        cols = get_column_names("materials")
        assert "name" in cols
        assert "id" in cols

    def test_properties_has_material_id(self):
        cols = get_column_names("material_properties")
        assert "material_id" in cols
        assert "property_name" in cols
        assert "property_value" in cols


class TestSQLGeneration:
    """Test SQL generation."""

    def test_generate_create_sql_materials(self):
        sql = generate_create_sql("materials")
        assert "CREATE TABLE IF NOT EXISTS materials" in sql
        assert '"name"' in sql
        assert "PRIMARY KEY" in sql

    def test_generate_create_sql_with_references(self):
        sql = generate_create_sql("material_properties")
        assert "FOREIGN KEY" in sql
        assert "materials" in sql

    def test_generate_create_sql_unknown_table(self):
        with pytest.raises(ValueError, match="Unknown table"):
            generate_create_sql("nonexistent")

    def test_generate_create_sql_has_indexes(self):
        sql = generate_create_sql("materials")
        assert "CREATE INDEX" in sql

    def test_generate_all_sql(self):
        sql = generate_all_sql()
        assert "OntoFuel Database Schema" in sql
        for name in get_table_names():
            assert f"CREATE TABLE IF NOT EXISTS {name}" in sql

    def test_all_tables_have_primary_key(self):
        for name in get_table_names():
            table = get_table(name)
            pk_cols = [c for c in table["columns"] if c.get("primary")]
            assert len(pk_cols) == 1, f"{name} should have exactly one primary key"
