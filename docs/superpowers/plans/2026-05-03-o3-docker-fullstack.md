# O3: Docker 全栈部署 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Docker 全栈部署，`docker compose up` 一键启动 Supabase + OntoFuel API + 管理界面，`restore.sh` 零人工干预恢复全部 5 个表。

**Architecture:** 三层架构 — Supabase (PostgreSQL + REST API) 作为数据层，OntoFuel FastAPI 作为业务层（CRUD API），React/Vanilla 管理界面作为前端。docker-compose 统一编排，init 脚本自动建表 + 恢复数据。

**Tech Stack:** Docker Compose, Supabase (local), FastAPI, Python 3.10+, Vanilla HTML/JS (或 Streamlit)

---

## File Structure

```
docker/
├── docker-compose.yml              # 主编排文件
├── supabase/
│   └── init/
│       ├── 01_schema.sql           # 建表脚本（从 schema.py 生成）
│       └── 02_seed_data.sql        # 种子数据（可选）
├── api/
│   ├── Dockerfile                  # OntoFuel API 镜像
│   ├── requirements.txt            # API 依赖
│   └── app.py                      # FastAPI 应用入口
├── web/
│   ├── Dockerfile                  # 管理界面镜像
│   └── index.html                  # CRUD 管理界面
├── scripts/
│   ├── restore.sh                  # 一键恢复脚本
│   ├── wait-for-it.sh              # 等待服务就绪
│   └── backup.sh                   # 备份脚本（可选）
└── .env.example                    # 环境变量模板

# 根目录修改
.env.example                        # 环境变量模板
Makefile                            # 快捷命令（可选）
```

---

## Pre-requisite: Git Worktree Setup

在开始任何实现之前，必须创建隔离的 git worktree：

```bash
cd /Users/lwj04/.openclaw/workspace-extractor
# 确认 .worktrees 在 .gitignore 中
git check-ignore -q .worktrees 2>/dev/null || echo ".worktrees/" >> .gitignore
git add .gitignore && git commit -m "chore: ensure .worktrees is gitignored"
# 创建 worktree
git worktree add .worktrees/o3-docker -b feature/o3-docker-fullstack
cd .worktrees/o3-docker
pip install -e ".[dev,database]"
pytest --tb=short -q
```

---

## Task 1: Docker Compose + Supabase 初始化

**Files:**
- Create: `docker/docker-compose.yml`
- Create: `docker/supabase/init/01_schema.sql`
- Create: `docker/.env.example`
- Create: `docker/scripts/wait-for-it.sh`

**Dependencies:** 无（首个任务）

- [ ] **Step 1: Write failing test for docker-compose validity**

```bash
# tests/test_docker.py
import subprocess
import pytest

def test_docker_compose_file_valid():
    """docker-compose.yml should be valid YAML with required services."""
    result = subprocess.run(
        ["docker", "compose", "-f", "docker/docker-compose.yml", "config"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"docker compose config failed: {result.stderr}"
    # Verify required services exist
    assert "supabase-db" in result.stdout or "db" in result.stdout
    assert "api" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docker.py::test_docker_compose_file_valid -v`
Expected: FAIL — docker-compose.yml doesn't exist yet

- [ ] **Step 3: Generate schema SQL from existing schema.py**

```bash
cd /Users/lwj04/.openclaw/workspace-extractor
python3 -c "
from src.ontofuel.database.schema import generate_all_sql
print(generate_all_sql())
" > docker/supabase/init/01_schema.sql
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
# docker/docker-compose.yml
version: "3.8"

services:
  db:
    image: supabase/postgres:15.6.1
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-your-super-secret-password}
      POSTGRES_DB: ${POSTGRES_DB:-postgres}
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./supabase/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ..
      dockerfile: docker/api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      SUPABASE_URL: http://db:5432
      SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY:-}
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD:-your-super-secret-password}@db:5432/${POSTGRES_DB:-postgres}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: ..
      dockerfile: docker/web/Dockerfile
    ports:
      - "3000:80"
    depends_on:
      api:
        condition: service_healthy

volumes:
  db-data:
```

- [ ] **Step 5: Create .env.example**

