# OntoFuel 🏗️

**Ontology-driven knowledge extraction and management system for nuclear materials science.**

## Overview

OntoFuel is a comprehensive system for:
- 📊 **Ontology Management** — 139 classes, 755 individuals, A+ quality score
- 🔍 **Knowledge Extraction** — Extract structured data from literature (200-2000 pages)
- 👁️ **Interactive Visualization** — D3.js force-directed graph (915 nodes + 1048 relationships)
- 🗄️ **Database Storage** — Supabase (PostgreSQL) with REST API
- 📤 **Multi-format Export** — JSON, CSV, Turtle, GraphML

## Quick Start

### Portable (No Installation)

```bash
# Download and extract
unzip ontofuel-portable-latest.zip
cd ontofuel-portable

# Start (Mac/Linux)
./start.sh

# Start (Windows)
start.bat
```

Browser opens automatically at http://localhost:9999

### Docker Compose (Full Stack)

```bash
git clone https://github.com/Etoile04/ontofuel.git
cd ontofuel
docker compose up -d
./tools/restore.sh
```

### Python Package

```bash
pip install ontofuel
ontofuel viz --port 9999
```

## Features

- ✅ Zero Python dependencies (all stdlib)
- ✅ Interactive ontology visualization
- ✅ Real-time search and filtering
- ✅ Multi-format export (JSON/CSV/Turtle/GraphML)
- ✅ Ontology quality validation (5-dimension scoring)
- ✅ Supabase integration with REST API
- ✅ Docker deployment ready

## Documentation

See [docs/](docs/) for detailed guides.

## License

MIT
## 🧪 测试

```bash
# 运行全部测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=ontofuel --cov-report=term-missing
```

**测试统计**: 139 tests, 100% pass rate, >80% coverage

## 🐍 Python API

```python
from ontofuel.core.ontology import load_ontology, get_stats
from ontofuel.core.query import OntologyQuery
from ontofuel.core.exporter import OntologyExporter
from ontofuel.extraction import Segmenter, Extractor, Merger, OntologyUpdater

# 加载本体
ont = load_ontology()
print(get_stats(ont))

# 查询
q = OntologyQuery(ont)
results = q.search("uranium")
results = q.by_class("NuclearFuel")

# 提取
ext = Extractor()
result = ext.extract("U-10Mo alloy has density 15.8 g/cm³")

# 导出
exp = OntologyExporter(ont)
exp.export_graphml("graph.graphml")
```

## 🐳 Docker 部署

OntoFuel 提供完整的 Docker Compose 编排，一键启动数据库 + API + Web 可视化。

### 前置要求

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2+
- 至少 2 GB 可用磁盘空间

### 快速启动

```bash
# 1. 进入 docker 目录
cd docker

# 2. （可选）配置环境变量
cp .env.example .env
# 编辑 .env 设置 POSTGRES_PASSWORD 等

# 3. 启动所有服务
docker compose up -d

# 4. 等待健康检查通过（约 30 秒）
docker compose ps
```

启动后可访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| Web 可视化 | http://localhost:3000 | 本体浏览器 |
| REST API | http://localhost:8000 | 材料数据 API |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| PostgreSQL | localhost:5432 | 直连数据库 |

### 常用命令

```bash
docker compose logs -f api    # 查看 API 日志
docker compose down           # 停止服务
docker compose down -v        # 停止并删除数据卷
```

> 💡 详细的部署方案对比（轻量包 vs Docker vs 全容器化）请参阅 [`docs/deployment_comparison.md`](docs/deployment_comparison.md)。

---

## 🔌 API 端点

OntoFuel FastAPI 服务提供以下 REST 端点（完整文档见 `http://localhost:8000/docs`）：

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 服务健康状态 |

### 材料管理 (Materials)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/materials` | 获取材料列表（支持分页） |
| `GET` | `/api/materials/{id}` | 获取单个材料详情 |
| `POST` | `/api/materials` | 创建新材料 |
| `PATCH` | `/api/materials/{id}` | 更新材料信息 |
| `DELETE` | `/api/materials/{id}` | 删除材料 |

