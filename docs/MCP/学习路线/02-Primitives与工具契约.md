---
title: MCP Primitives 与工具契约
aliases:
  - MCP tools resources prompts
  - MCP roots sampling elicitation
tags:
  - MCP
  - Tool-Calling
source_checked: 2026-07-14
---

# MCP Primitives 与工具契约

## 本节目标

学完后，你应能：

- 为需求选择 tool、resource、prompt、root、sampling 或 elicitation。
- 写出能确定性验证的 tool 输入/输出契约。
- 区分协议错误与工具执行错误。
- 解释分页、变更通知、用户同意和实验性 Tasks 为什么属于契约的一部分。

## 先按能力拥有者分类

“Primitive”经常被笼统翻译为“原语”。对初学者更有用的问法是：**这项能力由哪一方提供、谁控制、解决什么问题？**

### server features

| 能力 | 适合什么 | 示例 | 主要控制主体 |
| --- | --- | --- | --- |
| tools | 一次计算或动作，可能产生副作用 | 查询订单、创建 issue、运行分析 | 模型可建议，host 制定确认策略，server 执行并校验 |
| resources | 可寻址、可读取的上下文 | 文件、数据库 schema、日志、知识条目 | 应用选择读取和注入方式 |
| prompts | server 提供的可复用提示模板 | 周报模板、代码审查流程 | 通常由用户或应用显式选择 |

### client features

| 能力 | 适合什么 | 示例 | 主要控制主体 |
| --- | --- | --- | --- |
| roots | 告诉 server 当前允许关注的文件根 | `file:///D:/project` | host/用户决定范围 |
| sampling | server 请求 host 的模型生成 | 让 host 选择模型总结结果 | host 保留模型、权限和审查 |
| elicitation | server 经 client 向用户要额外信息 | 选择输出语言、打开外部授权页 | 用户可接受、拒绝或取消 |

这两组能力不能互换。比如 resource 让 client 读取 server 的内容；root 则让 server 查询 client 愿意暴露的文件边界。

## 如何选择 server feature

### Tool：动作或计算

当需求有明确参数、执行边界和返回结果时用 tool。一个教学级描述至少包含：

- `name`：会话内唯一、稳定，当前规范建议 1–128 个 ASCII 字母、数字、`_`、`-`、`.`；
- `description`：做什么、什么时候用、关键副作用；
- `inputSchema`：JSON Schema 对象；
- 可选 `outputSchema`：结构化输出的 JSON Schema；
- 可选 `annotations` 与 `execution.taskSupport`。

```json
{
  "name": "lookup_weather",
  "description": "读取离线样例天气；不访问网络。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "city": {"type": "string", "minLength": 1},
      "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["city"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "temperature": {"type": "number"},
      "conditions": {"type": "string"},
      "unit": {"type": "string"}
    },
    "required": ["temperature", "conditions", "unit"],
    "additionalProperties": false
  }
}
```

若定义了 `outputSchema`，server 必须让 `structuredContent` 符合它，client 应验证。为兼容旧客户端，规范建议同时在文本 content 中提供序列化结果。Schema 解决“结构是否可处理”，description 解决“模型是否选对工具”，两者都不等于权限控制。

工具错误有两层：

| 错误 | 适用情形 | 表达方式 | 模型是否通常能自修复 |
| --- | --- | --- | --- |
| JSON-RPC 协议错误 | 方法未知、请求结构不合法、server 内部错误 | response 的 `error` | 较难 |
| tool execution error | 参数值越界、下游 API 失败、业务规则拒绝 | tool result 中 `isError: true` 与可操作 content | 较可能 |

### Resource：可寻址的上下文

当内容需要浏览、读取、分页、缓存、订阅或复用时，resource 比“一个返回大段文本的 tool”更清晰。注意：

- URI 是身份边界，不要靠显示名称唯一标识。
- 列表可能分页，不能假设一次得到全部资源。
- `listChanged` 与单项 `subscribe` 是不同 sub-capability。
- resource 内容是不可信输入，可能含提示注入；保留来源并限制进入模型的内容。

### Prompt：可复用交互模板

Prompt 适合“用户选择一种工作方式”，例如“按团队模板做代码审查”。它不是绕过 host 系统指令的后门，也不是存放密钥的地方。模板参数仍需验证，server 返回的 prompt messages 仍受 host 策略控制。

## 如何选择 client feature

### Root：工作范围提示，不是沙箱

当前规范中的 root URI 必须是 `file://`。client 可声明 `roots.listChanged`，server 再发 `roots/list`。实现时仍需：