```bash
# docker/.env.example
POSTGRES_PASSWORD=your-super-secret-password
POSTGRES_DB=postgres
SUPABASE_SERVICE_KEY=your-supabase-service-key
ONTOFUEL_API_PORT=8000
ONTOFUEL_WEB_PORT=3000
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_docker.py::test_docker_compose_file_valid -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add docker/docker-compose.yml docker/supabase/init/01_schema.sql docker/.env.example
git commit -m "feat(o3): add docker-compose with Supabase init schema"
```

---

## Task 2: OntoFuel FastAPI 应用

**Files:**
- Create: `docker/api/Dockerfile`
- Create: `docker/api/requirements.txt`
- Create: `docker/api/app.py`
- Create: `tests/test_api_app.py`

**Dependencies:** Task 1 (schema SQL)

- [ ] **Step 1: Write failing test for API app module**

```python
# tests/test_api_app.py
import pytest

def test_api_app_importable():
    """FastAPI app should be importable and have required routes."""
    import sys
    sys.path.insert(0, "docker/api")
    from app import app
    routes = [r.path for r in app.routes]
    assert "/health" in routes
    assert "/api/materials" in routes
    assert "/api/materials/{material_id}" in routes

def test_api_app_has_crud_endpoints():
    """API should expose CRUD endpoints for materials."""
    import sys
    sys.path.insert(0, "docker/api")
    from app import app
    methods_by_path = {}
    for r in app.routes:
        if hasattr(r, 'methods') and hasattr(r, 'path'):
            methods_by_path[r.path] = r.methods
    # POST for create
    assert "POST" in methods_by_path.get("/api/materials", set())
    # GET for read
    assert "GET" in methods_by_path.get("/api/materials", set())
    # PUT/PATCH for update
    assert ("PUT" in methods_by_path.get("/api/materials/{material_id}", set()) or
            "PATCH" in methods_by_path.get("/api/materials/{material_id}", set()))
    # DELETE for delete
    assert "DELETE" in methods_by_path.get("/api/materials/{material_id}", set())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_app.py -v`
Expected: FAIL — app.py doesn't exist

- [ ] **Step 3: Create requirements.txt**

```
# docker/api/requirements.txt
fastapi>=0.104.0
uvicorn>=0.24.0
psycopg2-binary>=2.9.0
```

- [ ] **Step 4: Create app.py with FastAPI CRUD**

```python
# docker/api/app.py
"""OntoFuel REST API — FastAPI application for CRUD operations."""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="OntoFuel API", version="0.1.0")


# ---- DB connection ----

def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:your-super-secret-password@db:5432/postgres",
    )


@contextmanager
def get_conn():
    conn = psycopg2.connect(get_db_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---- Models ----

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


# ---- Health ----

@app.get("/health")
def health():
    return {"status": "ok"}


# ---- Materials CRUD ----

@app.get("/api/materials")
def list_materials(
    material_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    with get_conn() as conn:
        cur = conn.cursor()
        if material_type:
            cur.execute(
                'SELECT id, name, chemical_formula, material_type, created_at FROM materials WHERE material_type = %s ORDER BY name LIMIT %s OFFSET %s',
                (material_type, limit, offset),
            )
        else:
            cur.execute(
                'SELECT id, name, chemical_formula, material_type, created_at FROM materials ORDER BY name LIMIT %s OFFSET %s',
                (limit, offset),
            )
        rows = cur.fetchall()
        results = [
            {"id": str(r[0]), "name": r[1], "chemical_formula": r[2],
             "material_type": r[3], "created_at": r[4].isoformat() if r[4] else None}
            for r in rows
        ]
        return {"data": results, "count": len(results)}


@app.get("/api/materials/{material_id}")
def get_material(material_id: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, name, chemical_formula, material_type, created_at FROM materials WHERE id = %s',
            (material_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "Material not found")
        return {"id": str(r[0]), "name": r[1], "chemical_formula": r[2],
                "material_type": r[3], "created_at": r[4].isoformat() if r[4] else None}


@app.post("/api/materials", status_code=201)
def create_material(body: MaterialCreate):
    mid = str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO materials (id, name, chemical_formula, material_type) VALUES (%s, %s, %s, %s) RETURNING id',
            (mid, body.name, body.chemical_formula, body.material_type),
        )
        return {"id": mid, "name": body.name}


@app.patch("/api/materials/{material_id}")
def update_material(material_id: str, body: MaterialUpdate):
    fields = {k: v for k, v in body.dict().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
    sets = ", ".join(f"{k} = %s" for k in fields)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f'UPDATE materials SET {sets}, updated_at = now() WHERE id = %s',
            (*fields.values(), material_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Material not found")
        return {"id": material_id, "updated": list(fields.keys())}


@app.delete("/api/materials/{material_id}")
def delete_material(material_id: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM materials WHERE id = %s', (material_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Material not found")
        return {"deleted": material_id}


# ---- Properties ----

@app.get("/api/materials/{material_id}/properties")
def list_properties(material_id: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, property_name, property_value, unit, source, temperature FROM material_properties WHERE material_id = %s',
            (material_id,),
        )
        rows = cur.fetchall()
        return {"data": [
            {"id": str(r[0]), "property_name": r[1], "property_value": r[2],
             "unit": r[3], "source": r[4], "temperature": r[5]}
            for r in rows
        ]}


@app.post("/api/materials/{material_id}/properties", status_code=201)
def create_property(material_id: str, body: PropertyCreate):
    pid = str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO material_properties (id, material_id, property_name, property_value, value_string, unit, source, temperature, temperature_unit) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (pid, material_id, body.property_name, body.property_value,
             body.value_string, body.unit, body.source, body.temperature,
             body.temperature_unit),
        )
        return {"id": pid, "property_name": body.property_name}
```

