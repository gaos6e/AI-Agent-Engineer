---
title: "MCP 授权理解"
english_title: "Understanding Authorization in MCP"
source_url: "https://modelcontextprotocol.io/docs/tutorials/security/authorization.md"
source_path: "/docs/tutorials/security/authorization.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# MCP 授权理解

## 核心结论

- 当 MCP server 访问受保护资源或代表用户执行动作时，需要明确授权流程。
- 远程 MCP 授权通常围绕 OAuth 2.1、resource server、authorization server 和 client 注册展开。
- 授权目标是让用户知道谁在访问什么资源，并能授予、限制和撤销权限。

## 主要内容

- 应在 server 需要访问用户账户、企业数据、第三方 API 或敏感操作时启用授权。
- 典型流程包括发现受保护资源元数据、发起授权、用户登录并同意、客户端取得 token，然后带 token 调用 MCP server。
- 实现示例展示了身份提供方配置、MCP server 配置、测试授权 server 和排查常见错误的路径。

## 关键概念 / 流程 / 注意事项

- 不要把用户 token 透传给不该接触的下游系统；token audience、scope 和生命周期要明确。
- 本地开发可用简化配置验证流程，但生产环境必须使用 HTTPS 和可审计授权。
- 鉴权失败要返回可诊断但不泄密的错误信息。

## 相关页面

- [[02-连接远程 MCP 服务器|连接远程 MCP 服务器]]
- [[02-安全最佳实践|安全最佳实践]]
- [[01-客户端最佳实践|客户端最佳实践]]
- [[02-调试|调试]]
