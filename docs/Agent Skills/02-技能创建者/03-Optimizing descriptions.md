---
title: 优化技能描述
english_title: Optimizing skill descriptions
source_url: https://agentskills.io/skill-creation/optimizing-descriptions.md
source_path: /skill-creation/optimizing-descriptions.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 描述优化
---

# 优化技能描述

本页说明如何改进技能的 `description` 字段，让它在相关提示上稳定触发。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/skill-creation/optimizing-descriptions.md>。

技能只有被激活才有用。`SKILL.md` frontmatter 中的 `description` 是 agent 决定是否加载技能的主要依据。描述过窄会漏触发；描述过宽会在不该触发时触发。

## 技能触发机制

agent 使用[[02-Specification|渐进式披露]]管理上下文。启动时，它只加载所有可用技能的 `name` 和 `description`。当用户任务与某个描述匹配时，agent 才把完整 `SKILL.md` 读入上下文。

因此，触发判断几乎完全压在 `description` 上。如果描述没有准确表达技能何时有用，agent 就不知道该调用它。

还有一个细节：agent 通常只会在任务需要额外知识或能力时考虑技能。像“读取这个 PDF”这样简单的一步请求，即使描述匹配，也不一定触发 PDF 技能，因为 agent 可能用基础工具就能完成。技能描述最能发挥作用的场景，是涉及陌生 API、领域工作流或少见格式的任务。

## 编写有效描述

测试之前，先明确好描述应具备的特征：

- **使用指令式表达**：写成 “Use this skill when...” 而不是 “This skill does...”。agent 正在判断是否行动，所以要告诉它何时行动。
- **关注用户意图，而不是内部实现**：描述用户想完成什么，而不是技能内部如何运作。
- **宁可稍微主动一些**：明确列出适用场景，包括用户没有直接说出领域关键词的情况。
- **保持简洁**：通常几句话到一个短段落即可。[[02-Specification|规范]]对 `description` 有 1024 字符硬限制。

## 设计触发评测查询

要测试触发效果，需要一组 eval queries：真实感足够的用户提示，并标注它们是否应该触发技能。

```json
[
  {
    "query": "I've got a spreadsheet in ~/data/q4_results.xlsx with revenue in col C and expenses in col D — can you add a profit margin column and highlight anything under 10%?",
    "should_trigger": true
  },
  {
    "query": "whats the quickest way to convert this json file to yaml",
    "should_trigger": false
  }
]
```

建议准备约 20 条查询：8-10 条应该触发，8-10 条不应触发。

### 应触发查询

这些查询用于测试描述是否覆盖技能范围。应在多个维度上变化：

- **表达方式**：正式、随意、带错别字或缩写的说法都要有。
- **显式程度**：有些直接说出领域，如 “analyze this CSV”；有些只描述需求，如 “my boss wants a chart from this data file”。
- **细节量**：既要有简短提示，也要有带路径、列名和背景故事的长提示。
- **复杂度**：覆盖一步任务和多步骤工作流，测试 agent 是否能在更长任务链中识别技能相关性。

最有价值的正例，是那些技能确实有帮助、但从查询表面看不那么明显的情况。若用户已经准确说出了技能做什么，任何合理描述都容易触发。

### 不应触发查询

最有价值的反例是 **near-miss**：它们与技能共享关键词或概念，但实际需要不同能力。这能测试描述是否精准，而不只是宽泛。

对 CSV 分析技能来说，较弱反例包括：

- `"Write a fibonacci function"`：明显无关，几乎测不出东西。
- `"What's the weather today?"`：没有关键词重叠，太容易。

较强反例包括：

- `"I need to update the formulas in my Excel budget spreadsheet"`：共享 spreadsheet 和 data 概念，但需要 Excel 编辑，不是 CSV 分析。
- `"can you write a python script that reads a csv and uploads each row to our postgres database"`：涉及 CSV，但任务是数据库 ETL，不是分析。

### 真实感建议

真实用户提示会包含泛化测试查询中没有的上下文。可以加入：

- 文件路径，如 `~/Downloads/report_final_v2.xlsx`。
- 个人背景，如 “my manager asked me to...”。
- 具体细节，如列名、公司名、数据值。
- 随意表达、缩写和偶尔的 typo。

## 测试描述是否触发

基本做法是：安装技能后，把每条查询交给 agent 运行，并观察 agent 是否调用技能。需要确保技能已被 agent 注册且可发现；具体方式取决于客户端，例如技能目录、配置文件或 CLI flag。

很多 agent 客户端提供日志、工具调用历史或 verbose 输出，可用来判断技能是否被读取。若 agent 加载了该技能的 `SKILL.md`，则视为触发；若 agent 没咨询技能就继续工作，则视为未触发。

一条查询“通过”的条件是：

- `should_trigger` 为 `true`，且技能被调用。
- `should_trigger` 为 `false`，且技能未被调用。

