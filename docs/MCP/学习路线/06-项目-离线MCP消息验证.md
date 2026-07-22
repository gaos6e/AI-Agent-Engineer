---
title: 项目：离线 MCP 消息验证
aliases:
  - MCP offline validation project
  - MCP 教学协议验证器
tags:
  - MCP
  - 项目
source_checked: 2026-07-21
execution_verified: 2026-07-21
---

# 项目：离线 MCP 消息验证

## 项目目标

不用网络、真实 server、SDK 或 API key，完成一个可重复的 MCP 教学验证项目。它把本路线中的关键规则变成数据驱动检查：

- 严格 JSON 与 JSON-RPC envelope；
- initialize 状态机和双向 request ID；
- client/server capability 方向与 sub-capability；
- tool 输入、结构化输出和两类错误；
- Resources 的五个稳定方法、分页、内容与订阅状态；
- HTTP token audience/resource、tenant、scope 与授权修订绑定；
- roots、sampling、elicitation 与实验性 Tasks 的关键边界；
- 正向、负向与回归测试。

> [!warning] 能力边界
> 这是课程定义的 `offline-mcp-teaching-profile-v2`，不是 MCP 官方 conformance suite。它只实现 `2025-11-25` 稳定规范中课程使用的方法与 schema 子集，并在未知字段、URI、Base64 和 64 KiB 内容预算等位置故意加严。它不实现 Draft 候选协议。真实实现应优先使用官方 SDK，并针对双方版本做传输、互操作与安全测试。

> [!important] Wire 与控制面分离
> Fixture 的 `transport_context_defaults`、step 级 `transport_context`、`authorization_revision` 与 `control_event` 都是**课程控制面元数据**，不是 MCP JSON-RPC 字段。它们模拟 HTTP 层在验签、token introspection 与访问策略之后得到的可信身份快照；不得复制进真实 MCP message。

> [!tip] 下一层可执行证据
> 完成本项目后运行 [[MCP/学习路线/08-项目-Loopback-Streamable-HTTP与OAuth资源边界|Loopback Streamable HTTP 与 OAuth 资源边界项目]]。它不修改或复用本验证器的 `transport_context` fixture，而是在独立 endpoint 上真实验证 HTTP header/status、JSON/SSE、session、PRM 文档/challenge 形状和离线 token policy。其 HTTP resource 不宣称 RFC 9728 合规；两个项目分别覆盖 message contract 与 transport/resource boundary。

## 项目文件

| 文件 | 作用 |
| --- | --- |
| [validate_mcp_messages.py](MCP/examples/validate_mcp_messages.py) | 状态机、capability gate、schema 子集与命令行入口 |
| [mcp-cases.json](MCP/examples/mcp-cases.json) | 54 个数据驱动正/负场景 |
| [test_validate_mcp_messages.py](MCP/examples/test_validate_mcp_messages.py) | 108 个自动化回归测试 |

项目只使用 Python 3 标准库。Fixture 不含网络地址（文档保留域 `example.com` 除外）、真实用户数据或凭据。

## 运行环境

本库已在 Windows 11、PowerShell 7、Python 3.11 下验证。从仓库根目录进入 MCP：

```powershell
Set-Location ".\docs\MCP" # 进入项目目录，使示例和 fixture 的相对路径保持正确
```

运行 54 个数据场景：

```powershell
python -B .\examples\validate_mcp_messages.py # 运行严格 JSON fixture 验证；-B 避免生成本机缓存文件
```

运行测试：

```powershell
python -B .\examples\test_validate_mcp_messages.py # 普通模式运行单元与数据驱动回归测试
python -B -O .\examples\test_validate_mcp_messages.py # 检查安全逻辑没有错误依赖可移除的 bare assert
python -B -W error .\examples\test_validate_mcp_messages.py # 将任何 Python 警告转为失败
python -B -O -W error .\examples\test_validate_mcp_messages.py # 同时覆盖优化与严格警告两个运行条件
```

`-B` 防止生成 `__pycache__`；`-W error` 把警告当失败；`-O` 再跑一次，证明验证器没有把安全检查错误地写成会被优化移除的 `assert`。

预期摘要包含：

