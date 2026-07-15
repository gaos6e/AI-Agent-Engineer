---
title: "什么是 Model Context Protocol"
english_title: "What is the Model Context Protocol (MCP)?"
source_url: "https://modelcontextprotocol.io/docs/getting-started/intro.md"
source_path: "/docs/getting-started/intro.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 什么是 Model Context Protocol

## 核心结论

- MCP 是 AI 应用连接外部系统的开放协议，目标是把工具、数据源和工作流接入方式标准化。
- 它解决的不是模型推理本身，而是让 AI 客户端以统一方式发现、调用和管理外部能力。
- 可以把 MCP 理解为 AI 应用的通用连接层：客户端负责使用能力，服务器负责暴露能力。

## 主要内容

- MCP 让 Claude、ChatGPT、IDE、企业机器人等 AI 应用接入本地文件、数据库、搜索、日历、Notion、Figma 等外部系统。
- 协议生态分成客户端、服务器、SDK、开发工具、示例实现和官方扩展。开发者可以构建 MCP server 暴露能力，也可以构建 MCP client 接入现有 server。
- 最终用户得到的是更能执行任务的 AI 应用；开发者得到的是较少重复适配的集成边界。

## 关键概念 / 流程 / 注意事项

- MCP 的价值在于标准化连接，不保证某个 AI 应用会如何选择工具、压缩上下文或执行安全策略。
- 第一次学习建议顺序是：先读本页，再读 [[01-MCP 架构概览|MCP 架构概览]]，然后根据角色选择 [[04-构建 MCP 服务器|构建 MCP 服务器]] 或 [[05-构建 MCP 客户端|构建 MCP 客户端]]。
- 做本地集成时重点关注 stdio；做远程服务时重点关注 Streamable HTTP、鉴权和权限边界。

## 相关页面

- [[01-MCP 架构概览|MCP 架构概览]]
- [[02-理解 MCP 服务器|理解 MCP 服务器]]
- [[03-理解 MCP 客户端|理解 MCP 客户端]]
- [[02-SDKs|SDKs]]
