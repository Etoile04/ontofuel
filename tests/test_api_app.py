"""Tests for OntoFuel FastAPI CRUD API (Task 2).

These tests validate the API structure, models, and route definitions
without requiring a live database connection.
"""
import sys
import pytest

# Ensure docker/api is importable
sys.path.insert(0, "docker/api")


def test_api_app_importable():
    """FastAPI app should be importable."""
    from app import app
    assert app is not None
    assert app.title == "OntoFuel API"


def test_api_has_health_endpoint():
    """API should have /health endpoint."""
    from app import app
    routes = [r.path for r in app.routes]
    assert "/health" in routes


def test_api_has_materials_crud():
    """API should have full CRUD for materials."""
    from app import app
    routes = {}
    for r in app.routes:
        if hasattr(r, 'methods') and hasattr(r, 'path'):
            routes[r.path] = routes.get(r.path, set()) | r.methods
    assert "GET" in routes.get("/api/materials", set())
    assert "POST" in routes.get("/api/materials", set())
    assert "GET" in routes.get("/api/materials/{material_id}", set())
    assert ("PATCH" in routes.get("/api/materials/{material_id}", set()) or
            "PUT" in routes.get("/api/materials/{material_id}", set()))
    assert "DELETE" in routes.get("/api/materials/{material_id}", set())


def test_api_has_properties_endpoints():
    """API should have property endpoints."""
    from app import app
    routes = [r.path for r in app.routes]
    assert "/api/materials/{material_id}/properties" in routes


def test_models_exist():
    """Pydantic models should exist."""
    from app import MaterialCreate, MaterialUpdate, PropertyCreate
    m = MaterialCreate(name="test")
    assert m.name == "test"
