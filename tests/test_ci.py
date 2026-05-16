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


# --- Docker Image CI workflow tests ---


def test_docker_image_workflow_exists():
    assert pathlib.Path(".github/workflows/docker-image.yml").exists()


def test_docker_image_workflow_valid_yaml():
    with open(".github/workflows/docker-image.yml") as f:
        data = yaml.safe_load(f)
    assert "jobs" in data
    assert "api-image" in data["jobs"]
    assert "web-image" in data["jobs"]


def test_docker_image_workflow_triggers():
    with open(".github/workflows/docker-image.yml") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)  # YAML parses 'on' as boolean True
    # push to main/ontofuel-v0.1 and tags
    assert "push" in on
    push_branches = on["push"]["branches"]
    assert "ontofuel-v0.1" in push_branches
    assert "v*" in on["push"]["tags"]
    # pull_request
    assert "pull_request" in on


def test_docker_image_workflow_uses_buildx():
    content = pathlib.Path(".github/workflows/docker-image.yml").read_text()
    assert "docker/setup-buildx-action" in content
    assert "docker/build-push-action" in content
    assert "docker/login-action" in content


def test_docker_image_workflow_api_steps():
    with open(".github/workflows/docker-image.yml") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["api-image"]["steps"]
    step_names = [s.get("name", "") for s in steps]
    assert any("Build and push API" in n for n in step_names)
    # Check Dockerfile path
    push_step = [s for s in steps if "Build and push" in s.get("name", "")][0]
    assert push_step["with"]["file"] == "./docker/api/Dockerfile"
    assert "push" in push_step["with"] and push_step["with"]["push"] is True


def test_docker_image_workflow_web_steps():
    with open(".github/workflows/docker-image.yml") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["web-image"]["steps"]
    step_names = [s.get("name", "") for s in steps]
    assert any("Build and push Web" in n for n in step_names)
    push_step = [s for s in steps if "Build and push" in s.get("name", "")][0]
    assert push_step["with"]["file"] == "./docker/web/Dockerfile"


def test_docker_image_workflow_cache():
    content = pathlib.Path(".github/workflows/docker-image.yml").read_text()
    assert "cache-from: type=gha" in content
    assert "cache-to: type=gha,mode=max" in content


def test_docker_image_workflow_tags():
    with open(".github/workflows/docker-image.yml") as f:
        data = yaml.safe_load(f)
    # API tags
    api_steps = data["jobs"]["api-image"]["steps"]
    api_push = [s for s in api_steps if "Build and push" in s.get("name", "")][0]
    api_tags = api_push["with"]["tags"]
    assert "ontofuel/api:latest" in api_tags
    # Web tags
    web_steps = data["jobs"]["web-image"]["steps"]
    web_push = [s for s in web_steps if "Build and push" in s.get("name", "")][0]
    web_tags = web_push["with"]["tags"]
    assert "ontofuel/web:latest" in web_tags


def test_test_workflow_has_codecov():
    content = pathlib.Path(".github/workflows/test.yml").read_text()
    assert "codecov" in content
    assert "matrix.python-version == '3.12'" in content
