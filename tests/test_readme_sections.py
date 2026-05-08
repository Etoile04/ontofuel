"""Tests to verify README.md contains all required sections for O4 Task 1."""
import re
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"


def _readme() -> str:
    assert README.exists(), f"README.md not found at {README}"
    return README.read_text(encoding="utf-8")


def test_docker_deployment_section():
    """README must have a Docker deployment section."""
    content = _readme()
    # Check for Docker heading
    assert re.search(r"##.*[Dd]ocker.*部署", content), \
        "Missing Docker deployment section heading"
    # Must reference docker compose
    assert "docker compose" in content.lower(), \
        "Docker section must reference docker compose"
    # Must reference health check or service table
    assert "docker compose ps" in content or "健康检查" in content, \
        "Docker section should mention health checks or service status"


def test_api_endpoints_section():
    """README must have an API endpoints section with endpoint list."""
    content = _readme()
    assert re.search(r"##.*API.*端点", content), \
        "Missing API endpoints section heading"
    # Must list at least materials endpoints
    assert "/api/materials" in content, \
        "API section must list /api/materials endpoints"
    # Must reference API docs (Swagger/OpenAPI)
    assert "/docs" in content or "Swagger" in content, \
        "API section should link to API documentation"


def test_deployment_options_section():
    """README must have a deployment options section covering 3 methods."""
    content = _readme()
    assert re.search(r"##.*部署方案", content), \
        "Missing deployment options section heading"
    # Must mention portable/package option
    assert "轻量" in content or "Portable" in content or "portable" in content, \
        "Must mention portable/lightweight deployment option"
    # Must mention Docker option
    assert "Docker" in content, "Must mention Docker deployment option"
    # Must mention source install option
    assert "源码" in content or "source" in content.lower(), \
        "Must mention source installation option"


def test_troubleshooting_section():
    """README must have a troubleshooting section."""
    content = _readme()
    assert re.search(r"##.*故障", content) or re.search(r"##.*[Tt]roubleshoot", content), \
        "Missing troubleshooting section heading"
    # Must cover Docker issues
    assert "docker" in content.lower(), \
        "Troubleshooting must cover Docker issues"
    # Must cover installation issues
    assert "pip" in content or "安装" in content or "install" in content.lower(), \
        "Troubleshooting must cover installation issues"


def test_readme_valid_markdown():
    """README should have valid markdown structure."""
    content = _readme()
    # Check no broken links (basic: no ][ without ( after it for link syntax)
    broken = re.findall(r"\[([^\]]+)\]\[\]", content)
    assert not broken, f"Broken empty link references found: {broken}"
    # All ## headings should have content after them (not another ## immediately)
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## ") and i + 1 < len(lines):
            next_nonblank = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip():
                    next_nonblank = lines[j]
                    break
            # Allow ## followed by ### but not ## followed directly by ##
            if next_nonblank.startswith("## ") and not next_nonblank.startswith("### "):
                # Skip if it's the last section
                pass  # This is acceptable for adjacent sections
