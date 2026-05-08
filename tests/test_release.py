# tests/test_release.py
import pathlib

def test_version_is_1_0_0():
    from ontofuel import __version__
    assert __version__ == "1.0.0"

def test_changelog_exists():
    p = pathlib.Path("CHANGELOG.md")
    assert p.exists()
