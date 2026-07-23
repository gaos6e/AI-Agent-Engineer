---
title: "The Boundary Between Agents and Workflows"
tags:
  - agent-core
  - workflow
  - architecture
aliases:
  - Agent Selection Boundary
  - Agent Autonomy Levels
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: Agent 核心/02-Agent与工作流的边界.md
translation_source_hash: fb32a81a8c56191342dc76ee204d7ba2b33f1149ae96c8ceb3d0afd733330bf3
translation_route: zh-CN/Agent-核心/02-Agent与工作流的边界
translation_default_route: zh-CN/Agent-核心/02-Agent与工作流的边界
---

# The Boundary Between Agents and Workflows

## Objective

After this lesson, you should be able to:

- Make an explainable choice among a single call, deterministic program, LLM workflow, and Agent.
- Use task uncertainty, verifiability, risk, cost, and recovery to choose an autonomy level.
- Design a hybrid architecture with a fixed shell and local autonomy.
- Prove through baselines and evaluation that Agent complexity creates real benefit.

## Four structures, not two labels

| Structure | Who controls the path? | Suitable situation | Typical example |
| --- | --- | --- | --- |
| Deterministic program | Code or rules | Inputs and transformations are fully defined | Scheduled file copy, JSON validation |
| Single LLM call | Application calls the model once | Controlled summarization, classification, extraction | Extract fields from a ticket |
| LLM workflow | Code predefines steps and branches; a model makes local judgments | The path is broadly known but needs language understanding | Parse → validate → approve → post |
| Agent | A model dynamically chooses steps and tools from environment feedback | Path and number of steps cannot be preset; exploration and correction are needed | Locate a regression in an unfamiliar repository |

Anthropic’s first-party article describes workflows as predefined code paths and Agents as dynamic model-controlled processes using tools. OpenAI’s guide likewise centers an Agent on model-managed execution, dynamic tool choice, and the ability to stop or hand back control after failure. Both recommend starting simply.

This is not an argument about product names. A flow in an SDK called “Agent” can be fully fixed, while a short framework-free loop can be a genuine Agent.

## Six design questions

### 1. Does the next step depend on an unknown observation?

If design can enumerate most steps and legal branches, prefer a workflow. An Agent has clear value only when it must explore the environment and each observation can change the next action.

### 2. Can success be verified?

Agents amplify error chains. If you cannot define external success evidence, improve the task and verifier before adding autonomous planning.

### 3. Can risk be isolated and recovered?

If an error can create irreversible financial, legal, physical, or public-communication impact, reduce autonomy. Put high-risk steps behind candidate generation, human approval, sandboxes, or a fixed workflow.

### 4. Are rules already too complex to maintain?

Many exceptions, unstructured materials, and contextual judgments may suit a model. But “there are many rules” can also signal a weak domain model or poor data. Compare a rules or classifier baseline first.

### 5. Do latency and cost permit multiple turns?

Every Agent turn can call a model and tools. Tail latency, cost, rate limiting, and compound failure all grow. Quality improvements must be measured on a real task set.

### 6. Can an operator understand and take over?

The operator must see progress, stop reason, effects already produced, and the next approval object. Autonomy that cannot be safely taken over is not a mature design.

## A practical scorecard

Score each dimension from 0 to 2:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Path uncertainty | Fixed | Few branches | Continuous exploration |
| Environment feedback | None | One or two times | Multiple turns determine the next step |
| Success verification | Deterministic | Partly human | Automatically verifiable but open path |
| Recoverability | Hard to recover | Approval or compensation is available | Sandboxes, idempotency, and checkpoints are complete |
| Rule maintenance | Simple | Moderate | Language and exceptions are highly complex |
| Multi-turn benefit | No evidence | Effective on a small sample | Stable, significant gain in evaluation |

The score does not make the decision automatically:

- Low path and feedback scores favor a deterministic program or single call.
- Medium scores favor an LLM workflow or router.
- High path and feedback scores, with mature verification and recovery, support a local or full Agent.
- High risk with weak recovery should never be fully automated, regardless of total score.

