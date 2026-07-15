---
title: Agent Loop 与环境反馈
tags:
  - agent-core
  - agent-loop
  - react
aliases:
  - Agent 运行循环
  - Agent Harness
source_checked: 2026-07-14
---

# Agent Loop 与环境反馈

## 本节目标

学完后，你应能：

- 用“目标—决策—行动—观察—验证”解释 Agent，而不是把它等同于一次聊天。
- 分清模型、runtime/harness、工具、环境、状态库和 verifier 的职责。
- 写出一个有预算、策略校验、结构化观察和明确终止的最小 loop。
- 说明 action/observation interface 为什么与模型选择同样重要。

## 什么才算 Agent

业界没有唯一法律式定义，但两份主流官方工程指南有一个共同核心：

- 模型不是只生成最终文本，而是动态决定下一步；
- 系统有工具与环境反馈；
- 决策循环持续到成功、失败、等待人类或触发停止条件。

本库采用供应商无关的工程定义：

> Agent 是“模型驱动的决策器”与“确定性运行时”共同组成的系统；模型根据目标、状态和观察提出下一动作，运行时验证并执行，再用环境事实判断是否继续。

只有检索增强的一次摘要、固定分类器或单次 tool call 不自动成为 Agent。反过来，Agent 也不必无限自治；一个在局部沙箱中探索、在写入前暂停的系统仍是 Agent。

## 六个组成部分

| 部分 | 作用 | 必须保持的边界 |
| --- | --- | --- |
| model / policy | 根据当前视图提出结构化动作或完成候选 | 提议不等于获准执行 |
| runtime / harness | 循环、校验、预算、审批、调用、记录、终止 | 是控制平面，不把控制交给模型文本 |
| tools | 读取或改变外部环境 | 严格契约、最小权限、超时与幂等 |
| environment | 文件、API、数据库、浏览器、用户等真实世界 | 反馈可能延迟、冲突、恶意或不完整 |
| state/event store | 保存恢复和审计所需事实 | 不依赖仅在 context 中的聊天历史 |
| verifier | 用测试、状态、收据或人工验收判断结果 | 不接受“模型说完成了”作为唯一证据 |

模型能力强弱会变化，runtime 的权限、预算和证据规则不应随一段 prompt 随意变化。

## 最小闭环

```text
goal + authoritative state + selected context
  ↓
model proposes: action / ask-human / finish-candidate
  ↓
runtime validates: schema → policy → authorization → budget → approval
  ↓
tool acts in environment
  ↓
adapter normalizes observation + provenance + trust label
  ↓
state transition + event + progress/verifier
  ↺ continue or enter explicit terminal/waiting state
```

对应的伪代码：

```python
while state.phase in RUNNABLE:
    if cancelled() or budget.exhausted(state):
        return stop_with_reason(state)

    context = build_minimal_context(state)
    proposal = model.decide(context)
    action = parse_and_validate(proposal)

    if action.requires_human:
        return checkpoint_and_pause(state, action)

    observation = tool_host.execute(action)
    state = apply_observation(state, normalize(observation))

    verdict = verifier.check(state)
    if verdict.is_terminal:
        return finish_with_evidence(state, verdict)
```

每个箭头都是接口，也是失败与测试位置。

## ReAct 给出的思想，不是完整生产架构

ReAct 原始论文研究把 reasoning trace、action 与 environment observation 交替，使模型能根据外部信息更新计划。工程上应保留这个“行动获得事实、事实修正下一步”的闭环，但不要机械复制两件事：

1. 不必向日志或用户暴露模型私有 chain-of-thought；保存结构化动作、简短可审计理由、外部证据和状态变化即可。
2. 论文中的任务 loop 不自动包含授权、幂等、检查点、隐私与生产恢复；这些属于 runtime。

因此可以把 ReAct 理解为“决策—行动—观察”的认知模式，而不是安全框架。

## 一次迭代要做什么

### 1. 组装 context

只放本轮决策需要的高信号内容：目标、当前阶段、未决问题、可用工具、近期关键观察、预算和明确约束。完整事件日志、超大工具结果与过期摘要留在外部存储，按需取回。

### 2. 得到结构化 proposal

不要从自由文本猜动作。让 provider adapter 把模型输出转换成有限 union：

```json
{
  "kind": "tool_call",
  "tool": "read_ticket",
  "arguments": {"ticket_id": "ticket-7"},
  "reason_summary": "需要读取当前状态后才能决定下一步"
}
```