### 材料属性 (Properties)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/materials/{id}/properties` | 获取材料的所有属性 |
| `POST` | `/api/materials/{id}/properties` | 为材料添加属性 |

### 示例请求

```bash
# 获取所有材料
curl http://localhost:8000/api/materials

# 创建新材料
curl -X POST http://localhost:8000/api/materials \
  -H "Content-Type: application/json" \
  -d '{"name": "U-10Mo", "material_type": "FuelMaterial"}'

# 查询材料属性
curl http://localhost:8000/api/materials/<material_id>/properties
```

---

## 📋 部署方案

OntoFuel 支持三种部署方式，满足不同使用场景：

### 方案 A：轻量打包（Portable）

**适合**：演示汇报、个人使用、U盘分发

```bash
# 拷贝 ontofuel-portable/ 文件夹即可
cp -r ontofuel-portable/ /path/to/target
./start.sh   # Mac/Linux
start.bat    # Windows
```

- 包大小 ~15 MB，零依赖
- 包含可视化 + 查询脚本 + 本体数据
- 数据只读，适合查看和演示

### 方案 B：Docker Compose（推荐）

**适合**：课题组共享、实验室长期部署

```bash
cd docker && docker compose up -d
```

- 完整功能：数据库 + API + Web
- 支持在线数据增删改
- 多用户并发访问

### 方案 C：源码安装

**适合**：开发者、需要定制功能

```bash
git clone https://github.com/Etoile04/ontofuel.git
cd ontofuel
pip install -e ".[dev]"
```

- 完整开发环境
- 可运行测试套件
- 可修改和扩展功能

> 📊 详细的方案对比和成本分析见 [`docs/deployment_comparison.md`](docs/deployment_comparison.md)。

---

## 🔧 故障排除 (Troubleshooting)

### 安装问题

**`pip install` 失败**

```bash
# 确保使用 Python 3.9+
python --version

# 升级 pip
pip install --upgrade pip

# 使用虚拟环境
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**`ontofuel: command not found`**

```bash
# 确认安装成功
pip show ontofuel

# 如果使用虚拟环境，确保已激活
source .venv/bin/activate
```

### Docker 问题

**`docker compose up` 失败**

```bash
# 检查 Docker 是否运行
docker info

# 查看服务日志
docker compose logs

# 端口冲突？修改 .env 中的端口映射
```

**数据库连接失败**

```bash
# 检查数据库容器状态
docker compose ps db

# 等待健康检查通过
docker compose logs db

# 手动测试连接
docker compose exec db pg_isready -U postgres
```

**API 返回 500 错误**

```bash
# 查看 API 日志
docker compose logs api

# 检查 DATABASE_URL 环境变量
docker compose exec api env | grep DATABASE_URL
```

### 可视化问题

**本体可视化页面空白**

- 检查浏览器控制台是否有错误
- 确认 `data/nvl_ontology_data.json` 文件存在
- 尝试使用 Chrome/Edge（推荐浏览器）

**搜索无结果**

- 搜索关键词区分大小写（取决于查询模式）
- 尝试使用模糊搜索：`ontofuel query --fuzzy "uranium"`

### 数据问题

**本体验证评分低**

```bash
# 运行详细验证
ontofuel validate

# 查看具体哪些维度扣分
ontofuel validate --verbose
```

**数据库数据丢失**

```bash
# 从备份恢复
cd scripts
python restore_all_supabase_data.py
```

---

## 📜 许可证

MIT License

## 🙏 致谢

- 本体质量评估借鉴了 [OntoCast](https://github.com/growgraph/ontocast) 的设计
- 可视化基于 [D3.js](https://d3js.org/)
- 文档解析支持 [MinerU](https://github.com/opendatalab/MinerU)
