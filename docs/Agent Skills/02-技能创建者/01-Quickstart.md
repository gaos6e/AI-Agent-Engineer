---
title: Agent Skills 快速开始
english_title: Quickstart
source_url: https://agentskills.io/skill-creation/quickstart.md
source_path: /skill-creation/quickstart.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
  - 快速开始
---

# 快速开始

本教程会创建第一个 Agent Skill，并在 VS Code 中查看它如何生效。示例技能会让 agent 使用随机数生成器“掷骰子”。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/skill-creation/quickstart.md>。

## 前置条件

- 安装 [VS Code](https://code.visualstudio.com/)。
- 安装 [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)。

> [!note]
> 本教程使用 VS Code，但 Agent Skills 是开放格式。同一个技能也可用于其他兼容 agent，例如 Claude Code 和 OpenAI Codex。

## 创建技能

一个技能是包含 `SKILL.md` 的文件夹。VS Code 默认从 `.agents/skills/` 查找技能。在项目中创建 `.agents/skills/roll-dice/SKILL.md`：

````markdown
---
name: roll-dice
description: Roll dice using a random number generator. Use when asked to roll a die (d6, d20, etc.), roll dice, or generate a random dice roll.
---

To roll a die, use the following command that generates a random number from 1
to the given number of sides:

```bash
echo $((RANDOM % <sides> + 1))
```

```powershell
Get-Random -Minimum 1 -Maximum (<sides> + 1)
```

Replace `<sides>` with the number of sides on the die (e.g., 6 for a standard
die, 20 for a d20).
````

这就是完整技能：一个不到 20 行的文件。各部分作用如下：

- **`name`**：技能的短标识符，必须与文件夹名一致。
- **`description`**：告诉 agent 何时使用这个技能。agent 会基于这个字段决定是否激活技能。
- **正文**：技能激活后 agent 要遵循的说明。这里要求 agent 根据用户请求中的骰子面数，替换命令中的 `<sides>` 并生成随机数。

## 试运行

1. 在 VS Code 中打开项目。
2. 打开 Copilot Chat 面板。
3. 在聊天面板底部的模式下拉框中选择 **Agent** 模式。
4. 输入 `/skills`，确认列表中出现 `roll-dice`。如果没有出现，检查文件是否位于项目根目录下的 `.agents/skills/roll-dice/SKILL.md`。
5. 提问：**"Roll a d20"**。

agent 应该会激活 `roll-dice` 技能。它可能会请求运行终端命令的权限；允许后，它会执行命令并返回 1 到 20 之间的随机数。

> [!note]
> 不同模型的工具使用可靠性不同。有些模型会稳定遵循技能说明并运行命令，有些模型可能尝试自行回答。如果 agent 没有运行终端命令，可以在模型下拉框中尝试其他模型。

## 背后机制

上述流程背后发生了三件事：

1. **发现**：聊天会话启动时，agent 扫描默认技能目录并发现这个技能。它只读取 `name` 和 `description`，刚好足以判断技能何时可能相关。
2. **激活**：当用户要求掷骰子时，agent 将问题与技能描述匹配，然后把完整 `SKILL.md` 正文加载进上下文。
3. **执行**：agent 按正文说明操作，根据用户请求中的骰子面数调整终端命令。

这套流程使用渐进式披露（progressive disclosure），让 agent 能访问许多技能，而无需一开始就加载所有技能说明。

## 下一步

- [[02-Best practices|Best practices]]：如何编写范围清晰、效果稳定的技能。
- [[03-Optimizing descriptions|Optimizing skill descriptions]]：测试并改进技能 `description`，让它在正确提示上触发。
- [[02-Specification|Specification]]：`SKILL.md` 文件的完整格式参考。
- [Example skills](https://github.com/anthropics/skills)：浏览 GitHub 上的真实技能示例。