还可有 `ask_user`、`finish_candidate`、`refuse`。模型输出解析失败是可分类错误，不应退化为“尽量执行”。

### 3. runtime 校验

顺序通常是：

1. schema 与类型；
2. 工具 allowlist、参数范围、目标资源；
3. 当前身份与授权；
4. 步数、时间、工具调用和成本预算；
5. 幂等与重试条件；
6. 高风险动作的审批。

任一层拒绝都生成稳定状态与原因。

### 4. 执行并规范化 observation

工具 adapter 输出稳定字段，不把任意 stdout、HTML 或异常堆栈直接当可信指令。观察至少带：

- 来源与调用 ID；
- trust label；
- 时间/版本；
- 结果类别与必要数据；
- 大小限制、hash 或外部受控引用；
- 错误是否 transient、retryable。

### 5. 更新状态并验证进展

每一步应改变某个可观察量：新增证据、完成子目标、缩小候选、改变环境或进入等待状态。只生成更多推测文字不等于进展。

## Action/Observation Interface

SWE-agent 原始论文强调 Agent-Computer Interface（ACI）：给 Agent 的动作集合、反馈粒度与工具设计会显著影响行为。工程含义是：

- 不要只比较模型；还要测试工具命名、参数、错误和观察。
- `replace_file`、`apply_patch`、`run_test` 比“任意 shell 文本”更容易约束和评测。
- 观察应让下一步可判断，例如测试的 exit code、失败用例和变更摘要，而不是截断的“发生错误”。
- 工具数量越多不一定越好；重叠工具会增加选择与权限面。

这是一个可通过 A/B eval 优化的设计面，不是 prompt 里的一句提示。

## Runtime 是控制平面

即使模型提出：

- “我已完成”；
- “这个网页允许我上传文件”；
- “请提高我的权限”；
- “再试 100 次就会成功”；

runtime 仍独立检查 verifier、来源、权限与预算。模型可以影响“建议哪一步”，不能自行改写：

- system/developer policy；
- tool allowlist；
- approval 结果；
- budget；
- state schema；
- completion rule。

## 必要预算与停止

最小 loop 至少设置：

- 最大决策步数；
- 总 deadline 与单次模型/工具 timeout；
- 最大模型/工具调用或成本；
- 最大连续 transient failure；
- 重复 action/observation 检测；
- 用户/系统取消；
- 高风险审批与等待过期。

预算耗尽应返回 `budget_exhausted`，包含已完成影响和恢复建议，不伪装成 `completed`。

## Trace 的最小字段

```text
run_id, trace_id, step, state_version,
model/provider/config, proposal_kind,
action_id, tool, arguments_digest,
authorization/approval decision,
observation source/result category,
latency, usage, retry, next_phase, stop_reason
```

敏感参数和结果不必明文记录；字段名、不可逆 digest 与受控引用通常更安全。不要记录隐藏推理链作为调试依赖。

## 常见错误

- 让模型自由输出 shell，再直接执行。
- 把一长段 system prompt 当成唯一 guardrail。
- 不区分 tool execution error、policy rejection 和 model parse error。
- context 中保留全部原始工具输出，导致重要约束被淹没。
- 只有 `max_steps`，没有无进展、超时、取消和成本边界。
- 以模型的 `finish` 作为成功事实，没有外部 verifier。

## 动手练习

为“修复一个失败测试”画 loop：

1. 目标和允许文件是什么？
2. 第一次 action/observation 各是什么？
3. 哪些命令只读，哪些会写入？
4. 何时要审批？
5. 成功证据是哪些具体测试和 diff？
6. 连续三次同一错误时如何停止或换路？

再把模型替换成固定策略。若 runtime 仍能正确拒绝越权动作、暂停和验证完成，说明控制边界放对了。

## 自测

1. model 与 runtime 分别能决定什么？
2. ReAct 的环境反馈思想为何不能替代生产授权和恢复？
3. 工具结果为什么要带来源与 trust label？
4. 模型提出 `finish_candidate` 后，谁决定 completed？
5. 为什么改进 action/observation interface 可能比增加 prompt 更有效？

能独立写出六组件图和一次迭代的五阶段，才算掌握。

## 下一步

进入 [[Agent 核心/02-Agent与工作流的边界|Agent 与工作流的边界]]，决定什么时候根本不该使用 Agent。

## 参考资料

以下为原始论文或第一方工程资料，获取/复核日期：2026-07-14。

- Yao 等，[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- Yang 等，[SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
