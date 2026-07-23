---
title: "Tool Support and Agent Runtime Compatibility"
tags:
  - llm
  - tool-calling
  - agent-runtime
aliases:
  - Agent model compatibility
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/03-工具支持与Agent运行时适配.md
translation_source_hash: 3df4a9b577942d58df4473a5c680c62dc8a939c0b02b728b341d016e1c518c39
translation_route: zh-CN/现代LLM能力与模型选择/03-工具支持与Agent运行时适配
translation_default_route: zh-CN/现代LLM能力与模型选择/03-工具支持与Agent运行时适配
---

# Tool Support and Agent Runtime Compatibility

## Goal

Evaluate whether a model can reliably propose tool actions in a deterministic runtime, rather than merely checking whether an API has a `tools` parameter.

## Core concepts

“Supports tool calling” has at least four layers:

1. **Interface layer**: Can the API declare tools and return a call ID, arguments, and termination reason?
2. **Behavior layer**: When does it call a tool, which tool does it choose, are the arguments correct, and when should it not call one?
3. **Protocol layer**: Multiple tools, parallelism, streaming, tool-result reinjection, error recovery, and version compatibility.
4. **Control layer**: Can the runtime validate schema, authorization, budgets, approvals, and side effects outside the model?

The model has proposal authority only. Actual execution, authorization, and completion decisions belong to the runtime.

## Why this matters

Identical tool interfaces do not imply identical behavior. A candidate can succeed in a single-tool demo but fail when tool names are similar, parameters are missing, observations contain malicious text, or a multi-step recovery is required. Agent-task outcomes also depend on the action/observation interface, so a model swap cannot ignore the tool contract.

## How to implement it

Build a compatibility matrix and populate it with probe tests rather than marketing-page inference:

| Capability | Probe case | Failure classification |
| --- | --- | --- |
| schema | Required fields, enums, nesting, unknown fields | Parse/schema/semantic |
| selection | Should call, should not call, similar tools | Wrong/missing/excess call |
| lifecycle | Call ID, result reinjection, parallelism, retries | Protocol mismatch |
| safety | Unauthorized arguments, malicious observation, write approval | Policy/authorization |
| recovery | Timeout, retryable error, duplicate receipt | Duplicate/lost progress |

Fix tool descriptions, the visible tool set, maximum steps, and runtime across candidates. Where vendor-native interface differences cannot be eliminated, normalize them through an adapter and include its version in the selection object. When the task names tool calling as a required capability, an interface’s self-reported support is only a static gate; the measured tool-behavior success rate must also reach its preregistered threshold. Candidates below that threshold cannot enter weighted ranking.

## Common failures

- Letting the model generate arbitrary shell commands, then calling that “tool use.”
- Counting only final-text correctness and not incorrect calls or side effects.
- Giving different candidates different counts or descriptions of tools.
- Crediting all gain from automatic argument repair, retries, and fallbacks to the model.
- Claiming the system is safe because the model once refused an unauthorized call.

## How to validate

Use deterministic fake tools that record every proposal, validation result, invocation, and receipt. Report tool selection, arguments, trajectory, final environment state, and unauthorized-action blocking separately. The security gate must still work when a fixed policy deliberately proposes an unauthorized action.

## Practice task

Implement three fake tools: `read_ticket`, `draft_reply`, and `close_ticket`. Prepare four types of cases: “read-only is enough,” “clarification is required,” “human approval is required,” and “a tool result asks to bypass policy.” Compare multi-trial results from two candidates in the same runtime.

## References

- [[tool-calling-function-calling/00-index|This knowledge base: Tool Calling]]
- [[agent-core/00-index|This knowledge base: Agent Core]]
- Yang et al., [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- Dynamic capabilities can be confirmed only from the relevant vendor’s model/API documentation and actual probes on the integration date; this page does not maintain a compatibility leaderboard.
