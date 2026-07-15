---
title: "MCP 架构概览"
english_title: "Architecture overview"
source_url: "https://modelcontextprotocol.io/docs/learn/architecture.md"
source_path: "/docs/learn/architecture.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# MCP 架构概览

## 核心结论

- MCP 采用 host-client-server 架构：用户使用 host，host 为每个 server 创建一个 client 连接。
- 协议分成数据层和传输层：数据层定义 JSON-RPC 消息与 primitives，传输层负责进程或网络通信。
- 最核心的 server primitives 是 tools、resources、prompts；client 侧也可以提供 sampling、elicitation、logging 等能力。

## 主要内容

- Host 是 Claude Desktop、Claude Code、VS Code 等应用；Client 是 host 内部维护的协议连接；Server 是实际提供上下文和动作能力的程序。
- 数据层基于 JSON-RPC 2.0，覆盖初始化、能力协商、请求/响应、通知、工具调用、资源读取、prompt 获取和进度更新。
- 传输层主要包括 stdio 和 Streamable HTTP。stdio 适合本地单进程集成；Streamable HTTP 适合远程、多客户端和标准 HTTP 鉴权场景。

## 关键概念 / 流程 / 注意事项

- 不要把 MCP server 等同于远程服务器；==它可以是本地子进程，也可以是远程服务。==
- 工具列表可动态变化，server 可以通过 notifications 提醒 client 重新发现能力。
- 实现时通常先完成 initialize，再做 `tools/list`、`resources/list`、`prompts/list` 等发现流程，最后按需执行 `tools/call` 或读取资源。

## 相关页面

- [[03-理解 MCP 客户端|理解 MCP 客户端]]
- [[02-理解 MCP 服务器|理解 MCP 服务器]]
- [[04-版本管理|版本管理]]
- [[02-调试|调试]]
