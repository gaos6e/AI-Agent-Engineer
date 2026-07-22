---
title: 工具契约与 Schema 设计
tags:
  - ai-agent-engineer
  - tool-calling
  - json-schema
aliases:
  - Function Schema 设计
  - Tool Contract
source_checked: 2026-07-19
content_origin: original
content_status: dynamic
---

# 工具契约与 Schema 设计

## 本节目标

- 区分函数工具、自由文本工具、内置工具与执行位置；
- 用名称、描述、输入、输出、风险和版本定义完整合同；
- 让结构上的非法状态难以表达；
- 理解 JSON Schema 和供应商 strict 模式的边界。

## Tool 不是 Function 本身

工具定义是模型看到的“能力说明书”，handler 才是应用中真正执行代码。常见分类：

| 类型 | 输入形状 | 谁执行 | 适合 |
| --- | --- | --- | --- |
| Function tool | JSON Schema 参数 | 通常由你的应用 | 业务 API、数据库、受控动作 |
| Custom/free-form tool | 自由文本或受语法约束文本 | 由应用或平台 | 代码、查询语言等难以自然包装为 JSON 的输入 |
| Built-in/server tool | 供应商定义 | 供应商基础设施 | Web 搜索、代码沙箱等平台能力 |
| MCP tool | MCP server 声明 | 客户端、远程服务或平台连接器 | 跨客户端复用能力 |

具体供应商分类会变化。设计业务层时先问“代码在哪里执行、谁持有凭据、谁负责授权”，不能只看工具叫法。

## 完整合同的六部分

1. **名称**：动作 + 对象，例如 `get_order`、`create_refund_draft`；
2. **描述**：何时用、何时不用、是否副作用、结果代表什么；
3. **输入 schema**：类型、枚举、范围、格式、必填和额外字段策略；
4. **输出合同**：成功数据、稳定错误、来源、截断与不完整状态；
5. **执行策略**：风险、超时、重试、审批、幂等与数据分类；
6. **版本**：schema 和语义的稳定 revision。

只定义前三项，工具仍很难安全上线。

## 名称与描述

### 好名称表达具体动作

- `get_order`：读取；
- `list_open_orders`：返回集合；
- `create_refund_draft`：创建草稿，不等于提交退款；
- `submit_refund`：有真实副作用。

避免 `process`、`handle`、`do_action`。相近工具要在描述中写清互斥条件，例如“只查当前状态，不创建或修改订单”。

### 描述像给新同事的 docstring

至少写明：

- 输入 ID 从哪里来；
- 单位、币种、时区和日期格式；
- 最大列表大小、分页与空结果；
- 副作用、审批与幂等要求；
- 不适用场景；
- 输出字段是否新鲜、完整、可缓存。

OpenAI 当前官方建议可用“intern test”：只看工具合同的新同事能否正确使用？若仍会追问，就把答案写进合同或由代码消除该参数。

## 用 Schema 缩小错误空间

```jsonc
{ // 一个模型可见、但由 host/runtime 实际强制的函数工具合同
  "type": "function", // 表明该声明描述可调用函数，而非普通消息或资源
  "name": "create_refund_draft", // 稳定工具名；模型不能通过改文字创建新能力
  "description": "为当前已授权订单创建退款草稿；不提交真实退款。", // 说明效果边界：只创建草稿，不产生真实退款副作用
  "parameters": { // 参数 JSON Schema，供解析与 runtime 校验共同使用
    "type": "object", // 调用参数必须是命名对象，避免位置歧义
    "properties": { // 列出唯一允许出现的参数
      "order_ref": { // 当前已授权订单的引用字段
        "type": "string", // 订单引用以文本表示
        "minLength": 1, // 空引用没有可验证目标，必须在执行前拒绝
        "description": "应用展示给用户的订单引用" // 说明该值应从可信 UI/state 获得
      }, // 结束 order_ref 规则
      "reason": { // 退款草稿的受限原因字段
        "type": "string", // 原因以文本枚举值传递
        "enum": ["duplicate", "damaged", "other"] // 只允许预先审阅的三类原因
      } // 结束 reason 规则
    }, // 结束参数字段表
    "required": ["order_ref", "reason"], // 两项缺一不可，不能猜默认值
    "additionalProperties": false // 拒绝未声明字段，防止提示/参数注入扩大动作范围
  }, // 结束 parameters schema
  "strict": true // 请求 provider/adapter 按 schema 返回结构化调用，而不是宽松文本
}
```