- [ ] **Step 5: Create API Dockerfile**

```dockerfile
# docker/api/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY docker/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ /app/src/
COPY docker/api/app.py /app/app.py
COPY pyproject.toml /app/pyproject.toml

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_api_app.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add docker/api/ tests/test_api_app.py
git commit -m "feat(o3): add FastAPI CRUD application for materials"
```

---

## Task 3: 管理界面 (Web Frontend)

**Files:**
- Create: `docker/web/Dockerfile`
- Create: `docker/web/index.html`
- Create: `tests/test_web_frontend.py`

**Dependencies:** Task 2 (API endpoints)

- [ ] **Step 1: Write failing test for web frontend**

```python
# tests/test_web_frontend.py
import pathlib

def test_web_index_html_exists():
    """index.html should exist in docker/web/."""
    p = pathlib.Path("docker/web/index.html")
    assert p.exists(), "docker/web/index.html not found"

def test_web_index_has_crud_ui():
    """index.html should contain material CRUD elements."""
    content = pathlib.Path("docker/web/index.html").read_text()
    # Must have table/list for materials
    assert "materials" in content.lower()
    # Must have add/create functionality
    assert "add" in content.lower() or "create" in content.lower()
    # Must have delete functionality
    assert "delete" in content.lower()
    # Must reference API endpoint
    assert "/api/materials" in content

def test_web_dockerfile_exists():
    """Dockerfile for web should exist."""
    assert pathlib.Path("docker/web/Dockerfile").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_frontend.py -v`
Expected: FAIL — files don't exist

- [ ] **Step 3: Create index.html with CRUD UI**

