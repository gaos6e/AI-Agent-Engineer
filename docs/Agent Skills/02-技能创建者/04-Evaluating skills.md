---
title: 评估技能输出质量
english_title: Evaluating skill output quality
source_url: https://agentskills.io/skill-creation/evaluating-skills.md
source_path: /skill-creation/evaluating-skills.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 评估
---

# 评估技能输出质量

本页说明如何用 eval 驱动的迭代方式，测试一个技能是否能稳定产出高质量结果。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/skill-creation/evaluating-skills.md>。

写完技能并在一个提示上试过之后，它看起来可能能用。但关键问题是：它是否在不同提示、边界情况中都可靠？它是否真的比不使用技能更好？结构化评估能回答这些问题，并提供系统改进的反馈循环。

## 设计测试用例

一个测试用例包含三部分：

- **Prompt**：真实用户可能输入的消息。
- **Expected output**：用人能读懂的方式描述什么算成功。
- **Input files**（可选）：技能需要处理的输入文件。

把测试用例放在技能目录内的 `evals/evals.json`：

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"]
    },
    {
      "id": 2,
      "prompt": "there's a csv in my downloads called customers.csv, some rows have missing emails — can you clean it up and tell me how many were missing?",
      "expected_output": "A cleaned CSV with missing emails handled, plus a count of how many were missing.",
      "files": ["evals/files/customers.csv"]
    }
  ]
}
```

编写测试提示的建议：

- **先从 2-3 个测试用例开始**，不要在看到第一轮结果前过度投入。
- **变化提示写法**，覆盖不同表达、细节程度和正式程度。
- **覆盖边界情况**，至少加入一个 malformed input、不寻常请求或说明可能含糊的场景。
- **使用真实上下文**，加入文件路径、列名和个人背景；“process this data” 太笼统，测试价值有限。

一开始不必定义具体 pass/fail 检查。先写 prompt 和 expected output，第一轮运行后再补充更细的断言（assertions）。

## 运行 eval

核心模式是每个测试用例运行两次：一次 **with skill**，一次 **without skill**（或使用旧版本技能）。这样能得到可比较的基线。

### 工作区结构

把 eval 结果放在技能目录旁边的 workspace 中。每轮完整 eval 循环都有自己的 `iteration-N/` 目录；其中每个测试用例都有一个目录，内部含 `with_skill/` 和 `without_skill/`：

```text
csv-analyzer/
├── SKILL.md
└── evals/
    └── evals.json
csv-analyzer-workspace/
└── iteration-1/
    ├── eval-top-months-chart/
    │   ├── with_skill/
    │   │   ├── outputs/       # 本次运行产生的文件
    │   │   ├── timing.json    # tokens 与耗时
    │   │   └── grading.json   # 断言评分结果
    │   └── without_skill/
    │       ├── outputs/
    │       ├── timing.json
    │       └── grading.json
    ├── eval-clean-missing-emails/
    │   ├── with_skill/
    │   └── without_skill/
    └── benchmark.json         # 聚合统计
```

需要手写的主要文件是 `evals/evals.json`。其他 JSON 文件通常由 eval 流程中的 agent、脚本或人工步骤生成。

### 启动运行

每次 eval run 都应从干净上下文开始，避免继承开发技能时的残留状态。这样才能确认 agent 只按 `SKILL.md` 工作。支持 subagent 的环境天然适合做隔离；不支持时，可为每次运行开独立会话。

每次运行提供：

- 技能路径，或对 baseline 不提供技能。
- 测试 prompt。
- 输入文件。
- 输出目录。

示例指令：

```text
Execute this task:
- Skill path: /path/to/csv-analyzer
- Task: I have a CSV of monthly sales data in data/sales_2025.csv.
  Can you find the top 3 months by revenue and make a bar chart?
- Input files: evals/files/sales_2025.csv
- Save outputs to: csv-analyzer-workspace/iteration-1/eval-top-months-chart/with_skill/outputs/
```

baseline 使用同样 prompt，但不提供 skill path，并保存到 `without_skill/outputs/`。改进已有技能时，可以把旧版技能复制到 workspace 作为快照，然后用 `old_skill/outputs/` 代替 `without_skill/`。

### 记录耗时数据

timing 数据可比较技能相对 baseline 增加了多少时间和 token 成本。每次运行完成后记录：

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332
}
```

> [!tip]
> 在 Claude Code 中，subagent 任务完成通知包含 `total_tokens` 和 `duration_ms`。应立即保存这些值，因为它们不会自动持久化到其他地方。

## 编写断言

断言是关于输出应包含什么或达成什么的可验证陈述。建议在看到第一轮输出后再添加，因为你往往需要先看一次结果，才能知道“好输出”具体长什么样。

好的断言：

- `"The output file is valid JSON"`：可用程序验证。
- `"The bar chart has labeled axes"`：具体且可观察。
- `"The report includes at least 3 recommendations"`：可计数。

较弱断言：

- `"The output is good"`：太模糊。
- `"The output uses exactly the phrase 'Total Revenue: $X'"`：过于脆弱，正确输出可能用不同措辞。

不是所有质量都适合断言。写作风格、视觉设计、“感觉是否对”等更适合由人工审查捕捉。

