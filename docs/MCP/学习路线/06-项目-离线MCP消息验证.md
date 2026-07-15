---
title: 项目：离线 MCP 消息验证
aliases:
  - MCP offline validation project
  - MCP 教学协议验证器
tags:
  - MCP
  - 项目
source_checked: 2026-07-14
---

# 项目：离线 MCP 消息验证

## 项目目标

不用网络、真实 server、SDK 或 API key，完成一个可重复的 MCP 教学验证项目。它把本路线中的关键规则变成数据驱动检查：

- 严格 JSON 与 JSON-RPC envelope；
- initialize 状态机和双向 request ID；
- client/server capability 方向与 sub-capability；
- tool 输入、结构化输出和两类错误；
- roots、sampling、elicitation 与实验性 Tasks 的关键边界；
- 正向、负向与回归测试。

> [!warning] 能力边界
> 这是课程定义的 `offline-mcp-teaching-profile-v1`，不是 MCP 官方 conformance suite。它只实现课程使用的 JSON Schema/方法子集，并在若干位置故意比通用 JSON-RPC 更严格。真实实现应优先使用官方 SDK，并针对双方版本做集成与安全测试。

## 项目文件

| 文件 | 作用 |
| --- | --- |
| [validate_mcp_messages.py](MCP/examples/validate_mcp_messages.py) | 状态机、capability gate、schema 子集与命令行入口 |
| [mcp-cases.json](MCP/examples/mcp-cases.json) | 33 个数据驱动正/负场景 |
| [test_validate_mcp_messages.py](MCP/examples/test_validate_mcp_messages.py) | 58 个自动化回归测试 |

项目只使用 Python 3 标准库。Fixture 不含网络地址（文档保留域 `example.com` 除外）、真实用户数据或凭据。

## 运行环境

本库已在 Windows 11、PowerShell 7、Python 3.11 下验证。先进入目录：

```powershell
Set-Location "X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\MCP"
```

运行 33 个数据场景：

```powershell
python -B .\examples\validate_mcp_messages.py
```

运行测试：

```powershell
python -B -W error .\examples\test_validate_mcp_messages.py
python -B -O -W error .\examples\test_validate_mcp_messages.py
```

`-B` 防止生成 `__pycache__`；`-W error` 把警告当失败；`-O` 再跑一次，证明验证器没有把安全检查错误地写成会被优化移除的 `assert`。

预期摘要包含：

```json
{
  "status": "ok",
  "profile": "offline-mcp-teaching-profile-v1",
  "protocol_version": "2025-11-25",
  "case_count": 33,
  "passed": 10,
  "expected_failures": 23
}
```

“expected_failures”表示负向样例被正确拒绝，不是测试失败。

## 先读 Fixture

`mcp-cases.json` 有五部分：

1. `protocol_version`：课程当前验证的规范日期。
2. `client`：clientInfo 与 roots/sampling/elicitation/tasks capabilities。
3. `server`：serverInfo 与 tools/resources/prompts/logging/tasks capabilities。
4. `tool`：一个离线天气工具，含 input/output schema 和可选 task support。
5. `cases`：每个场景的 setup、双向 steps、预期 pass/fail 与错误片段。

每个 step 明确写方向：

```json
{
  "direction": "server_to_client",
  "message": {
    "jsonrpc": "2.0",
    "id": 10,
    "method": "roots/list"
  }
}
```

方向不是装饰。`roots/list` 必须由 server 请求 client；把它改成 `client_to_server` 应被拒绝。

## 验证器怎样工作

### 1. 严格 JSON

Python 默认 `json.loads` 会接受重复 key（后值覆盖前值）和 NaN/Infinity。项目显式拒绝这些输入，避免签名、审计或不同解析器看到不同值。

### 2. JSON-RPC envelope

验证器区分：

- request：method + ID；
- notification：method，无 ID；
- response：ID + result/error 二选一。

请求按“发送方向 + ID 类型 + ID 值”关联。整数 `5` 和字符串 `"5"` 不同；双方可以各自同时使用 ID `5`；同一发送方不能在前一请求未响应时复用 ID。

### 3. 初始化状态机

状态依次是：

```text
new
→ waiting_for_initialize_response
→ waiting_for_initialized_notification
→ ready
```

普通请求不能越过握手。响应 ID、版本、info 与 capabilities 必须匹配课程 profile。

### 4. 双向 capability gate

验证器会拒绝：

- server 未声明 tools，client 仍发 `tools/list`；
- client 未声明 roots，server 仍发 `roots/list`；
- client 只有 sampling，却未声明 `sampling.tools`，server 发送 tool-enabled sampling；
- client 未声明 `elicitation.url`，server 发 URL mode；
- server 未声明 `tasks.requests.tools.call`，client 把 `tools/call` 任务化。

