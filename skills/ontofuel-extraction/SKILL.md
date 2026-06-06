---
name: ontofuel-extraction
description: "OntoFuel 超长文档本体提取系统。用于从大型 PDF/文档（200-2000 页）中提取结构化材料知识并映射到领域本体。核心能力：章节分割→提取计划生成→并行 agent 提取→结果合并→本体增量更新。支持断点续传、智能模型切换、自动恢复。触发词：本体提取、ontology extraction、材料数据提取、文档本体化、PDF 本体、ontofuel、超长文档提取、章节提取。"
---

# OntoFuel Extraction (v2.1)

## 概述

OntoFuel 从大型 PDF 文档中提取结构化材料知识，映射到领域本体（JSON 格式），输出新个体（Individuals）和属性值。

**核心流程**：PDF → 章节分割 → 提取计划 → 并行提取 → 合并去重 → 本体更新

**适用场景**：
- 材料科学手册（500-2000 页）
- 核燃料性能数据报告
- 合金体系文献综述
- 任何有结构化章节的大型技术文档

**不适用场景**：
- 单篇论文（用 ontology-driven-extraction）
- 无结构化的文本（需要先做 NER）
- 非材料科学领域（需先适配本体）

---

## 工具清单

| 工具 | 位置 | 用途 |
|------|------|------|
| `segment_book.py` | `skills/ontofuel-extraction/scripts/` | PDF 章节分割 |
| `generate_extraction_plan.py` | 同上 | 生成章节级提取计划 |
| `run_parallel_extraction.py` | 同上 | 并行 agent 提取 |
| `merge_extractions.py` | 同上 | 合并去重结果 |
| `update_ontology.py` | 同上 | 本体增量更新 |
| `monitor.py` | 同上 | 后台进度监控 |
| `progress_persistence.py` | 同上 | 断点续传 |
| `model_switcher.py` | 同上 | 智能模型切换 |

---

## 完整提取流程

### Step 1: PDF 预处理

🔴 **CHECKPOINT** — 必须串行执行，禁止并发操作同一 PDF

```bash
# 输入：PDF 文件路径
# 输出：章节 JSON 文件

cd ~/.openclaw/workspace-extractor

python3 skills/ontofuel-extraction/scripts/segment_book.py \
  --input "path/to/handbook.pdf" \
  --output "data/segments.json" \
  --min-pages 5 \
  --toc-pages 10
```

**验证输出**：
```bash
# 确认章节数量和页数
python3 -c "
import json
with open('data/segments.json') as f:
    segs = json.load(f)
for s in segs:
    print(f\"  {s['chapter_id']}: {s['title']} ({s['start_page']}-{s['end_page']}, {s['page_count']}p)\")
print(f'总计: {len(segs)} 章节')
"
```

**如果目录提取失败**（PDF 无目录）→ 使用 `--mode by-page --chunk-size 50` 按固定页数分割。

### Step 2: 生成提取计划

```bash
# 输入：章节 JSON + 本体文件
# 输出：提取计划 JSON

python3 skills/ontofuel-extraction/scripts/generate_extraction_plan.py \
  --segments "data/segments.json" \
  --ontology "memory/trustgraph-fix/material_ontology_enhanced.json" \
  --output "data/extraction_plan.json" \
  --max-chapter-tokens 8000
```

提取计划包含每章的：
- 目标本体类（从 `classes` 中匹配）
- 目标属性（从 `datatypeProperties` 中匹配）
- 提取 prompt 模板

🔴 **CHECKPOINT** — 展示提取计划给用户确认，确认后再执行

### Step 3: 并行提取

```bash
# 输入：提取计划 + PDF + 本体
# 输出：各章节提取结果 JSON

python3 skills/ontofuel-extraction/scripts/run_parallel_extraction.py \
  --plan "data/extraction_plan.json" \
  --pdf "path/to/handbook.pdf" \
  --ontology "memory/trustgraph-fix/material_ontology_enhanced.json" \
  --output "data/extractions/" \
  --concurrency 2 \
  --timeout 600 \
  --progress "progress.json"
```

