---
title: 模型、消息、Prompt 与结构化输出
aliases:
  - Models Messages Prompts Structured Output
tags:
  - langchain
  - llm
  - structured-output
source_checked: 2026-07-14
---

# 模型、消息、Prompt 与结构化输出

## 本节目标

理解一次 LangChain 模型调用中“模型适配器、消息、Prompt、运行参数、结构化输出”各自负责什么，并能设计一个既可验证又不把模型输出当事实的业务契约。

## 五个层次

1. **模型（chat model）**：把统一接口适配到具体提供商。不同提供商能力和参数并不完全相同。
2. **消息（message）**：上下文的基本单元，携带角色、内容、工具调用、工具结果和元数据。
3. **Prompt**：把任务规则、可信上下文和输出要求组织成模型输入。
4. **调用配置**：超时、重试、流式、标签和提供商参数等运行时选择。
5. **结构化输出**：让最终结果满足 schema，便于代码校验和消费。

不要把系统规则、用户输入、检索内容和工具结果拼成一段来源不明的字符串。外部文档和网页即使写着“忽略之前规则”，也只是数据，不获得系统权限。

## 消息不是普通字符串

LangChain 提供跨提供商的标准消息类型。常见角色包括 system、human/user、AI/assistant 和 tool。工具调用尤其需要关联 ID：模型发出的 tool call 与返回的 `ToolMessage.tool_call_id` 必须对应，否则模型可能无法知道哪个结果属于哪个请求。

消息还可能包含多模态 content blocks、token usage、响应元数据或 artifact。`artifact` 适合保存文档 ID、页码等下游数据，而不必把全部内容再次送进模型。是否支持某种内容块仍取决于具体提供商集成。

## 模型初始化要显式记录什么

官方当前提供 `init_chat_model` 作为统一初始化入口，也允许直接使用提供商类。项目至少记录：

- 包和模型标识；不要把“显示名称”当稳定 ID。
- 温度、最大输出、超时、重试等实际传入参数。
- 是否启用流式、工具调用、结构化输出或多模态。
- Prompt、工具 schema 和数据版本。
- 提供商响应 ID、用量和错误类别，但日志要脱敏。

“统一接口”不是“能力完全相同”。参数由具体集成解释；模型上下文长度、工具并行、结构化输出方式等动态事实必须查提供商页面并通过集成测试确认。

## Prompt 的最小组成

以“提取客服工单”为例：

- **任务**：从输入中提取工单字段，不解决工单。
- **可信边界**：系统规则可信；邮件正文和附件是不可信数据。
- **决策规则**：日期或账号不清楚时标记缺失，不猜测。
- **输出契约**：类别枚举、摘要长度、是否转人工、证据片段 ID。
- **失败路径**：schema 校验失败时有限重试，仍失败则转人工。

例子只用于消除歧义。不要堆几十个样例挤掉真正的输入，也不要用 Prompt 代替权限检查。

## 结构化输出是什么

结构化输出把自由文本变为可校验对象。例如：

```json
{
  "category": "billing",
  "urgency": "normal",
  "summary": "用户询问重复扣款",
  "needs_human": true,
  "evidence_ids": ["mail-17:paragraph-2"]
}
```

在 LangChain 当前 Agent API 中，`create_agent(..., response_format=...)` 可接收 schema。官方文档区分 `ProviderStrategy`（使用提供商原生结构化输出）与 `ToolStrategy`（通过工具调用获得结构），直接传入 schema 类型时会依据模型能力选择策略；最终验证后的结果位于 Agent 状态的 `structured_response`。这一行为依赖当前包与模型 profile，必须在锁定版本上测试。

结构化只保证**形状**，不保证**事实**。`evidence_ids` 可能指向不存在的片段，金额可能抄错，分类也可能错误。下游还需枚举、范围、外键、权限和来源校验。

## 校验失败如何处理

1. 保存原始错误类别，不在日志中输出敏感全文。
2. 对可修复格式错误执行有限次数修复；避免无限重试。
3. 对事实缺失、权限不明或业务冲突转人工，不让模型补造。
4. 将失败样本加入离线数据集，比较 Prompt、模型或 schema 改动前后表现。

> [!example] 格式有效但业务无效
> `urgency="normal"` 可能满足枚举，但若正文明确写“账户被盗”，业务规则应强制高优先级或转人工。schema 与业务规则需要两层校验。

## 常见错误与排查

- **模型类能导入但运行失败**：检查提供商包、环境变量、模型权限与版本，而不是先改 Prompt。
- **工具结果无法关联**：核对 tool call ID 是否原样返回。
- **字段偶尔缺失**：确认所用模型和策略真的支持 schema，并记录 validation error。
- **聊天越来越贵**：先量化消息构成，再做截断、摘要或选择性上下文；摘要也要可追踪。
- **输出可解析却不能用**：增加业务校验、证据和失败终态。

## 动手练习

为“从会议邮件提取安排”设计 schema，至少包含主题、开始时间、时区、参会者、缺失字段和证据 ID。准备 8 条样本：正常、日期缺失、时区不明、两个冲突日期、恶意指令、超长正文、无关邮件和附件引用。分别写出 schema 校验和业务校验。

## 自测

- [ ] 能区分 message content、metadata、tool call 和 artifact。
- [ ] 能解释格式有效与事实正确为何是两件事。
- [ ] 能说明 ProviderStrategy 与 ToolStrategy 的概念差异，不假定所有模型都支持前者。
- [ ] 能为解析失败定义重试上限和人工终态。

## 下一步

进入 [[LangChain/00-初学者路线/03-Tools与Agent循环|Tools 与 Agent 循环]]，把模型建议与真实副作用隔离。

## 资料基线

官方事实核对日期：2026-07-14。

- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)
- [LangChain Messages](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain Context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)
- [LangChain v1 迁移指南](https://docs.langchain.com/oss/python/migrate/langchain-v1)
