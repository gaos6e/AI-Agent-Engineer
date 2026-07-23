---
title: "Failure Recovery, Evaluation, and Observability"
aliases:
  - Recovery Evaluation Observability
  - Agent Reliability and Evaluation
tags:
  - ai-agent
  - reliability
  - evaluation
source_checked: 2026-07-22
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/06-失败恢复评测与可观测性.md
translation_source_hash: 0c22beff65937893238497be6a3028af85c6de0ca5af7318c7fd11c1080adfa2
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/06-失败恢复评测与可观测性
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/06-失败恢复评测与可观测性
---

# Failure Recovery, Evaluation, and Observability

## Goal

You will choose retry, degradation, failure, or human takeover by error category; design checkpoints and idempotent receipts; and evaluate components, traces, task outcomes, and runtime metrics together.

## Classify before recovering

| Category | Example | Default handling |
| --- | --- | --- |
| Input/business error | Missing field; policy disallows action | Do not retry; clarify, reject, or cancel |
| Permission error | Identity lacks write permission | Do not retry; alert or hand off |
| Transient infrastructure error | Short timeout; rate limit | Bounded retries and backoff |
| Permanent dependency error | Resource missing; incompatible API | Fail or degrade |
| Policy/model error | Misroute; out-of-bounds action | Preserve trace; enter evaluation or human review |
| Unknown commit state | Write request timed out | Query idempotent receipt first |

Uniform retry amplifies cost and can repeat side effects. A retry policy needs per-step attempt count, total time, retryable-error set, and circuit-break condition. Backoff is only a mechanism; intervals must respect service guidance and business deadlines.

## Checkpoints and idempotency solve different problems

- A **checkpoint** answers, “Where is the internal flow and what is next?”
- An **idempotency key and receipt** answer, “Did the external action already happen?”

A classic failure window occurs when an external write commits but the process crashes before saving the new checkpoint. Recovery still sees `execute`. Repeating immediately creates a duplicate record; querying a stable action-ID receipt first restores the committed fact into state.

Atomic replacement of local JSON only demonstrates checkpoint concepts. Production systems also need concurrency control, transactions, authorization, backup, migration, retention, and disaster-recovery design.

## Observability: logs, metrics, and traces

Record at least:

- `run_id`, input digest, and version;
- model, Prompt, tool, and policy versions;
- start, end, status, and duration of each step;
- tool name, safe parameter summary, structured result, and error category;
- routing, retry, approval, budget, and terminal state; and
- local run / operation / action IDs, protocol request IDs, remote task IDs, and references to external action receipts—stored separately by scope.

**Logs** explain one event. **Metrics** present aggregate trends. A **trace / trajectory** connects model decisions, tool actions, and observations. Minimize sensitive data; replayability does not require retaining every raw document or secret.

## Cross-protocol traces: correlate, do not conflate

When a workflow crosses [[mcp/00-index|MCP]] or [[a2a/00-index|A2A]], “success” contains at least four different facts: whether the local state machine completed, whether the protocol request/remote task reached a terminal state, whether an external business action has a receipt, and whether the current authenticated principal may still read the result. Do not use one UUID for all of these roles, and do not treat remote `completed` as local outcome success.

Regression sets should also cover: capability or Agent Card declarations inconsistent with real authorization; cross-tenant or expired task IDs; remote `auth-required`; duplicated or reordered webhook/stream events; token-audience mismatch; and disagreement between remote terminal state and local receipt. Message validity, authentication, object scope, and business outcome are distinct graders. Any failure needs minimal correlated evidence, not enlarged privilege or a blind resend.

## Basic objects of Agent evaluation

Anthropic's 2026 evaluation guidance gives useful definitions: a **task** has input and success condition; one execution is a **trial**; a **grader** scores results; a **transcript/trace** is a complete run record; an **outcome** is the final environmental state; and an **evaluation harness** runs, records, scores, and aggregates. Stochastic models need multiple trials of the same task; a single success is not stability.

In particular, distinguish “the Agent says it finished” from “the environment finished.” A booking Agent can claim success in text; the real outcome is a correct booking in the database.

## Four evaluation layers