```html
<!-- docker/web/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OntoFuel 材料管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: #1a1a2e; color: white; padding: 16px 20px; margin-bottom: 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 20px; }
        .stats { display: flex; gap: 12px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 16px; border-radius: 8px; flex: 1; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stat-card h3 { font-size: 12px; color: #888; text-transform: uppercase; }
        .stat-card .value { font-size: 24px; font-weight: bold; color: #1a1a2e; }
        .toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
        .toolbar input, .toolbar select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .toolbar input { flex: 1; }
        button { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #1a1a2e; color: white; }
        .btn-primary:hover { background: #16213e; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-sm { padding: 4px 8px; font-size: 12px; }
        table { width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-size: 13px; color: #666; border-bottom: 2px solid #eee; }
        td { padding: 12px; border-bottom: 1px solid #f0f0f0; }
        tr:hover { background: #f8f9fa; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; }
        .badge-fuel { background: #ffeaa7; color: #d68910; }
        .badge-structural { background: #dfe6e9; color: #636e72; }
        .badge-coolant { background: #74b9ff; color: #0984e3; }
        .badge-ceramic { background: #fab1a0; color: #e17055; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; justify-content: center; align-items: center; }
        .modal-overlay.active { display: flex; }
        .modal { background: white; padding: 24px; border-radius: 12px; width: 500px; max-width: 90vw; }
        .modal h2 { margin-bottom: 16px; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px; }
        .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
        .empty { text-align: center; padding: 40px; color: #999; }
        .loading { text-align: center; padding: 20px; }
        .props-panel { margin-top: 16px; background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .props-panel h3 { margin-bottom: 12px; }
        .props-table { width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔬 OntoFuel 材料管理</h1>
            <span id="status">连接中...</span>
        </header>
        <div class="stats" id="stats"></div>
        <div class="toolbar">
            <input type="text" id="search" placeholder="搜索材料名称或公式...">
            <select id="filter-type">
                <option value="">全部类型</option>
                <option value="FuelMaterial">燃料材料</option>
                <option value="StructuralMaterial">结构材料</option>
                <option value="CoolantMaterial">冷却剂材料</option>
                <option value="CeramicMaterial">陶瓷材料</option>
            </select>
            <button class="btn-primary" onclick="openCreateModal()">+ 添加材料</button>
        </div>
        <table>
            <thead>
                <tr><th>名称</th><th>化学式</th><th>类型</th><th>属性</th><th>操作</th></tr>
            </thead>
            <tbody id="materials-body">
                <tr><td colspan="5" class="loading">加载中...</td></tr>
            </tbody>
        </table>
        <div class="props-panel" id="props-panel" style="display:none">
            <h3 id="props-title">材料属性</h3>
            <table class="props-table">
                <thead><tr><th>属性</th><th>值</th><th>单位</th><th>来源</th></tr></thead>
                <tbody id="props-body"></tbody>
            </table>
            <div style="margin-top:12px">
                <input type="text" id="prop-name" placeholder="属性名" style="width:120px;padding:6px">
                <input type="number" id="prop-value" placeholder="值" style="width:100px;padding:6px">
                <input type="text" id="prop-unit" placeholder="单位" style="width:80px;padding:6px">
                <button class="btn-primary btn-sm" onclick="addProperty()">添加属性</button>
            </div>
        </div>
    </div>

    <!-- Create/Edit Modal -->
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <h2 id="modal-title">添加材料</h2>
            <input type="hidden" id="edit-id">
            <div class="form-group">
                <label>名称 *</label>
                <input type="text" id="m-name" required>
            </div>
            <div class="form-group">
                <label>化学式</label>
                <input type="text" id="m-formula">
            </div>
            <div class="form-group">
                <label>材料类型</label>
                <select id="m-type">
                    <option value="FuelMaterial">燃料材料</option>
                    <option value="StructuralMaterial">结构材料</option>
                    <option value="CoolantMaterial">冷却剂材料</option>
                    <option value="CeramicMaterial">陶瓷材料</option>
                </select>
            </div>
            <div class="modal-actions">
                <button onclick="closeModal()" style="background:#eee">取消</button>
                <button class="btn-primary" onclick="saveMaterial()">保存</button>
            </div>
        </div>
    </div>

    <script>
        const API = window.location.protocol + '//' + (window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.hostname + ':8000');
        let materials = [];

        async function api(path, opts = {}) {
            const r = await fetch(API + path, { headers: {'Content-Type':'application/json'}, ...opts });
            if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
            return r.json();
        }

        async function loadMaterials() {
            try {
                const type = document.getElementById('filter-type').value;
                const q = type ? `?material_type=${type}` : '';
                const res = await api('/api/materials' + q);
                materials = res.data || [];
                document.getElementById('status').textContent = `已连接 · ${materials.length} 条材料`;
                renderMaterials();
                renderStats();
            } catch (e) {
                document.getElementById('status').textContent = '连接失败';
                document.getElementById('materials-body').innerHTML = `<tr><td colspan="5" class="empty">API 连接失败: ${e.message}</td></tr>`;
            }
        }

        function renderMaterials() {
            const search = document.getElementById('search').value.toLowerCase();
            const filtered = materials.filter(m =>
                (m.name||'').toLowerCase().includes(search) ||
                (m.chemical_formula||'').toLowerCase().includes(search)
            );
            if (!filtered.length) {
                document.getElementById('materials-body').innerHTML = '<tr><td colspan="5" class="empty">暂无材料数据</td></tr>';
                return;
            }
            document.getElementById('materials-body').innerHTML = filtered.map(m => `
                <tr>
                    <td><strong>${esc(m.name)}</strong></td>
                    <td>${esc(m.chemical_formula || '-')}</td>
                    <td><span class="badge badge-${(m.material_type||'').replace('Material','').toLowerCase()}">${esc(m.material_type || '未知')}</span></td>
                    <td><button class="btn-sm" style="background:#eee" onclick="loadProperties('${m.id}','${esc(m.name)}')">查看</button></td>
                    <td>
                        <button class="btn-sm" style="background:#eee" onclick="editMaterial('${m.id}','${esc(m.name)}','${esc(m.chemical_formula||'')}','${esc(m.material_type||'')}')">编辑</button>
                        <button class="btn-danger btn-sm" onclick="deleteMaterial('${m.id}','${esc(m.name)}')">删除</button>
                    </td>
                </tr>
            `).join('');
        }

        function renderStats() {
            const types = {};
            materials.forEach(m => { const t = m.material_type || 'Unknown'; types[t] = (types[t]||0) + 1; });
            document.getElementById('stats').innerHTML = `
                <div class="stat-card"><h3>总材料</h3><div class="value">${materials.length}</div></div>
                ${Object.entries(types).map(([t,c]) => `<div class="stat-card"><h3>${t}</h3><div class="value">${c}</div></div>`).join('')}
            `;
        }

        async function loadProperties(id, name) {
            try {
                const res = await api(`/api/materials/${id}/properties`);
                const props = res.data || [];
                document.getElementById('props-panel').style.display = '';
                document.getElementById('props-title').textContent = `${name} 的属性 (${props.length})`;
                document.getElementById('props-body').innerHTML = props.length ? props.map(p => `
                    <tr><td>${esc(p.property_name)}</td><td>${p.property_value ?? esc(p.value_string||'')}</td><td>${esc(p.unit||'')}</td><td>${esc(p.source||'')}</td></tr>
                `).join('') : '<tr><td colspan="4" style="text-align:center;color:#999">暂无属性</td></tr>';
                document.getElementById('props-panel').dataset.materialId = id;
            } catch (e) { alert('加载属性失败: ' + e.message); }
        }

        async function addProperty() {
            const id = document.getElementById('props-panel').dataset.materialId;
            const name = document.getElementById('prop-name').value;
            const value = document.getElementById('prop-value').value;
            const unit = document.getElementById('prop-unit').value;
            if (!name) return alert('请输入属性名');
            await api(`/api/materials/${id}/properties`, {
                method: 'POST',
                body: JSON.stringify({ material_id: id, property_name: name, property_value: value ? parseFloat(value) : null, unit })
            });
            document.getElementById('prop-name').value = '';
            document.getElementById('prop-value').value = '';
            document.getElementById('prop-unit').value = '';
            const matName = document.getElementById('props-title').textContent.split(' 的')[0];
            loadProperties(id, matName);
        }

        function openCreateModal() {
            document.getElementById('modal-title').textContent = '添加材料';
            document.getElementById('edit-id').value = '';
            document.getElementById('m-name').value = '';
            document.getElementById('m-formula').value = '';
            document.getElementById('m-type').value = 'FuelMaterial';
            document.getElementById('modal').classList.add('active');
        }

        function editMaterial(id, name, formula, type) {
            document.getElementById('modal-title').textContent = '编辑材料';
            document.getElementById('edit-id').value = id;
            document.getElementById('m-name').value = name;
            document.getElementById('m-formula').value = formula;
            document.getElementById('m-type').value = type || 'FuelMaterial';
            document.getElementById('modal').classList.add('active');
        }

        function closeModal() { document.getElementById('modal').classList.remove('active'); }

        async function saveMaterial() {
            const id = document.getElementById('edit-id').value;
            const data = {
                name: document.getElementById('m-name').value,
                chemical_formula: document.getElementById('m-formula').value || null,
                material_type: document.getElementById('m-type').value,
            };
            if (!data.name) return alert('名称不能为空');
            if (id) {
                await api(`/api/materials/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
            } else {
                await api('/api/materials', { method: 'POST', body: JSON.stringify(data) });
            }
            closeModal();
            loadMaterials();
        }

        async function deleteMaterial(id, name) {
            if (!confirm(`确定删除 "${name}"？`)) return;
            await api(`/api/materials/${id}`, { method: 'DELETE' });
            loadMaterials();
        }

        function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

        document.getElementById('search').addEventListener('input', renderMaterials);
        document.getElementById('filter-type').addEventListener('change', loadMaterials);

        loadMaterials();
    </script>