它同时检查 `tools.listChanged`、`roots.listChanged` 等布尔 sub-capability。

### 5. Tool 契约

输入检查必填、类型、枚举、minLength 和未知字段；输出在存在 `outputSchema` 时必须提供相符 `structuredContent`。`isError: true` 的执行错误可只给可操作 content；JSON-RPC error 则表示协议层失败。

### 6. Client features 与 Tasks

- root response 的 URI 必须是 `file://`。
- sampling 检查 messages、maxTokens、tools/context sub-capability。
- form elicitation 拒绝常见秘密字段；URL mode 在本教学 profile 中要求绝对 HTTPS URL。
- task augmentation 检查 capability 与 tool-level `taskSupport`，并区分 `CreateTaskResult` 与普通 tool result。

这些检查是教学子集；例如它没有实现完整的受限 elicitation schema、所有 content type、SSE framing、任务所有权存储或 OAuth。

## 逐步实验

每次只改一个 fixture 场景，先写下预测，再运行：

1. 把 valid roots 的方向改反。
2. 删除 client 的 `sampling.tools`，保留带 tools 的 sampling request。
3. 给 notification 加 `id`。
4. 同一方向发两个未响应且相同 ID 的 request。
5. 把 tool `unit` 改为 `kelvin`。
6. 删除成功 tool result 的 `structuredContent`。
7. 用 form elicitation 请求 `api_key`。
8. 删除 server 的 `tasks.requests.tools.call`，仍发送 task-augmented tool call。
9. 把 URL elicitation 改成 `http://`，观察课程 profile 的加严策略。

完成后还原 fixture，并重新跑 58 个测试。

## 扩展任务

### 基础扩展

- 为 tool 加整数参数与 minimum/maximum，并补正负 fixture。
- 为 tools/list response 增加 descriptor 列表验证。
- 为 accepted form response 按原 requestedSchema 验证 content。

### 进阶扩展

- 实现 JSON-RPC batch 是否允许的明确策略。
- 为 progress/cancellation 建立 request token 关联。
- 为 task status、`tasks/get`、`tasks/result` 和 related-task metadata 建状态机。
- 另建 transport 层测试：stdio 按行 framing；Streamable HTTP POST/GET、Content-Type 与 SSE 重连。
- 用官方 SDK 各写一个最小 client/server，与本 fixture 做集成测试；不要把教学验证器改名为官方 conformance。

每个扩展都应先增加失败测试，再实现最小规则。

## 排错指南

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| fixture root/key 报错 | JSON 结构或未知字段 | 检查严格 schema 与重复 key |
| “wrong direction” | 方法放在错误发送方 | 对照 server/client capability |
| “did not declare capability” | 顶层或 sub-capability 缺失 | 修 capability 或不要发送该请求 |
| response 无 matching request | ID/方向错或重复响应 | 查看 outstanding 请求 |
| structuredContent 失败 | output schema 不匹配 | 修 server 返回，不要只改文本 |
| 测试在 `-O` 才异常 | 逻辑误用了 `assert` | 用显式异常与测试断言分离 |

## 项目验收

- [ ] CLI 报告 33 个场景：10 个正向通过、23 个负向按预期拒绝。
- [ ] 58 个测试在普通模式全部通过。
- [ ] 58 个测试在 `-O` 模式全部通过。
- [ ] warnings-as-errors 下无警告。
- [ ] 能解释方向 + ID 为什么共同决定 request/response 关联。
- [ ] 能分别举出 server capability、client capability 和 sub-capability gate。
- [ ] 能说明 tool protocol error 与 execution error 的区别。
- [ ] 能说明 URL elicitation 与 Tasks 在当前版本中的动态/实验性边界。
- [ ] 未生成 cache、密钥、真实数据或网络副作用。

## 自测

1. 为什么负向场景被拒绝在摘要中算“通过”？
2. 为什么不能只用一个全局 set 记录 request ID？
3. 为什么 output schema 存在时还要检查 structuredContent？
4. 验证器为何拒绝 form 中的 `api_key`，却仍不能证明整个 elicitation 安全？
5. 这个项目缺少哪些证据，才不能称为协议一致性测试？

参考答案应至少提到：完整规范 schema、真实传输、官方 SDK、版本互操作、授权、并发/断线、性能和安全测试。

## 下一步

完成后回到 [[MCP/00-目录|MCP 目录]]，再选择官方参考层中的服务器/客户端教程，用真实 SDK 复现；然后进入 [[Agent 核心/00-目录|Agent 核心]]，把 MCP 当作受控集成边界，而不是规划器本身。

## 参考资料

以下均为第一方或协议原始来源，获取/复核日期：2026-07-14。

- [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP Schema Reference](https://modelcontextprotocol.io/specification/2025-11-25/schema)
- [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