> [!note] JSONC 教学表示
> `//` 后是逐行解释；提交给严格 JSON schema/API 前请删除这些注释。

这个结构能拒绝：

- 缺少 `order_ref`；
- `reason` 为任意提示注入文字；
- 模型额外生成 `is_admin: true`；
- 类型不符合。

它不能证明：

- 订单存在；
- 订单属于当前用户/tenant；
- 状态允许退款；
- 退款理由真实；
- 用户已审批；
- 重试不会重复创建。

这些属于业务和安全合同。

## 让非法状态难以表达

| 差设计 | 问题 | 更好设计 |
| --- | --- | --- |
| `set_light(on, off)` 两个布尔 | 可同时真或同时假 | `state: "on" \| "off"` |
| `amount: "ten dollars"` | 单位和类型不清 | `amount_minor: integer` + `currency enum` |
| `user_id` 让模型填写 | 可越权/猜测 | 从可信会话注入 |
| `execute(command: string)` | 任意命令空间 | 多个窄工具或受控枚举 |
| `send_email(to: string)` 无限制 | 数据外传 | 收件人策略、预览与审批 |

如果两个函数总是安全且必然连续执行，可把它们合为一个业务工具；不要强迫模型重复传递应用已经知道的参数。

## Strict 模式与 JSON Schema 方言

JSON Schema 2020-12 定义通用数据模型和词汇，但供应商通常只支持子集。截至 2026-07-19，OpenAI function calling 文档说明 strict 模式要求每个 object 的 `additionalProperties: false`，并把 `properties` 中字段都列为 required；可用包含 `null` 的类型表达可空。

OpenAI Responses 与 Chat Completions 的默认行为不同：Chat Completions 的函数默认非 strict；Responses 省略 `strict` 时会尝试规范化为 strict，无法兼容时回退到 best effort，并把解析后的 tool 标为 `strict: false`。所以应显式声明期望模式，并在 adapter/契约测试中检查最终行为；不能只凭省略字段就声称结构一定受约束。

这类规则属于动态适配层：

- 在 adapter/CI 中用目标 API 验证 schema；
- 记录 provider、API、model 与 schema revision；
- 不假设其他供应商的 `strict` 语义完全相同；
- 服务端仍进行独立校验；
- 不支持的 schema 关键字要在发布前失败，不在运行时猜测。

## 输出合同同样重要

输出不能只声明“返回 JSON”。至少应为每个工具定义 exact fields、类型、枚举/格式、大小、嵌套深度、来源版本，以及输出字段与输入参数的绑定关系。`get_order` 的 `data.status` 可以是业务字段，`create_refund_draft` 若未声明它就必须拒绝；不能用一个宽松的全局 schema 接受所有工具。

本库采用模型/审计双投影。模型可见部分只包含完成任务所需的数据与有限恢复状态：

