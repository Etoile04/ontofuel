# Q3 Task Breakdown — 可执行任务分解

**创建时间**: 2026-05-27
**目标**: 把 20 个 KR 拆成可在一周内完成的 bite-sized tasks

---

## O1: 知识图谱扩展 (P0)

### KR 1.1: 本体个体数 755 → 1000+ (+245)
需要从文献中系统性提取，按材料类别分批：

| Task | 新增个体 | 来源 | 预计耗时 |
|------|---------|------|---------|
| T1.1a: U-Zr 合金性能数据 | 30 | Zotero 现有文献 | 2h |
| T1.1b: U-Mo 燃料辐照数据 | 40 | ANL Handbook + ScienceDirect | 3h |
| T1.1c: 结构材料（SS316/HT9/T91） | 50 | 材料手册 | 4h |
| T1.1d: 冷却剂材料（Na/PbBi/He） | 25 | 手册 + 文献 | 2h |
| T1.1e: 陶瓷材料（SiC/Al₂O₃/UN） | 30 | 文献补充 | 2h |
| T1.1f: 高熵合金扩展 | 40 | 2025-2026 新文献 | 3h |
| T1.1g: 包壳材料（Zr合金/FeCrAl） | 30 | 手册 | 2h |

**执行方式**: 每批使用 OntoFuel extraction pipeline + subagent parallel

### KR 1.2: OntoCast 集成
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T1.2a: GraphUpdate 模块集成到 OntoFuel | Token 节省 80-95% | 4h |
| T1.2b: 本体升华机制集成 | 自动分离本体/事实 | 3h |
| T1.2c: 版本控制集成 | 替代手动备份 | 2h |
| T1.2d: LLM 本体批判集成 | 质量保证 | 3h |

**前置**: 需要安装 OntoCast 依赖

### KR 1.3: SPARQL 查询接口
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T1.3a: 本体 → RDF/Turtle 转换 | JSON → Turtle | 3h |
| T1.3b: 搭建 local SPARQL endpoint | Apache Jena Fuseki | 4h |
| T1.3c: Python SPARQL 查询封装 | 查询 API | 2h |
| T1.3d: 查询示例 + 文档 | 10 个常用查询 | 2h |

### KR 1.4: 知识图谱可视化优化
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T1.4a: NVL 交互增强（缩放/过滤/搜索） | 已有 Fuse.js | 3h |
| T1.4b: GraphML 导出 → Gephi 工作流 | 已有 exportUtils | 2h |
| T1.4c: 本体层级树状视图 | 新组件 | 4h |

---

## O2: 生产级部署 (P1)

### KR 2.1: CI/CD 全流程
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T2.1a: Lint step (ruff/mypy) | 已有 test.yml | 2h |
| T2.1b: Coverage gate (>90%) | Codecov 已配 | 1h |
| T2.1c: Release automation (tag → publish) | GitHub Action | 3h |
| T2.1d: Pre-commit hooks | ruff + mypy | 1h |

### KR 2.2: Docker Hub 自动发布
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T2.2a: Multi-arch build (amd64 + arm64) | docker buildx | 3h |
| T2.2b: Tag策略 (latest + semver) | workflow 更新 | 1h |
| T2.2c: 镜像大小优化 | multi-stage build | 2h |

**前置**: ✅ Docker Hub secrets 已配，镜像已推送

### KR 2.3: 云端 Supabase 迁移方案
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T2.3a: 迁移方案文档 | 架构设计 | 3h |
| T2.3b: 数据导出/导入脚本 | JSON → Supabase Cloud | 4h |
| T2.3c: 环境变量配置方案 | .env management | 1h |

### KR 2.4: 监控告警
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T2.4a: 健康检查 endpoint | FastAPI /health | 2h |
| T2.4b: 日志结构化 | JSON logging | 2h |
| T2.4c: 基础告警（磁盘/内存/服务） | cron + notify | 2h |

---

## O3: 文献管道优化 (P1)

### KR 3.1: ClawTeam 流程完善
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T3.1a: 搜索策略质量检查脚本 | 已有原型 | 2h |
| T3.1b: 本体映射成功率提升 | >95% | 3h |
| T3.1c: 完整大规模测试 (20+ 文献) | 压力测试 | 4h |

