---
title: 技能创建最佳实践
english_title: Best practices for skill creators
source_url: https://agentskills.io/skill-creation/best-practices.md
source_path: /skill-creation/best-practices.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 最佳实践
---

# 技能创建最佳实践

本页说明如何编写范围清晰、与任务匹配度高的技能。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/skill-creation/best-practices.md>。

## 从真实专业经验出发

创建技能时，一个常见误区是直接让 LLM 生成技能，却不给它具体领域上下文，只依赖模型通用知识。这样得到的往往是“妥善处理错误”“遵循身份认证最佳实践”这类泛泛流程，而不是具体 API 模式、边界情况和项目约定。

有效技能应植根于真实专业经验。关键是把领域上下文输入到技能创建过程中。

### 从一次真实任务中提取

先和 agent 完成一次真实任务，在过程中给出上下文、纠正和偏好。任务完成后，再把可复用模式提炼成技能。重点观察：

- **真正有效的步骤**：哪些操作顺序带来了成功结果。
- **你做过的纠正**：例如“用 X 库而不是 Y 库”“先检查 Z 边界情况”。
- **输入/输出格式**：任务开始和结束时数据长什么样。
- **你补充的上下文**：agent 原本不知道的项目事实、约定或约束。

### 从现有项目材料中综合

如果已有大量内部知识，可以把材料交给 LLM，让它综合成技能。用真实事故报告和 runbook 综合出的数据管线技能，通常会比基于通用“数据工程最佳实践”文章生成的技能更好，因为它捕捉了你们自己的 schema、故障模式和恢复流程。

适合作为素材的内容包括：

- 内部文档、runbook 和风格指南。
- API 规范、schema 和配置文件。
- 代码评审意见和 issue，尤其是反复出现的关注点。
- 版本控制历史，特别是补丁和修复记录。
- 真实故障案例及其解决方案。

## 用真实执行结果迭代

技能初稿通常需要打磨。把技能用于真实任务，然后把执行结果反馈回创建过程。不要只看失败案例，也要看成功案例。需要追问：哪些情况误触发了？哪些情况漏掉了？哪些说明可以删掉？

哪怕只做一次“执行-修订”循环，也能明显提升质量。复杂领域通常需要多轮。

> [!tip]
> 阅读 agent 的执行轨迹，而不只是最终输出。如果 agent 在无效步骤上浪费时间，常见原因包括：说明太模糊，导致它尝试多条路径；说明与当前任务无关，但它仍然照做；或给了太多等价选项，却没有明确默认方案。

更结构化的迭代方法见 [[04-Evaluating skills|Evaluating skill output quality]]。

## 节省上下文预算

技能一旦激活，完整 `SKILL.md` 会与对话历史、系统上下文和其他技能一起进入 agent 的上下文窗口。技能中的每个 token 都会与其他内容竞争注意力。

### 写 agent 缺少的内容，删掉它已经知道的内容

重点写 agent 没有技能时可能不知道的东西：项目专属约定、领域流程、非显而易见的边界情况、特定工具或 API 的使用方式。无需解释 PDF 是什么、HTTP 如何工作、数据库迁移是什么。

````markdown
<!-- 过于冗长：agent 已经知道 PDF 是什么 -->
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. pdfplumber is recommended because it handles most cases well.

<!-- 更好：直接写 agent 不一定知道的操作选择 -->
## Extract PDF text

Use pdfplumber for text extraction. For scanned documents, fall back to
pdf2image with pytesseract.

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
````

逐段检查技能内容时，可以问自己：“如果没有这条说明，agent 会不会做错？”如果答案是否定的，就删掉。如果不确定，就测试。如果 agent 在没有技能时也能很好完成整个任务，那么技能可能没有提供足够价值。

### 设计连贯的功能单元

决定一个技能覆盖什么，类似于决定一个函数负责什么：它应封装一个连贯的工作单元，并能与其他技能组合。过窄的技能会让同一任务加载多个技能，增加上下文负担和冲突概率；过宽的技能又难以精准触发。例如，“查询数据库并格式化结果”可能是一个连贯技能，而把数据库管理也放进去就可能过宽。

### 控制在适中的细节层级

过于全面的技能可能适得其反：agent 难以提取与当前任务相关的部分，甚至被不适用的说明带偏。通常，简洁的分步指导加一个可运行示例，比穷尽所有边界情况更好。若你发现自己在覆盖每个小分支，应考虑这些是否可以交给 agent 自身判断。

### 大技能使用渐进式披露

[[02-Specification|规范]]建议 `SKILL.md` 少于 500 行、5000 tokens，只保留每次运行都需要的核心说明。若技能确实需要更多内容，应把详细参考材料放入 `references/` 等独立文件。

关键是告诉 agent **什么时候**加载哪个文件。比如“如果 API 返回非 200 状态码，就读取 `references/api-errors.md`”比“详见 references/”更有用。这样 agent 能按需加载上下文，而不是一次性读取所有材料。

## 校准控制粒度

技能中不同部分不需要同等强度的规定。应根据任务脆弱程度匹配说明的具体程度。

### 根据脆弱程度决定具体程度

当多种做法都有效、任务容忍一定变化时，可以给 agent 更大自由。解释“为什么”通常比硬性命令更有效，因为 agent 理解意图后能更好地因地制宜。

```markdown
## Code review process

1. Check all database queries for SQL injection (use parameterized queries)
2. Verify authentication checks on every endpoint
3. Look for race conditions in concurrent code paths
4. Confirm error messages don't leak internal details
```

当操作脆弱、需要一致性，或必须按特定顺序执行时，就应更明确：

````markdown
## Database migration

Run exactly this sequence:

```bash
python scripts/migrate.py --verify --backup
```

