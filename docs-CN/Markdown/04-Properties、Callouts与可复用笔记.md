---
title: "Properties、Callouts 与可复用笔记"
tags:
  - AI-Agent-Engineer
  - Markdown
  - Obsidian
  - Properties
aliases:
  - Obsidian Properties 入门
  - 可复用笔记结构
source_checked: 2026-07-14
lang: zh-CN
translation_key: Markdown/04-Properties、Callouts与可复用笔记.md
translation_route: en/markdown/04-properties-callouts-and-reusable-notes
translation_default_route: zh-CN/Markdown/04-Properties、Callouts与可复用笔记
---

# Properties、Callouts 与可复用笔记

## 本节目标

本节把一篇“能显示”的 Markdown 笔记升级为“能检索、能复用、能长期维护”的 Obsidian 笔记。你将学会设计简单 Properties、选择 callout 类型，并避免把正文、秘密或复杂对象塞进 frontmatter。

## Properties 是元数据，不是正文

Properties 存在文件顶部的 YAML frontmatter 中，由成对的 `---` 包围。它适合保存短小、原子、可检索的信息，例如标题、标签、别名、日期和布尔状态。

```yaml
---
title: 可靠 API 客户端运行手册
tags:
  - AI-Agent-Engineer
  - API
aliases:
  - API Runbook
status: draft
reviewed: false
source_checked: 2026-07-14
related:
  - "[[Knowledge/AI Agent Engineer/docs-CN/API/00-目录|API]]"
---
```

关键规则：

- frontmatter 必须从文件第一行开始；
- 每个属性名在同一篇笔记中只能出现一次；
- `tags`、`aliases`、`cssclasses` 是 Obsidian 默认属性名；
- 属性中的内部链接要加引号，避免 YAML 把方括号解释为其他结构；
- `title` 是元数据值，不会自动替代真实文件名；链接仍以文件路径为目标；
- Properties 不是加密区，隐藏显示后值仍在纯文本文件中。

## 选择正确的属性类型

Obsidian 当前支持文本、列表、数字、checkbox、日期、日期时间和 tags 等属性类型。一个属性名在整个 vault 中会关联一种类型，因此同名键不要一会儿写列表、一会儿写自由文本。

| 类型 | 示例 | 适合 | 不适合 |
| --- | --- | --- | --- |
| 文本 | `status: draft` | 短状态、版本标签 | 多段说明 |
| 列表 | `aliases:` 下多项 | 别名、相关主题、负责人 | 有顺序的操作步骤 |
| 数字 | `score: 8` | 可比较数值 | `8/10` 这类表达式 |
| Checkbox | `reviewed: false` | 是/否状态 | 多状态流程 |
| 日期 | `source_checked: 2026-07-14` | 核对日、截止日 | 模糊的“最近” |
| 日期时间 | ISO 8601 时间 | 事件时间 | 无时区的跨系统日志 |
| Tags | `tags:` 列表 | 稳定分类 | 整句描述 |

Obsidian 官方明确说明：Properties 不渲染 Markdown，也不原生支持嵌套属性的可视化编辑。需要复杂对象、长理由或多步流程时，把它写进正文；若机器必须消费复杂结构，考虑独立 JSON/YAML 文件并定义契约。

## YAML 常见错误

### 冒号、井号与引号

值包含 `: `、`#`、`[`、`]` 或可能被解析成布尔/日期的文本时，使用引号更安全：

```yaml
summary: "边界：只读取本地文件"
ticket: "#123"
literal_date: "2026-07-14"
```

不要机械给所有值加引号；目标是让类型明确。需要日期检索时应保留日期类型，而不是把它强制成文本。

### 重复键

下面不是“两组标签”，而是冲突的重复键：

```yaml
tags:
  - Markdown
tags:
  - Obsidian
```

应合并为一个列表。某些 YAML 工具会静默保留最后一个值，造成数据丢失，因此静态检查要显式拒绝重复键。

### 把敏感信息当元数据

错误示例包括 `api_key`、cookie、内部服务完整地址、真实客户姓名。Properties 会被搜索、插件和同步工具读取；“不显示在阅读视图”不代表不泄漏。密钥只放受控环境变量，教学材料只提供 `.env.example` 或占位符。

## Callout 用于语义强调

Callout 是 Obsidian 对 blockquote 的扩展。基本写法：

```markdown
> [!warning] 停止条件
> 如果输入含真实客户数据，立即停止，不要继续测试。
```

折叠状态写在类型后：

```markdown
> [!example]- 展开查看示例
> 这是默认折叠的补充示例。

> [!info]+ 默认展开
> 这是额外背景，不是必做步骤。
```