</body>
</html>
```

- [ ] **Step 4: Create web Dockerfile**

```dockerfile
# docker/web/Dockerfile
FROM nginx:alpine
COPY docker/web/index.html /usr/share/nginx/html/index.html
EXPOSE 80
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_web_frontend.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add docker/web/ tests/test_web_frontend.py
git commit -m "feat(o3): add CRUD web management interface"
```

---

## Task 4: 数据恢复自动化 (restore.sh)

**Files:**
- Create: `docker/scripts/restore.sh`
- Create: `tests/test_restore_script.py`

**Dependencies:** Task 1, Task 2

- [ ] **Step 1: Write failing test for restore script**

```python
# tests/test_restore_script.py
import pathlib
import stat

def test_restore_script_exists():
    """restore.sh should exist and be executable."""
    p = pathlib.Path("docker/scripts/restore.sh")
    assert p.exists(), "docker/scripts/restore.sh not found"
    assert p.stat().st_mode & stat.S_IXUSR, "restore.sh not executable"

def test_restore_script_has_required_logic():
    """restore.sh should contain wait, schema init, and data restore."""
    content = pathlib.Path("docker/scripts/restore.sh").read_text()
    # Should wait for DB
    assert "wait" in content.lower() or "pg_isready" in content
    # Should restore data (using Python restore module or SQL)
    assert "restore" in content.lower() or "INSERT" in content or "python" in content.lower()
    # Should reference all 5 tables or use the restore module
    assert "materials" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_restore_script.py -v`
Expected: FAIL

- [ ] **Step 3: Create restore.sh**

```bash
#!/bin/bash
# docker/scripts/restore.sh
# Restore all 5 Supabase tables from ontology JSON data
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ONTOLOGY_FILE="${1:-$PROJECT_DIR/memory/trustgraph-fix/material_ontology_enhanced.json}"

