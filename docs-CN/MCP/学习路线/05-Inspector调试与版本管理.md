---
title: "MCP Inspector、调试与版本管理"
aliases:
  - MCP debugging
  - MCP Inspector
tags:
  - MCP
  - 调试
source_checked: 2026-07-19
lang: zh-CN
translation_key: MCP/学习路线/05-Inspector调试与版本管理.md
translation_route: en/mcp/learning-path/05-inspector-debugging-and-versioning
translation_default_route: zh-CN/MCP/学习路线/05-Inspector调试与版本管理
---

# MCP Inspector、调试与版本管理

## 本节目标

学完后，你应能：

- 用 Inspector 验证连接、capability、resource/prompt/tool 与 notification。
- 按层收集最小证据，不把所有故障都归因于“版本不兼容”。
- 设计不泄露秘密的结构化日志和问题单。
- 区分规范版本、协商版本、SDK 版本和应用版本，并建立升级门禁。

## Inspector 适合回答什么

官方 MCP Inspector 是交互式开发工具，可连接 stdio 或 Streamable HTTP server，查看：

- 连接命令、参数、环境与传输；
- initialize 后暴露的 resources、prompts、tools；
- resource 内容与订阅；
- prompt 参数与生成的 messages；
- tool schema、手工输入与执行结果；
- server 日志和 notifications。

它特别适合回答“server 实际声明了什么、实际返回了什么”，而不是凭配置猜测。它不能单独证明：

- 生产身份与权限正确；
- 并发、超时、重试和恢复可靠；
- 所有负向参数都被拒绝；
- 版本升级无回归；
- server 或返回内容安全可信。

因此 Inspector 是开发证据入口，不替代自动契约测试、集成测试、负载测试和安全审查。

## 在 Windows 11 / PowerShell 7 启动

官方文档在 2026-07-14 给出的通用形式是：

```powershell
npx @modelcontextprotocol/inspector "<server-command>" "<arg1>" "<arg2>" # 由 npx 启动 Inspector；尖括号占位符必须替换为已核对的真实 server 命令与参数。
```

例如检查本地 Python server，可把最后部分替换为项目 README 中真实、已核对的启动命令。不要直接复制未知包名或示例路径。`npx` 可能联网下载依赖并执行代码；在企业或敏感环境中先审查包、版本与来源，必要时固定版本并在隔离环境运行。

安全启动步骤：

1. 先在终端单独确认 server command 能运行，记录绝对路径与工作目录。
2. 只传必需环境变量；不要把真实 token 写进教程、命令历史或截图。
3. 启动 Inspector，选择正确传输。
4. 保存 initialize 的协议版本与双方 capabilities。
5. 先做只读列表/读取，再测试写操作；写操作使用测试账户和可恢复数据。

## 一套七层排错法

### 1. 配置与进程

检查 command 是否存在、绝对路径、cwd、文件权限、运行时版本。GUI host 的环境与当前 PowerShell 可能不同；“终端能运行”不等于 host 能启动。

### 2. 传输

- stdio：stdin/stdout framing、UTF-8、换行、stderr。
- HTTP：URL、DNS、TLS、代理、Origin、状态码、Content-Type、GET/SSE。

先证明字节能正确往返，再看协议。

### 3. JSON-RPC

检查 `jsonrpc`、method、ID 配对、result/error 二选一、notification 不带 ID、是否有重复 outstanding ID。保存脱敏的首个错误消息，不要只看 UI 中一句“connection failed”。

### 4. 生命周期与版本

检查 initialize 是否第一条、server 选了哪个版本、client 是否接受、initialized notification 是否到达。HTTP 后续请求是否带协商后的 `MCP-Protocol-Version`。

### 5. Capability 与方向

从 initialize 原始交换确认：

- server 是否声明 tools/resources/prompts；
- client 是否声明 roots/sampling/elicitation；
- sub-capability（`listChanged`、`sampling.tools`、elicitation mode、tasks request path）是否满足；
- 方法方向是否正确。

`-32602 Invalid params` 有很多原因，其中之一就是 server 向未声明能力的 client 发 sampling/elicitation。不能只凭错误码锁定根因。

### 6. 契约

检查工具名、input schema、必填、枚举、未知字段、output schema、structuredContent，以及协议错误和 execution error 是否被正确区分。

### 7. 业务与下游

最后检查身份、scope、资源所有权、限流、数据库、第三方 API、幂等性和恢复。业务失败不需要盲目重启 MCP 会话。

## 日志策略

stdio server：

- stdout 只写 MCP JSON-RPC；
- 诊断写 stderr；
- stderr 有日志不自动表示失败。

Streamable HTTP：

- client 通常不会捕获远程 server 的 stderr；
- 使用 server 端日志聚合、HTTP 工具和 MCP logging notifications；
- 跟踪 `Mcp-Session-Id` 与 SSE，但不要把 session ID 当身份。

