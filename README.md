# OntoFuel

**本体驱动的核材料知识提取系统**

OntoFuel 是一个面向核材料领域的本体驱动知识提取与管理系统。它能够从超长文档（200-2000页）中自动提取结构化材料数据，并将结果整合到本体知识库中。

## ✨ 核心功能

- **📖 超长文档提取** — 支持 200-2000 页 PDF/Markdown 文档的章节分割与并行提取
- **🔍 智能知识提取** — 规则 + 模板驱动的合金成分、物理性能、相结构自动识别
- **🔄 增量更新** — 本体增量合并、去重、冲突解决
- **📊 本体验证** — 5 维质量评估（命名/结构/语义/完整/覆盖）
- **🖥️ Web 可视化** — D3.js 力导向图，支持搜索、过滤、缩放
- **💾 数据库集成** — Supabase (PostgreSQL) 存储，REST API

## 📦 安装

```bash
# 从源码安装
git clone https://github.com/Etoile04/ontofuel.git
cd ontofuel
pip install -e ".[dev]"

# 验证安装
ontofuel --help
```

**零运行时依赖** — 核心功能全部使用 Python 标准库。

## 🚀 快速开始

```bash
# 查看本体统计
ontofuel stats

# 搜索材料
ontofuel query "U-10Mo"
ontofuel query --class NuclearFuel

# 导出
ontofuel export json output.json
ontofuel export graphml graph.graphml
ontofuel export markdown report.md

# 质量评估
ontofuel validate
ontofuel validate --quick

# 启动可视化
ontofuel viz --port 9999
```

## 🏗️ 项目结构

```
ontofuel/
├── src/ontofuel/           # 核心包
│   ├── core/               # 核心模块
│   │   ├── ontology.py     # 本体加载与查询
│   │   ├── query.py        # 搜索引擎
│   │   ├── exporter.py     # 多格式导出
│   │   └── validator.py    # 质量评估
│   ├── extraction/         # 提取模块
│   │   ├── segmenter.py    # 文本分段
│   │   ├── extractor.py    # 知识提取
│   │   ├── merger.py       # 结果合并
│   │   └── updater.py      # 本体更新
│   ├── database/           # 数据库模块
│   │   ├── client.py       # Supabase 客户端
│   │   ├── schema.py       # 表结构定义
│   │   └── restore.py      # 数据恢复
│   ├── visualization/      # Web 可视化
│   └── cli.py              # 命令行工具
├── ontology/               # 本体数据
│   ├── material_ontology_enhanced.json   # 主本体 (738KB)
│   └── nvl_ontology_data.json            # NVL 可视化数据
├── tests/                  # 测试套件 (139 tests)
├── docs/                   # 文档
└── scripts/                # 辅助脚本
```

## 📊 本体数据

| 指标 | 数值 |
|------|------|
| 类 (Classes) | 139 |
| 对象属性 | 162 |
| 数据属性 | 279 |
| 个体 (Individuals) | 755 |
| 质量评分 | 80/100 (A) |

覆盖领域：核燃料、包壳材料、冷却剂、高熵合金、辐照效应、扩散系数、热物理性能等。

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

## 📜 许可证

MIT License

## 🙏 致谢

- 本体质量评估借鉴了 [OntoCast](https://github.com/growgraph/ontocast) 的设计
- 可视化基于 [D3.js](https://d3js.org/)
- 文档解析支持 [MinerU](https://github.com/opendatalab/MinerU)
