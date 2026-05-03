# Superpowers 开发流程

## 概述

OntoFuel 项目使用 **Superpowers 技能集** 驱动开发流程。Superpowers 是一套结构化的 AI 辅助开发方法论，确保从需求到交付的每一步都有质量保障。

## 流程总览

```
Brainstorming → Writing-Plans → Subagent-Driven Development → Finishing-Branch
    (探索)          (规划)            (实现 + 审查)            (收尾)
```

每个阶段都有明确的输入、输出和质量门禁。**禁止跳过任何阶段。**

---

## 1. Brainstorming 阶段

**目标**: 从模糊的需求到清晰的 spec。

### 步骤

1. **探索上下文** — 阅读现有代码、文档、相关 issue，理解现状
2. **澄清需求** — 与用户确认边界、约束、预期行为
3. **提出方案** — 列出可行方案，标注优劣和 trade-off
4. **写 spec** — 输出为 `docs/superpowers/specs/<feature-name>.md`
5. **用户审批** — 用户确认 spec 后才进入下一阶段

### Spec 模板

```markdown
# <Feature Name>

## 目标
<!-- 一句话描述 -->

## 背景
<!-- 为什么需要这个功能 -->

## 行为规格
### 正常流程
<!-- 步骤描述 -->

### 边界情况
<!-- 异常、空值、并发等 -->

## 约束
<!-- 性能、兼容性、安全等 -->

## 验收标准
<!-- 可测试的完成条件 -->
```

**输出**: 用户批准的 spec 文件。

---

## 2. Writing-Plans 阶段

**目标**: 将 spec 分解为可直接执行的 bite-sized tasks。

### 原则

- 每个 task 预估 **2-5 分钟** 完成时间
- 每个 task 包含 **精确的文件路径**
- 每个 task 包含 **完整的代码**（不使用 "..." 占位）
- 每个 task 包含 **测试用例**

### Plan 模板

```markdown
# Plan: <Feature Name>

## Task 1: <具体描述>
- 文件: `src/module/file.py`
- 预估: 2 min
- 代码: (完整代码)
- 测试: (完整测试代码)

## Task 2: ...
```

Plan 文件保存到 `docs/superpowers/plans/<feature-name>-plan.md`。

**输出**: 用户批准的 plan 文件。

---

## 3. Subagent-Driven Development 阶段

**目标**: 通过多个专门化的 subagent 并行/串行实现 tasks，并经过独立审查。

### 角色分工

| 角色 | 职责 | 模型建议 |
|------|------|----------|
| **Implementer** | 按 TDD 流程实现代码 | 标准/快速 |
| **Spec Reviewer** | 对照 spec 独立验证实现 | 标准 |
| **Code Quality Reviewer** | 审查代码质量、风格、潜在问题 | 标准 |

### 单个 Task 的执行流程

```
Implement (TDD: Red → Green → Refactor)
    ↓
Spec Review (对照 spec 逐条验证)
    ↓
Code Quality Review (代码质量审查)
    ↓
┌─ Pass → mark complete ✅
└─ Fail → Fix Loop → 重新审查
```

### TDD: Red → Green → Refactor

1. **Red** — 先写测试，确认测试失败
2. **Green** — 写最少的代码让测试通过
3. **Refactor** — 在测试保护下重构

### Spec Review 要点

- **不信任 implementer 的 self-report** — 独立运行测试验证
- 逐条对照 spec 的验收标准
- 检查边界情况是否覆盖
- 检查是否有 spec 未要求的"额外功能"

### Code Quality Review 要点

- 代码可读性和命名
- 错误处理是否完善
- 是否有潜在的性能问题
- 是否遵循项目约定

---

## 4. Finishing-Branch 阶段

**目标**: 验证整体质量，合并或发布。

### 步骤

1. **验证测试** — 运行完整测试套件，确保全部通过
2. **选择收尾方式** (4 个选项):
   - **Merge to main** — 直接合并
   - **Create PR** — 创建 Pull Request 待审查
   - **Squash & Merge** — 压缩提交后合并
   - **Archive** — 归档分支，暂不合并
3. **执行** — 执行选定的操作
4. **清理** — 删除临时分支、更新文档、归档 spec/plan

---

## 模型选择指南

| 场景 | 推荐模型级别 | 说明 |
|------|-------------|------|
| 机械性任务（格式化、重命名） | 快速/廉价 | 低风险、高确定性 |
| 集成任务（实现功能、写测试） | 标准 | 平衡质量和成本 |
| 架构决策（设计 API、重构） | 最强 | 高风险、需要深度思考 |

---

## 红线 🚫

以下行为**严格禁止**：

1. **禁止跳过 Brainstorming** — 没有 spec 就不写代码
2. **禁止跳过 TDD** — 先写测试，再写实现
3. **禁止跳过 Spec Review** — 必须独立验证
4. **禁止跳过 Code Review** — 必须有质量审查
5. **禁止猜测式调试** — 遇到 bug 用 Systematic Debugging 流程，不要盲改

---

## 目录结构

```
docs/superpowers/
├── CONTRIBUTING.md          # 本文档
├── specs/                   # Brainstorming 阶段的 spec 文件
│   └── <feature-name>.md
└── plans/                   # Writing-Plans 阶段的 plan 文件
    └── <feature-name>-plan.md
```

---

## 技能集参考

Superpowers 包含以下技能，按需调用：

| 技能 | 用途 |
|------|------|
| `brainstorming` | 探索需求和方案 |
| `writing-plans` | 分解任务 |
| `executing-plans` | 执行计划 |
| `subagent-driven-development` | 多 agent 协作开发 |
| `test-driven-development` | TDD 流程 |
| `systematic-debugging` | 系统化调试 |
| `finishing-a-development-branch` | 分支收尾 |
| `using-superpowers` | 流程总览 |
| `verification-before-completion` | 完成前验证 |
| `receiving-code-review` | 接受代码审查 |
| `requesting-code-review` | 发起代码审查 |
| `coding-agent-enhanced` | 增强的编码 agent |
| `super-spec` | 高级 spec 编写 |

---

*最后更新: 2026-05-02*
