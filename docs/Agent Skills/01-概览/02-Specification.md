---
title: Agent Skills 规范
english_title: Specification
source_url: https://agentskills.io/specification.md
source_path: /specification.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 规范
---

# Agent Skills 规范

本页是 Agent Skills 的完整格式规范。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/specification.md>。

## 目录结构

一个技能至少是一个包含 `SKILL.md` 的目录：

```text
skill-name/
├── SKILL.md          # 必需：元数据 + 说明
├── scripts/          # 可选：可执行代码
├── references/       # 可选：文档资料
├── assets/           # 可选：模板和资源
└── ...               # 其他文件或目录
```

## `SKILL.md` 格式

`SKILL.md` 必须包含 YAML frontmatter，随后是 Markdown 正文。

### Frontmatter

| 字段 | 必需 | 约束 |
| --- | --- | --- |
| `name` | 是 | 最多 64 个字符。只能使用小写字母、数字和连字符；不能以连字符开头或结尾。 |
| `description` | 是 | 最多 1024 个字符。不能为空。说明技能做什么，以及何时使用。 |
| `license` | 否 | 许可证名称，或指向随技能一起提供的许可证文件。 |
| `compatibility` | 否 | 最多 500 个字符。说明环境要求，如目标产品、系统包、网络访问等。 |
| `metadata` | 否 | 任意键值映射，用于额外元数据。 |
| `allowed-tools` | 否 | 空格分隔的预授权工具字符串。该字段仍属实验性质。 |

最小示例：

```markdown
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

带可选字段的示例：

```markdown
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
metadata:
  author: example-org
  version: "1.0"
---
```

#### `name` 字段

必需的 `name` 字段需要满足：

- 长度为 1-64 个字符。
- 只能包含 Unicode 小写字母数字字符（`a-z`）和连字符（`-`）。
- 不能以连字符开头或结尾。
- 不能包含连续连字符（`--`）。
- 必须与父目录名一致。

有效示例：

```yaml
name: pdf-processing
```

```yaml
name: data-analysis
```

```yaml
name: code-review
```

无效示例：

```yaml
name: PDF-Processing  # 不允许大写字母
```

```yaml
name: -pdf  # 不能以连字符开头
```

```yaml
name: pdf--processing  # 不允许连续连字符
```

#### `description` 字段

必需的 `description` 字段需要满足：

- 长度为 1-1024 个字符。
- 应同时说明技能能做什么，以及何时使用。
- 应包含能帮助 agent 判断相关性的具体关键词。

较好的示例：

```yaml
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

较差的示例：

```yaml
description: Helps with PDFs.
```

#### `license` 字段

可选的 `license` 字段用于说明技能适用的许可证。建议保持简短，可以写许可证名称，也可以写随技能提供的许可证文件名。

```yaml
license: Proprietary. LICENSE.txt has complete terms
```

#### `compatibility` 字段

可选的 `compatibility` 字段用于说明具体环境要求。只有技能确实依赖特定环境时才需要提供。可以写目标产品、必需系统包、网络访问要求等。

示例：

```yaml
compatibility: Designed for Claude Code (or similar products)
```

```yaml
compatibility: Requires git, docker, jq, and access to the internet
```

```yaml
compatibility: Requires Python 3.14+ and uv
```

> [!note]
> 大多数技能不需要 `compatibility` 字段。

#### `metadata` 字段

可选的 `metadata` 字段是字符串键到字符串值的映射。客户端可以用它保存 Agent Skills 规范之外的额外属性。建议键名尽量唯一，减少与其他实现发生冲突的概率。

```yaml
metadata:
  author: example-org
  version: "1.0"
```

#### `allowed-tools` 字段

可选的 `allowed-tools` 字段是空格分隔的工具列表，表示这些工具预先获准运行。该字段仍为实验性质，不同 agent 实现的支持程度可能不同。

```yaml
allowed-tools: Bash(git:*) Bash(jq:*) Read
```

### 正文内容

frontmatter 后面的 Markdown 正文就是技能说明。规范不限制正文格式，写入任何能帮助 agent 有效完成任务的内容即可。

推荐包含：

- 分步骤说明。
- 输入和输出示例。
- 常见边界情况。

注意：一旦 agent 决定激活技能，就会加载整个 `SKILL.md`。如果内容较长，应拆分到引用文件中。

## 可选目录

### `scripts/`

用于存放 agent 可以运行的可执行代码。脚本应满足：

- 自包含，或清楚说明依赖。
- 提供有帮助的错误信息。
- 能稳健处理边界情况。

具体支持哪些语言取决于 agent 实现，常见选择包括 Python、Bash 和 JavaScript。

### `references/`

用于存放 agent 在需要时读取的补充文档，例如：

- `REFERENCE.md`：详细技术参考。
- `FORMS.md`：表单模板或结构化数据格式。
- 领域专用文件，如 `finance.md`、`legal.md` 等。

保持单个参考文件聚焦。agent 会按需加载这些文件，文件越小，对上下文的占用越低。

### `assets/`

用于存放静态资源，例如：

- 模板：文档模板、配置模板。
- 图片：图表、示例。
- 数据文件：查找表、schema。

## 渐进式披露

agent 会渐进式加载技能，只在任务需要时拉取更多细节。技能结构应配合这种机制：

1. **元数据**（约 100 tokens）：启动时加载所有技能的 `name` 和 `description` 字段。
2. **说明**（建议少于 5000 tokens）：技能被激活时加载完整 `SKILL.md` 正文。
3. **资源**（按需）：只有在需要时才加载 `scripts/`、`references/`、`assets/` 中的文件。

建议主 `SKILL.md` 控制在 500 行以内。详细参考材料应移到独立文件中。

## 文件引用

在技能中引用其他文件时，使用相对于技能根目录的路径：

```markdown
See [the reference guide](references/REFERENCE.md) for details.

Run the extraction script:
scripts/extract.py
```

保持从 `SKILL.md` 出发的一层引用关系，避免深层嵌套的引用链。

## 校验

可以使用 [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) 参考库校验技能：

```bash
skills-ref validate ./my-skill
```

该命令会检查 `SKILL.md` frontmatter 是否有效，并验证命名规则。
