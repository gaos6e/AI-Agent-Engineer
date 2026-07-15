---
title: "连接远程 MCP 服务器"
english_title: "Connect to remote MCP Servers"
source_url: "https://modelcontextprotocol.io/docs/develop/connect-remote-servers.md"
source_path: "/docs/develop/connect-remote-servers.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 连接远程 MCP 服务器

## 核心结论

- 远程 MCP server 通过网络暴露能力，通常使用 Streamable HTTP 和标准 Web 鉴权方式。
- Custom Connector 是客户端连接远程 MCP 服务的一种方式，重点在 URL、授权和权限范围。
- 远程接入要把网络安全、OAuth、令牌存储和数据边界作为一等需求。

## 主要内容

- 远程 server 适合 SaaS、企业系统、云数据库和跨设备共享能力，不需要在用户本机启动子进程。
- 连接流程通常包括添加 connector、输入 server URL、完成授权、确认权限范围并在客户端中使用暴露的工具。
- 最佳实践包括使用 HTTPS、最小权限、清晰命名、可撤销授权和针对敏感工具的用户确认。

## 关键概念 / 流程 / 注意事项

- 不要把远程 MCP server 当作普通无状态 HTTP API；MCP 仍有会话、能力协商和通知等协议语义。
- 生产环境优先使用 OAuth 或等价的可审计授权机制，避免把长期密钥直接发给客户端。
- 远程 server 需要考虑多租户隔离、速率限制、日志脱敏和错误信息最小化。

## 相关页面

- [[01-连接本地 MCP 服务器|连接本地 MCP 服务器]]
- [[01-MCP 授权理解|MCP 授权理解]]
- [[02-安全最佳实践|安全最佳实践]]
- [[01-客户端最佳实践|客户端最佳实践]]