- 规范化路径后再判断是否在允许根下；
- 处理 `..`、大小写、junction 与 symlink；
- 不把“出现在 root 中”解释为“任意读写均获授权”；
- root 改变后刷新缓存和权限判断。

### Sampling：借用 host 的模型能力

server 发送 `sampling/createMessage`，host 保留模型选择、访问控制和用户审查。当前规范还允许 sampling 请求携带 tools，但 client 必须显式声明 `sampling.tools`。`includeContext` 的 `thisServer`/`allServers` 已软弃用；除非 client 声明 `sampling.context`，server 不应依赖它们。

Sampling 的关键边界是：server 提出生成请求，不拥有 host 的模型、上下文和最终批准权。

### Elicitation：向用户补充信息

`elicitation/create` 有两种模式：

- **form**：在 MCP 内收集扁平、受限 JSON Schema 的普通结构化信息。不得索要密码、API key、access token、支付凭据等秘密。
- **url**：让用户在外部 HTTPS 页面完成敏感输入或第三方授权。秘密不应穿过 client/LLM；它也不能替代 client → MCP server 自身的 MCP Authorization。

Client 要清楚展示是哪个 server 在请求，允许用户 accept、decline 或 cancel。URL 模式是 `2025-11-25` 新能力，接入前应核对实际 SDK 支持。

## Tasks：给请求套上持久执行壳

Tasks 在 `2025-11-25` 引入，当前仍标记为实验性。它不是新的业务 primitive，而是给已有请求增加“立即返回任务、随后轮询状态/获取结果”的执行方式：

1. 请求参数带 `task`，例如 TTL。
2. receiver 立即返回 `CreateTaskResult`，而非最终工具结果。
3. requestor 用 `tasks/get` 轮询状态，并用 `tasks/result` 取得最终原请求结果。

双方必须声明精确 task capability；tool 还要通过 `execution.taskSupport` 声明 `forbidden`、`optional` 或 `required`。只看到顶层 `tasks` 不足以证明某个 `tools/call` 可任务化。

## 一个选择决策树

面对需求时依次问：

1. 是读取可复用上下文，还是执行一次动作？前者优先 resource，后者优先 tool。
2. 是 server 给 host 能力，还是 server 需要 host/用户提供能力？后者考虑 root、sampling、elicitation。
3. 是否需要固定提示模板供用户选择？考虑 prompt。
4. 是否长时间运行且需要持久状态？在双方明确支持时考虑 Tasks，而不是把长任务误包装成普通同步调用。
5. 无论选择什么：谁同意、谁校验、谁最小授权、谁记录审计？

## 贯穿练习

需求：“用户选择一个代码项目，读取 README，生成审查摘要，询问输出语言，并在确认后创建 issue。”

- 项目范围：root。
- README：resource。
- 摘要生成：host 自己调用模型，或 server 在明确支持时请求 sampling。
- 输出语言：form elicitation。
- 创建 issue：tool。
- 团队审查格式：prompt。
- 若创建报告耗时很长：在 capability 与工具级支持都满足时用 task augmentation。

为每一项再写出输入 schema、输出 schema、同意点和失败方式，才算完成设计。

## 常见错误

- 一个 tool 同时查询、修改、发消息，导致权限与重试无法推理。
- `inputSchema` 只有 `type: object`，没有必填、枚举和未知字段策略。
- 定义了 `outputSchema`，却只返回自由文本。
- 把 annotation 中的“只读”当成事实；规范要求不可信 server 的 annotations 必须视为不可信。
- 用 form elicitation 索要秘密。
- server 未检查 client capability 就发 roots/sampling/elicitation 请求。
- 把 Tasks 当成稳定、普遍可用的队列系统。

## 自测与掌握标准

1. “数据库 schema”“删除记录”“周报模板”“用户选择的项目目录”分别属于哪项能力？
2. 为什么 resource 内容和 tool annotation 都必须按不可信输入处理？
3. `outputSchema` 与 `structuredContent` 各自承担什么责任？
4. 为什么 `sampling.tools` 需要独立 sub-capability？
5. form elicitation 与 URL elicitation 的秘密边界是什么？
6. Tasks 为什么需要会话 capability 和 tool-level support 两层判断？

能独立完成上面的贯穿练习，并对每项选择说明“方向、控制主体、契约、失败方式”，才算掌握。

## 下一步

进入 [[MCP/学习路线/03-生命周期能力协商与传输|生命周期、能力协商与传输]]，把这些能力放进真实会话顺序。

## 参考资料

以下均为 MCP 第一方资料，获取/复核日期：2026-07-14。

- [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Server Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [Server Prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts)
- [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
