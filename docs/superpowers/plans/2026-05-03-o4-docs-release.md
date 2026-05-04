# O4: 文档与开源发布 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** 完成文档 + CI/CD + v1.0 Release，实现 O4 OKR 目标。

**Architecture:**
- KR 4.1: 扩展 README + 新增 API docs + User Manual + Deployment Guide
- KR 4.2: GitHub Actions CI/CD（自动测试 + Docker 镜像自动构建）
- KR 4.3: v1.0.0 tag + GitHub Release + Docker Hub 镜像

**Tech Stack:** GitHub Actions, Docker Hub, Sphinx/API docs, Markdown

---

## File Structure

```
.github/workflows/
├── test.yml               # 自动测试 CI
├── docker-image.yml       # Docker 镜像自动构建
└── publish.yml            # 自动发布（v1.0.0 tag 触发）

docs/
├── api/                   # API 文档 (Sphinx)
│   ├── conf.py
│   ├── index.rst
│   └── api_reference.rst
├── user_manual.md         # 用户手册
└── deployment.md          # 部署指南

README.md                   # 扩展主 README
CONTRIBUTING.md             # 贡献指南
LICENSE                     # 已存在（MIT）
```

---

## Task 1: 扩展 README.md

**Files:**
- Modify: `README.md`

**Dependencies:** 无

- [ ] **Step 1: Read current README.md and identify gaps**

- [ ] **Step 2: Add sections:**
  - Docker 部署章节（引用 O3）
  - API 端点列表（链接到 API docs）
  - 部署选项（便携包 vs Docker vs 源码）
  - 故障排查

- [ ] **Step 3: Verify markdown syntax**

- [ ] **Step 4: Commit**

---

## Task 2: API 文档 (Sphinx)

**Files:**
- Create: `docs/api/conf.py`
- Create: `docs/api/index.rst`
- Create: `docs/api/api_reference.rst`
- Create: `docs/Makefile`
- Create: `docs/api/.gitignore`
- Modify: `pyproject.toml` (add sphinx dependencies)

**Dependencies:** 无

- [ ] **Step 1: Write failing test for API docs build**

```python
# tests/test_api_docs.py
import subprocess
import pathlib

def test_api_docs_build():
    """API docs should build without errors."""
    result = subprocess.run(
        ["make", "html"],
        cwd="docs/api",
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"make html failed: {result.stderr}"
    assert (pathlib.Path("docs/api/_build/html/index.html").exists())

def test_api_docs_index_exists():
    """API docs index should exist."""
    assert pathlib.Path("docs/api/index.rst").exists()
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create conf.py**

```python
# docs/api/conf.py
project = "OntoFuel API"
author = "OntoFuel Contributors"
copyright = "2026, OntoFuel"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
}
```

- [ ] **Step 4: Create index.rst**

```rst
.. OntoFuel API Documentation

Welcome to the OntoFuel API Reference.

.. toctree::
   :maxdepth: 2

   api_reference
```

- [ ] **Step 5: Create api_reference.rst**

```rst
API Reference
=============

CLI
---

.. automodule:: ontofuel.cli
   :members:

Core Module
------------

.. automodule:: ontofuel.core.ontology
   :members: load_ontology, get_stats
.. automodule:: ontofuel.core.query
   :members: OntologyQuery
.. automodule:: ontofuel.core.exporter
   :members: OntologyExporter

Database Module
----------------

.. automodule:: ontofuel.database.client
   :members: SupabaseClient
.. automodule:: ontofuel.database.restore
   :members: DataRestorer

Extraction Module
------------------

.. automodule:: ontofuel.extraction.extractor
   :members: Extractor
```

- [ ] **Step 6: Create Makefile (Sphinx standard)**

```makefile
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = OntoFuelAPI
SOURCEDIR     = .
BUILDDIR      = _build

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