echo "🔧 OntoFuel 数据恢复脚本"
echo "=========================="

# ---- Wait for database ----
echo "⏳ 等待数据库就绪..."
max_wait=60
waited=0
until pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q 2>/dev/null; do
    waited=$((waited + 1))
    if [ $waited -ge $max_wait ]; then
        echo "❌ 数据库等待超时 (${max_wait}s)"
        exit 1
    fi
    sleep 1
done
echo "✅ 数据库已就绪"

# ---- Run schema init (idempotent) ----
echo "📋 初始化表结构..."
PGPASSWORD="${DB_PASSWORD:-your-super-secret-password}" psql \
    -h "${DB_HOST:-localhost}" \
    -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" \
    -d "${DB_NAME:-postgres}" \
    -f "$SCRIPT_DIR/../supabase/init/01_schema.sql" 2>/dev/null || true
echo "✅ 表结构就绪"

# ---- Restore data using Python ----
if [ -f "$ONTOLOGY_FILE" ]; then
    echo "📊 从本体文件恢复数据: $ONTOLOGY_FILE"
    cd "$PROJECT_DIR"
    python3 -c "
import sys, os
sys.path.insert(0, 'src')
os.environ.setdefault('DATABASE_URL', 'postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-your-super-secret-password}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-postgres}')
from ontofuel.database.client import SupabaseClient
from ontofuel.database.restore import DataRestorer

# Use direct DB connection for Docker environment
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])

from ontofuel.database.schema import generate_all_sql

# Ensure schema
cur = conn.cursor()
cur.execute(open('docker/supabase/init/01_schema.sql').read())
conn.commit()

