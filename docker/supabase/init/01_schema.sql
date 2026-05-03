-- OntoFuel Database Schema
-- Auto-generated

CREATE TABLE IF NOT EXISTS materials (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "name" text NOT NULL UNIQUE,
  "chemical_formula" text,
  "material_type" text,
  "created_at" timestamptz DEFAULT now(),
  "updated_at" timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_materials_name ON materials("name");
CREATE INDEX IF NOT EXISTS idx_materials_material_type ON materials("material_type");

CREATE TABLE IF NOT EXISTS material_properties (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "material_id" uuid NOT NULL,
  "property_name" text NOT NULL,
  "property_value" float8,
  "value_string" text,
  "unit" text,
  "source" text,
  "temperature" float8,
  "temperature_unit" text DEFAULT 'K',
  "notes" text,
  FOREIGN KEY ("material_id") REFERENCES materials(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_material_properties_material_id ON material_properties("material_id");
CREATE INDEX IF NOT EXISTS idx_material_properties_property_name ON material_properties("property_name");

CREATE TABLE IF NOT EXISTS material_composition (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "material_id" uuid NOT NULL,
  "element" text NOT NULL,
  "weight_fraction" float8,
  "atomic_fraction" float8,
  FOREIGN KEY ("material_id") REFERENCES materials(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_material_composition_material_id ON material_composition("material_id");
CREATE INDEX IF NOT EXISTS idx_material_composition_element ON material_composition("element");

CREATE TABLE IF NOT EXISTS literature_sources (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "title" text NOT NULL,
  "authors" text[],
  "year" int4,
  "doi" text UNIQUE,
  "journal" text,
  "url" text
);
CREATE INDEX IF NOT EXISTS idx_literature_sources_year ON literature_sources("year");
CREATE INDEX IF NOT EXISTS idx_literature_sources_doi ON literature_sources("doi");

CREATE TABLE IF NOT EXISTS irradiation_behavior (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "material_id" uuid NOT NULL,
  "irradiation_type" text,
  "fluence" float8,
  "fluence_unit" text DEFAULT 'n/cm²',
  "temperature" float8,
  "property_changed" text,
  "change_percent" float8,
  FOREIGN KEY ("material_id") REFERENCES materials(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_irradiation_behavior_material_id ON irradiation_behavior("material_id");
CREATE INDEX IF NOT EXISTS idx_irradiation_behavior_irradiation_type ON irradiation_behavior("irradiation_type");