.PHONY: help Makefile
```

- [ ] **Step 7: Create .gitignore**

```
_build/
*.pyc
__pycache__/
```

- [ ] **Step 8: Add sphinx dependencies to pyproject.toml**

```toml
[project.optional-dependencies]
docs = ["sphinx>=7.0", "sphinx-rtd-theme>=2.0"]
```

- [ ] **Step 9: Install docs deps**

```bash
pip install -e ".[docs]"
```

- [ ] **Step 10: Run tests — should PASS**

- [ ] **Step 11: Commit**

---

## Task 3: User Manual

**Files:**
- Create: `docs/user_manual.md`

**Dependencies:** Task 1 (README reference)

- [ ] **Step 1: Write failing test for user manual existence**

```python
# tests/test_docs.py
import pathlib

def test_user_manual_exists():
    p = pathlib.Path("docs/user_manual.md")
    assert p.exists()

def test_user_manual_has_sections():
    content = pathlib.Path("docs/user_manual.md").read_text()
    assert "安装" in content or "Install" in content
    assert "快速开始" in content or "Quick Start" in content
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create user_manual.md**

包含章节：
1. 安装（源码、便携包、Docker）
2. 快速开始（5 分钟上手）
3. CLI 命令详解
4. 常用场景（本体查询、数据提取、可视化）
5. 故障排查

- [ ] **Step 4: Run tests — should PASS**

- [ ] **Step 5: Commit**

---

## Task 4: Deployment Guide

**Files:**
- Create: `docs/deployment.md`

**Dependencies:** Task 1, Task 3

- [ ] **Step 1: Write failing test**

```python
# tests/test_docs.py (append)

def test_deployment_guide_exists():
    p = pathlib.Path("docs/deployment.md")
    assert p.exists()

def test_deployment_guide_covers_docker():
    content = pathlib.Path("docs/deployment.md").read_text()
    assert "Docker" in content or "docker" in content.lower()
    assert "docker compose" in content.lower()
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create deployment.md**

包含章节：
1. Docker 部署（详细步骤）
2. 数据库配置（Supabase）
3. 环境变量说明
4. 生产环境注意事项
5. 备份与恢复

- [ ] **Step 4: Run tests — should PASS**

- [ ] **Step 5: Commit**

---

## Task 5: GitHub Actions CI (测试)

**Files:**
- Create: `.github/workflows/test.yml`

**Dependencies:** 无

- [ ] **Step 1: Write failing test for workflow existence**

```python
# tests/test_ci.py
import pathlib

def test_test_workflow_exists():
    p = pathlib.Path(".github/workflows/test.yml")
    assert p.exists()

def test_test_workflow_runs_pytest():
    content = pathlib.Path(".github/workflows/test.yml").read_text()
    assert "pytest" in content
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create test.yml**

```yaml
name: Tests

on:
  push:
    branches: [main, ontofuel-v0.1, "feature/*"]
  pull_request:
    branches: [main, ontofuel-v0.1]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    - name: Run tests
      run: pytest tests/ -v --tb=short
    - name: Upload coverage
      uses: codecov/codecov-action@v4
      if: matrix.python-version == '3.12'
```

- [ ] **Step 4: Validate YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"
```

- [ ] **Step 5: Run tests — should PASS**

- [ ] **Step 6: Commit**

---

## Task 6: GitHub Actions CI (Docker 镜像)

**Files:**
- Create: `.github/workflows/docker-image.yml`

**Dependencies:** Task 5 (workflow structure)

- [ ] **Step 1: Write failing test**

```python
# tests/test_ci.py (append)

def test_docker_workflow_exists():
    p = pathlib.Path(".github/workflows/docker-image.yml")
    assert p.exists()

def test_docker_workflow_builds_image():
    content = pathlib.Path(".github/workflows/docker-image.yml").read_text()
    assert "docker/build-push-action" in content
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create docker-image.yml**

