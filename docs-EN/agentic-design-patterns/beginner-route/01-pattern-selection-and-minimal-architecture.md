---
title: "Pattern Selection and Minimal Architecture"
aliases:
  - Agent Architecture Selection
  - Minimal Agentic Architecture
tags:
  - ai-agent
  - design-patterns
  - beginner
source_checked: 2026-07-14
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/01-模式选择与最小架构.md
translation_source_hash: 70ec880d403de1c757a8a1946ac160283542b0753c09181c010e5852d64b1803
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/01-模式选择与最小架构
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/01-模式选择与最小架构
---

# Pattern Selection and Minimal Architecture

## Goal

After this lesson, you should be able to describe a task before choosing ordinary code, a deterministic workflow, a single Agent, or multiple Agents. You should also be able to write that choice as a checkable state graph rather than assuming that a model is “smart enough.”

> [!important] Clarify three terms first
>
> - A **component** is a part such as a model, tool, retriever, or database.
> - A **pattern** is a recurring problem and a reusable way to organize it, such as routing, parallelism, approval, or checkpoints.
> - A **framework** is software that implements patterns. A pattern is not a framework API; state, authorization, and acceptance constraints remain after a framework upgrade.

## Start from task uncertainty

Anthropic's engineering guidance separates agentic systems into **workflows**, which orchestrate models and tools through predefined code paths, and **Agents**, which let a model dynamically choose the process and tools. The same guidance recommends starting with the simplest solution and increasing complexity only when its benefit covers extra latency, cost, and accumulated-error risk. This is a source-backed design recommendation, not a mandate that every team use the same implementation.

Use this four-level ladder for an initial decision:

| Level | Who chooses the next step? | Suitable situation | Primary verification |
| --- | --- | --- | --- |
| Ordinary function or script | Program rules | Rules are stable and I/O is explicit | Unit tests and property checks |
| Deterministic workflow | Program state machine | Steps and branches can be listed beforehand | Node and transition tests |
| Single Agent | Model chooses from constrained actions | Paths cannot be enumerated beforehand and must respond to environmental observations | Trace, outcome, and budget evaluation |
| Multi-Agent system | Several model roles coordinate | Permission, context, or expertise must be isolated and the coordination benefit is demonstrated | Protocol, handoff, and system-level evaluation |

For example, “convert a fixed CSV to JSON” is ordinary code. “Parse a document → retrieve → generate → verify citations” is normally a workflow. “Locate a failure in an unfamiliar codebase and choose inspection tools” may require an Agent. Copying the same prompt to three roles does not automatically produce three independent pieces of evidence.

## Six diagnostic questions

Answer each question before drawing an architecture:

1. Can success be written as assertions, tests, or a human rubric?
2. Can steps and dependencies be listed in advance?
3. Which branches can deterministic rules decide?
4. Which actions change the outside world, and can they be reversed?
5. Can the environment change during execution, requiring replanning?
6. How many steps, elapsed time, model calls, and human approvals are allowed?

If success is unclear, adding an Agent only moves an ambiguous requirement into runtime. When steps and branches are known, a workflow is usually easier to replay. A model-driven dynamic loop has unique value only when the path truly depends on observations from an unknown environment.

## A one-page minimum architecture card

At minimum, a design document should state the following:

| Item | Question that must be answered | Verifiable artifact |
| --- | --- | --- |
| Input | What are its type, size, source, trust level, and rejection conditions? | JSON Schema or input tests |
| Output | Who consumes it, what is its structure, and how is completion judged? | Acceptance assertions or a scoring rubric |
| State | Which fields survive across steps, and who may change them? | State schema and version |
| Decisions | Which are rule-driven and which are delegated to the model? | Routing table and unknown branch |
| Tools | What are their permissions, timeouts, errors, and side effects? | Tool contract |
| Stop | When do success, failure, over-budget, and human handoff occur? | Explicit terminal states |
| Evidence | How can a failure be replayed and located? | Event trace, receipts, and test set |

A minimal state can be:

```json
{
  "run_id": "run-001",
  "stage": "classify",
  "input_ref": "sha256:...",
  "budget": {"steps_left": 6},
  "approval": null,
  "result": null
}
```

Read the fields this way:

- `run_id` ties one execution's state, events, and audit records to one stable identifier.
- `stage` is the current business-flow stage controlled by application code; a model must not rewrite it freely.
- `input_ref` points to a frozen, reviewable input digest or version.
- `budget.steps_left` puts the maximum execution steps into verifiable state instead of only in a Prompt.
- `approval` stays `null` until a trusted approval is obtained; model prose is not authorization.
- `result` stores a controlled artifact or reference only after a legal terminal state is reached.

State stores the facts needed to continue. It does not turn the entire chat history into a database. `input_ref` should identify a controlled input version; a real system also defines access control and retention periods.

## Build it step by step: a fixed daily report

The request is: “Read three fixed RSS feeds every day, filter for designated keywords, generate a summary, and save a draft.”

1. Sources are fixed and fetch/filter steps can be listed, so begin with a workflow.
2. The three feeds are independent and can be fetched in parallel; after joining, check whether any source is missing.
3. A model may generate the summary, but code still controls the flow.
4. Saving a draft is a write action, so use a fixed directory and idempotent file name.
5. Success means all three fetch statuses are present, summary fields are valid, and a draft receipt exists.

If the requirement later becomes “discover relevant sources, decide how many queries to run, and handle anti-bot limits,” reassess whether an Agent is justified. Architecture should change with task evidence, not with buzzwords.

## Common mistakes and troubleshooting

- **Treating autonomy as the goal**: ask first about the business result, not “can it be more autonomous?” More autonomy expands the verification surface.
- **Treating model output as state fact**: a model suggestion is a candidate decision; tool receipts or database records are evidence of external state.
- **Choosing a framework before defining state**: framework defaults make implicit decisions that are hard to explain after failure.
- **Having only a success path**: network failure, permission denial, human rejection, and budget exhaustion all need terminal states.
- **Trusting a one-time demo**: one pass from a stochastic model is not stability; build a repeatable task set and run multiple trials.

## Exercise: complete an architecture card

For “read customer tickets and draft replies; refunds may be suggested but not executed,” submit:

1. Your choice on the four-level ladder and the reason.
2. Input, output, state, decisions, tools, stop conditions, and evidence.
3. A state graph containing `success`, `failed`, and `human_review`.
4. Three normal samples, two boundary samples, and one adversarial-input sample.

Reference judgment: classification, retrieval, and draft generation can form a workflow; a refund recommendation should be isolated from a real refund tool. Consider dynamic Agent tool selection only if the ticket-handling path truly cannot be specified in advance.

## Mastery check

- [ ] I can name a task that should not use an Agent and explain why.
- [ ] I can distinguish a component, pattern, and framework.
- [ ] I can rewrite “done” as a checkable result or environmental state.
- [ ] I can list the cost, latency, and verification surface added by model decisions.
- [ ] I can write terminal states for success, failure, cancellation, over-budget, and human takeover.

## Next

Continue with [[agentic-design-patterns/beginner-route/02-routing-parallelism-and-joining|Routing, Parallelism, and Joining]] to compose work with predictable structures.

## References

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — published 2024-12-19; checked 2026-07-14.
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) — checked 2026-07-14.
- [[agentic-design-patterns/upstream-references/section-01/reference-01-2096542b|Reference layer: Prompt Chaining]] — frozen translated-reference version; see the course index for source details.
