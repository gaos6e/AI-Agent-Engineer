---
title: Tools、Agent 循环与中间件
aliases:
  - LangChain Tools and Agents
tags:
  - langchain
  - tools
  - agent
source_checked: 2026-07-14
---

# Tools、Agent 循环与中间件

## 本节目标

看清 LangChain Agent 的最小循环，学会把工具 schema、执行权限、错误与副作用写成代码契约，并理解 `create_agent` 和 middleware 的当前边界。

## Agent 循环并不神秘

```text
用户消息 -> 模型
            | 无工具调用 -> 最终消息
            | 工具调用   -> 参数校验 -> 执行工具 -> ToolMessage -> 模型
                                      \_________________________/ 有限循环
```

模型只**提出**动作。真正的执行器必须再次校验工具名、参数、调用者身份和资源范围。工具返回观察后，模型可能继续调用或结束。最大轮数、总耗时、成本、重复调用和人工接管条件必须由运行时限制。

LangChain v1 以 `from langchain.agents import create_agent` 作为标准高层 Agent 入口，取代旧的 `langgraph.prebuilt.create_react_agent` 首选位置。高层 Agent 建立在 LangGraph 上，但标准工具循环不要求初学者先手写 StateGraph。

## 从一个只读工具开始

当前官方 Python 工具入口是 `from langchain.tools import tool`。装饰器默认使用函数名和 docstring 构造工具描述，类型提示参与参数 schema。示意代码：

```python
from langchain.tools import tool

@tool
def lookup_order(order_id: str) -> dict[str, str]:
    """按订单 ID 查询当前调用者有权查看的订单摘要。"""
    # 身份与资源授权必须由业务代码校验。
    return {"order_id": order_id, "status": "pending"}
```

工具描述要说明何时使用和边界，但它不是授权系统。模型生成的 `order_id`、路径、URL 或 SQL 都是不可信输入。

## 好工具的契约

| 维度 | 要回答的问题 |
| --- | --- |
| 名称 | 是否是单一动作，例如 `lookup_order` 而不是 `manage_order`？ |
| 输入 | 类型、长度、枚举、资源范围和必填字段是什么？ |
| 输出 | 模型看到什么，应用保留什么 artifact，来源如何追踪？ |
| 错误 | 输入错误、权限拒绝、瞬时故障和永久故障如何区分？ |
| 副作用 | 是否写数据、扣费、发消息？能否预览和审批？ |
| 幂等 | 重试相同请求会不会重复执行？幂等键存在哪里？ |
| 预算 | 超时、速率、调用次数和结果大小上限是什么？ |

只读和写入工具要分开。对发送邮件、删除文件、执行 SQL 等高风险动作，先返回预览，再通过外部审批令牌执行；审批应绑定动作、参数、状态版本和有效期。

## `create_agent` 负责什么

高层 Agent 负责标准模型—工具循环、消息状态以及与中间件结合的扩展点。典型形状包含 `model`、`tools`、可选 `system_prompt`、`middleware`、`response_format` 和检查点相关配置。模型标识、提供商包和某些参数会随版本变化，代码只能在项目锁定依赖后视为已验证。

它不会自动保证：

- 工具只访问当前用户有权访问的资源；
- 外部动作幂等；
- Prompt injection 无法影响动作；
- 每个工具都有合理超时和错误分类；
- 最终回答有事实来源。

## Middleware 在哪里使用

当前官方文档把 middleware 作为 `create_agent` 的主要扩展面，可用于动态 Prompt、上下文裁剪、工具选择、重试、fallback、速率限制、PII 处理、guardrail、人工审批和日志。middleware hook 运行在 `create_agent` 编译出的 LangGraph 内；整个 Agent 也可作为更大 StateGraph 的节点。

工程上把 middleware 当“可组合策略”，不要把所有业务逻辑塞进一个 hook。权限仍要在工具执行层落实，敏感日志在产生时脱敏，middleware 失败也要有明确终态。

## 失败与停止策略

- 参数不符合 schema：不执行工具，把可修复错误返回模型或直接失败。
- 权限拒绝：不可通过重试绕过，记录审计并转人工或拒绝。
- 网络瞬时错误：有限指数退避，受总时间预算约束。
- 永久业务错误：立即停止，不把“找不到订单”当网络故障。
- 重复相同调用：检查观察是否丢失；达到阈值时停止。
- 写操作结果未知：先查幂等回执，不能盲目重放。

## 动手实践

为“查询政策并创建工单”设计三个工具：`search_policy`、`preview_ticket`、`create_ticket`。逐项写出输入 schema、输出、错误、副作用、授权、幂等键和审批要求。然后画出最多 6 次模型调用、3 次工具调用、30 秒总预算的终止图。

## 自测

- [ ] 能复述模型、Agent 运行时、执行器和工具的责任边界。
- [ ] 能解释为什么 `@tool` 的 schema 不能代替对象级授权。
- [ ] 能为写工具设计预览、审批、幂等和未知结果恢复。
- [ ] 能说明 middleware 适合横切策略，但不是安全边界的唯一实现。

## 下一步

进入 [[LangChain/00-初学者路线/04-Retrieval与RAG组件|Retrieval 与 RAG 组件]]，学习如何让 Agent 使用可追踪知识。

## 资料基线

官方事实核对日期：2026-07-14。

- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [LangChain Middleware overview](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- [LangChain v1 变化](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [[Tool Calling（含 Function Calling）/00-目录|Tool Calling（含 Function Calling）]]