```yaml
name: Docker Image

on:
  push:
    branches: [ontofuel-v0.1]
    tags: ["v*"]
  pull_request:
    branches: [ontofuel-v0.1]

jobs:
  api-image:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Log in to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    - name: Build and push API image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/api/Dockerfile
        push: true
        tags: ontofuel/api:latest,ontofuel/api:${{ github.ref_name }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  web-image:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Log in to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    - name: Build and push Web image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/web/Dockerfile
        push: true
        tags: ontofuel/web:latest,ontofuel/web:${{ github.ref_name }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

- [ ] **Step 4: Validate YAML**

- [ ] **Step 5: Run tests — should PASS**

- [ ] **Step 6: Commit**

---

## Task 7: Contributing Guide

**Files:**
- Create: `CONTRIBUTING.md`

**Dependencies:** Task 5 (CI reference)

- [ ] **Step 1: Write failing test**

```python
# tests/test_docs.py (append)

def test_contributing_exists():
    p = pathlib.Path("CONTRIBUTING.md")
    assert p.exists()

def test_contributing_mentions_tests():
    content = pathlib.Path("CONTRIBUTING.md").read_text()
    assert "test" in content.lower()
    assert "pytest" in content
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Create CONTRIBUTING.md**

包含：
1. 开发环境设置
2. 测试要求
3. 提交规范
4. PR 流程
5. Superpowers 工作流

- [ ] **Step 4: Run tests — should PASS**

- [ ] **Step 5: Commit**

---

## Task 8: v1.0.0 Release 准备

**Files:**
- Modify: `src/ontofuel/__init__.py` (version bump)
- Create: `CHANGELOG.md`

**Dependencies:** Task 1-7 全部完成

- [ ] **Step 1: Write failing test for version**

```python
# tests/test_release.py
import pathlib

def test_version_is_1_0_0():
    from ontofuel import __version__
    assert __version__ == "1.0.0"

def test_changelog_exists():
    p = pathlib.Path("CHANGELOG.md")
    assert p.exists()
```

- [ ] **Step 2: Run tests — should FAIL**

- [ ] **Step 3: Bump version in `src/ontofuel/__init__.py`**

```python
__version__ = "1.0.0"
```

- [ ] **Step 4: Create CHANGELOG.md**

```markdown
# Changelog

## [1.0.0] - 2026-05-03

### Added
- Docker 全栈部署（docker-compose.yml, API, Web 界面）
- FastAPI CRUD API（8 端点）
- 管理界面（单页 HTML/JS/CSS）
- 自动恢复脚本（restore.sh）
- API 文档（Sphinx）
- 用户手册
- 部署指南
- 贡献指南
- GitHub Actions CI/CD

### Changed
- 测试覆盖率提升到 >80%

### Fixed
- Docker 代码评审问题（healthcheck, 持久化, CASCADE, unique constraints）
```

- [ ] **Step 5: Run tests — should PASS**

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: prepare for v1.0.0 release"
```

---

## Task 9: Tag + GitHub Release

**Dependencies:** Task 8 (v1.0.0 prep)

- [ ] **Step 1: Create tag**

```bash
git tag -a v1.0.0 -m "v1.0.0 — First stable release"
```

- [ ] **Step 2: Push tag**

```bash
git push origin v1.0.0
```

- [ ] **Step 3: Create GitHub Release via gh CLI**

```bash
gh release create v1.0.0 \
  --title "v1.0.0 — First Stable Release" \
  --notes "Full-featured OntoFuel release with Docker deployment, API, and web management interface."
```

- [ ] **Step 4: Verify release**

```bash
gh release view v1.0.0
```

- [ ] **Step 5: Merge ontofuel-v0.1 into main (if needed)**

```bash
git checkout main
git merge ontofuel-v0.1
git push origin main
```

---

## Self-Review Checklist

- Each KR mapped to tasks? ✅
  - KR 4.1 → Tasks 1, 2, 3, 4, 7
  - KR 4.2 → Tasks 5, 6
  - KR 4.3 → Tasks 8, 9
- No placeholders? ✅
- TDD for each task? ✅
- Dependencies correct? ✅

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-o4-docs-release.md`.**

**Recommended: Subagent-Driven Development** — 9 个任务，两阶段评审确保质量。
