---
title: "构建 MCP 服务器"
english_title: "Build an MCP server"
source_url: "https://modelcontextprotocol.io/docs/develop/build-server.md"
source_path: "/docs/develop/build-server.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 构建 MCP 服务器

## 核心结论

- 构建 MCP server 的最小路径是：定义能力、实现工具/资源/prompt、启动传输层、用 Inspector 或客户端测试。
- server 应专注暴露一个清晰领域的能力，而不是把大量无关动作塞进同一个入口。
- 输入 schema、错误处理、权限校验和日志是 server 可维护性的关键。

## 主要内容

- 官方 quickstart 通常通过一个小 server 演示核心概念：注册工具，定义输入参数，返回结构化结果，再用命令或 Inspector 调用。
- 底层流程包括 client 初始化、能力协商、工具发现、工具执行和结果返回。SDK 会封装 JSON-RPC 细节，但协议边界仍然存在。
- 测试时应覆盖正常调用、缺失参数、非法参数、外部依赖失败和权限不足。

## 关键概念 / 流程 / 注意事项

- 工具命名要稳定、语义明确，描述要告诉模型何时使用、输入是什么、风险在哪里。
- 不要在导入模块时做重 IO 或申请长期资源；server 初始化失败会直接表现为客户端连接失败。
- 本地开发优先用 [[01-MCP Inspector|MCP Inspector]]，接入客户端前先确认工具列表和工具调用能独立工作。

## 相关页面

- [[02-理解 MCP 服务器|理解 MCP 服务器]]
- [[01-MCP Inspector|MCP Inspector]]
- [[02-调试|调试]]
- [[02-SDKs|SDKs]]