## Fixed shell, autonomous core

A common robust structure is:

~~~text
deterministic entry
  → validate identity, input, goal, and budget
  → [constrained Agent: explore, retrieve, generate candidates]
  → deterministic verifier
  → approval / fixed commit step
  → audit and compensation
~~~

For a refund system:

- Fixed: authentication, order ownership, statutory period, maximum amount, payment API, and audit.
- Agent: locate the problem in unstructured conversation, collect missing material, and propose a refund rationale and amount.
- Human or rules: thresholds, conflicting evidence, or high-risk accounts.

A model must not freely decide monetary authority, receiving account, or whether to bypass audit.

## Autonomy is not a switch

Increase it in levels:

1. **Suggestion**: Generate only a plan or candidate; execute no tools.
2. **Read-only Agent**: Explore but cannot write.
3. **Constrained writes**: Approve each write action.
4. **Automatic writes within rules**: Automate low-risk, idempotent, narrow writes; pause outside the boundary.
5. **Long-task autonomy**: Add durable checkpoints, budgets, monitoring, and takeover.

Every level needs matching evaluation, safety, and recovery evidence. “The model became stronger” is not a substitute for risk analysis.

## How typical patterns are classified

| Pattern | Default classification | When it becomes an Agent |
| --- | --- | --- |
| Prompt chaining | Workflow | The model dynamically chooses whether or how to continue |
| Routing | Workflow | The router can loop, explore, and change route |
| Parallelization | Workflow | The model dynamically creates and converges the task set |
| Evaluator–optimizer | Workflow | The model dynamically controls iteration count, tools, and path |
| Planner–executor | Depends on implementation | The plan can freely change from observations and step count is open |

Multiple LLM calls alone do not make something an Agent.

## Evaluate whether complexity is worth it

Build three baselines:

1. A rules-based or deterministic script.
2. A single LLM call or fixed workflow.
3. A constrained Agent.

Compare them on the same task set:

- Task success and critical subgoals.
- Human-intervention rate.
- Illegal actions or safety violations.
- p50 and p95 latency plus model and tool cost.
- Mean steps, repeated actions, and recovery success.
- Explainability and auditability.

If an Agent only makes a small subjective gain in “seems smarter” while greatly expanding cost and failure surface, return to the simpler structure.

## Counterexamples and redesigns

### Fixed report upload

“At 9:00 each day, read a fixed CSV, validate it, and upload it to a fixed location” calls for a scheduler and script. An LLM may explain exceptions, but an Agent need not dynamically choose the path.

### Performance regression in an unfamiliar repository

The system must inspect files, run different tests, and change hypotheses from profiles, so the path is difficult to preset. An Agent may be appropriate, provided that it:

- Restricts the repository and commands.
- Is read-only by default and sends changes through a diff.
- Has time and step limits.
- Requires benchmark evidence for completion.

### Customer refund

Do not let an Agent refund automatically end to end. Use a local Agent for material understanding, and keep identity, amount, account, approval, and payment submission in the fixed shell.

## Exercise

Choose one task and complete an architecture decision record:

- Automatically process customer refunds.
- Migrate 500 Markdown files.
- Investigate elevated production API latency.
- Produce a fixed weekly report.

Your ADR must state the selected autonomy level, why a simpler design was rejected, fixed actions, success evidence, budget, worst failure, human takeover, and fallback.

## Self-check

1. Is the key difference between a workflow and an Agent who controls the execution path, or whether an LLM is used?
2. Why is “many rules” not enough to justify an Agent?
3. Which high-risk steps should remain in the fixed shell?
4. How do baselines prove the value of a multi-turn Agent?
5. What verification evidence differs between a read-only Agent and an automatic-writing Agent?

You have mastered this lesson when you can write a selection ADR with a baseline, risk, and fallback.

## Next

Continue to [[agent-core/03-agent-state-context-and-memory|Agent State, Context, and Memory]] so the chosen Agent can preserve facts consistently across turns.

## References

The following are first-party engineering sources, obtained or rechecked on 2026-07-21.

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