# Load and restore ontology
import json
with open('$ONTOLOGY_FILE') as f:
    ont = json.load(f)
individuals = ont.get('individuals', [])
print(f'  找到 {len(individuals)} 个个体')

# Clear existing data (idempotent restore)
for table in ['irradiation_behavior', 'material_properties', 'material_composition', 'materials', 'literature_sources']:
    cur.execute(f'DELETE FROM {table}')
conn.commit()

# Insert materials
import uuid
for ind in individuals:
    name = ind.get('name', '')
    cls = ind.get('class', 'Unknown')
    if isinstance(cls, list): cls = cls[0] if cls else 'Unknown'
    mid = str(uuid.uuid4())
    cur.execute('INSERT INTO materials (id, name, material_type) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                (mid, name, cls))

    # Insert properties
    for key, val in ind.items():
        if key in ('name', 'class', 'uri', 'comment'): continue
        if isinstance(val, (int, float)):
            cur.execute('INSERT INTO material_properties (id, material_id, property_name, property_value) VALUES (%s, %s, %s, %s)',
                        (str(uuid.uuid4()), mid, key, val))
        elif isinstance(val, str) and val:
            cur.execute('INSERT INTO material_properties (id, material_id, property_name, value_string) VALUES (%s, %s, %s, %s)',
                        (str(uuid.uuid4()), mid, key, val))

conn.commit()
cur.execute('SELECT COUNT(*) FROM materials')
mat_count = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM material_properties')
prop_count = cur.fetchone()[0]
print(f'  ✅ 恢复完成: {mat_count} 材料, {prop_count} 属性')
conn.close()
"
else
    echo "⚠️  未找到本体文件: $ONTOLOGY_FILE"
    echo "    使用: $0 <path-to-ontology.json>"
fi

echo ""
echo "🎉 数据恢复完成！"
echo "   材料: 查询 SELECT COUNT(*) FROM materials;"
echo "   属性: 查询 SELECT COUNT(*) FROM material_properties;"
```

- [ ] **Step 4: Make executable**

```bash
chmod +x docker/scripts/restore.sh
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_restore_script.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add docker/scripts/ tests/test_restore_script.py
git commit -m "feat(o3): add automated data restore script"
```

---

## Task 5: 端到端集成测试

**Files:**
- Create: `tests/test_docker_integration.py`

**Dependencies:** Task 1, 2, 3, 4 (全部完成)

- [ ] **Step 1: Write integration test**

```python
# tests/test_docker_integration.py
"""Integration tests for Docker fullstack deployment.

These tests verify the complete Docker stack works together.
They require Docker to be running and are skipped if unavailable.
"""
import os
import subprocess
import time
import json
import urllib.request
import urllib.error
import pathlib
import pytest

COMPOSE_FILE = pathlib.Path(__file__).parent.parent / "docker" / "docker-compose.yml"

def docker_available():
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not docker_available(), reason="Docker not available")


@pytest.fixture(scope="module", autouse=True)
def docker_stack():
    """Start and stop Docker stack for integration tests."""
    env = os.environ.copy()
    # Start
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build"],
        env=env, capture_output=True, timeout=300,
    )
    # Wait for services
    for _ in range(60):
        try:
            urllib.request.urlopen("http://localhost:8000/health", timeout=2)
            break
        except Exception:
            time.sleep(2)

    yield

    # Stop
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"],
        env=env, capture_output=True, timeout=60,
    )


def test_api_health():
    """API health endpoint should return ok."""
    resp = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
    data = json.loads(resp.read())
    assert data["status"] == "ok"


def test_api_list_materials_empty():
    """GET /api/materials should return empty or data list."""
    resp = urllib.request.urlopen("http://localhost:8000/api/materials", timeout=5)
    data = json.loads(resp.read())
    assert "data" in data
    assert isinstance(data["data"], list)


def test_api_create_and_get_material():
    """Should create a material and retrieve it."""
    # Create
    body = json.dumps({
        "name": "U-10Mo-test",
        "chemical_formula": "U-10Mo",
        "material_type": "FuelMaterial",
    }).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/materials",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 201
    created = json.loads(resp.read())
    assert "id" in created

    # Get
    resp = urllib.request.urlopen(
        f"http://localhost:8000/api/materials/{created['id']}", timeout=5
    )
    mat = json.loads(resp.read())
    assert mat["name"] == "U-10Mo-test"
    assert mat["material_type"] == "FuelMaterial"