```jsonc
{ // 一次“尚未执行、需要审批”的结构化工具结果
  "schema_version": "tool-model-result-v2", // 让 consumer 选择相匹配的解析合同
  "status": "failed", // 此处代表动作未获准继续，不是模型可以自行重试的成功
  "data": null, // 未执行就没有业务结果数据
  "error": { // 只暴露给调用方安全、可恢复的错误信息
    "code": "APPROVAL_REQUIRED", // 稳定机器代码，适合 UI/流程分支判断
    "category": "approval", // 将错误归到审批 gate，而非工具故障或参数错误
    "safe_message": "此操作需要绑定当前参数的审批。", // 人读提示不包含敏感参数或内部异常
    "recovery": "request_approval", // 建议的受控下一步，而非盲目重试
    "retry_after_ms": null // 审批不是按时间自动重试，需等待新的人工决定
  }, // 结束错误对象
  "execution": { // 记录副作用是否已开始及交付状态
    "outcome": "not_started", // 明确任何下游写入都还没有发生
    "delivery": "fresh", // 本次并非重放旧结果或已缓存副作用
    "complete": true, // 该拒绝结果已完整生成，不需要分页/续传
    "truncated": false // 输出没有被大小限制裁剪
  }, // 结束执行状态对象
  "provenance": { // 让 consumer 知道结果由谁、按何版本产生
    "source_label": "offline-dispatcher", // 产出来源标签，不把它当用户授权依据
    "producer_revision": "offline-dispatcher-v2", // dispatcher 合同/实现修订，用于追踪兼容性
    "resource_revision": null, // 尚未读取或修改业务资源，因此没有资源版本
    "observed_at": "2026-07-19T00:00:00Z", // 结果产生时间，便于日志与过期判断
    "trust": "trusted_control" // 控制面字段可信，但任何业务 data 仍需单独分类
  } // 结束来源对象
}
```

主体引用、provider response/call、operation、工具合同版本、下游 receipt 与完整 SHA-256 绑定放入独立 `protected_audit`，不送给模型。程序逻辑依赖固定 code/outcome/recovery，不解析自由文本。详见[[Tool Calling（含 Function Calling）/05-结果、错误与不可信数据|结果、错误与不可信数据]]。

## 工具数量与版本

工具定义会占上下文并影响选错率。先暴露当前任务最相关的少量工具；能力很多时使用领域 namespace、路由或供应商支持的 tool search，但这些只是发现优化，不是授权。

Schema 变更规则：

- 新增可选语义也要评估 provider strict 兼容；
- 改单位、含义或副作用时升级 major revision；
- Adapter 可同时支持过渡版本，handler 内部仍使用统一域模型；
- 评测集固定 schema revision，避免“同名工具语义漂移”。

## 实践

分别设计：

1. `get_inventory(product_ref)`：只读；
2. `reserve_inventory(product_ref, quantity)`：可逆写入。

为每个工具写：

- 名称、何时用/不用；
- 输入 schema；
- 哪些参数由模型给，哪些由会话注入；
- 成功与 5 个错误 code；
- 超时、幂等、审批和结果新鲜度；
- schema revision 的升级条件。

再让一位不了解业务的人仅看合同复述执行语义，记录仍有歧义的地方。

## 常见错误

- 用描述弥补本可由 enum/类型消除的错误；
- 把 `strict=true` 当成业务正确；
- 输出只返回自然语言；
- 工具名不区分读取、草稿和提交；
- 把 tenant/user/role 交给模型；
- 一次暴露大量同义工具，却没有路由评测。

## 自测

1. Tool definition 与 handler 有何区别？
2. `additionalProperties: false` 阻止什么，不阻止什么？
3. 为什么创建“草稿”和“提交”最好是不同工具？
4. 已知的 order ID 为什么应由应用注入？
5. Provider strict 模式为何仍不能替代服务端校验？

下一步：[[Tool Calling（含 Function Calling）/02-调用建议、校验与授权|调用建议、校验与授权]]。

## 参考资料

- [OpenAI API：Function calling—Defining functions](https://developers.openai.com/api/docs/guides/function-calling#defining-functions)
- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
- [JSON Schema：The basics](https://json-schema.org/understanding-json-schema/basics)

来源获取日期：2026-07-19。供应商支持的 schema 子集与 strict 默认值会变化。
