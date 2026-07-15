---
title: "SDKs"
english_title: "SDKs"
source_url: "https://modelcontextprotocol.io/docs/sdk.md"
source_path: "/docs/sdk.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# SDKs

## 核心结论

- 官方 SDK 提供 MCP 协议实现，减少手写 JSON-RPC、传输层和能力协商的工作量。
- 选择 SDK 时应关注语言生态、维护状态、协议版本支持和目标部署环境。
- SDK 能简化实现，但不能替代应用层的权限设计、用户确认和错误处理。

## 主要内容

- SDK 页面是查找官方语言实现和入门链接的入口。常见任务包括构建 server、构建 client、测试工具调用和连接不同传输。
- 使用 SDK 时，仍要清楚 primitives 的语义：tool 有副作用，resource 提供上下文，prompt 提供模板。
- 升级 SDK 前要检查 changelog、协议 revision、breaking changes 和目标客户端兼容性。

## 关键概念 / 流程 / 注意事项

- 不要跨语言照搬示例代码；以所选 SDK 的官方模式为准。
- 如果遇到协议层问题，先用 [[01-MCP Inspector|MCP Inspector]] 或最小 client/server 复现，确认是 SDK 使用问题还是客户端集成问题。
- 生产服务要固定依赖版本，并记录 server 支持的 MCP revision。

## 相关页面

- [[04-构建 MCP 服务器|构建 MCP 服务器]]
- [[05-构建 MCP 客户端|构建 MCP 客户端]]
- [[04-版本管理|版本管理]]
- [[02-调试|调试]]
