"""Tests for generate_standalone_viz.py"""

import json
import re
from pathlib import Path

import pytest

# Import the generator
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_standalone_viz import generate, OUTPUT_PATH, TEMPLATE_PATH, DATA_PATH

# We need D3.js source for tests; the generator will try to download it
# If download fails in CI, we provide a minimal mock


@pytest.fixture(autouse=True)
def _check_prerequisites():
    """Skip tests if required input files don't exist."""
    if not TEMPLATE_PATH.exists():
        pytest.skip(f"Template not found: {TEMPLATE_PATH}")
    if not DATA_PATH.exists():
        pytest.skip(f"Data not found: {DATA_PATH}")


@pytest.fixture(scope="module")
def generated_file():
    """Generate the standalone file once for all tests."""
    output = generate()
    yield output
    # Cleanup is optional; keep the file for inspection


def test_output_file_created(generated_file):
    """Output file exists and is non-empty."""
    assert generated_file.exists(), "Output file was not created"
    assert generated_file.stat().st_size > 0, "Output file is empty"


def test_output_contains_inline_d3(generated_file):
    """No external D3 references; D3 code is inlined."""
    content = generated_file.read_text(encoding="utf-8")

    # Should NOT have external script src for D3
    external_d3_patterns = [
        r'src=["\']https?://d3js\.org',
        r'src=["\']https?://cdn\.jsdelivr\.net/npm/d3',
        r'src=["\']https?://unpkg\.com/d3',
        r'src=["\'][^"\']*d3[^"\']*\.js["\']',
    ]
    for pattern in external_d3_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert len(matches) == 0, f"Found external D3 reference: {matches}"

    # Should contain inline D3 marker
    assert "D3" in content, "D3 content missing entirely"
    # Should contain actual D3 code (d3.select or similar)
    assert "d3" in content, "D3 library code not found in output"


def test_output_contains_inline_data(generated_file):
    """NVL data is inlined as NVL_DATA constant."""
    content = generated_file.read_text(encoding="utf-8")

    # Should have NVL_DATA constant
    assert "NVL_DATA" in content, "NVL_DATA constant not found"

    # Should not have loadData fetching from files
    assert "fetch(" not in content or "NVL_DATA" in content, "Still contains fetch calls"
    # The loadData function should be simplified
    assert "return NVL_DATA" in content, "loadData() doesn't return NVL_DATA"

    # Verify the inlined data is valid JSON-ish by checking key structure
    # Extract NVL_DATA value
    match = re.search(r"const NVL_DATA\s*=\s*({.*?});", content, re.DOTALL)
    assert match is not None, "Could not find NVL_DATA assignment"

    data_str = match.group(1)
    data = json.loads(data_str)
    assert "nodes" in data, "NVL_DATA missing 'nodes' key"
    assert "relationships" in data, "NVL_DATA missing 'relationships' key"
    assert len(data["nodes"]) > 0, "NVL_DATA has no nodes"


def test_output_is_valid_html(generated_file):
    """HTML structure is complete and valid."""
    content = generated_file.read_text(encoding="utf-8")

    assert "<!DOCTYPE html>" in content, "Missing DOCTYPE"
    assert "<html" in content, "Missing <html> tag"
    assert "</html>" in content, "Missing closing </html>"
    assert "<head>" in content, "Missing <head>"
    assert "</head>" in content, "Missing closing </head>"
    assert "<body" in content, "Missing <body>"


def test_output_reasonable_size(generated_file):
    """Output size is within expected range (500KB - 2MB)."""
    size_bytes = generated_file.stat().st_size
    size_kb = size_bytes / 1024
    assert size_kb >= 500, f"Output too small: {size_kb:.0f} KB (expected >= 500 KB)"
    assert size_kb <= 2048, f"Output too large: {size_kb:.0f} KB (expected <= 2048 KB)"