Do not modify the command or add additional flags.
````

多数技能会混合两种风格，应逐段校准。

### 给默认方案，而不是菜单

当多个工具或方案都可行时，选择一个默认方案，并简短提及替代方案，不要把所有方案并列成同等选项。

````markdown
<!-- 选项过多 -->
You can use pypdf, pdfplumber, PyMuPDF, or pdf2image...

<!-- 更清晰：默认方案 + 例外路径 -->
Use pdfplumber for text extraction:

```python
import pdfplumber
```

For scanned PDFs requiring OCR, use pdf2image with pytesseract instead.
````

### 偏向流程，而不是一次性答案

技能应教 agent 如何处理一类问题，而不是只给某个具体实例的答案。

```markdown
<!-- 具体答案：只对这一个任务有用 -->
Join the `orders` table to `customers` on `customer_id`, filter where
`region = 'EMEA'`, and sum the `amount` column.

<!-- 可复用方法：适用于任意分析查询 -->
1. Read the schema from `references/schema.yaml` to find relevant tables
2. Join tables using the `_id` foreign key convention
3. Apply any filters from the user's request as WHERE clauses
4. Aggregate numeric columns as needed and format as a markdown table
```

这并不意味着技能不能包含具体细节。输出模板、约束（如“永不输出 PII”）和工具级说明都很有价值。重点是方法应可泛化。

## 有效说明的常见模式

以下是组织技能内容的可复用模式。不是每个技能都需要全部使用，应按任务选择。

### Gotchas 小节

许多技能中最有价值的内容是 gotchas：那些违背合理直觉的环境专属事实。它们不是“妥善处理错误”这类通用建议，而是 agent 如果不知道就很可能犯错的具体纠正。

```markdown
## Gotchas

- The `users` table uses soft deletes. Queries must include
  `WHERE deleted_at IS NULL` or results will include deactivated accounts.
- The user ID is `user_id` in the database, `uid` in the auth service,
  and `accountId` in the billing API. All three refer to the same value.
- The `/health` endpoint returns 200 as long as the web server is running,
  even if the database connection is down. Use `/ready` to check full
  service health.
```

这些 gotchas 最好放在 `SKILL.md` 中，让 agent 在遇到相关情况之前就读到。也可以放到参考文件，但必须清楚说明何时加载；对于非显而易见的问题，agent 可能根本不会意识到需要打开参考文件。

> [!tip]
> 当 agent 犯了一个你必须纠正的错误时，把这条纠正加入 gotchas。这是迭代改进技能最直接的方法之一。

### 输出格式模板

如果需要 agent 产出特定格式，直接提供模板比用自然语言描述更可靠。agent 很擅长匹配具体结构。短模板可以直接放在 `SKILL.md`；长模板或只在特定情况使用的模板，可以放到 `assets/` 并在 `SKILL.md` 中引用。

````markdown
## Report structure

Use this template, adapting sections as needed for the specific analysis:

```markdown
# [Analysis Title]

## Executive summary
[One-paragraph overview of key findings]

## Key findings
- Finding 1 with supporting data
- Finding 2 with supporting data

## Recommendations
1. Specific actionable recommendation
2. Specific actionable recommendation
```
````

### 多步骤工作流清单

显式 checklist 能帮助 agent 跟踪进度，避免遗漏步骤，尤其适合有依赖关系或验证门槛的流程。

```markdown
## Form processing workflow

Progress:
- [ ] Step 1: Analyze the form (run `scripts/analyze_form.py`)
- [ ] Step 2: Create field mapping (edit `fields.json`)
- [ ] Step 3: Validate mapping (run `scripts/validate_fields.py`)
- [ ] Step 4: Fill the form (run `scripts/fill_form.py`)
- [ ] Step 5: Verify output (run `scripts/verify_output.py`)
```

### 验证循环

要求 agent 在进入下一步前验证自己的工作。模式是：完成工作，运行验证器（脚本、参考清单或自检），修复问题，再验证，直到通过。

```markdown
## Editing workflow

1. Make your edits
2. Run validation: `python scripts/validate.py output/`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. Only proceed when validation passes
```

参考文档也可以作为“验证器”：要求 agent 在最终交付前对照参考检查自己的工作。

### 计划-验证-执行

对批量或破坏性操作，让 agent 先用结构化格式创建中间计划，再对照事实来源验证计划，最后才执行。

```markdown
## PDF form filling

1. Extract form fields: `python scripts/analyze_form.py input.pdf` → `form_fields.json`
   (lists every field name, type, and whether it's required)
2. Create `field_values.json` mapping each field name to its intended value
3. Validate: `python scripts/validate_fields.py form_fields.json field_values.json`
   (checks that every field name exists in the form, types are compatible, and
   required fields aren't missing)
4. If validation fails, revise `field_values.json` and re-validate
5. Fill the form: `python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

关键是第 3 步：用验证脚本把计划（`field_values.json`）与事实来源（`form_fields.json`）比对。像 “Field 'signature_date' not found — available fields: customer_name, order_total, signature_date_signed” 这样的错误信息，能让 agent 自行修正。

### 打包可复用脚本

在[[04-Evaluating skills|迭代技能]]时，对比不同测试用例中的 agent 执行轨迹。如果发现 agent 每次都在独立重写同一段逻辑，例如生成图表、解析固定格式、验证输出，就说明应把这段逻辑写成已测试脚本，并放入 `scripts/`。

脚本设计和打包详见 [[05-Using scripts|Using scripts in skills]]。

## 下一步

- [[04-Evaluating skills|Evaluating skill output quality]]：设置测试用例、评分输出并系统迭代。
- [[03-Optimizing descriptions|Optimizing skill descriptions]]：测试并优化 `description` 字段，让技能在正确提示上触发。
