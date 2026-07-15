---
title: "连接本地 MCP 服务器"
english_title: "Connect to local MCP servers"
source_url: "https://modelcontextprotocol.io/docs/develop/connect-local-servers.md"
source_path: "/docs/develop/connect-local-servers.md"
fetched_at: "2026-05-07T20:46:27+08:00"
tags:
  - MCP
  - 官方文档
---

# 连接本地 MCP 服务器

## 核心结论

- 本地 MCP server 通常通过 stdio 作为子进程启动，适合文件系统、命令行工具和本机资源集成。
- 客户端配置负责声明 server 的启动命令、参数和允许访问的路径或资源范围。
- 本地 server 能力强，配置时必须重视授权提示、路径范围和日志排查。

## 主要内容

- 官方示例通常从文件系统 server 入门：安装 server，配置 Claude Desktop 或其他 host，然后让 AI 读取、列出或管理指定目录。
- 使用流程包括准备运行环境、安装 server、写入客户端配置、重启 host、确认 server 连接状态，再进行工具调用。
- 本地文件管理示例能展示 MCP 的权限确认模型：模型提出操作，客户端展示风险和目标，用户确认后才执行。

## 关键概念 / 流程 / 注意事项

- 本地 server 不等于低风险；文件系统、shell、浏览器自动化等能力都应限定目录和命令范围。
- Windows 环境要特别注意命令路径、Node/Python 可执行文件、环境变量和工作目录。
- 如果连接失败，优先检查 host 日志、server 启动命令、依赖安装和工作目录。

## 相关页面

- [[02-连接远程 MCP 服务器|连接远程 MCP 服务器]]
- [[01-MCP Inspector|MCP Inspector]]
- [[02-调试|调试]]
- [[02-安全最佳实践|安全最佳实践]]
