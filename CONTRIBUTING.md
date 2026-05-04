# 贡献指南

感谢你对 workspace-extractor 项目的关注！无论是修复 Bug、新增功能还是改进文档，我们都非常欢迎你的贡献。

---

## 开发环境设置

### 1. Fork + Clone

1. 在 GitHub 上 Fork 本仓库
2. Clone 你 Fork 的仓库到本地：

```bash
git clone https://github.com/<your-username>/workspace-extractor.git
cd workspace-extractor
```

3. 添加上游仓库：

```bash
git remote add upstream https://github.com/<org>/workspace-extractor.git
```

### 2. 安装依赖

推荐使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"
```

这会安装项目及其所有开发依赖（包括 pytest、linter 等）。

### 3. Pre-commit Hooks（可选）

如果项目配置了 pre-commit，安装并启用：

```bash
pip install pre-commit
pre-commit install
```

---

## 开发流程

### 分支策略

- 所有开发都在 **feature 分支** 上进行，命名格式：`feature/<简短描述>`
- 修复 Bug 使用：`fix/<简短描述>`
- 文档改进使用：`docs/<简短描述>`

```bash
git checkout -b feature/add-new-extractor
```

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>
```

常用 type：

| type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `test` | 测试相关 |
| `refactor` | 代码重构（不影响功能） |
| `chore` | 构建/工具变更 |

示例：

```
feat(extractor): add support for PDF table extraction
fix(ontology): resolve duplicate material entries
docs: update contributing guide
```

### 测试要求

- **所有 PR 必须通过完整的 pytest 测试套件**
- 新功能必须附带对应的测试用例
- Bug 修复应包含回归测试

---

## 代码规范

### Python 风格

- 遵循 **PEP 8** 编码规范
- 使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化（如果配置了）
- 保持函数简洁，单一职责

### Type Hints

- 所有公共函数和类方法必须添加类型注解
- 使用 Python 3.10+ 的类型语法（`X | Y` 代替 `Union[X, Y]`）

```python
def extract_properties(text: str, source: str) -> dict[str, Any]:
    """从文本中提取材料属性。"""
    ...
```

### Docstrings

- 公共 API 必须包含 docstring
- 使用 Google 风格或 NumPy 风格

```python
def calculate_density(mass: float, volume: float) -> float:
    """计算材料密度。

    Args:
        mass: 材料质量（g）。
        volume: 材料体积（cm³）。

    Returns:
        密度值（g/cm³）。
    """
    return mass / volume
```

---

## PR 流程

### 创建 Pull Request

1. 确保你的分支已经与上游同步：

```bash
git fetch upstream
git rebase upstream/main
```

2. 推送到你的 Fork：

```bash
git push origin feature/add-new-extractor
```

3. 在 GitHub 上创建 Pull Request，填写 PR 模板

### CI 检查

所有 PR 会自动运行 CI 检查，包括：

- pytest 测试套件
- 代码风格检查
- 类型检查（如果配置了 mypy/pyright）

请确保所有检查通过。如果 CI 失败，请在本地修复后再推送。

### Code Review

- 至少需要一位维护者 Review 后才能合并
- Review 时请保持友善和建设性
- 收到修改建议后及时响应

---

## 测试指南

### 运行测试

运行全部测试：

```bash
pytest
```

运行指定测试文件：

```bash
pytest tests/test_docs.py
```

运行时显示详细输出：

```bash
pytest -v
```

### 编写新测试

- 测试文件放在 `tests/` 目录下，命名格式：`test_<module>.py`
- 每个测试函数以 `test_` 开头
- 使用清晰的测试名称，描述预期行为

```python
def test_extract_temperature_from_valid_string():
    """应从有效字符串中正确提取温度值。"""
    result = extract_temperature("熔点: 1085°C")
    assert result == 1085.0
```

### 覆盖率

- 目标：核心模块测试覆盖率 ≥ 80%
- 运行覆盖率报告：

```bash
pytest --cov=src --cov-report=term-missing
```

---

## 有问题？

如果你在贡献过程中遇到任何问题，欢迎：

- 在 GitHub Issues 中提问
- 在 PR 中 @ 维护者
- 参考已有代码和测试作为范例

再次感谢你的贡献！🎉
