---
title: 在技能中使用脚本
english_title: Using scripts in skills
source_url: https://agentskills.io/skill-creation/using-scripts.md
source_path: /skill-creation/using-scripts.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 脚本
---

# 在技能中使用脚本

本页说明如何在技能中运行命令、打包可执行脚本，并为 agent 设计易用的脚本接口。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/skill-creation/using-scripts.md>。

技能可以在 `SKILL.md` 中指导 agent 运行 shell 命令，也可以在 `scripts/` 目录中打包可复用脚本。常见场景包括一次性命令、自包含脚本及带结构化输出的工具。

## 一次性命令

如果现有包已经能完成任务，可以直接在 `SKILL.md` 中引用命令，而无需单独创建 `scripts/`。许多生态提供运行时自动解析依赖的工具。

### `uvx`

[uvx](https://docs.astral.sh/uv/guides/tools/) 会在隔离环境中运行 Python 包，并积极缓存。它随 [uv](https://docs.astral.sh/uv/) 提供。

```bash
uvx ruff@0.8.0 check .
uvx black@24.10.0 .
```

- 不随 Python 自带，需要单独安装。
- 速度快，缓存积极，重复运行通常接近瞬时。

### `pipx`

[pipx](https://pipx.pypa.io/) 会在隔离环境中运行 Python 包，可通过系统包管理器安装，例如 `apt install pipx` 或 `brew install pipx`。

```bash
pipx run 'black==24.10.0' .
pipx run 'ruff==0.8.0' check .
```

- 不随 Python 自带，需要单独安装。
- 是 `uvx` 的成熟替代方案。虽然 `uvx` 已成为标准推荐，但 `pipx` 在操作系统包管理器中的可用性更广。

### `npx`

[npx](https://docs.npmjs.com/cli/commands/npx) 会按需下载并运行 npm 包。它随 npm 提供，而 npm 随 Node.js 提供。

```bash
npx eslint@9 --fix .
npx create-vite@6 my-app
```

- 随 Node.js 提供，无需额外安装。
- 会下载包、运行并缓存以备后续使用。
- 使用 `npx package@version` 固定版本以提高可复现性。

### `bunx`

[bunx](https://bun.sh/docs/cli/bunx) 是 Bun 对应的 `npx`，随 [Bun](https://bun.sh/) 提供。

```bash
bunx eslint@9 --fix .
bunx create-vite@6 my-app
```

- 可在 Bun 环境中作为 `npx` 的直接替代。
- 只适合用户环境有 Bun 而不是 Node.js 的情况。

### `deno run`

[deno run](https://docs.deno.com/runtime/reference/cli/run/) 可以直接从 URL 或 specifier 运行脚本，随 [Deno](https://deno.com/) 提供。

```bash
deno run npm:create-vite@6 my-app
deno run --allow-read npm:eslint@9 -- --fix .
```

- 文件系统或网络访问需要权限 flags，例如 `--allow-read`。
- 使用 `--` 分隔 Deno 自己的 flags 和工具的 flags。

### `go run`

[go run](https://pkg.go.dev/cmd/go#hdr-Compile_and_run_Go_program) 可直接编译并运行 Go 包，内置在 `go` 命令中。

```bash
go run golang.org/x/tools/cmd/goimports@v0.28.0 .
go run github.com/golangci/golangci-lint/cmd/golangci-lint@v1.62.0 run
```

- 内置于 Go，无需额外工具。
- 固定版本，或使用 `@latest` 明确指定版本策略。

一次性命令的建议：

- **固定版本**，例如 `npx eslint@9.0.0`，保证长期行为一致。
- **在 `SKILL.md` 中说明前置条件**，例如 “Requires Node.js 18+”；运行时要求可写入 [[02-Specification|`compatibility`]] 字段。
- **把复杂命令移入脚本**。如果命令复杂到难以一次写对，已测试的 `scripts/` 脚本更可靠。

## 在 `SKILL.md` 中引用脚本

引用打包文件时，使用相对于技能目录根的路径。agent 会自动解析这些路径，无需绝对路径。

在 `SKILL.md` 中列出可用脚本，让 agent 知道它们存在：

```markdown
## Available scripts

- **`scripts/validate.sh`** — Validates configuration files
- **`scripts/process.py`** — Processes input data
```

然后在工作流中指导 agent 运行：

````markdown
## Workflow

1. Run the validation script:
   ```bash
   bash scripts/validate.sh "$INPUT_FILE"
   ```

2. Process the results:
   ```bash
   python3 scripts/process.py --input results.json
   ```
````

> [!note]
> 同样的相对路径约定也适用于 `references/*.md` 等支持文件。代码块中的脚本执行路径相对于 **技能目录根**，因为 agent 会从那里运行命令。

## 自包含脚本

如果需要可复用逻辑，可以在 `scripts/` 中打包一个直接声明依赖的脚本。agent 只需运行一个命令，无需单独 manifest 或安装步骤。

### Python

[PEP 723](https://peps.python.org/pep-0723/) 定义了内联脚本元数据格式，可在 `# ///` 标记内用 TOML 块声明依赖：

```python
# /// script
# dependencies = [
#   "beautifulsoup4",
# ]
# ///

from bs4 import BeautifulSoup

html = '<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>'
print(BeautifulSoup(html, "html.parser").select_one("p.info").get_text())
```

推荐用 [uv](https://docs.astral.sh/uv/) 运行：

```bash
uv run scripts/extract.py
```

`uv run` 会创建隔离环境、安装声明依赖并运行脚本。[pipx](https://pipx.pypa.io/) 的 `pipx run scripts/extract.py` 也支持 PEP 723。

- 使用 [PEP 508](https://peps.python.org/pep-0508/) specifier 固定版本范围，例如 `"beautifulsoup4>=4.12,<5"`。
- 使用 `requires-python` 约束 Python 版本。
- 使用 `uv lock --script` 生成 lockfile，以获得完整可复现性。

### Deno

Deno 的 `npm:` 和 `jsr:` import specifier 让脚本天然自包含：

```typescript
#!/usr/bin/env -S deno run

import * as cheerio from "npm:cheerio@1.0.0";

const html = `<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>`;
const $ = cheerio.load(html);
console.log($("p.info").text());
```

```bash
deno run scripts/extract.ts
```

- `npm:` 用于 npm 包，`jsr:` 用于 Deno 原生包。
- 版本 specifier 遵循 semver，例如 `@1.0.0`（精确）或 `@^1.0.0`（兼容）。
- 依赖会全局缓存。使用 `--reload` 强制重新获取。
- 带 native addons（node-gyp）的包可能无法工作；带预构建二进制的包更合适。

### Bun

当没有 `node_modules` 目录时，Bun 会在运行时自动安装缺失包。可直接在 import 路径中固定版本：

```typescript
#!/usr/bin/env bun

import * as cheerio from "cheerio@1.0.0";

const html = `<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>`;
const $ = cheerio.load(html);
console.log($("p.info").text());
```

```bash
bun run scripts/extract.ts
```

- 不需要 `package.json` 或 `node_modules`，TypeScript 可原生运行。
- 包会全局缓存，首次运行下载，后续通常很快。
- 如果当前目录或上级目录存在 `node_modules`，自动安装会禁用，Bun 会回退到标准 Node.js 解析。

### Ruby

Ruby 2.6 起自带 Bundler。可以用 `bundler/inline` 在脚本中直接声明 gems：

```ruby
require 'bundler/inline'

gemfile do
  source 'https://rubygems.org'
  gem 'nokogiri'
end

html = '<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>'
doc = Nokogiri::HTML(html)
puts doc.at_css('p.info').text
```

```bash
ruby scripts/extract.rb
```

- 显式固定版本，例如 `gem 'nokogiri', '~> 1.16'`；这里没有 lockfile。
- 工作目录中的已有 `Gemfile` 或 `BUNDLE_GEMFILE` 环境变量可能造成干扰。

## 为 agent 使用设计脚本

agent 运行脚本后，会读取 stdout 和 stderr 来决定下一步。以下设计会显著提高脚本可用性。

### 避免交互式提示

这是 agent 执行环境的硬要求。agent 在非交互 shell 中运行，不能回应 TTY prompt、密码弹窗或确认菜单。脚本若等待交互输入，会无限挂起。

通过命令行 flags、环境变量或 stdin 接收所有输入：

```text
# 反例：会卡住等待输入
$ python scripts/deploy.py
Target environment: _

# 正例：给出清晰错误和下一步提示
$ python scripts/deploy.py
Error: --env is required. Options: development, staging, production.
Usage: python scripts/deploy.py --env staging --tag v1.2.3
```

### 用 `--help` 说明用法

`--help` 输出是 agent 学习脚本接口的主要方式。应包含简短说明、可用 flags 和使用示例：

```text
Usage: scripts/process.py [OPTIONS] INPUT_FILE

Process input data and produce a summary report.

Options:
  --format FORMAT    Output format: json, csv, table (default: json)
  --output FILE      Write output to FILE instead of stdout
  --verbose          Print progress to stderr

Examples:
  scripts/process.py data.csv
  scripts/process.py --format csv --output report.csv data.csv
```

保持简洁，因为这些输出也会进入 agent 的上下文窗口。

### 写有帮助的错误信息

错误信息会直接影响 agent 的下一次尝试。模糊的 “Error: invalid input” 会浪费一轮。应说明哪里错了、期望是什么、下一步该怎么做：

```text
Error: --format must be one of: json, csv, table.
       Received: "xml"
```

### 使用结构化输出

优先使用 JSON、CSV、TSV 等结构化格式，而不是自由文本。结构化格式既能被 agent 使用，也能被 `jq`、`cut`、`awk` 等标准工具消费。

```text
# 空白对齐：程序解析困难
NAME          STATUS    CREATED
my-service    running   2025-01-15

# 分隔格式：字段边界明确
{"name": "my-service", "status": "running", "created": "2025-01-15"}
```

**分离数据和诊断信息**：把结构化数据写到 stdout，把进度、警告和诊断信息写到 stderr。这样 agent 可以捕获干净可解析的输出，同时在需要时仍能看到诊断信息。

### 其他考虑

- **幂等性**：agent 可能重试命令。“不存在则创建”比“创建并在重复时失败”更安全。
- **输入约束**：对含糊输入给出清晰错误，而不是猜测。能用枚举和封闭集合时优先使用。
- **dry-run 支持**：对破坏性或有状态操作，`--dry-run` 可让 agent 预览将发生的事情。
- **有意义的退出码**：为不同失败类型使用不同退出码，例如 not found、invalid arguments、auth failure，并在 `--help` 中记录。
- **安全默认值**：考虑破坏性操作是否需要 `--confirm`、`--force` 或其他显式防护。
- **可预测输出规模**：很多 agent harness 会在阈值外截断工具输出，例如 10-30K 字符。若脚本可能产生大量输出，默认输出摘要或合理限制，并支持 `--offset` 这类参数；如果大输出无法分页，应要求 agent 传入 `--output`，或用 `-` 明确选择 stdout。
