---
title: "理解 MCP 服务器"
english_title: "Understanding MCP servers"
source_url: "https://modelcontextprotocol.io/docs/learn/server-concepts.md"
source_path: "/docs/learn/server-concepts.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 理解 MCP 服务器

## 核心结论

- MCP server 是暴露特定能力的程序，核心能力是 ==tools==、==resources== 和 ==prompts==。
- ==Tools 用于执行动作，resources 用于提供上下文数据，prompts 用于复用交互模板。==
- 优秀的 server 应职责聚焦、权限清晰，并让 host/client 能够动态发现其能力。

## 主要内容

- Tools 通常带有名称、说明和输入 schema，client 先发现工具，再在模型决定或用户确认后调用。
- Resources 通过 URI 暴露文件、数据库记录、API 响应、配置等上下文，适合让模型读取而不是直接执行动作。
- Prompts 是可复用的提示模板，适合把常见工作流封装成可发现、可参数化的入口。

## 关键概念 / 流程 / 注意事项

- 工具是高风险边界，输入 schema、权限校验和错误信息必须清楚。
- 资源适合提供上下文，不应把需要副作用的操作伪装成资源读取。
- 多个 MCP server 可以组合使用，例如旅行场景中日历、文件、搜索和预订系统分别由不同 server 提供。

## 相关页面

- [[01-MCP 架构概览|MCP 架构概览]]
- [[04-构建 MCP 服务器|构建 MCP 服务器]]
- [[02-示例服务器|示例服务器]]
- [[02-安全最佳实践|安全最佳实践]]
