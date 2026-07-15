---
title: "使用 Agent Skills 构建"
english_title: "Build with Agent Skills"
source_url: "https://modelcontextprotocol.io/docs/develop/build-with-agent-skills.md"
source_path: "/docs/develop/build-with-agent-skills.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 使用 Agent Skills 构建

## 核心结论

- Agent Skills 用来给 AI 编码助手提供结构化任务指导，帮助它按 MCP 设计原则构建 server 或 client。
- 它不是 MCP 协议 primitive 本身，而是面向开发过程的说明、模板和约束集合。
- 适合在已有代码库中生成或改造 MCP 集成时减少遗漏。

## 主要内容

- 官方提供的 skills 覆盖 server 构建、client 构建、调试、部署等方向，可作为 AI agent 的任务手册。
- 使用时应先选择目标 skill，再给出项目背景、语言、框架、要暴露的能力和安全约束。
- 部署路径取决于 server 形态：本地 stdio server 通常随客户端配置启动；远程 server 需要 Web 服务、鉴权和运维策略。

## 关键概念 / 流程 / 注意事项

- Skill 只能指导实现，不能替代对真实代码、配置和安全策略的验证。
- 如果让 agent 修改现有仓库，应把工具范围、写入范围、测试命令和不允许触碰的文件写清楚。
- 生成 MCP server 后仍要用 [[01-MCP Inspector|MCP Inspector]] 和目标客户端实测。

## 相关页面

- [[04-构建 MCP 服务器|构建 MCP 服务器]]
- [[05-构建 MCP 客户端|构建 MCP 客户端]]
- [[02-调试|调试]]
- [[01-MCP Inspector|MCP Inspector]]
