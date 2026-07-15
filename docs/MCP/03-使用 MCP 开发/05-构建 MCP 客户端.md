---
title: "构建 MCP 客户端"
english_title: "Build an MCP client"
source_url: "https://modelcontextprotocol.io/docs/develop/build-client.md"
source_path: "/docs/develop/build-client.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 构建 MCP 客户端

## 核心结论

- MCP client 负责连接 server、初始化会话、发现能力，并把可用工具/资源/prompt 呈现给 host 或模型层。
- 构建 client 的重点是连接管理、能力注册、用户授权、错误恢复和安全边界。
- 一个 host 通常会为每个 server 维护独立 client，以隔离状态和权限。

## 主要内容

- 最小客户端流程包括读取 server 配置、建立传输、创建 session、发送 initialize、读取 capabilities、列出 primitives。
- 工具调用通常不是 client 自己随意决定，而是由 host 的交互流程、模型输出和用户授权共同决定。
- client 还需要处理 server 通知、连接断开、版本不兼容和多 server 工具合并。

## 关键概念 / 流程 / 注意事项

- 客户端实现不要把所有 server 工具无差别暴露给模型；应有发现、筛选、授权和上下文预算策略。
- 本地 server 和远程 server 的认证、生命周期和失败模式不同，连接层要显式区分。
- 如果面向生产 host，优先阅读 [[01-客户端最佳实践|客户端最佳实践]] 和 [[02-安全最佳实践|安全最佳实践]]。

## 相关页面

- [[03-理解 MCP 客户端|理解 MCP 客户端]]
- [[01-客户端最佳实践|客户端最佳实践]]
- [[01-MCP 架构概览|MCP 架构概览]]
- [[02-SDKs|SDKs]]
