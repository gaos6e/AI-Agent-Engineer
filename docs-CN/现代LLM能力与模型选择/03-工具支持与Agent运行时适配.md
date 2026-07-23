---
title: "工具支持与 Agent 运行时适配"
tags:
  - llm
  - tool-calling
  - agent-runtime
aliases:
  - Agent 模型适配
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 现代LLM能力与模型选择/03-工具支持与Agent运行时适配.md
translation_route: en/modern-llm-capabilities-and-model-selection/03-tool-support-and-agent-runtime-compatibility
translation_default_route: zh-CN/现代LLM能力与模型选择/03-工具支持与Agent运行时适配
---

# 工具支持与 Agent 运行时适配

## 本节目标

评估模型是否能在确定性 runtime 中可靠提出工具动作，而不是只检查 API 是否有 `tools` 参数。

## 核心概念

“支持 tool calling”至少分成四层：

1. **接口层**：能否声明工具、返回 call ID、参数和终止原因；
2. **行为层**：何时调用、选哪个工具、参数是否正确、何时不该调用；
3. **协议层**：多工具、并行、流式、工具结果回填、错误恢复和版本兼容；
4. **控制层**：runtime 是否能在模型之外校验 schema、授权、预算、审批与副作用。

模型只拥有 proposal 权。真正的执行、权限和完成判定属于 runtime。

## 为什么需要

工具接口相同不代表行为相同。候选可能在单工具 demo 中成功，却在工具名称相近、参数缺失、观察含恶意文本或多步恢复时失效。Agent 任务的结果还取决于 action/observation interface；更换模型时不能忽略工具契约。

## 怎样实现

建立兼容矩阵并用探测测试填充，不从营销页推断：

| 能力 | 探测用例 | 失败分类 |
| --- | --- | --- |
| schema | 必填、枚举、嵌套、未知字段 | parse/schema/semantic |
| selection | 应调用、不应调用、相似工具 | wrong/missing/excess call |
| lifecycle | call ID、结果回填、并行、重试 | protocol mismatch |
| safety | 越权参数、恶意 observation、写入审批 | policy/authorization |
| recovery | timeout、可重试错误、重复 receipt | duplicate/lost progress |

候选间固定工具描述、可见工具集合、最大步骤与 runtime。若供应商原生接口差异无法消除，应通过 adapter 规范化，并把 adapter 版本纳入选择对象。任务把 tool calling 列为 required capability 时，接口自报支持只是静态 gate；实测工具行为成功率还要达到预注册阈值，低于阈值的候选不得进入加权排序。

## 常见失败

- 让模型生成任意 shell，再把“会用工具”当成功。
- 只统计最终文本正确，不检查错误调用和副作用。
- 给不同候选不同数量或不同描述的工具。
- 把参数自动修复、重试和 fallback 的收益全部记到模型上。
- 因模型拒绝一次越权调用，就宣称系统安全。

## 怎样验证

用确定性 fake tools 记录每个 proposal、校验结果、调用和 receipt。至少分别报告工具选择、参数、轨迹、最终环境状态和越权阻断；安全门必须在替换为故意越权的固定策略后仍有效。

## 实践任务

实现 `read_ticket`、`draft_reply`、`close_ticket` 三个 fake tools。准备“只读即可”“必须澄清”“需人工批准”“工具结果提示绕过策略”四类 case，比较两个候选在相同 runtime 中的多 trial 结果。

## 参考资料

- [[Tool Calling（含 Function Calling）/00-目录|本库：Tool Calling]]
- [[Agent 核心/00-目录|本库：Agent 核心]]
- Yang 等，[SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- 动态能力只能在接入当日从对应供应商模型/API 文档和实际探测中确认；本页不保存兼容性排行榜。
