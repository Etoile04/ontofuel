# OntoFuel 部署方案对比分析

## 目标用户画像

| 角色 | 需求 | 典型场景 |
|------|------|---------|
| 小张（研究生） | 查看本体数据、汇报演示 | U盘拷贝到课题组电脑 |
| 李老师（教授） | 团队共享、在线编辑 | 实验室服务器长期部署 |
| 王工（合作方） | 开箱即用、零配置 | 交付后独立运行 |

---

## 三种方案概述

**方案A：轻量打包（Portable）**
仅打包核心数据文件 + 可视化页面 + 查询脚本。拷贝文件夹即可使用，无需安装任何依赖。

**方案B：Docker Compose（Full Stack）**
在方案A基础上加入 Supabase 数据库（Docker），提供 REST API 和管理界面，支持在线数据增删改。

**方案C：容器化（All-in-One Docker）**
将方案B全部封装进一个 Docker 镜像，一条命令启动，最适合交付给非技术用户。

---

## 功能对比矩阵

| 功能 | 方案A 轻量 | 方案B Docker | 方案C 容器化 |
|------|-----------|-------------|-------------|
| 浏览本体可视化 | ✅ | ✅ | ✅ |
| 搜索/筛选节点 | ✅ | ✅ | ✅ |
| 查看本体统计 | ✅ | ✅ | ✅ |
| 查询脚本工具 | ✅ | ✅ | ✅ |
| 导出 CSV/JSON | ✅ | ✅ | ✅ |
| 本体质量评估 | ✅ | ✅ | ✅ |
| Supabase 数据库 | ❌ | ✅ | ✅ |
| REST API 查询 | ❌ | ✅ | ✅ |
| Studio 管理界面 | ❌ | ✅ | ✅ |
| 数据在线增删改 | ❌ | ✅ | ✅ |
| 多用户并发访问 | ❌ | ✅ | ✅ |
| 数据持久化 | 文件级 | 数据库级 | 数据库级 |
| PDF 提取（需AI） | ❌ | 需配置Key | 需配置Key |
| 文献搜索（需AI） | ❌ | 需配置Key | 需配置Key |

---

## 部署成本对比

| 指标 | 方案A 轻量 | 方案B Docker | 方案C 容器化 |
|------|-----------|-------------|-------------|
| 包大小 | ~15 MB | ~200 MB | ~500 MB |
| 首次安装时间 | 1 分钟 | 10 分钟 | 15 分钟 |
| 前置依赖 | 无 | Docker | Docker |
| 学习成本 | 低 | 中 | 低 |
| 维护成本 | 低 | 中 | 中 |
| 目标机器要求 | 任意电脑 | Docker环境 | Docker环境 |

---

## 用户体验流程对比

### 方案A — 小张的体验（1分钟上手）

1. U盘拷贝 `ontofuel-portable/` 文件夹（15MB，10秒）
2. 双击 `start.sh`（或 Windows 上 `start.bat`）
3. 浏览器自动打开 → 看到本体可视化
4. 搜索框输入 "U-10Mo" → 显示5个相关节点
5. 点击节点 → 右侧弹出详情面板
6. 终端运行 `python3 query_tool.py --search "U-Zr"` 查询
7. 完成

**满意度：⭐⭐⭐⭐** — 够用，但数据只读

### 方案B — 李老师的体验（10分钟部署）

1. `git clone` + `docker compose up`（5分钟下载镜像）
2. 运行 `restore.sh` → Supabase 数据自动恢复
3. 浏览器打开 → 可视化 + Studio 管理界面同时可用
4. 通过 Studio 修改材料属性值，实时生效
5. REST API 查询：`curl localhost:54321/rest/v1/materials`
6. 跑提取脚本 → 新数据自动入库
7. 课题组其他成员通过 IP 访问同一系统

**满意度：⭐⭐⭐⭐⭐** — 完整功能，团队共享

### 方案C — 王工的体验（一条命令）

1. `docker run -p 9999:9999 -p 54321:54321 ontofuel:latest`
2. 浏览器打开 → 一切就绪
3. 不用了 → `docker stop`
4. 下次 → `docker start`（数据还在）

