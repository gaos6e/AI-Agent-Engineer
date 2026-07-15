---
title: "MCP Inspector"
english_title: "MCP Inspector"
source_url: "https://modelcontextprotocol.io/docs/tools/inspector.md"
source_path: "/docs/tools/inspector.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# MCP Inspector

## 核心结论

- MCP Inspector 是开发和调试 MCP server 的交互式工具，可以连接 server、查看 primitives 并直接调用工具。
- 它适合在接入真实客户端之前验证 server 启动、能力发现、资源读取、prompt 获取和工具执行。
- Inspector 能把协议层问题和目标客户端集成问题分开定位。

## 主要内容

- 常见用法包括检查 npm/PyPI 安装的 server、本地开发 server、资源列表、prompt 列表、工具 schema 和工具返回结果。
- 界面通常包含 server 连接、resources、prompts、tools 和 notifications 等区域。
- 开发循环是：改 server，重启或重新连接 Inspector，验证 initialize、list 和 call，再接入实际 host。

## 关键概念 / 流程 / 注意事项

- 如果 Inspector 能调用成功但客户端失败，优先检查客户端配置、工作目录、环境变量和权限提示。
- 如果 Inspector 也失败，优先检查 server 启动命令、依赖、标准输出污染和初始化异常。
- 不要在工具返回中暴露调试密钥或敏感环境变量。

## 相关页面

- [[02-调试|调试]]
- [[04-构建 MCP 服务器|构建 MCP 服务器]]
- [[01-连接本地 MCP 服务器|连接本地 MCP 服务器]]
- [[02-SDKs|SDKs]]