**参数说明**：
- `--concurrency 2`：同时运行 2 个 agent（默认，可调至 5）
- `--timeout 600`：每章节最长 10 分钟
- `--progress`：启用断点续传

**每个 agent 执行的提取逻辑**：

```
对于每个章节：
1. 读取章节文本（从 segment_book 输出）
2. 读取匹配的本体类和属性定义
3. 构造提取 prompt：
   - 系统：你是材料数据提取专家
   - 上下文：本体类定义 + 属性列表
   - 输入：章节全文
   - 输出格式：JSON 数组，每个元素是一个个体
4. 调用 LLM，解析 JSON 输出
5. 验证输出：
   - 每个个体必须有 name 和 type
   - type 必须匹配本体中的类名
   - 属性名必须在 datatypeProperties 中存在
6. 标记置信度（0-1）
7. 写入结果文件
```

**提取输出格式**：
```json
{
  "chapter_id": "ch5",
  "chapter_title": "U-Mo 合金燃料性能",
  "extraction_time": "2026-03-01T10:00:00",
  "model": "zai/glm-5.1",
  "individuals": [
    {
      "name": "U-10Mo_monolithic_fuel",
      "type": "NuclearFuel",
      "properties": {
        "density": {"value": 17.0, "unit": "g/cm³", "confidence": 0.95},
        "meltingPoint": {"value": 1133, "unit": "°C", "confidence": 0.90}
      },
      "source_text": "U-10Mo monolithic fuel has a density of 17.0 g/cm³...",
      "confidence": 0.92
    }
  ],
  "stats": {
    "individuals_count": 5,
    "properties_count": 23,
    "avg_confidence": 0.91
  }
}
```

### Step 4: 合并去重

```bash
# 输入：各章节提取结果目录
# 输出：合并后的 JSON

python3 skills/ontofuel-extraction/scripts/merge_extractions.py \
  --input "data/extractions/" \
  --output "data/merged_extraction.json" \
  --dedup-strategy "fuzzy" \
  --similarity-threshold 0.85
```

**去重策略**：
- `exact`：名称完全匹配
- `fuzzy`：名称相似度 > 阈值（默认 0.85）
- `semantic`：用 LLM 判断是否为同一实体（最慢但最准）

**冲突解决**：
- 同一属性多个值 → 保留置信度最高的
- 不同类型冲突 → 保留源文本更完整的

### Step 5: 更新本体

🛑 **STOP** — 本体更新前必须人工确认提取结果

```bash
# 输入：合并后的提取结果 + 现有本体
# 输出：更新后的本体文件（带备份）

python3 skills/ontofuel-extraction/scripts/update_ontology.py \
  --extraction "data/merged_extraction.json" \
  --ontology "memory/trustgraph-fix/material_ontology_enhanced.json" \
  --backup \
  --dry-run  # 先 dry-run 看变更预览
```

**dry-run 输出示例**：
```
=== 本体更新预览 ===
新增个体: 25
新增属性值: 120
更新属性值: 15
跳过(重复): 8
本体版本: v1.10.5 → v1.10.6

确认执行？移除 --dry-run 参数以实际更新。
```

确认无误后移除 `--dry-run` 执行实际更新。

---

## 运维功能

### 断点续传

```bash
# 查看当前进度
python3 skills/ontofuel-extraction/scripts/progress_persistence.py summary

# 从断点恢复（在 run_parallel_extraction 中自动生效）
# 如果手动恢复：
python3 skills/ontofuel-extraction/scripts/run_parallel_extraction.py \
  --plan "data/extraction_plan.json" \
  --resume "progress.json"
```

### 智能模型切换

当 API 限流时自动切换到本地模型：

