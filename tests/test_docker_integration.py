"""Integration tests for Docker fullstack deployment.
Requires Docker running — skipped if unavailable.
"""
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

import pytest

COMPOSE_FILE = pathlib.Path(__file__).parent.parent / "docker" / "docker-compose.yml"
API_URL = "http://localhost:8000"
WEB_URL = "http://localhost:3000"


def docker_available():
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not docker_available(), reason="Docker not available")


@pytest.fixture(scope="module", autouse=True)
def docker_stack():
    """Start and stop Docker stack."""
    env = os.environ.copy()
    # Build and start
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build"],
        env=env, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        pytest.skip(f"docker compose up failed: {result.stderr}")

    # Wait for API to be healthy (up to 120s)
    for _ in range(60):
        try:
            resp = urllib.request.urlopen(f"{API_URL}/health", timeout=2)
            if resp.status == 200:
                break
        except Exception:
            time.sleep(2)

    yield

    # Tear down
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"],
        env=env, capture_output=True, timeout=60,
    )


def test_api_health():
    resp = urllib.request.urlopen(f"{API_URL}/health", timeout=5)
    data = json.loads(resp.read())
    assert data["status"] == "ok"


def test_api_list_materials():
    resp = urllib.request.urlopen(f"{API_URL}/api/materials", timeout=5)
    data = json.loads(resp.read())
    assert "data" in data
    assert isinstance(data["data"], list)


def test_api_create_material():
    body = json.dumps({
        "name": "U-10Mo-integration-test",
        "chemical_formula": "U-10Mo",
        "material_type": "FuelMaterial",
    }).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 201
    created = json.loads(resp.read())
    assert "id" in created
    assert created["name"] == "U-10Mo-integration-test"

    # Verify we can GET it
    resp = urllib.request.urlopen(f"{API_URL}/api/materials/{created['id']}", timeout=5)
    mat = json.loads(resp.read())
    assert mat["name"] == "U-10Mo-integration-test"
    assert mat["material_type"] == "FuelMaterial"


def test_api_update_material():
    # Create
    body = json.dumps({"name": "update-test-material"}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    mat = json.loads(resp.read())

    # Update
    update = json.dumps({"chemical_formula": "UO2", "material_type": "CeramicMaterial"}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials/{mat['id']}",
        data=update, headers={"Content-Type": "application/json"}, method="PATCH",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 200

    # Verify
    resp = urllib.request.urlopen(f"{API_URL}/api/materials/{mat['id']}", timeout=5)
    updated = json.loads(resp.read())
    assert updated["chemical_formula"] == "UO2"
    assert updated["material_type"] == "CeramicMaterial"


def test_api_delete_material():
    # Create
    body = json.dumps({"name": "delete-test-material"}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    mat = json.loads(resp.read())

    # Delete
    req = urllib.request.Request(
        f"{API_URL}/api/materials/{mat['id']}", method="DELETE",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 200

    # Verify gone
    try:
        urllib.request.urlopen(f"{API_URL}/api/materials/{mat['id']}", timeout=5)
        assert False, "Should have raised 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_api_properties():
    # Create material
    body = json.dumps({"name": "props-test-material"}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    mat = json.loads(resp.read())

    # Add property
    prop = json.dumps({
        "material_id": mat["id"],
        "property_name": "density",
        "property_value": 19.1,
        "unit": "g/cm³",
    }).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/materials/{mat['id']}/properties",
        data=prop, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 201

    # List properties
    resp = urllib.request.urlopen(f"{API_URL}/api/materials/{mat['id']}/properties", timeout=5)
    data = json.loads(resp.read())
    assert len(data["data"]) >= 1
    found = [p for p in data["data"] if p["property_name"] == "density"]
    assert len(found) == 1
    assert found[0]["property_value"] == 19.1


def test_web_frontend_accessible():
    resp = urllib.request.urlopen(f"{WEB_URL}/", timeout=5)
    assert resp.status == 200
    content = resp.read().decode()
    assert "OntoFuel" in content or "materials" in content.lower()
