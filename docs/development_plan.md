# OntoFuel 系统开发计划

## 项目概述

**OntoFuel** 是一个面向核材料领域的本体驱动知识提取与管理系统。核心能力包括：
- 超长文档本体提取（200-2000页）
- 文献知识管理与本体关联
- 本体可视化与查询
- 数据库存储与API服务

**当前状态**：功能完整，运行于 OpenClaw 智能体平台上，需剥离为独立可部署系统。

---

## 系统资产清单

| 资产 | 数量 | 说明 |
|------|------|------|
| Python 脚本 | 112 | 核心工具链（全部纯 stdlib） |
| 本体数据 | 1 | 738KB，139类+755个体，A+级质量 |
| NVL 可视化数据 | 1 | 984KB，915节点+1048关系 |
| 文档 | 39 | 使用指南、API文档、教程 |
| 数据文件 | 25 | 提取结果、搜索结果、备份 |
| 可视化页面 | 1 | D3.js 力导向图 |
| Supabase 表 | 5 | materials, material_properties 等 |

---

## 分阶段开发计划

### Phase 0：项目初始化（1天）

**目标**：建立 repo 结构，整理代码，定义 CI/CD 基础

**任务清单**：
- [x] 创建 GitHub repo：`Etoile04/ontofuel`
- [ ] 整理项目目录结构（清理临时文件）
- [ ] 编写 README.md（项目介绍、快速开始）
- [ ] 编写 LICENSE（MIT）
- [ ] 创建 .gitignore
- [ ] 初始 commit + tag `v0.1.0-alpha`

**目录结构**：
```
ontofuel/
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml              # Python 包配置
├── requirements.txt            # 依赖（最小化）
│
├── ontology/                   # 核心数据
│   ├── material_ontology_enhanced.json
│   └── nvl_ontology_data.json
│
├── src/                        # 源码
│   └── ontofuel/
│       ├── __init__.py
│       ├── core/               # 核心模块
│       │   ├── ontology.py     # 本体加载与查询
│       │   ├── query.py        # 查询引擎
│       │   ├── exporter.py     # 导出工具
│       │   └── validator.py    # 质量验证
│       ├── extraction/         # 提取模块
│       │   ├── pdf_parser.py   # PDF 解析
│       │   ├── segmenter.py    # 章节分割
│       │   ├── planner.py      # 提取计划
│       │   └── merger.py       # 结果合并
│       ├── database/           # 数据库模块
│       │   ├── supabase_client.py
│       │   ├── schema.py       # 表结构定义
│       │   └── restore.py      # 数据恢复
│       ├── visualization/      # 可视化模块
│       │   ├── web_viewer.py   # Web 可视化
│       │   └── templates/      # HTML 模板
│       │       └── ontology_viz.html
│       └── cli.py              # 命令行入口
│
├── scripts/                    # 独立脚本（保留兼容）
│   └── *.py                    # 112 个脚本
│
├── docker/                     # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── supabase/
│       ├── config.toml
│       └── seed.sql
│
├── docs/                       # 文档
│   ├── deployment_comparison.md
│   ├── USER_MANUAL.md
│   └── api/                    # API 文档
│
├── data/                       # 示例/测试数据
│   └── samples/
│
├── tests/                      # 测试
│   ├── test_ontology.py
│   ├── test_query.py
│   ├── test_exporter.py
│   └── test_validator.py
│
└── tools/                      # 部署工具
    ├── pack_portable.sh        # 方案A打包
    └── start.sh                # 启动脚本
```

**交付物**：干净的 repo + 完整目录结构 + README

---

### Phase 1：核心功能独立化（2-3天）

**目标**：将 112 个脚本整合为 Python 包，脱离 OpenClaw 独立运行

**1.1 核心模块开发**（1.5天）
- [ ] `src/ontofuel/core/ontology.py` — 统一本体加载、查询接口
- [ ] `src/ontofuel/core/query.py` — 按类/属性/个体/关键词查询
- [ ] `src/ontofuel/core/exporter.py` — 导出 JSON/CSV/Turtle/GraphML
- [ ] `src/ontofuel/core/validator.py` — 本体质量评估（5维评分）
- [ ] `src/ontofuel/cli.py` — 统一 CLI 入口

**CLI 设计**：
```bash
# 查询
ontofuel query --search "U-10Mo"
ontofuel query --class NuclearFuel
ontofuel query --property density --value ">10"

# 导出
ontofuel export --format csv --output data.csv
ontofuel export --format graphml --output graph.graphml

# 统计
ontofuel stats                    # 打印本体统计
ontofuel validate                 # 质量评估

# 可视化
ontofuel viz --port 9999          # 启动 Web 可视化
```

**1.2 数据库模块开发**（1天）
- [ ] `src/ontofuel/database/supabase_client.py` — Supabase 连接
- [ ] `src/ontofuel/database/schema.py` — 5 表结构定义
- [ ] `src/ontofuel/database/restore.py` — 从 JSON 恢复数据
- [ ] 数据库备份导出脚本

**1.3 测试**（0.5天）
- [ ] 单元测试（ontology, query, exporter, validator）
- [ ] 集成测试（数据库恢复 + 查询）
- [ ] 测试覆盖率 > 80%

