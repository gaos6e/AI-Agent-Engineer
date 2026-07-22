---
title: LangGraph 边界、审批、恢复与评测
aliases:
  - LangGraph Control Boundary
  - LangGraph 人工审批与恢复
tags:
  - langgraph
  - human-in-the-loop
  - evaluation
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
---

# LangGraph 边界、审批、恢复与评测

## 本节目标

判断何时需要从 LangChain 高层 Agent 下沉到 LangGraph；把任务表达成显式状态、节点、边和终态；正确使用持久化与 interrupt，并为节点、轨迹、恢复和最终结果建立分层测试。

## 什么时候下沉到 LangGraph

先选最低复杂度：

| 需求 | 首选 | 原因 |
| --- | --- | --- |
| 两三个固定步骤 | 普通 Python / LCEL | 路径确定，不需要状态运行时 |
| 标准模型—工具循环 | LangChain `create_agent` | 高层入口减少样板 |
| 显式分支、循环、并行、长等待 | LangGraph | 拓扑和状态可见 |
| 暂停审批、检查点恢复、旧状态迁移 | LangGraph + 持久后端 | 需要运行时状态合同 |
| 多个独立团队或权限域 | 先做系统设计，再考虑子图/多 Agent | “节点更多”不等于“应增加 Agent” |

LangGraph 提供 Graph API 与 Functional API。两者是表达方式，不是能力排行榜：Graph API 让拓扑一眼可见，Functional API 便于给现有函数添加持久执行语义。团队应选一种主风格，避免同一业务流程在两套抽象间跳转。

## 从状态合同开始

不要先画节点，再把任意对象塞进共享字典。状态至少区分：

- 原始且不可变的请求引用；
- 规范化业务字段；
- 模型候选输出与校验结果；
- 工具回执或外部结果引用；
- 路由决策、预算、错误类别与终态；
- schema、Prompt、模型、工具和图定义版本。

节点返回的是状态更新。并行分支写同一字段时必须定义 reducer；若顺序会改变含义，就不应依赖默认覆盖。敏感文档和大模型响应通常保存受控引用与指纹，而不是把全文复制进每个 checkpoint。

## 节点与边的设计

好节点是一个可独立测试、可分类失败的工作单元：

1. 输入和输出 schema 明确；
2. 纯计算与外部副作用分开；
3. 错误分为可重试、永久、业务拒绝和结果未知；
4. 每个循环都有最大步数、deadline、完成判据和人工出口；
5. 路由只返回允许节点枚举，模型文本不能成为任意节点名；
6. 外部动作有对象级授权、幂等键和完成验证器。

Graph API 中的条件边只负责选择路径，不替代业务验证。并行节点只能在无数据依赖、无共享写冲突并且总并发受限时同时运行。

## Persistence 的准确边界

官方当前文档说明，图在编译时配置 checkpointer 后，会按 `thread_id` 保存和读取检查点。持久化支持会话状态、人工在环、time travel 与故障恢复。`InMemorySaver` 适合测试；生产环境要选择持久后端，并验证租户隔离、并发、备份、加密、保留、删除和 schema 迁移。

Checkpoint 不是跨系统事务。若节点在付款成功后、状态写入前崩溃，恢复仍可能再次进入节点。外部副作用必须用稳定幂等键，或者先查询同一意图的回执。

## Interrupt 的真实恢复语义

当前官方 Interrupts 文档要求：

1. 图使用 checkpointer；
2. 调用配置提供 `thread_id`；
3. 节点调用 `interrupt()`，载荷必须可 JSON 序列化；
4. 恢复时使用同一 thread ID，并以 `Command(resume=...)` 提供值。

最容易忽略的事实是：**恢复会从包含 interrupt 的节点开头重新执行，而不是从那一行之后继续。** 因此：

- 不要用宽泛 `try/except` 吞掉 interrupt 的运行时异常；
- 不要在同一节点中按不稳定条件改变 interrupt 的顺序；
- interrupt 前的副作用必须幂等，最好把副作用移到审批后的独立节点；
- 审批载荷只放简单、可序列化、经裁剪的数据；
- 复杂表单不要在一个节点中用 `while True + interrupt()`，官方指南建议一次节点调用只产生一次 interrupt，再通过条件边重问。

应用还必须在调用 `Command(resume=...)` **之前**检查 checkpoint。锁定的 `langgraph==1.2.9` 实验表明，已完成 thread 的 resume 可能只返回旧状态，而不存在的 thread 甚至可能从 `START` 进入新运行；因此不能把 runtime 的默认行为当成业务拒绝。至少检查 thread 所有权、`snapshot.next`、pending interrupt 数量及审批动作指纹。

## 审批要绑定什么

“approved=true”不足以授权动作。审批请求至少绑定：

- thread / workflow instance 与目标节点；
- 工具名、规范化参数和动作指纹；
- state、图、策略和工具版本；
- 审批者身份、角色、决定、理由与时间；
- 到期时间和一次性 request ID。

恢复后重新校验资源、权限和参数；金额、收件人或 SQL 改变时，旧批准立即失效。即使有 `HumanInTheLoopMiddleware` 或 interrupt，工具服务端仍必须执行真实授权。

## 四层评测

1. **节点测试**：固定输入检查状态更新、错误分类和无副作用分支。
2. **图/轨迹测试**：断言允许节点、路由、工具、循环次数和终态，不要求脆弱的逐 token 相等。
3. **恢复测试**：在 interrupt、工具提交后崩溃、旧 checkpoint、重复事件和迟到结果处恢复。
4. **任务评测**：最终业务结果、证据、成本、时延、安全违规与人工接管率。

LangGraph 官方测试指南展示了单独编译节点、使用测试 checkpointer、`update_state(..., as_node=...)` 和指定 interrupt 位置等方法。测试用内存 saver 通过不能证明生产持久化、并发或灾备正确。

## 练习

画一个“生成只读 SQL → 静态校验 → 人工审批 → 执行 → 结果验证”的图：

1. 写出 state 字段和每个字段的来源。
2. 标出 interrupt 节点以及恢复时会重新执行的代码。
3. 为执行节点设计对象级授权、幂等键和未知结果查询。
4. 写 12 条测试，至少覆盖篡改审批、过期、错误 thread ID、工具提交后崩溃和旧 schema。

## 自测

- [ ] 能说明普通 Python、`create_agent` 与 LangGraph 的边界。
- [ ] 能解释 thread ID、checkpointer、checkpoint 和 store 的区别。
- [ ] 能说明为什么 interrupt 前的代码会重跑。
- [ ] 能把审批绑定到动作，而不是相信自然语言说明。
- [ ] 能区分节点、轨迹、恢复与任务结果评测。

## 下一步

先完成 [[LangChain/00-初学者路线/07-项目-离线工具代理骨架|Layer A：离线工具代理骨架]]，再运行 [[LangChain/00-初学者路线/10-项目-无密钥create_agent运行时合同|Layer B：无密钥 create_agent 运行时合同]]，最后进入 [[LangChain/00-初学者路线/08-项目-LangGraph可恢复审批流|Layer C：LangGraph 可恢复审批流]]。三步分别验证框架无关执行器、当前 LangChain harness 和真实 runtime 恢复语义；它们都不替代 provider 集成、授权或外部副作用的生产测试。

## 资料基线

官方事实与锁定 runtime 核对日期：2026-07-21。

- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Test](https://docs.langchain.com/oss/python/langgraph/test)
- [LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [[LangChain/01-Conceptual Overviews/06-Graph API|既有官方译文：Graph API]]
