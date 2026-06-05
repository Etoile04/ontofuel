# Plan: CI 质量门禁（T2.1a + T2.1b）

**项目：** ci-quality-gates
**规模：** M 级
**创建时间：** 2026-06-05
**状态：** Draft

---

## Task List

### T1: 配置 ruff + 本地 lint 修复 — 预计 45 min

- [ ] T1: 添加 ruff 配置到 pyproject.toml + 修复 lint 问题
  - files: `pyproject.toml`, `src/**/*.py`, `tests/**/*.py`
  - fail_test: `ruff check src/ tests/` → 预期发现 lint issues
  - impl: 添加 `[tool.ruff]` 配置，运行 `ruff check --fix` + `ruff format`
  - pass_test: `ruff check src/ tests/` → 0 errors + `ruff format --check src/ tests/` → 无差异
  - assign: subagent-1

### T2: 修复 6 个失败测试 — 预计 30 min

- [ ] T2: 修复 elastic constants 和 restore 测试失败
  - files: `tests/test_ontology_elastic_constants.py`, `tests/test_restore.py`, `src/ontofuel/database/restore.py`
  - fail_test: `pytest tests/test_ontology_elastic_constants.py tests/test_restore.py -v` → 6 failed
  - impl: 分析失败原因，修复测试或源码
  - pass_test: `pytest tests/test_ontology_elastic_constants.py tests/test_restore.py -v` → 0 failed
  - assign: subagent-2

### T3: 补充覆盖率测试 — 预计 45 min

- [ ] T3: 为 segmenter.py 和 database/client.py 补充测试，达到 90%
  - files: `tests/test_segmenter.py`, `tests/test_database_client.py`（新建或扩展）
  - fail_test: `pytest --cov=ontofuel --cov-report=term-missing` → 88%
  - impl: 针对未覆盖行编写测试（segmenter 62 行 + client 20 行 + 其他小缺口）
  - pass_test: `pytest --cov=ontofuel --cov-report=term-missing` → >= 90%
  - assign: subagent-3

### T4: CI workflow 更新 — 预计 20 min

- [ ] T4: 新增 lint.yml + 修改 test.yml 添加覆盖率门禁
  - files: `.github/workflows/lint.yml`（新建）, `.github/workflows/test.yml`（修改）
  - impl: 创建独立 lint job + 在 test.yml 添加 coverage threshold check
  - pass_test: 审查 workflow YAML 语法正确
  - assign: main（PM 执行，等 T1-T3 完成后）
  - deps: [T1, T2, T3]

### T5: 端到端验证 — 预计 10 min

- [ ] T5: 完整 CI 模拟验证
  - impl: 本地运行完整 test + lint + coverage check
  - pass_test: 全部通过，覆盖率 >= 90%
  - assign: main
  - deps: [T1, T2, T3, T4]

### 执行策略

- **Phase 1（并行）**：T1 + T2 + T3 三个 subagent 并行
- **Phase 2（串行）**：T4 等待 Phase 1 完成
- **Phase 3（串行）**：T5 最终验证