### KR 3.2: MinerU 本地部署
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T3.2a: MinerU 本地安装 | pip install | 1h |
| T3.2b: GPU 加速配置 | Magic-PDF | 2h |
| T3.2c: 批量解析性能测试 | vs MCP | 2h |

### KR 3.3: 提取模板系统
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T3.3a: 领域模板 DSL 设计 | YAML/JSON schema | 3h |
| T3.3b: 核燃料模板 | U-Mo/U-Zr/UN | 2h |
| T3.3c: 结构材料模板 | SS/ODS/HEA | 2h |
| T3.3d: 模板渲染引擎 | jinja2/f-string | 3h |

### KR 3.4: 语义搜索增强
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T3.4a: Embedding pipeline | model2vec/sentence-transformers | 3h |
| T3.4b: 向量存储 (pgvector/ChromaDB) | 选型 + 集成 | 4h |
| T3.4c: 混合检索 (关键词 + 向量) | fusion ranking | 3h |
| T3.4d: 评测基准 | MRR/Recall@K | 2h |

**前置**: ✅ model2vec + sentence-transformers 已安装

---

## O4: 开源准备 (P2)

### KR 4.1: README + Quick Start
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T4.1a: README 重写 | 架构图 + 特性列表 | 3h |
| T4.1b: Quick Start guide | 5 分钟上手 | 2h |
| T4.1c: 示例 notebook | 3 个用例 | 3h |

### KR 4.2: API 文档自动生成
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T4.2a: Sphinx/MkDocs 配置 | 选型 + 搭建 | 3h |
| T4.2b: Docstring 补全 | 所有 public API | 4h |
| T4.2c: CI 自动发布文档 | GitHub Pages | 2h |

### KR 4.3: 贡献者指南
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T4.3a: CONTRIBUTING.md | 已有 Superpowers 流程 | 2h |
| T4.3b: Code of Conduct | Contributor Covenant | 1h |
| T4.3c: Issue/PR templates | GitHub templates | 1h |

### KR 4.4: 外部用户试用
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T4.4a: 试用指南文档 | 独立文档 | 2h |
| T4.4b: 收集反馈机制 | Google Form / GitHub Issue | 1h |

---

## O5: 性能优化 (P1)

### KR 5.1: 2000+ 页文档端到端
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T5.1a: 大文档基准测试 | 核工程手册 vol4+5 | 3h |
| T5.1b: 内存优化（分块加载） | streaming | 4h |
| T5.1c: 超时和重试策略 | exponential backoff | 2h |

### KR 5.2: 内存和 Token 优化
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T5.2a: Token 使用基准 | 测量各步骤 | 2h |
| T5.2b: GraphUpdate 集成 (KR 1.2a) | 减少 80-95% token | — |
| T5.2c: 缓存策略 | LRU cache | 3h |

### KR 5.3: 错误恢复
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T5.3a: 进度持久化增强 | 已有原型 | 2h |
| T5.3b: 断点续传机制 | checkpoint file | 3h |
| T5.3c: 自动重试 + 降级 | model switching | 2h |

### KR 5.4: 性能基准套件
| Task | 描述 | 预计耗时 |
|------|------|---------|
| T5.4a: benchmark 框架 | pytest-benchmark | 2h |
| T5.4b: 关键路径基准 | 分段/提取/合并 | 3h |
| T5.4c: CI 集成 + 回归检测 | performance gate | 2h |

---

## 推荐执行顺序 (Q3 第一个月: 7月)

**Week 1-2**: O1 基础 + O5 基准
- T1.1a ~ T1.1c (U-Zr, U-Mo, 结构材料提取)
- T5.4a ~ T5.4b (benchmark 框架)
- T5.1a (大文档基准测试)

**Week 3**: O2 CI + O1 OntoCast
- T2.1a ~ T2.1d (CI/CD 全流程)
- T1.2a ~ T1.2b (GraphUpdate + 升华)

**Week 4**: O3 管道 + O4 文档
- T3.4a ~ T3.4b (语义搜索)
- T4.1a ~ T4.1b (README 重写)