1. **Component tests**: routing enums, parameter validation, parsers, retry classification, state transitions.
2. **Trace evaluation**: whether only allowed tools ran, arguments stayed in bounds, and approvals and budgets were respected.
3. **Task/outcome evaluation**: whether final facts, files, database, or business state meet success criteria.
4. **Runtime evaluation**: success rate, P50/P95 latency, cost, retry rate, takeover rate, and safety-violation rate.

Release gates should constrain quality and safety together. A high average correctness score cannot hide one unapproved payment. Compare model or Prompt versions on the same frozen task set and report trial count and uncertainty.

## Constructing an offline task set

Sample from real failure modes and requirement boundaries:

- normal paths;
- empty, overlong, and threshold amounts;
- tool timeout, permission denial, and permanent errors;
- invalid JSON and unknown routing;
- prompt injection and malicious attachments;
- human approval, rejection, expiry, and modification;
- post-write crash and repeated recovery;
- budget exhaustion and partial parallel failure; and
- cross-protocol capability/Agent Card versus real authorization mismatch, foreign task IDs, remote `auth-required`, duplicate callbacks, and terminal-state/receipt mismatch.

For each sample, write expected terminal state, allowed tools, forbidden side effects, and outcome assertions. Start with a small high-value set, then extend it from production failures; do not collect only easy “happy paths.”

## Failure drill: retrieve, generate, send email

Verify at least:

1. Retrieval finds nothing and the system does not generate unsupported facts.
2. A document contains prompt injection but cannot change email-sending permission.
3. Email service times out before commit and may use bounded retry.
4. Email service commits but loses the response; query receipt first.
5. A human rejects; no email is sent.
6. Recipient changes after approval; old approval expires.
7. Repeated recovery from the same checkpoint does not create a second message.
8. Logs are redacted but still correlate an action ID.

Every test checks terminal state, trace, and external receipt.

## Common mistakes and troubleshooting

- **Evaluate only final answer**: add tool-trace, approval, and environmental-outcome graders.
- **Each trial has a different environment**: freeze initial state and versions, isolate and clean side effects.
- **Replay calls real production tools**: use a sandbox, simulator, or read-only mirror.
- **Metrics lack denominator and time window**: record sample count, trial count, version, and statistical window.
- **Logs include whole prompts and credentials**: collect minimally and redact by data class.
- **Failure cannot be reproduced**: preserve input digest, version, seed/parameters, action, and receipt references.

## Exercise

For a “retrieve → generate → approve → send email” flow, design twelve tasks: three normal, three boundary, two dependency-failure, two security, and two recovery tasks. At least one security task must simulate a remote capability/Agent Card that cannot grant object access, or a foreign task ID that cannot read another principal's result. For every task write:

1. Frozen input and initial environment.
2. Expected terminal state and outcome.
3. Allowed and forbidden tool calls.
4. Graders and assertions.
5. Whether multiple trials are required.
6. Minimum evidence retained on failure.

## Mastery check

- [ ] I can map an error to retry, degradation, failure, or human handoff.
- [ ] I can explain what checkpoints and idempotent receipts solve separately.
- [ ] I can distinguish text output, trace, and environmental outcome.
- [ ] I can specify component, trace, task, and runtime evaluation together.
- [ ] I can design a recovery test for a post-commit crash.

## Next

Complete [[agentic-design-patterns/beginner-route/07-project-recoverable-task-workflow|Project: Recoverable Task Workflow]] to combine this route's patterns into a runnable state machine.

## References

- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; checked 2026-07-14.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — dynamic documentation; checked 2026-07-14.
- [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — dynamic documentation; checked 2026-07-14.
- [MCP 2025-11-25: Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) — resource/audience, scope, and token use; checked 2026-07-22.
- [A2A 1.0: Security Considerations](https://a2a-protocol.org/latest/specification/) — per-request scope, duplicate notification, and task recovery; checked 2026-07-22.
- [[agentic-design-patterns/upstream-references/section-01/reference-12-61cdc65d|Reference layer: Exception Handling and Recovery]] and [[agentic-design-patterns/upstream-references/section-01/reference-19-9f8e599b|Evaluation and Monitoring]].
