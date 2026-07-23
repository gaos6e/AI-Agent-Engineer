---
title: "Budgets, Stopping, and Human Intervention"
tags:
  - multi-agent
  - budget
  - human-in-the-loop
aliases:
  - Multi-Agent Stopping Conditions
  - Multi-Agent Human in the Loop
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/02-工程与质量/06-预算、停止与人工介入.md
translation_source_hash: bd24d2eb87203d907e1e87b4a1107e28f50d2e5bb01a3f841b23bc0ab9f7f1da
translation_route: zh-CN/多Agent协作/02-工程与质量/06-预算、停止与人工介入
translation_default_route: zh-CN/多Agent协作/02-工程与质量/06-预算、停止与人工介入
---

# Budgets, Stopping, and Human Intervention

## Goal

Set hard limits for the whole collaboration system and every subtask. Make completion, failure, pause, cancellation, and human approval explicit states.

## A budget is more than money

Consider at least seven limits:

- maximum model and tool calls;
- token or monetary budget;
- wall-clock deadline;
- maximum concurrency;
- maximum delegation depth and subtask count;
- maximum attempts or rework per task;
- quotas for files, network, databases, and other resources.

The global budget covers all sub-agents; do not let each one believe it owns the full allowance. Preserve capacity for recovery and aggregation — a research phase must not consume the writer's and reviewer's budget.

## Terminal states should be exclusive and explainable

Distinguish:

- `succeeded` — acceptance evidence is complete;
- `failed` — completion is impossible, with a stable failure class;
- `denied` — policy rejected the action;
- `budget_exhausted` — a hard limit was reached;
- `canceled` — a user or superior layer canceled actively;
- `waiting_human` — paused for approval or clarification;
- `partial` — the contract allows a partial result and names the gap.

“The agent says it finished” must not transition state to `succeeded`. The scheduler checks all required tasks, output schema, and acceptor results.

## Stopping conditions

Beyond success and budget, detect:

- consecutive identical actions or messages;
- rework loops with no new evidence;
- a quality score that does not improve across several rounds;
- a dependency graph that cannot make progress;
- a missing waiting object or expired lease;
- conflict count over a threshold;
- a safety-policy trigger.

After stopping, retain the last stable checkpoint, verified artifacts, reason for incompletion, and recommended human action. Do not automatically widen permission or remove guardrails merely to “continue.”

## Human in the loop is not one prompt

An effective approval contains:

- the exact action requested;
- target resource and impact scope;
- a preview of important input and output;
- risk and reversibility;
- who may approve;
- transitions for approve, reject, modify, and timeout;
- the approval record and corresponding task or tool-call ID.

As of 2026-07-22, the OpenAI Agents SDK Human-in-the-Loop documentation describes interrupting a tool call, serializing run state, and resuming after approval or rejection. Interfaces will change, but the engineering principle is stable: pause without executing, let an external principal decide, and resume from the same state.

The SDK aggregates interruptions in an outer `RunState`, including tools in a handoff or nested `Agent.as_tool()`, and can serialize and resume it. This is SDK behavior, not a guarantee that external authorization stays valid. Serialized state can include application context and runtime metadata, so govern it as persistent data: do not place secrets or broad capability tokens in context; production approval still requires independent identity, scope, expiration, and audit checks at the execution boundary. See [Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) (accessed 2026-07-22).

## Actions that normally need a human decision

- External sending, publishing, payment, deletion, or irreversible write;
- data-access or permission expansion;
- high-impact health, legal, or financial decisions;
- conflicting evidence where automatic arbitration is risky;
- user-intent ambiguity that would change the outcome;
- material budget expansion.

Low-risk, reversible, fully validated repetition may be automatically approved by policy, but the authorization must remain revocable.

## Budget-allocation example

```text
Total call limit 20
  Manager and routing: 4
  Two parallel specialists: 5 each
  Aggregation: 3
  Review or correction: 3
Total deadline 60 seconds; each tool 10 seconds; maximum concurrency 2
Delegation depth 1; at most 2 attempts per task
```

If one specialist uses all five calls early, it must not consume the review budget. The manager can deliver partially or stop.

## Exercise and self-check

List budgets and at least two approval points for “generate and publish a weekly report.” Does approval timeout mean failure or `waiting_human`? After user cancellation, how do already-started parallel agents and tools receive the cancellation signal?

## Next step

Continue with [[multi-agent-collaboration/engineering-and-quality/07-evaluation-observability-and-security-boundaries|Evaluation, Observability, and Security Boundaries]].

## References

- [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) — accessed 2026-07-22.
- [OpenAI Agents SDK: Running agents](https://openai.github.io/openai-agents-python/running_agents/) — accessed 2026-07-22.
