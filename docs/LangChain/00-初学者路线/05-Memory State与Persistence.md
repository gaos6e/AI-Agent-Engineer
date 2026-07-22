---
title: Memory、State 与 Persistence
aliases:
  - LangChain Memory and State
tags:
  - langchain
  - langgraph
  - memory
  - persistence
source_checked: 2026-07-19
content_origin: original
content_status: dynamic
---

# Memory、State 与 Persistence

## 本节目标

区分消息历史、运行状态、检查点、线程和长期记忆；理解 LangGraph persistence 如何支持恢复与人工在环，并能为数据隔离、过期、删除和副作用重放设计规则。

## 先区分五件事

| 概念 | 含义 | 典型生命周期 |
| --- | --- | --- |
| 消息历史 | 用户、模型与工具消息 | 一个会话或线程 |
| 运行状态 state | 下一节点继续执行所需的结构化字段 | 一次图运行及其恢复 |
| 检查点 checkpoint | 特定 super-step 的状态快照 | 按保留策略持久化 |
| 线程 thread | 组织一系列检查点的标识 | 一段持续交互 |
| 长期记忆 store | 跨线程检索的信息 | 按主体、目的和过期策略 |

不要把它们全部叫“memory”。例如订单 ID 更适合结构化 state，用户长期偏好才可能进入 store，检索到的政策文档属于知识库，不应混进用户记忆。

## LangGraph Persistence 的当前事实

官方文档说明：编译图时配置 checkpointer 后，LangGraph 会在执行边界保存 checkpoint，并按 thread 组织。调用时通过 `configurable.thread_id` 选择持久游标。对已有 thread 传普通字典是在其最新状态上开始一次新 run；只有目标确实停在 interrupt 时，才应传 `Command(resume=...)`，把值交回那个 interrupt。新 ID 没有历史状态，但错误地对新 ID 发送 resume 不应依赖 runtime 自动拒绝。

`thread_id` 不是审批凭据或授权证明。应用恢复前要校验租户/主体所有权、`snapshot.next` 和 pending interrupts；已完成、未知或停在其他节点的 thread 应由包装层失败关闭。

生产环境不能把进程内 saver 当持久存储。测试可用 `InMemorySaver`，生产应选择可靠后端并验证备份、并发、加密、迁移和保留策略。

当前 runtime 的 durability mode 还会改变 checkpoint 写入时机：`sync` 在进入下一步前同步落盘，`async` 与下一步并行写入而保留较小崩溃窗口，`exit` 只在运行退出、报错或 interrupt 时保存。本课程真实恢复项目显式使用 `sync`；这仍不把外部 API 与 checkpoint 变成同一事务。

## Thread ID 是隔离边界的一部分

线程 ID 不应由模型生成，也不应直接相信客户端任意传入。服务端应把租户、用户、会话映射到不可猜测的内部 ID，并在每次读写时再次校验所有权。错误复用 ID 可能把 A 用户历史暴露给 B 用户。

建议记录：tenant、subject、thread_id、created_at、expires_at、schema_version、application_version。日志中不要输出完整敏感消息。

## 短期记忆不是无限聊天

上下文窗口和预算有限。常见策略包括：

- 只保留最近 N 轮；简单但会丢早期约束。
- 按 token 预算截断；比按消息数稳定。
- 摘要旧历史；节省上下文，但摘要可能误写事实。
- 选择性保留业务字段；更可靠，但需定义 schema。

业务真相应从数据库或结构化 state 获取，不要每轮让模型从自然语言历史猜。任何摘要都应记录来源范围和生成版本，重要事实可回到原记录核对。

## 长期记忆需要写入门

每条长期记忆至少考虑：主体、内容、来源、事实/推断标签、创建时间、过期时间、可见范围、用途和删除方式。模型推断的“用户喜欢红色”不能冒充用户确认；敏感属性不应因为“以后可能有用”而保存。

写入前问：任务是否需要？用户是否预期？是否允许保存？多久删除？能否撤回？不同租户如何隔离？

## 恢复与副作用

恢复可能重新执行节点。纯计算通常可重放，发送邮件、扣款、写数据库则必须使用幂等键或先查询回执。官方 persistence 还描述了 pending writes：同一 super-step 中已成功节点的写入可用于恢复，避免无谓重跑；但应用仍需为外部副作用设计 exactly-once 的业务语义，不能把 checkpoint 当分布式事务。

旧 checkpoint 还可能与新代码、Prompt、工具 schema 或 state schema 不兼容。恢复前校验版本；无法迁移时明确失败或走人工恢复，不要静默解释旧字段。

## 动手实践

为“旅行规划助手”设计：

1. 当前行程 state：目的地、日期、预算、待确认项。
2. 消息历史：用户和工具消息。
3. 长期记忆：用户明确确认的座位偏好及过期规则。
4. 禁止保存：证件原文和支付凭据。
5. thread_id 服务端映射规则。
6. “订票”节点的幂等键、回执查询与恢复流程。

再写 6 条测试：线程隔离、同线程续聊、过期删除、摘要不覆盖结构化字段、恢复不重复订票、旧 schema 拒绝恢复。

## 自测

- [ ] 能区分 state、checkpoint、thread 与 long-term store。
- [ ] 能说明相同 `thread_id` 的含义和错误复用后果。
- [ ] 能解释测试 saver 与生产持久后端的区别。
- [ ] 能为外部副作用设计恢复而不重复执行。

## 下一步

进入 [[LangChain/00-初学者路线/06-LangGraph边界审批恢复与评测|LangGraph 边界、审批、恢复与评测]]，把状态映射到显式图控制。

## 资料基线

官方事实与锁定 runtime 核对日期：2026-07-19。

- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [LangChain Agents - Memory](https://docs.langchain.com/oss/python/langchain/agents)
- [[LangChain/01-Conceptual Overviews/04-Memory|既有官方译文：Memory]]