```json
{
  "status": "ok",
  "profile": "offline-mcp-teaching-profile-v2",
  "protocol_version": "2025-11-25",
  "case_count": 54,
  "passed": 16,
  "expected_failures": 38
}
```

“expected_failures”表示负向样例被正确拒绝，不是测试失败。

## 先读 Fixture

`mcp-cases.json` 有八部分：

1. `schema_version`：fixture 自身结构版本，不是 MCP 版本。
2. `protocol_version`：课程当前验证的稳定规范日期。
3. `transport_context_defaults`：HTTP 传输类型、active token、token audience 与 RFC 8707 `resource` 的无秘密默认值。
4. `authorization`：protected resource、授权修订、principal/tenant/scope、资源图和模板策略。
5. `client`：clientInfo 与 roots/sampling/elicitation/tasks capabilities。
6. `server`：serverInfo 与 tools/resources/prompts/logging/tasks capabilities。
7. `tool`：一个离线天气工具，含 input/output schema 和可选 task support。
8. `cases`：每个场景的 setup、双向 steps、控制事件、预期 pass/fail 与错误片段。

每个 step 明确写方向：

```jsonc
{ // 测试 fixture 用外层方向信息消除双向 JSON-RPC 的歧义
  "direction": "server_to_client", // 表示该 request 从 server 发往 client，决定 capability 与方法检查方向
  "message": { // 内层才是严格 JSON-RPC message 对象
    "jsonrpc": "2.0", // 固定协议版本字段
    "id": 10, // request ID；client 之后应以同 ID 返回 response 或 error
    "method": "roots/list" // server 请求 client 列出当前可访问的 roots
  } // 结束内层 JSON-RPC request
}
```

> [!note] JSONC 教学表示
> 外层 fixture 与内层 JSON-RPC message 的职责不同；若将它作为严格 JSON 测试数据，请先移除 `//` 注释。

方向不是装饰。`roots/list` 必须由 server 请求 client；把它改成 `client_to_server` 应被拒绝。

## 验证器怎样工作

### 1. 严格 JSON

Python 默认 `json.loads` 会接受重复 key（后值覆盖前值）和 NaN/Infinity。项目显式拒绝这些输入，并在递归解码前限制 fixture 为 2 MB、JSON 容器深度为 64 层；文件读取只取“上限 + 1 byte”，I/O 错误不回显本地路径。这样既避免签名、审计或不同解析器看到不同值，也避免“先完整读入再检查大小”的伪预算。

### 2. JSON-RPC envelope

验证器区分：

- request：method + ID；
- notification：method，无 ID；
- response：ID + result/error 二选一。

请求按“发送方向 + ID 类型 + ID 值”关联。整数 `5` 和字符串 `"5"` 不同；双方可以各自同时使用 ID `5`；同一发送方不能在前一请求未响应时复用 ID。

消息不能同时携带 `method` 与 `result/error`。成功 response 先按 pending method 校验结果，再原子消费 pending request；畸形 `InitializeResult`、`tools/list` 或其他成功结果不会先把关联状态弹出，从而避免一条无效 response 使后续合法 response 永久失配。合法 JSON-RPC error response 则会结束对应 request，但不会伪造订阅等业务成功状态。

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

它同时检查 `tools.listChanged`、`resources.listChanged`、`resources.subscribe`、`roots.listChanged` 等布尔 sub-capability。

### 5. Resources 契约与订阅状态

稳定 profile 明确只接受五个 client → server 方法：

- `resources/list` 与 `resources/templates/list`：可带 opaque string cursor；结果 cursor、descriptor、URI template、MIME、annotation 与 size 均受检查。
- `resources/read`：请求 URI 必须在当前 tenant 的显式资源策略中；结果只能包含被请求 URI 或策略图明确列出的 child URI。
- `resources/subscribe` 与 `resources/unsubscribe`：只有 server 声明 `resources.subscribe: true` 才可使用。

状态迁移发生在成功 response 之后，而不是 request 发出时：subscribe 失败不会产生订阅，unsubscribe 失败会保留旧订阅。`notifications/resources/updated` 必须对应同一 principal/tenant 的 active subscription；child 关系来自显式策略图，不能把字符串前缀相同误当父子关系。`notifications/resources/list_changed` 只依赖 `resources.listChanged`，不依赖单项订阅。