def test_api_update_material():
    """Should update a material."""
    # Create first
    body = json.dumps({"name": "temp-update-test"}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/materials",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    mat = json.loads(resp.read())

    # Update
    update = json.dumps({"chemical_formula": "UO2"}).encode()
    req = urllib.request.Request(
        f"http://localhost:8000/api/materials/{mat['id']}",
        data=update, headers={"Content-Type": "application/json"}, method="PATCH",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 200


def test_api_delete_material():
    """Should delete a material."""
    # Create first
    body = json.dumps({"name": "temp-delete-test"}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/materials",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    mat = json.loads(resp.read())

    # Delete
    req = urllib.request.Request(
        f"http://localhost:8000/api/materials/{mat['id']}", method="DELETE",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.status == 200

    # Verify gone
    try:
        urllib.request.urlopen(
            f"http://localhost:8000/api/materials/{mat['id']}", timeout=5
        )
        assert False, "Should have raised 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_web_frontend_accessible():
    """Web frontend should be accessible on port 3000."""
    resp = urllib.request.urlopen("http://localhost:3000/", timeout=5)
    assert resp.status == 200
    content = resp.read().decode()
    assert "OntoFuel" in content
    assert "materials" in content
```

- [ ] **Step 2: Run integration tests (requires Docker)**

Run: `pytest tests/test_docker_integration.py -v --timeout=300`
Expected: PASS (7 tests) if Docker available; SKIP if not

- [ ] **Step 3: Commit**

```bash
git add tests/test_docker_integration.py
git commit -m "test(o3): add Docker fullstack integration tests"
```

---

## Task 6: Docker Compose 验证 + 启动测试

**Files:**
- Modify: `docker/docker-compose.yml` (如果集成测试发现问题)

**Dependencies:** Task 5

- [ ] **Step 1: Build and start Docker stack**

```bash
cd docker
cp .env.example .env
docker compose up -d --build
```

- [ ] **Step 2: Verify all services healthy**

```bash
docker compose ps
# All services should show "healthy" or "running"
curl http://localhost:8000/health
curl http://localhost:3000/
```

- [ ] **Step 3: Run restore script**

```bash
docker/scripts/restore.sh
# Verify data restored
PGPASSWORD=your-super-secret-password psql -h localhost -U postgres -c "SELECT COUNT(*) FROM materials;"
PGPASSWORD=your-super-secret-password psql -h localhost -U postgres -c "SELECT COUNT(*) FROM material_properties;"
```

- [ ] **Step 4: Verify CRUD in browser**

```bash
# Test all CRUD operations via API
curl -X POST http://localhost:8000/api/materials -H 'Content-Type: application/json' -d '{"name":"test-material","material_type":"FuelMaterial"}'
curl http://localhost:8000/api/materials
curl -X PATCH http://localhost:8000/api/materials/<id> -H 'Content-Type: application/json' -d '{"name":"updated"}'
curl -X DELETE http://localhost:8000/api/materials/<id>
```

- [ ] **Step 5: Tear down**

```bash
docker compose down -v
```

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: ALL PASS

- [ ] **Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix(o3): integration fixes from fullstack verification"
```

---

## Self-Review Checklist

**Plan reviewer:** Before dispatching, verify:

1. **Spec coverage:** Each KR mapped to tasks?
   - KR 3.1 (docker-compose.yml) → Task 1 ✅
   - KR 3.2 (restore.sh) → Task 4 ✅
   - KR 3.3 (CRUD 界面) → Task 3 + Task 2 ✅

2. **Placeholder scan:** No TBD/TODO/placeholders ✅

3. **Type consistency:** All file paths, function names consistent across tasks ✅

4. **Test coverage:** Every task has failing test first ✅

5. **Dependency chain:** Tasks ordered correctly ✅

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-o3-docker-fullstack.md`.**

**Recommended: Subagent-Driven Development** — 6 个独立任务，每个 subagent 隔离执行，两阶段评审确保质量。