在 `evals/evals.json` 中加入断言：

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"],
      "assertions": [
        "The output includes a bar chart image file",
        "The chart shows exactly 3 months",
        "Both axes are labeled",
        "The chart title or caption mentions revenue"
      ]
    }
  ]
}
```

## 评分输出

评分就是对实际输出逐条评估断言，并记录 **PASS** 或 **FAIL** 及具体证据。证据应引用或指向输出内容，而不是只写主观判断。

最简单做法是把输出和断言交给 LLM 评估。对于可用代码验证的断言，例如 JSON 是否有效、行数是否正确、文件是否存在且尺寸符合预期，优先写验证脚本；这比 LLM 判断更可靠，也更容易跨迭代复用。

```json
{
  "assertion_results": [
    {
      "text": "The output includes a bar chart image file",
      "passed": true,
      "evidence": "Found chart.png (45KB) in outputs directory"
    },
    {
      "text": "The chart shows exactly 3 months",
      "passed": true,
      "evidence": "Chart displays bars for March, July, and November"
    },
    {
      "text": "Both axes are labeled",
      "passed": false,
      "evidence": "Y-axis is labeled 'Revenue ($)' but X-axis has no label"
    },
    {
      "text": "The chart title or caption mentions revenue",
      "passed": true,
      "evidence": "Chart title reads 'Top 3 Months by Revenue'"
    }
  ],
  "summary": {
    "passed": 3,
    "failed": 1,
    "total": 4,
    "pass_rate": 0.75
  }
}
```

### 评分原则

- **PASS 必须有具体证据**。不要默认给通过。如果断言要求“包含 summary”，而输出只有一个 Summary 标题和一句空泛话，也应判 FAIL。
- **审查断言本身**。评分时注意哪些断言太容易、太难或不可验证，并在下一轮修正。

> [!tip]
> 比较两个技能版本时，可以做 blind comparison：把两个输出交给 LLM judge，但不说明哪个来自哪个版本。让 judge 根据组织、格式、可用性、完成度等整体维度打分。这能补充断言评分，因为两个输出可能都通过断言，但整体质量差异很大。

## 聚合结果

每轮所有运行都评分后，按配置计算汇总统计，并把结果保存到 `benchmark.json`：

```json
{
  "run_summary": {
    "with_skill": {
      "pass_rate": { "mean": 0.83, "stddev": 0.06 },
      "time_seconds": { "mean": 45.0, "stddev": 12.0 },
      "tokens": { "mean": 3800, "stddev": 400 }
    },
    "without_skill": {
      "pass_rate": { "mean": 0.33, "stddev": 0.10 },
      "time_seconds": { "mean": 32.0, "stddev": 8.0 },
      "tokens": { "mean": 2100, "stddev": 300 }
    },
    "delta": {
      "pass_rate": 0.50,
      "time_seconds": 13.0,
      "tokens": 1700
    }
  }
}
```

`delta` 说明技能带来了什么收益，也付出了什么成本。增加 13 秒但通过率提升 50 个百分点，通常值得；如果 token 翻倍只换来 2 个百分点提升，则可能不值得。

> [!note]
> `stddev` 只有在每个 eval 多次运行时才有意义。早期只有 2-3 个测试用例且每例只跑一次时，更应关注原始通过数量和 delta。

## 分析模式

聚合统计可能掩盖重要模式。计算 benchmark 后应检查：

- **移除或替换两种配置都总是通过的断言**。这些断言不能说明技能价值。
- **调查两种配置都总是失败的断言**。可能是断言本身有问题、测试太难，或断言检查了错误对象。
- **研究有技能通过、无技能失败的断言**。这些地方明确显示技能提供了价值，应理解是哪条说明或哪个脚本带来了差异。
- **对不稳定结果收紧说明**。同一 eval 时过时不过，可能是 eval flaky，也可能是技能说明含糊。
- **检查时间和 token 异常值**。如果某个 eval 比其他 eval 慢 3 倍，应阅读完整执行 transcript 找瓶颈。

## 人工复审

断言评分和模式分析能抓住很多问题，但只能检查你预先想到的内容。人工复审可以发现未预期的问题、技术正确但偏离意图的输出，以及难以写成 pass/fail 的质量问题。

可以为每个测试用例保存人工反馈，例如 `feedback.json`：

```json
{
  "eval-top-months-chart": "The chart is missing axis labels and the months are in alphabetical order instead of chronological.",
  "eval-clean-missing-emails": ""
}
```

反馈应具体可执行。“缺少坐标轴标签”有用，“看起来不好”没有用。空字符串表示该输出看起来没问题。

## 迭代技能

评分和复审后，你会得到三类信号：

- **失败断言**：指出具体缺口，如缺少步骤、说明不清，或技能未覆盖某个情况。
- **人工反馈**：指出更宽的质量问题，如方法错误、结构差、技术上正确但不实用。
- **执行 transcript**：解释为什么出错。如果 agent 忽略说明，说明可能含糊；如果它花时间做无效步骤，说明可能需要简化或删除。

最有效的改进方式，是把这三类信号连同当前 `SKILL.md` 交给 LLM，让它提出修改建议。提示 LLM 时应加入这些要求：

- **从反馈中泛化**，不要只为某个测试用例打补丁。
- **保持技能精简**，更少但更好的说明常常胜过穷尽规则。
- **说明为什么**，带理由的说明通常比僵硬的 “ALWAYS/NEVER” 更容易被模型正确执行。
- **把重复工作打包为脚本**，如果每次测试都在重写同类 helper，应把它放进 `scripts/`。

### 循环

1. 把 eval 信号和当前 `SKILL.md` 交给 LLM，请它提出改进。
2. 审查并应用修改。
3. 在新的 `iteration-<N+1>/` 目录中重跑所有测试。
4. 评分并聚合新结果。
5. 人工复审。重复以上流程。

当结果令人满意、人工反馈稳定为空，或迭代之间不再有明显改善时停止。

> [!tip]
> [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) Skill 可以自动完成大量流程，包括运行 eval、评分断言、聚合 benchmark 和展示结果供人工复审。