**交付物**：`pip install -e .` 可安装的 Python 包 + CLI 工具

---

### Phase 2：方案A 轻量打包（1天）

**目标**：一键生成可分发的 portable 包

**任务清单**：
- [ ] `tools/pack_portable.sh` — 自动打包脚本
  - 筛选核心文件（排除 memory/, backups/, .openclaw/）
  - 内嵌 Python 运行时检查
  - 生成 start.sh / start.bat
- [ ] `tools/start.sh` — 启动脚本
  - 检测 Python3
  - 启动 HTTP 服务
  - 打开浏览器
- [ ] `tools/start.bat` — Windows 启动脚本
- [ ] `README_PORTABLE.md` — portable 版使用说明
- [ ] GitHub Release 自动发布

**打包产物**：
```
ontofuel-portable-v0.1.0.zip (~15 MB)
├── start.sh / start.bat
├── ontology_viz.html
├── data/
├── scripts/
├── docs/USER_MANUAL.md
└── README.md
```

**交付物**：GitHub Release 页面可下载的 zip 包

---

### Phase 3：方案B Docker Compose（1-2天）

**目标**：完整系统含 Supabase 数据库

**任务清单**：
- [ ] `docker/docker-compose.yml` — Supabase 服务编排
- [ ] `docker/supabase/config.toml` — Supabase 配置
- [ ] `docker/supabase/seed.sql` — 初始化 SQL（建表+种子数据）
- [ ] `tools/restore.sh` — 数据恢复脚本
- [ ] `.env.example` — 环境变量模板
- [ ] 可视化页面连接 Supabase REST API
- [ ] 管理界面（简单的 CRUD 页面）

**docker-compose.yml 设计**：
```yaml
services:
  supabase-db:      # PostgreSQL
  supabase-api:     # REST API
  supabase-studio:  # 管理界面
  ontofuel-web:     # 可视化 + HTTP
```

**交付物**：`docker compose up` 一键启动完整系统

---

### Phase 4：方案C 容器化（1天）

**目标**：All-in-One Docker 镜像

**任务清单**：
- [ ] `docker/Dockerfile` — 多阶段构建
- [ ] `docker/entrypoint.sh` — 容器入口（启动 Supabase + Web）
- [ ] `Makefile` — 构建/发布自动化
- [ ] Docker Hub 发布
- [ ] 验证测试（干净环境）

**使用方式**：
```bash
docker run -p 9999:9999 -p 54321:54321 etoile04/ontofuel:latest
```

**交付物**：Docker Hub 上的公开镜像

---

### Phase 5：文档与发布（1-2天）

**目标**：完善的文档和发布流程

**任务清单**：
- [ ] 完整 README.md（含安装、使用、截图）
- [ ] CONTRIBUTING.md（贡献指南）
- [ ] CHANGELOG.md（版本历史）
- [ ] API 文档（OpenAPI/Swagger）
- [ ] GitHub Actions CI/CD
  - 自动测试（push触发）
  - 自动打包（tag触发）
  - 自动发布 Release
  - 自动构建 Docker 镜像
- [ ] Demo 视频/GIF

**交付物**：完整的开源项目

---

## 时间线总览

```
Week 1                     Week 2                     Week 3
├── Phase 0 (1天) ──────┤                            │
│   Repo初始化           │                            │
│                        │                            │
├── Phase 1 (2-3天) ───────────────┤                  │
│   核心模块独立化        │                              │
│   CLI工具               │                             │
│   测试                  │                             │
│                        │                            │
│                        ├── Phase 2 (1天) ──────┤    │
│                        │   轻量打包             │    │
│                        │                        │    │
│                        ├── Phase 3 (1-2天) ─────────┤
│                        │   Docker Compose       │    │
│                        │                        │    │
│                        │                        ├── Phase 4 (1天) ─┤
│                        │                        │   容器化          │
│                        │                        │                   │
│                        │                        ├── Phase 5 (1-2天) ──────┤
│                        │                        │   文档与发布               │
```

**总工时**：约 8-12 天（1 人全职）
**里程碑**：每个 Phase 完成后打 tag + GitHub Release

---

## 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 已有112个脚本，生态丰富 |
| 包管理 | pyproject.toml + pip | 现代 Python 标准 |
| 数据库 | Supabase (PostgreSQL) | 已在使用，REST API 开箱即用 |
| 可视化 | D3.js + HTML | 轻量、无框架依赖 |
| 容器 | Docker + Compose | 标准化部署 |
| CI/CD | GitHub Actions | 免费、与 GitHub 集成 |
| 测试 | pytest | Python 标准测试框架 |
| 文档 | Markdown + MkDocs | 简洁、GitHub Pages 免费托管 |

---

## 版本规划

| 版本 | 内容 | 时间 |
|------|------|------|
| v0.1.0-alpha | Phase 0 + Phase 1 | Week 1 |
| v0.2.0-beta | Phase 2（Portable） | Week 2 |
| v0.3.0-rc1 | Phase 3（Docker Compose） | Week 2-3 |
| v1.0.0 | Phase 4+5（容器化+文档） | Week 3 |

---

*OntoFuel Extractor · 2026-04-25*
