import pathlib
import yaml


def test_test_workflow_exists():
    assert pathlib.Path(".github/workflows/test.yml").exists()


def test_test_workflow_runs_pytest():
    content = pathlib.Path(".github/workflows/test.yml").read_text()
    assert "pytest" in content


def test_test_workflow_valid_yaml():
    with open(".github/workflows/test.yml") as f:
        data = yaml.safe_load(f)
    assert "jobs" in data
    assert "test" in data["jobs"]