常用语义：

| 类型 | 用途 | 使用边界 |
| --- | --- | --- |
| `note` / `info` | 背景与补充 | 不隐藏必做步骤 |
| `tip` | 提效建议 | 不是正确性的必要条件 |
| `warning` / `danger` | 数据损失、安全或不可逆风险 | 少而明确，不默认折叠 |
| `example` | 参考案例、答案 | 与主流程分离 |
| `question` | 自测或待决策点 | 给出回答方式或负责人 |

Callout 可以嵌套并包含链接、embed 和普通 Markdown，但层级过深会降低源文本可读性。若一段内容是主流程的一部分，就用普通标题和正文，不要藏进折叠框。

## 设计可复用笔记骨架

模板的价值是减少遗漏，不是让所有主题长得一样。一个工程说明可以从以下骨架开始：

````markdown
---
title: 工具名称与任务
tags:
  - AI-Agent-Engineer
aliases:
  - 可搜索旧称
source_checked: 2026-07-14
---

# 工具名称与任务

## 目标与非目标

说明读者完成什么，以及明确不做什么。

## 前置条件

列出环境和验证命令。

## 输入输出契约

定义格式、敏感级别和失败条件。

## 操作步骤

按依赖顺序写目的、命令、预期和停止条件。

## 验证与未验证项

区分实际执行、预期结果和待人工复核。

## 参考资料

记录一手来源与核对日期。
````

对概念笔记、实验记录和运行手册，可以复用元数据键，却应选择不同正文结构。不要把“模板完整”误当成“内容正确”。

## 一个小型属性契约

多人维护时，先给高频键定义含义：

| 键 | 类型 | 约束 | 示例 |
| --- | --- | --- | --- |
| `title` | 文本 | 一篇一个，描述真实主题 | `Markdown 链接审计` |
| `tags` | 列表 | 使用已有分类，避免同义词爆炸 | `AI-Agent-Engineer` |
| `aliases` | 列表 | 只放真实旧称或常用缩写 | `GFM` |
| `source_checked` | 日期 | 只在确实核对来源后更新 | `2026-07-14` |
| `status` | 文本 | 受控枚举，如 `draft/reviewed` | `reviewed` |

工程建议与 Obsidian 强制规则要分开：上表是本课程建议，不是 Obsidian 内置 schema。

## 动手练习

1. 为一篇“本地日志分析”笔记设计 frontmatter，至少包含 `title`、`tags`、`aliases`、`source_checked` 和一个 checkbox。
2. 在正文写“目标、输入输出、步骤、验证”四节；不要把步骤塞进 Properties。
3. 加一个不折叠的安全 warning 和一个默认折叠的 example。
4. 故意复制一个属性键，观察源码，再删除重复项；不要依赖解析器替你决定保留哪个值。
5. 写出三个不应进入 Properties 的内容，并解释原因。

验收：另一位读者只看 Properties 就能筛选笔记，只看正文就能理解任务；两处信息不重复承担同一职责。

## 常见误区

- **把 `title` 当文件别名**：要使用 `aliases`，链接目标仍是路径。
- **标签越多越容易搜索**：同义标签会让分类失控，正文全文搜索仍然存在。
- **所有信息都结构化**：长解释放正文，Properties 保持原子。
- **折叠 warning 更简洁**：关键风险不应默认隐藏。
- **模板字段都必须填写**：删除无意义字段比填“无”更清楚。
- **更新日期就是重新核对**：只有实际复核来源和行为后才改 `source_checked`。

## 自测与掌握标准

1. Properties 与正文各自适合保存什么？
2. 为什么同名属性应保持同一类型？
3. 属性中的 wikilink 为什么需要引号？
4. 哪些 callout 不应默认折叠？
5. Properties 隐藏显示为什么不等于安全？

- [ ] 能写合法、无重复键的 frontmatter。
- [ ] 能选择文本、列表、日期和 checkbox 类型。
- [ ] 能用 callout 表达补充、示例和真实警告。
- [ ] 能设计一份简洁的属性契约并区分工程建议与产品规则。

上一节：[[Markdown/03-Obsidian链接、附件与嵌入|Obsidian 链接、附件与嵌入]]。  
下一节：[[Markdown/05-面向Agent工程的结构化技术写作|面向 Agent 工程的结构化技术写作]]。

## 参考资料

核对日期：**2026-07-14**。

- [Obsidian：Properties](https://obsidian.md/help/properties)
- [Obsidian：Aliases](https://obsidian.md/help/aliases)
- [Obsidian：Callouts](https://obsidian.md/help/callouts)
- [YAML 1.2.2 Specification](https://yaml.org/spec/1.2.2/)

