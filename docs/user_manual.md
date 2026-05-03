# OntoFuel 用户手册

> 本体驱动的核材料知识提取与管理系统

---

## 目录

1. [简介](#1-简介)
2. [安装](#2-安装)
3. [快速开始](#3-快速开始)
4. [CLI 命令详解](#4-cli-命令详解)
5. [常用场景](#5-常用场景)
6. [配置说明](#6-配置说明)
7. [故障排查](#7-故障排查)

---

## 1. 简介

### OntoFuel 是什么？

OntoFuel 是一个面向核材料领域的本体驱动知识提取与管理系统。它能够从超长文档（200–2000 页 PDF/Markdown）中自动提取结构化材料数据，并将结果整合到本体知识库中。

### 核心能力

| 能力 | 说明 |
|------|------|
| 超长文档提取 | 支持 200–2000 页文档的章节分割与并行提取 |
| 智能知识提取 | 规则 + 模板驱动的合金成分、物理性能、相结构自动识别 |
| 增量更新 | 本体增量合并、去重、冲突解决 |
| 质量评估 | 5 维质量评估（命名 / 结构 / 语义 / 完整 / 覆盖） |
| Web 可视化 | D3.js 力导向图，支持搜索、过滤、缩放 |
| 数据库集成 | Supabase (PostgreSQL) 存储，REST API |

### 本体数据概览

| 指标 | 数值 |
|------|------|
| 类 (Classes) | 139 |
| 对象属性 | 162 |
| 数据属性 | 279 |
| 个体 (Individuals) | 755 |

覆盖领域：核燃料、包壳材料、冷却剂、高熵合金、辐照效应、扩散系数、热物理性能等。

---

## 2. 安装

OntoFuel 提供三种安装方式：源码安装、便携包、Docker。

### 2.1 源码安装（推荐开发者）

**前置条件**：Python ≥ 3.10

```bash
# 克隆仓库
git clone https://github.com/Etoile04/ontofuel.git
cd ontofuel

# 安装（开发模式，包含测试工具）
pip install -e ".[dev]"

# 验证安装
ontofuel --help
```

**可选依赖**：

```bash
# 数据库支持（Supabase）
pip install -e ".[database]"

# 可视化支持（高级图表）
pip install -e ".[viz]"

# 全部安装
pip install -e ".[all]"
```

> **注意**：核心功能零运行时依赖，全部使用 Python 标准库。`database` 和 `viz` 仅用于扩展功能。

### 2.2 便携包（无需安装）

```bash
# 下载发行版压缩包
wget https://github.com/Etoile04/ontofuel/releases/latest/download/ontofuel-portable.tar.gz
tar xzf ontofuel-portable.tar.gz
cd ontofuel

# 直接运行
./bin/ontofuel --help
```

### 2.3 Docker 安装

适用于生产部署和 CI/CD 场景。

```bash
# 使用 Docker Compose 一键启动（含数据库 + API + Web）
cd docker
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api
```

Docker Compose 包含三个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| `db` | 5432 | PostgreSQL 数据库 |
| `api` | 8000 | REST API 服务 |
| `web` | 3000 | Web 前端界面 |

> 首次启动时数据库会自动执行初始化脚本（`docker/supabase/init/`）。

---

## 3. 快速开始

以下流程约 5 分钟即可完成，帮助您快速上手 OntoFuel。

### 3.1 查看本体概况

```bash
# 基础统计
ontofuel stats

# 输出示例：
# ═══ OntoFuel Ontology Stats ═══
#   Classes:            139
#   Object Properties:  162
#   Datatype Properties:279
#   Individuals:        755

# 详细统计（含类分布）
ontofuel stats -v
```

### 3.2 搜索材料

```bash
# 关键词搜索
ontofuel query "U-10Mo"

# 按类过滤
ontofuel query --class NuclearFuel

# 按属性过滤
ontofuel query --property "density"

# 查看类层次结构
ontofuel query --hierarchy NuclearFuel
```

### 3.3 导出数据

```bash
# 导出为 JSON
ontofuel export json output.json

# 导出为 GraphML（用于图分析工具）
ontofuel export graphml graph.graphml

# 导出为 Markdown 报告
ontofuel export markdown report.md
```

### 3.4 质量验证

```bash
# 快速健康检查
ontofuel validate --quick

# 完整质量评估
ontofuel validate
```

### 3.5 可视化浏览

```bash
# 启动 Web 可视化（默认端口 9999）
ontofuel viz
```

浏览器自动打开 `http://localhost:9999`，即可浏览本体知识图谱。

---

## 4. CLI 命令详解

OntoFuel 提供以下子命令：

```
ontofuel stats      — 查看本体统计信息
ontofuel query      — 搜索本体实体
ontofuel export     — 导出本体数据
ontofuel validate   — 验证本体质量
ontofuel viz        — 启动可视化服务
```

### 全局选项

| 选项 | 说明 |
|------|------|
| `--ontology, -o <路径>` | 指定本体 JSON 文件路径（默认：自动检测） |
| `--help` | 显示帮助信息 |

---

### 4.1 `ontofuel stats` — 本体统计

显示本体中的类、属性、个体数量等信息。

```bash
# 基础统计
ontofuel stats

# 详细统计（含每个类的个体数量分布）
ontofuel stats -v
```

**输出说明**：

| 字段 | 说明 |
|------|------|
| Classes | 本体中定义的类数量 |
| Object Properties | 对象属性（关系）数量 |
| Datatype Properties | 数据属性数量 |
| Individuals | 个体（实例）数量 |

使用 `-v` 时额外显示按个体数量排名的前 10 个类。

---

### 4.2 `ontofuel query` — 本体查询

支持关键词搜索、类过滤、属性过滤和类层次结构查看。

```bash
# 关键词搜索
ontofuel query "U-10Mo"

# 按类名过滤
ontofuel query --class NuclearFuel

# 按属性过滤（名称或名称=值）
ontofuel query --property "density"
ontofuel query --property "density=19.1"

# 查看类的层次结构
ontofuel query --hierarchy NuclearFuel

# 限定搜索类别
ontofuel query "fuel" --category classes
ontofuel query "U-10Mo" --category individuals

# 限制结果数量
ontofuel query "U" --limit 10

# 将搜索结果导出为 JSON
ontofuel query "U-10Mo" --output results.json
```

**选项**：

| 选项 | 说明 |
|------|------|
| `query` | 搜索关键词（可选，不提供则返回全部） |
| `--class, -c <类名>` | 按类名过滤个体 |
| `--property, -p <属性>` | 按属性过滤（`name` 或 `name=value`） |
| `--hierarchy, -H <类名>` | 显示指定类的层次结构 |
| `--category` | 搜索类别：`all` / `classes` / `individuals`（默认 `all`） |
| `--limit, -n <数量>` | 最大返回数量（默认 20） |
| `--output, -O <文件>` | 将结果导出为 JSON 文件 |

**输出格式**：

```
  [CLASS] NuclearFuel — 核燃料材料基类
  [IND]   U_10Mo_monolithic_fuel → NuclearFuel
  [ITEM]  U-Zr合金
```

---

### 4.3 `ontofuel export` — 数据导出

将本体数据导出为多种格式。

```bash
# JSON 格式（完整本体数据）
ontofuel export json output.json

# CSV 格式
ontofuel export csv-classes classes.csv        # 类列表
ontofuel export csv-individuals individuals.csv # 个体列表
ontofuel export csv-properties properties.csv   # 属性列表

# GraphML 格式（用于 Gephi、Cytoscape 等图分析工具）
ontofuel export graphml graph.graphml

# Markdown 报告
ontofuel export markdown report.md
```

**支持的格式**：

| 格式 | 说明 | 用途 |
|------|------|------|
| `json` | JSON | 数据交换、程序处理 |
| `csv-classes` | CSV | 类列表查看、Excel 分析 |
| `csv-individuals` | CSV | 个体列表查看 |
| `csv-properties` | CSV | 属性列表查看 |
| `graphml` | GraphML | 图分析工具（Gephi、Cytoscape） |
| `markdown` | Markdown | 可读性报告 |

---

### 4.4 `ontofuel validate` — 质量验证

对本体进行多维度质量评估。

```bash
# 快速健康检查
ontofuel validate --quick

# 完整质量评估（5 维度打分）
ontofuel validate

# 将评估报告保存为 JSON
ontofuel validate --output report.json
```

**快速检查项**：

快速检查返回若干布尔值，标识关键健康指标是否通过。

**完整评估维度**：

| 维度 | 说明 | 评估内容 |
|------|------|----------|
| 命名规范 | 命名一致性 | 检查类名、属性名是否遵循统一命名规范 |
| 结构完整性 | 本体结构 | 检查类层次、属性域范围等结构关系 |
| 语义一致性 | 语义正确性 | 检查是否有语义矛盾或不合理的关系 |
| 数据完整性 | 数据填充率 | 检查必填属性是否都有值 |
| 覆盖度 | 领域覆盖 | 评估本体对目标领域的覆盖范围 |

**评分体系**：

总分 100 分，按等级划分：

| 分数 | 等级 |
|------|------|
| 90–100 | A（优秀） |
| 80–89 | B（良好） |
| 70–79 | C（一般） |
| 60–69 | D（需改进） |
| < 60 | F（不合格） |

**选项**：

| 选项 | 说明 |
|------|------|
| `--quick, -q` | 快速健康检查 |
| `--output, -O <文件>` | 将完整报告保存为 JSON |

---

### 4.5 `ontofuel viz` — 可视化服务

启动 Web 可视化服务器，以 D3.js 力导向图展示本体知识图谱。

```bash
# 启动可视化（默认端口 9999，自动打开浏览器）
ontofuel viz

# 指定端口
ontofuel viz --port 8080

# 指定数据目录
ontofuel viz --data-dir /path/to/ontology

# 不自动打开浏览器
ontofuel viz --no-browser
```

**选项**：

| 选项 | 说明 |
|------|------|
| `--port, -p <端口>` | 服务端口（默认 9999） |
| `--data-dir, -d <目录>` | 本体数据目录 |
| `--no-browser` | 不自动打开浏览器 |

---

## 5. 常用场景

### 5.1 本体查询与搜索

**场景**：查找所有核燃料类型的材料及其属性。

```bash
# 1. 查看 NuclearFuel 类的层次结构
ontofuel query --hierarchy NuclearFuel

# 2. 列出所有 NuclearFuel 个体
ontofuel query --class NuclearFuel

# 3. 搜索特定材料
ontofuel query "U-10Mo"

# 4. 按密度属性搜索
ontofuel query --property "density"

# 5. 导出查询结果
ontofuel query --class NuclearFuel --output nuclear_fuels.json
```

### 5.2 数据提取流程

OntoFuel 支持从 PDF/Markdown 文档中提取结构化材料数据。提取流程如下：

```
原始文档 → 文本分段 → 知识提取 → 结果合并 → 本体更新
```

**各阶段说明**：

| 阶段 | 模块 | 说明 |
|------|------|------|
| 文本分段 | `Segmenter` | 将长文档按标题或固定大小切分为块 |
| 知识提取 | `Extractor` | 从文本块中提取材料个体、属性和关系 |
| 结果合并 | `Merger` | 合并多个提取结果，处理重复和冲突 |
| 本体更新 | `Updater` | 将合并后的结果增量写入本体 |

**分段策略**：

- **标题分段**：按 `##` / `###` 标题切分，适合结构化文档
- **固定分段**：按字符数（默认 4000）切分，适合无结构文本

**提取策略**：

- **规则提取**：正则模式匹配常见材料科学数据（成分、性能等）
- **模板提取**：使用属性模板进行结构化提取

### 5.3 可视化浏览

**场景**：交互式浏览本体知识图谱。

```bash
# 启动可视化
ontofuel viz

# 在浏览器中可以：
# - 搜索节点
# - 按类过滤
# - 缩放和拖拽
# - 查看节点详情
```

### 5.4 Docker 部署使用

**场景**：在生产环境或隔离环境中部署 OntoFuel。

```bash
# 1. 进入 Docker 目录
cd docker

# 2. （可选）配置环境变量
cp .env.example .env
# 编辑 .env 设置密码等

# 3. 启动所有服务
docker compose up -d

# 4. 验证服务
curl http://localhost:8000/health   # API 健康检查
open http://localhost:3000          # Web 前端

# 5. 查看日志
docker compose logs -f

# 6. 停止服务
docker compose down

# 7. 停止并清除数据卷
docker compose down -v
```

**环境变量配置**（`.env` 文件）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码 |
| `POSTGRES_DB` | `ontofuel` | 数据库名称 |
| `SUPABASE_SERVICE_KEY` | （空） | Supabase 服务密钥 |

---

## 6. 配置说明

### 6.1 环境变量

OntoFuel 通过环境变量进行配置，无需修改代码。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ONTOFUEL_ONTOLOGY_PATH` | 自动检测 | 本体 JSON 文件路径 |
| `DATABASE_URL` | — | PostgreSQL 连接字符串（Docker 模式） |
| `SUPABASE_SERVICE_KEY` | — | Supabase 服务端密钥 |
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码（Docker 模式） |
| `POSTGRES_DB` | `ontofuel` | 数据库名称（Docker 模式） |

### 6.2 本体文件自动检测

当不指定 `--ontology` 参数时，OntoFuel 按以下顺序查找本体文件：

1. 当前目录下的 `material_ontology_enhanced.json`
2. `ontology/material_ontology_enhanced.json`
3. 包内自带的默认本体

### 6.3 Docker Compose 配置

Docker 部署通过 `docker/docker-compose.yml` 管理：

```yaml
services:
  db:      # PostgreSQL 数据库（端口 5432）
  api:     # REST API 服务（端口 8000）
  web:     # Web 前端界面（端口 3000）
```

自定义端口映射：

```bash
# 修改端口（例如 API 使用 9000）
API_PORT=9000 docker compose up -d
```

---

## 7. 故障排查

### 常见问题

#### `ontofuel: command not found`

**原因**：未正确安装或未激活虚拟环境。

**解决**：

```bash
# 检查是否在虚拟环境中
which python3

# 重新安装
pip install -e ".[dev]"

# 或直接用模块方式运行
python3 -m ontofuel.cli --help
```

#### 本体文件找不到

**原因**：默认路径下没有本体 JSON 文件。

**解决**：

```bash
# 手动指定本体文件
ontofuel -o /path/to/ontology.json stats

# 或设置环境变量
export ONTOFUEL_ONTOLOGY_PATH=/path/to/ontology.json
ontofuel stats
```

#### Docker 数据库连接失败

**原因**：数据库未就绪或连接配置错误。

**解决**：

```bash
# 检查数据库是否运行
docker compose ps db

# 查看数据库日志
docker compose logs db

# 等待数据库就绪后重启 API
docker compose restart api
```

#### 可视化页面空白

**原因**：本体数据未加载或端口被占用。

**解决**：

```bash
# 检查本体文件是否存在
ls -la ontology/

# 尝试指定数据目录
ontofuel viz --data-dir ontology/

# 更换端口
ontofuel viz --port 8080
```

#### 查询结果为空

**原因**：搜索关键词不匹配或本体数据为空。

**解决**：

```bash
# 先确认本体有数据
ontofuel stats

# 尝试模糊搜索
ontofuel query "U"

# 查看所有类名
ontofuel query --category classes ""
```

#### 导出文件编码错误

**原因**：终端编码设置不正确。

**解决**：

```bash
# 确保使用 UTF-8 编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# 或在 Windows 上
chcp 65001
```

### 获取更多帮助

- **GitHub Issues**：[https://github.com/Etoile04/ontofuel/issues](https://github.com/Etoile04/ontofuel/issues)
- **项目文档**：`docs/` 目录下的其他文档
- **CLI 帮助**：`ontofuel --help` 或 `ontofuel <command> --help`

---

*本文档最后更新：2026-05-03*