### 多次运行

模型行为有非确定性。同一查询可能一次触发、一次不触发。建议每条查询运行多次，3 次是合理起点，并计算 **trigger rate**：触发次数占总运行次数的比例。

应触发查询的触发率应高于阈值；不应触发查询的触发率应低于阈值。0.5 是一个可用默认阈值。

20 条查询、每条 3 次，总计 60 次调用，最好脚本化。下面示例使用 Claude Code 的 JSON 输出检查 Skill 工具调用；实际使用时应替换为目标 agent 客户端的调用和检测逻辑。

```bash
#!/bin/bash
QUERIES_FILE="${1:?Usage: $0 <queries.json>}"
SKILL_NAME="my-skill"
RUNS=3

# 此示例使用 Claude Code 的 JSON 输出检查 Skill 工具调用。
# 请把本函数替换为你的 agent 客户端对应的检测逻辑。
# 如果技能被调用，返回 0；否则返回 1。
check_triggered() {
  local query="$1"
  claude -p "$query" --output-format json 2>/dev/null \
    | jq -e --arg skill "$SKILL_NAME" \
      'any(.messages[].content[]; .type == "tool_use" and .name == "Skill" and .input.skill == $skill)' \
      > /dev/null 2>&1
}

count=$(jq length "$QUERIES_FILE")
for i in $(seq 0 $((count - 1))); do
  query=$(jq -r ".[$i].query" "$QUERIES_FILE")
  should_trigger=$(jq -r ".[$i].should_trigger" "$QUERIES_FILE")
  triggers=0

  for run in $(seq 1 $RUNS); do
    check_triggered "$query" && triggers=$((triggers + 1))
  done

  jq -n \
    --arg query "$query" \
    --argjson should_trigger "$should_trigger" \
    --argjson triggers "$triggers" \
    --argjson runs "$RUNS" \
    '{query: $query, should_trigger: $should_trigger, triggers: $triggers, runs: $runs, trigger_rate: ($triggers / $runs)}'
done | jq -s '.'
```

> [!tip]
> 如果 agent 客户端支持，在结果已经明确时可以提前停止运行：agent 要么已经咨询了技能，要么已经开始在不使用技能的情况下工作。这样能显著降低完整 eval 集的耗时和成本。

## 用训练/验证拆分避免过拟合

如果把所有查询都拿来优化描述，就可能过拟合：描述对这些具体说法很好用，但面对新说法表现变差。

解决方法是拆分查询集：

- **训练集（约 60%）**：用于发现失败并指导改进。
- **验证集（约 40%）**：先放在一边，只用来检查改进是否能泛化。

两个集合都应按比例包含 should-trigger 和 should-not-trigger 查询。随机打乱后固定拆分，确保不同迭代之间可比较。

## 优化循环

1. **评估**当前描述在训练集和验证集上的表现。训练结果用于指导修改，验证结果用于判断泛化。
2. **分析训练集失败**：哪些应触发查询没触发？哪些不应触发查询误触发？
3. **修订描述**：
   - 若正例漏触发，描述可能太窄，应扩大适用范围或增加技能有用场景。
   - 若反例误触发，描述可能太宽，应更清楚划定它不做什么，或说明与相邻能力的边界。
   - 避免直接把失败查询中的具体关键词塞进描述，这会过拟合。应找出它们代表的一般类别或概念。
   - 若多轮迭代没有改善，尝试换一种结构或表述框架。
   - 保持在 1024 字符限制内。
4. **重复** 1-3，直到训练集全部通过，或没有明显改善。
5. **按验证集通过率选择最佳版本**。最佳描述不一定是最后一个版本；后续版本可能已经过拟合训练集。

通常 5 轮足够。如果性能没有提升，问题可能在查询本身：太容易、太难或标注不清。

> [!tip]
> [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) Skill 可以自动完成这套循环：拆分 eval 集、并行评估触发率、用 Claude 提出描述改进，并生成实时 HTML 报告。

## 应用优化结果

选定最佳描述后：

1. 更新 `SKILL.md` frontmatter 中的 `description` 字段。
2. 确认描述少于 [[02-Specification|1024 字符限制]]。
3. 验证描述按预期触发。可以先手动试几条提示；更严谨的做法是写 5-10 条全新查询，混合 should-trigger 与 should-not-trigger，再运行 eval 脚本。因为这些查询没有参与优化，所以能更真实地检查泛化能力。

优化前后示例：

```yaml
# 优化前
description: Process CSV files.

# 优化后
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

改进后的描述更具体地说明技能做什么（统计摘要、派生列、图表、数据清洗），也更宽泛地说明何时适用（CSV、TSV、Excel，即使用户没有明确说 CSV 或 analysis）。

## 下一步

当技能能可靠触发后，下一步应评估它的输出是否足够好。见 [[04-Evaluating skills|Evaluating skill output quality]]。
