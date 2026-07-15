---
title: Agent Skills 概览
english_title: Agent Skills Overview
source_url: https://agentskills.io/home.md
source_path: /home.md
fetched_at: 2026-05-12T14:48:55+08:00
tags:
  - Agent-Skills
  - 官方文档
---

# Agent Skills 概览

Agent Skills（智能体技能）是一种标准化方式，用来为 AI agent 增加新的能力和专业知识。

> [!info] 文档索引
> 完整页面索引见 <https://agentskills.io/llms.txt>。本页来源为 <https://agentskills.io/home.md>。

## 什么是 Agent Skills？

Agent Skills 是一种轻量、开放的格式，用来通过专门知识和工作流扩展 AI agent 的能力。一个技能本质上是一个包含 `SKILL.md` 文件的文件夹。这个文件至少包含 `name` 和 `description` 等元数据，以及指导 agent 完成某类任务的说明。

技能也可以携带脚本、参考资料、模板和其他资源：

```text
my-skill/
├── SKILL.md          # 必需：元数据 + 说明
├── scripts/          # 可选：可执行代码
├── references/       # 可选：文档资料
├── assets/           # 可选：模板和资源
└── ...               # 其他文件或目录
```

## 为什么需要 Agent Skills？

Agent 的能力越来越强，但在真实工作中经常缺少足够的上下文。Skills 通过可移植、可版本管理的文件夹，把流程知识、公司/团队/个人的特定上下文打包起来，让 agent 在需要时按需加载。

这带来三个直接价值：

- **领域专业知识**：把法律审查流程、数据分析管线、演示文稿格式等专业知识沉淀为可复用说明和资源。
- **可重复工作流**：把多步骤任务转成稳定、可审计的过程。
- **跨产品复用**：一次构建技能，即可在任何兼容 Agent Skills 的 agent 中使用。

## Agent Skills 如何工作？

Agent 通过渐进式披露（progressive disclosure）加载技能，通常分为三步：

1. **发现（Discovery）**：启动时只加载每个技能的 `name` 和 `description`，让 agent 知道技能大概何时相关。
2. **激活（Activation）**：当任务匹配某个技能描述时，agent 才读取完整的 `SKILL.md` 说明。
3. **执行（Execution）**：agent 按说明执行任务，并在需要时运行技能携带的代码或加载引用文件。
#注意：激活不代表调用，读取全部skill后才决定是否调用

完整说明只在任务确实需要时进入上下文，因此 agent 可以同时持有大量可用技能，而不显著增加默认上下文成本。

## 可以在哪里使用？

Agent Skills 已被许多 AI 工具和 agent 客户端支持。兼容工具列表见 [[03-Client Showcase|Client Showcase]]。

## 开放开发

Agent Skills 格式最初由 Anthropic 开发，并作为开放标准发布；目前已经被越来越多 agent 产品采用。该标准开放给更广泛的生态系统参与贡献，讨论入口包括 [GitHub](https://github.com/agentskills/agentskills) 和 [Discord](https://discord.gg/)。

## 下一步

- [[01-Quickstart|Quickstart]]：创建第一个 Agent Skill 并实际运行。
- [[02-Specification|Specification]]：查看完整格式规范。