建议字段：

```text
timestamp, server_name, server_version, transport,
negotiated_protocol, request_direction, request_id, method,
capability_decision, duration_ms, outcome, retry_or_cancel
```

默认脱敏 token、cookie、prompt/resource 正文、个人数据和本地敏感路径。为了复现可记录 schema 版本、参数字段名与不可逆摘要，不必记录明文。

## Inspector 的最小测试矩阵

| 区域 | 正向 | 负向 | 要保存的证据 |
| --- | --- | --- | --- |
| initialize | 支持的版本与能力 | 不支持版本/缺能力 | 双方 version/capability |
| tools | 合法参数 | 缺参、错类型、未知字段 | schema、result/error |
| resources | list/read/templates、成功订阅→updated→重读→unsubscribe | 无效 URI/template/cursor/Base64、越界、总量超限、缺 sub-capability、失败订阅、撤销后旧通知 | URI/MIME/大小、capability、订阅状态、脱敏授权决策 |
| prompts | 合法参数 | 缺失参数 | 返回 messages 与来源 |
| notifications | 声明后收到 | 未声明 sub-capability | 方向与方法 |
| 安全 | 测试账户允许 | 错 audience/resource/tenant/scope、失效 token、旧授权修订、Roots 冒充 ACL | 授权决策与脱敏审计 |

涉及 sampling、elicitation、roots 或 Tasks 时，Inspector/host 是否实现 client features 会随工具版本变化。没有观察到相应 UI 或消息时，应记录“当前工具未验证”，不要推断协议不存在。

## 版本记录：四个事实

| 字段 | 示例含义 | 从哪里取 |
| --- | --- | --- |
| spec version | 当前按哪份协议阅读 | 官方版本页，例如 `2025-11-25` |
| negotiated version | 本次会话实际使用什么 | initialize response |
| SDK version | 实现库支持什么 | lockfile/package metadata/SDK release |
| app/server version | 哪个产品与构建 | app About、包版本、Git commit |

还要记录文档获取日期。不要只写“最新版”，也不要因为 SDK 包版本数字更大就推断它支持最新规范所有可选能力。

## 升级门禁

升级协议或 SDK 前：

1. 阅读目标规范 key changes 和 SDK release notes。
2. 列出新增、删除、软弃用字段与能力。
3. 对现有 initialize、tools/resources/prompts 和 client features 建回归样例。
4. 运行离线消息/契约测试。
5. 用 Inspector 验证真实 server。
6. 在目标 host 中做集成测试，尤其是授权、用户同意和错误呈现。
7. 测试旧 peer 或明确停止兼容；记录回滚方案。

`2025-11-25` 中 URL elicitation、sampling tool use 与 Tasks 等边界可能不是所有 SDK/host 都同时实现；Tasks 仍标记实验性。上线判断要以“双方声明 + 实测”而不是规范页面存在为准。

## 可复用问题单

```text
host/client 名称与版本：
server 包/提交：
SDK 与运行时：
文档获取日期：
请求协议版本 / server 选择版本：
双方 capabilities：
传输与 endpoint/command（已脱敏）：
最小复现：
预期 / 实际：
首个失败层：
首个失败 request ID 和 method：
Inspector 观察 / 脱敏日志：
是否涉及真实写入、凭据或生产数据：
```

## 动手练习

1. 对“Inspector 能列出 tools，但 `tools/call` 返回 invalid params”按七层法写出下一条最小证据。
2. 对“stdio JSON parse error”分别验证 stdout 污染、编码与换行 framing。
3. 模拟一次 capability 缺失：对照 initialize，说明为什么重启 server 不能修复未实现的 client sampling。
4. 为一次 SDK 升级填写四版本表和回归矩阵。
5. 把一段包含 token 和完整正文的日志改成既可关联又不泄密的结构。

## 自测

1. Inspector 成功调用一次 tool，为什么还不能证明生产可用？
2. stderr 有内容是否等于 stdio server 失败？
3. `-32602` 为什么不能直接归因于 schema？
4. 规范版本与协商版本分别从哪里获得？
5. Tasks 出现在当前规范中，为什么仍要检查 SDK/host capability 和实测？

能独立完成“七层定位 + 四版本记录 + 最小测试矩阵”，才算掌握。

## 下一步

进入 [[MCP/学习路线/06-项目-离线MCP消息验证|项目：离线 MCP 消息验证]]，把这些检查变成可重复的自动化证据。

## 参考资料

以下均为 MCP 第一方资料，获取/复核日期：2026-07-14。

- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- [Debugging MCP](https://modelcontextprotocol.io/docs/tools/debugging)
- [Protocol Versioning](https://modelcontextprotocol.io/docs/learn/versioning)
- [Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