```bash
# 查看当前模型状态
python3 skills/ontofuel-extraction/scripts/model_switcher.py status

# 手动切换
python3 skills/ontofuel-extraction/scripts/model_switcher.py switch ollama/qwen3-coder-next

# 恢复远程模型
python3 skills/ontofuel-extraction/scripts/model_switcher.py restore
```

模型优先级：`zai/glm-5.1` → `zai/glm-4.7` → `ollama/qwen3-coder-next`

### 后台监控

```bash
python3 skills/ontofuel-extraction/scripts/monitor.py \
  --progress progress.json \
  --interval 300 &

echo $! > monitor.pid
```

触发恢复条件：连续 3 次检查无进展 / Gateway 不健康 / API 限流。

---

## 失败模式与 fallback

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|-----------|
| PDF 无目录 / 目录解析为空 | `--mode by-page --chunk-size 50` 按页分割 | 手动指定章节范围：`--ranges "1-50,51-100"` |
| LLM 输出不是合法 JSON | 重试 1 次，附带错误反馈 | 降级为文本正则提取关键数值 |
| 章节文本超过 8000 tokens | `--max-chapter-tokens 4000` 切分章节 | 子章节级提取后合并 |
| 所有模型都不可用 | 等待 60 秒重试远程模型 | 暂停任务，通知用户手动干预 |
| 本体类匹配率 < 50% | 检查 PDF 是否为非材料领域文档 | 扩展本体或切换通用提取模式 |
| 去重发现 > 30% 重复 | 检查章节分割是否重叠 | 调整 `--similarity-threshold` 至 0.90 |
| `progress.json` 损坏 | 从提取结果目录重建进度 | 从头重新运行（最坏情况） |
| `update_ontology.py` dry-run 报异常 | 检查提取结果格式是否符合 schema | 逐个个体验证后分批更新 |

---

## 🚫 反例与黑名单

**禁止操作**：

| # | 禁止 | 原因 | 正确做法 |
|---|------|------|---------|
| 1 | 并发操作同一个 PDF 文件 | 文件锁冲突导致数据损坏 | PDF 预处理必须串行 |
| 2 | 跳过 dry-run 直接更新本体 | 不可逆操作可能污染数据 | 先 `--dry-run` 预览再确认 |
| 3 | 不备份本体文件就更新 | 无法回滚错误更新 | 使用 `--backup` 参数 |
| 4 | `concurrency > 5` | 触发 API 限流 | 最多 5 个并行 agent |
| 5 | 在 Step 2 跳过用户确认 | 提取计划可能有误匹配 | 🔴 必须人工确认计划 |
| 6 | 使用 `rm` 删除提取结果 | 数据不可恢复 | 使用 `trash` 或移至备份目录 |
| 7 | 忽略置信度 < 0.5 的提取结果 | 低质量数据污染本体 | 标记为 `needs_review` |
| 8 | 一次性处理 > 2000 页文档 | 上下文窗口溢出 | 分卷处理，每卷 ≤ 500 页 |

---

## 配置

默认配置文件：`skills/ontofuel-extraction/config/default.json`

```json
{
  "model": {
    "primary": "zai/glm-5.1",
    "fallbacks": ["zai/glm-4.7", "ollama/qwen3-coder-next"]
  },
  "subagents": {
    "maxConcurrent": 2,
    "timeout": 600
  },
  "extraction": {
    "maxChapterTokens": 8000,
    "minConfidence": 0.5,
    "dedupStrategy": "fuzzy",
    "similarityThreshold": 0.85
  }
}
```

---

## 相关资源

- **本体文件**: `memory/trustgraph-fix/material_ontology_enhanced.json`
- **本体可视化**: `memory/trustgraph-fix/material_ontology_docs.html`
- **通用本体提取模式**: `~/.openclaw/skills/ontology-driven-extraction/SKILL.md`
- **Zotero 文献搜索**: `skills/zotero-ontology-research/SKILL.md`
