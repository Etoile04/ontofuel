# Spec: CI 质量门禁（T2.1a + T2.1b）

**项目：** ci-quality-gates
**KR 对齐：** O2.1 CI/CD 全流程
**创建时间：** 2026-06-05
**状态：** Draft

---

## 1. 背景与目标

### 当前状态
- ✅ `test.yml`：Python 3.12/3.13 矩阵测试 + Codecov 上传
- ✅ `docker-image.yml`：Docker Hub 自动发布
- ❌ 无 lint step
- ❌ 无覆盖率门禁（只上传，不阻塞 PR/merge）
- 当前覆盖率：**88%**（TOTAL 1367 stmts, 165 miss）
- 6 个测试失败（elastic constants + restore）
- 最大缺口：`segmenter.py` 69%

### 目标状态
1. CI pipeline 中添加 ruff lint + format check step
2. CI pipeline 中添加覆盖率 >= 90% 门禁
3. 修复导致测试失败的代码，使 baseline 全绿
4. 补充测试使覆盖率达到 90%

### 决策
- **D001：** Lint 工具 = ruff（lint + format + import sort 三合一）
- **D002：** 覆盖率阈值 = 90%

---

## 2. 技术方案

### 2.1 ruff 配置

在 `pyproject.toml` 中添加 `[tool.ruff]` 配置：

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### 2.2 CI workflow 更新

**新增 `lint.yml` workflow**（独立 job，与 test 并行运行）：

```yaml
name: Lint
on: [push, pull_request]
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-ruff@v3
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/
```

**修改 `test.yml`**，添加独立覆盖率门禁 step（仅 3.12）：

```yaml
    - name: Enforce coverage gate
      if: matrix.python-version == '3.12'
      run: pytest tests/ --ignore=tests/test_docker_integration.py --cov=ontofuel --cov-fail-under=90 --cov-report=term-missing -q
```

> 使用 pytest-cov 内置的 `--cov-fail-under` 参数，比 XML 解析更简洁可靠。
> 仅在 Python 3.12 job 检查，3.13 为辅助验证。

### 2.3 覆盖率缺口分析

需要补充测试的文件（按缺口排序）：

| 文件 | 当前覆盖率 | 未覆盖行数 | 优先级 |
|------|-----------|-----------|--------|
| `segmenter.py` | 69% | 62 | P0 |
| `database/client.py` | 78% | 20 | P0 |
| `visualization/__init__.py` | 77% | 6 | P1 |
| `extractor.py` | 84% | 20 | P1 |
| `_compat.py` | 88% | 2 | P2 |
| `ontology.py` | 87% | 8 | P2 |
| `restore.py` | 90% | 8 | P2 |
| `updater.py` | 91% | 13 | P2 |

**总缺口：165 → 137 行（达 90% 需覆盖 ~137 行新覆盖）**

---

## 3. 约束

- 不修改生产代码逻辑（只添加测试）
- ruff 规则不能产生大量 false positive
- CI 不能显著增加运行时间（lint 应 < 30s）
- coverage gate 在 Python 3.12 job 上检查（3.13 为辅助）

---

## 4. 验收标准

- [ ] ruff check 通过（0 errors, 0 warnings）
- [ ] ruff format --check 通过（无格式差异）
- [ ] 所有测试通过（0 failed）
- [ ] 覆盖率 >= 90%
- [ ] CI lint job < 30s
- [ ] pyproject.toml 中 ruff 配置完整
