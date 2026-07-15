---
title: "理解 MCP 客户端"
english_title: "Understanding MCP clients"
source_url: "https://modelcontextprotocol.io/docs/learn/client-concepts.md"
source_path: "/docs/learn/client-concepts.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 理解 MCP 客户端

## 核心结论

- MCP client 是 host 内部的协议组件，负责和单个 MCP server 维持连接、协商能力并交换消息。
- 客户端不只是消费 server 的工具和资源，也可以向 server 暴露 elicitation、roots、sampling 等能力。
- 理解 client 能力有助于设计更安全、更符合用户意图的 MCP 交互。

## 主要内容

- Elicitation 允许 server 请求用户补充信息或确认动作，适合订票、删除、授权等需要人类确认的流程。
- Roots 让 client 告诉 server 当前可访问的工作区或文件范围，帮助 server 在明确边界内提供能力。
- Sampling 允许 server 请求 host 使用其 LLM 生成内容，但仍由 client/host 控制模型调用和用户体验。

## 关键概念 / 流程 / 注意事项

- Client 能力应当由 host 策略控制，不能让 server 绕过用户授权直接扩大权限。
- Roots 是重要的最小权限边界：server 应只围绕 client 暴露的 workspace 工作。
- Sampling 适合 server 需要模型能力但不想绑定具体 LLM SDK 的场景；安全实现必须明确提示来源和用户同意。

## 相关页面

- [[01-MCP 架构概览|MCP 架构概览]]
- [[02-理解 MCP 服务器|理解 MCP 服务器]]
- [[01-客户端最佳实践|客户端最佳实践]]
- [[01-MCP 授权理解|MCP 授权理解]]
