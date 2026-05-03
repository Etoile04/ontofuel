"""OntoFuel FastAPI CRUD API — Task 2.

Provides REST endpoints for managing materials and their properties
in the OntoFuel PostgreSQL database.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="OntoFuel API", version="0.1.0")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@db:5432/postgres",
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
@contextmanager
def get_conn():
    """Yield a psycopg2 connection; commit on success, rollback on error."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class MaterialCreate(BaseModel):
    name: str
    chemical_formula: Optional[str] = None
    material_type: Optional[str] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    chemical_formula: Optional[str] = None
    material_type: Optional[str] = None


class PropertyCreate(BaseModel):
    material_id: str
    property_name: str
    property_value: Optional[float] = None
    value_string: Optional[str] = None
    unit: Optional[str] = None
    source: Optional[str] = None
    temperature: Optional[float] = None
    temperature_unit: str = "K"
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Materials CRUD
# ---------------------------------------------------------------------------
@app.get("/api/materials")
def list_materials(
    material_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if material_type:
                cur.execute(
                    "SELECT id, name, chemical_formula, material_type, created_at, updated_at "
                    "FROM materials WHERE material_type = %s ORDER BY name "
                    "LIMIT %s OFFSET %s",
                    (material_type, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT id, name, chemical_formula, material_type, created_at, updated_at "
                    "FROM materials ORDER BY name LIMIT %s OFFSET %s",
                    (limit, offset),
                )
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": str(r[0]),
                    "name": r[1],
                    "chemical_formula": r[2],
                    "material_type": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                    "updated_at": r[5].isoformat() if r[5] else None,
                })
            return results


@app.get("/api/materials/{material_id}")
def get_material(material_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, chemical_formula, material_type, created_at, updated_at "
                "FROM materials WHERE id = %s",
                (material_id,),
            )
            r = cur.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail="Material not found")
            return {
                "id": str(r[0]),
                "name": r[1],
                "chemical_formula": r[2],
                "material_type": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "updated_at": r[5].isoformat() if r[5] else None,
            }


@app.post("/api/materials", status_code=201)
def create_material(body: MaterialCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO materials (name, chemical_formula, material_type) "
                "VALUES (%s, %s, %s) "
                "RETURNING id, name, chemical_formula, material_type, created_at, updated_at",
                (body.name, body.chemical_formula, body.material_type),
            )
            r = cur.fetchone()
            return {
                "id": str(r[0]),
                "name": r[1],
                "chemical_formula": r[2],
                "material_type": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "updated_at": r[5].isoformat() if r[5] else None,
            }


@app.patch("/api/materials/{material_id}")
def update_material(material_id: str, body: MaterialUpdate):
    # Build dynamic SET clause from non-None fields
    updates: dict = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [material_id]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE materials SET {set_clause}, updated_at = now() "
                "WHERE id = %s "
                "RETURNING id, name, chemical_formula, material_type, created_at, updated_at",
                values,
            )
            r = cur.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail="Material not found")
            return {
                "id": str(r[0]),
                "name": r[1],
                "chemical_formula": r[2],
                "material_type": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "updated_at": r[5].isoformat() if r[5] else None,
            }


@app.delete("/api/materials/{material_id}")
def delete_material(material_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM materials WHERE id = %s RETURNING id",
                (material_id,),
            )
            r = cur.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail="Material not found")
            return {"deleted": str(r[0])}


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
@app.get("/api/materials/{material_id}/properties")
def list_properties(material_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify material exists
            cur.execute("SELECT id FROM materials WHERE id = %s", (material_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Material not found")
            cur.execute(
                "SELECT id, material_id, property_name, property_value, value_string, "
                "unit, source, temperature, temperature_unit, notes "
                "FROM material_properties WHERE material_id = %s ORDER BY property_name",
                (material_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "material_id": str(r[1]),
                    "property_name": r[2],
                    "property_value": r[3],
                    "value_string": r[4],
                    "unit": r[5],
                    "source": r[6],
                    "temperature": r[7],
                    "temperature_unit": r[8],
                    "notes": r[9],
                }
                for r in rows
            ]


@app.post("/api/materials/{material_id}/properties", status_code=201)
def create_property(material_id: str, body: PropertyCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify material exists
            cur.execute("SELECT id FROM materials WHERE id = %s", (material_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Material not found")
            cur.execute(
                "INSERT INTO material_properties "
                "(material_id, property_name, property_value, value_string, "
                "unit, source, temperature, temperature_unit, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id, material_id, property_name, property_value, value_string, "
                "unit, source, temperature, temperature_unit, notes",
                (
                    material_id,
                    body.property_name,
                    body.property_value,
                    body.value_string,
                    body.unit,
                    body.source,
                    body.temperature,
                    body.temperature_unit,
                    body.notes,
                ),
            )
            r = cur.fetchone()
            return {
                "id": str(r[0]),
                "material_id": str(r[1]),
                "property_name": r[2],
                "property_value": r[3],
                "value_string": r[4],
                "unit": r[5],
                "source": r[6],
                "temperature": r[7],
                "temperature_unit": r[8],
                "notes": r[9],
            }