URI、URI template、MIME、descriptor、canonical padded Base64 和 UTF-8 字节数都有本地检查。单项及整个 `resources/read.contents` 共享 64 KiB 教学预算，并最多接收 64 个 content items；每个列表页最多 256 项，避免用大量空对象或多个小块绕过总量门禁。Resource 内容仍是不可信数据；结构合法不代表可直接提升成系统指令。

### 6. Wire 外授权快照与撤销

对每个教学 Resources 操作，验证器在处理 MCP message 前检查完整的 `transport_context`：

1. transport 是本项目建模的 `streamable_http`；
2. access token 仍 active；
3. token audience 与授权/换 token时使用的 RFC 8707 `resource` 都精确绑定当前 MCP protected resource；
4. subject 存在且未撤销，tenant 与 principal 绑定一致；
5. 本次 claims 不超过策略授予的 scopes，且含当前方法需要的 scope；
6. `authorization_revision` 必须是当前生效修订。

修订切换会先清空 active subscriptions；旧 revision 的请求、通知投递上下文与 pending 成功结果都 fail closed。Fixture 不保存或验证真实 bearer token，也不模拟签名、issuer、expiry、introspection、401/403 和 `WWW-Authenticate`；这些属于真实 HTTP/OAuth 集成测试。stdio 不使用这套 HTTP 授权流程，应从受控环境取得凭据。

### 7. Tool 契约

输入检查必填、类型、枚举、minLength 和未知字段；schema 只接受课程实际执行的显式关键词，并限制递归深度、properties、enum、数组与字符串预算，避免“声明了却不执行”的静默 schema。输出在存在 `outputSchema` 时必须提供相符 `structuredContent`。`tools/list` 成功结果还会验证分页 cursor、descriptor、唯一 tool name 和最多 256 项。`isError: true` 的执行错误可只给可操作 content；JSON-RPC error 则表示协议层失败。

### 8. Client features 与 Tasks

- root response 的 URI 必须是 `file://`；Roots 只表达协调范围，绝不替代 resource ACL、token scope 或文件系统沙箱。
- sampling 检查 messages、maxTokens、tool descriptor、tools/context sub-capability；本 profile 的成功结果只验收有界 text content，不冒充完整 multimodal/tool-use schema。
- form elicitation 拒绝常见秘密字段；URL mode 在本教学 profile 中要求绝对 HTTPS URL。
- task augmentation 检查 capability 与 tool-level `taskSupport`，并区分 `CreateTaskResult` 与普通 tool result；`tasks/list` 的每个 Task snapshot 至少检查 ID、状态、时间戳、必填 TTL 及可选 poll interval 的基本类型与范围。

这些检查是教学子集；例如它没有实现完整的受限 elicitation schema、所有 content type、SSE framing、任务所有权存储、真实 OAuth 或官方 conformance corpus。`tasks/list` 只校验有界的结构快照，不证明当前 requestor 有权看到任务、不会校验状态迁移，也不会保存 task state。`prompts/*`、`logging/setLevel`、`completion/complete` 与 `tasks/get/result/cancel` 的成功 schema 尚未实现，因此验证器会在创建 pending 状态前显式拒绝这些请求，而不是接受一个自己不会校验的成功结果。

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
10. 把 `token_audience` 或 RFC 8707 `resource` 改到另一个 server。
11. 先成功 subscribe，再切到 `authz-v2`，观察订阅失效和旧 revision 读取被拒绝。
12. 把 child URI 改成只有字符串前缀相似的 `handbookish`。

完成后还原 fixture，并重新跑 108 个测试。

## 扩展任务

### 基础扩展

- 为 tool 加整数参数与 minimum/maximum，并补正负 fixture。
- 为 tools/list 增加多页状态、跨页唯一性与动态 `listChanged` 缓存失效验证。
- 为 accepted form response 按原 requestedSchema 验证 content。

### 进阶扩展