**满意度：⭐⭐⭐⭐⭐** — 最省心

---

## 各方案痛点分析

### 方案A 痛点
- 数据更新需要重新拷贝整个文件夹
- 无法在线编辑，改数据要手动改 JSON
- 没有数据库，复杂查询受限
- **适合场景**：演示、汇报、个人查看

### 方案B 痛点
- 需要 Docker 基础知识
- docker compose 配置对非技术人员有门槛
- 首次恢复数据需要等待
- **适合场景**：课题组、实验室长期使用

### 方案C 痛点
- 构建 Docker 镜像需要一次性的工程投入
- 镜像体积较大（500MB）
- 定制化不如方案B灵活
- **适合场景**：交付给合作方、非技术用户

---

## 建议策略：分步实施

### 第一步：先做方案A（当天完成，约2小时）
打包核心文件 + start.sh + README
→ 立即可用于演示和汇报

### 第二步：再做方案B（1-2天）
docker-compose.yml + restore.sh + 文档
→ 适合实验室长期部署

### 第三步：最后做方案C（额外1天）
把方案B包装成 Docker 镜像
→ 交付给合作方

> 方案A 和 B 的文件大部分重叠，逐步升级投入产出比最高。

---

## 当前系统依赖清单

### 核心数据文件（必须）
| 文件 | 大小 | 内容 |
|------|------|------|
| `data/nvl_ontology_data.json` | 984 KB | 915节点 + 1048关系 |
| `memory/trustgraph-fix/material_ontology_enhanced.json` | 738 KB | 完整本体定义 |

### 可视化（必须）
| 文件 | 大小 | 说明 |
|------|------|------|
| `ontology_viz.html` | 19 KB | D3.js 力导向图 |
| `index.html` | 0.4 KB | 入口跳转页 |

### Python 脚本（80+，全部纯 stdlib）
- 查询工具、导出工具、质量评估
- **无第三方 Python 依赖**

### Supabase 数据库（方案B/C 需要）
| 表名 | 记录数 | 说明 |
|------|--------|------|
| materials | 9 | 材料基础信息 |
| material_properties | 26 | 材料属性 |
| material_composition | 0 | 材料成分（待补充） |
| literature_sources | 0 | 文献来源（待补充） |
| irradiation_behavior | 0 | 辐照行为（待补充） |

### AI 功能（可选，需额外配置）
| 功能 | 依赖 | 说明 |
|------|------|------|
| PDF 提取 | LLM API Key + MinerU | 从文献提取结构化数据 |
| 文献搜索 | Zotero MCP | 管理和搜索文献库 |
| 本体生成 | LLM API Key | 自动生成本体类和属性 |

---

## 目录结构预览

### 方案A 目录结构
```
ontofuel-portable/
├── start.sh              # 一键启动（Mac/Linux）
├── start.bat             # 一键启动（Windows）
├── README.md             # 使用说明
├── ontology_viz.html     # 可视化页面
├── index.html            # 入口页
├── data/
│   ├── nvl_ontology_data.json
│   └── material_ontology_enhanced.json
├── scripts/
│   ├── ontology_query_tool.py
│   ├── ontology_versioning.py
│   ├── ontology_critic.py
│   ├── graph_update.py
│   └── ...（80+ 脚本）
├── docs/
│   ├── USER_MANUAL.md
│   └── ...（20+ 文档）
└── supabase-backup/
    ├── materials.json
    └── material_properties.json
```

### 方案B 追加文件
```
├── docker-compose.yml    # Supabase 服务编排
├── restore.sh            # 数据恢复脚本
├── supabase/
│   ├── config.toml       # Supabase 配置
│   └── seed.sql          # 初始化 SQL
└── .env.example          # 环境变量模板
```

### 方案C 追加文件
```
├── Dockerfile            # 构建镜像
├── entrypoint.sh         # 容器入口
└── Makefile              # 构建和发布
```

---

*OntoFuel Extractor · 2026-04-25*