- 实现 JSON-RPC batch 是否允许的明确策略。
- 为 progress/cancellation 建立 request token 关联。
- 为 task status、`tasks/get`、`tasks/result` 和 related-task metadata 建状态机。
- 扩展现有 [[MCP/学习路线/08-项目-Loopback-Streamable-HTTP与OAuth资源边界|独立 transport 项目]]：补官方 SDK adapter、长连接 backpressure、代理故障与持久 SSE resume；不要把这些逻辑塞进消息 fixture。
- 用官方 SDK 各写一个最小 client/server，与本 fixture 做集成测试；不要把教学验证器改名为官方 conformance。

每个扩展都应先增加失败测试，再实现最小规则。

## 排错指南

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| fixture root/key 报错 | JSON 结构或未知字段 | 检查严格 schema 与重复 key |
| “wrong direction” | 方法放在错误发送方 | 对照 server/client capability |
| “did not declare capability” | 顶层或 sub-capability 缺失 | 修 capability 或不要发送该请求 |
| token audience/resource 报错 | token 或 RFC 8707 resource 发给了别的 server | 停止请求并重新走正确的授权流程 |
| stale authorization revision | 策略已撤销或刷新，旧身份快照仍被复用 | 丢弃旧请求/订阅并用新身份重新授权 |
| resource update 无 active subscription | subscribe 失败、已 unsubscribe、已撤销或 URI 不在显式 child 图 | 重新订阅并核对资源图；不要用字符串前缀猜关系 |
| response 无 matching request | ID/方向错或重复响应 | 查看 outstanding 请求 |
| structuredContent 失败 | output schema 不匹配 | 修 server 返回，不要只改文本 |
| 测试在 `-O` 才异常 | 逻辑误用了 `assert` | 用显式异常与测试断言分离 |

## 项目验收

- [ ] CLI 报告 54 个场景：16 个正向通过、38 个负向按预期拒绝。
- [ ] 108 个测试在普通模式全部通过。
- [ ] 108 个测试在 `-O` 模式全部通过。
- [ ] 108 个测试在 `-W error` 模式下无警告。
- [ ] 108 个测试在组合的 `-O -W error` 模式全部通过。
- [ ] 能解释方向 + ID 为什么共同决定 request/response 关联。
- [ ] 能分别举出 server capability、client capability 和 sub-capability gate。
- [ ] 能说明 tool protocol error 与 execution error 的区别。
- [ ] 能说明 URL elicitation 与 Tasks 在当前版本中的动态/实验性边界。
- [ ] 能解释 capability、Roots、token scope、tenant ACL 与订阅状态为什么不能互相替代。
- [ ] 能指出 `transport_context`、授权修订与控制事件不是 MCP wire 字段。
- [ ] 未生成 cache、密钥、真实数据或网络副作用。

## 自测

1. 为什么负向场景被拒绝在摘要中算“通过”？
2. 为什么不能只用一个全局 set 记录 request ID？
3. 为什么 output schema 存在时还要检查 structuredContent？
4. 验证器为何拒绝 form 中的 `api_key`，却仍不能证明整个 elicitation 安全？
5. 这个项目缺少哪些证据，才不能称为协议一致性测试？
6. 为什么 subscribe request 已发出仍不能立即接受 updated notification？
7. 为什么 URI 前缀不能证明 sub-resource 关系？
8. 为什么 token 有正确 scope 仍要检查 audience、resource、tenant 和撤销修订？

参考答案应至少提到：完整规范 schema、真实传输、官方 SDK、版本互操作、授权、并发/断线、性能和安全测试。

## 下一步

完成后先进入 [[MCP/学习路线/08-项目-Loopback-Streamable-HTTP与OAuth资源边界|Loopback Streamable HTTP 与 OAuth 资源边界项目]]，补足真实 header/status/session 证据；再回到 [[MCP/00-目录|MCP 目录]]，选择官方参考层中的服务器/客户端教程，用真实 SDK 复现。之后进入 [[Agent 核心/00-目录|Agent 核心]]，把 MCP 当作受控集成边界，而不是规划器本身。

## 参考资料

以下均为第一方或协议原始来源，获取/复核日期：2026-07-21。

- [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP Schema Reference](https://modelcontextprotocol.io/specification/2025-11-25/schema)
- [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Server Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
