---
title: "Message Protocols and Shared State"
tags:
  - multi-agent
  - messaging
  - shared-state
aliases:
  - Agent Message Protocol
  - Multi-Agent Shared State
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/02-工程与质量/04-消息协议与共享状态.md
translation_source_hash: dd76de7a3b7d01aaa5ffd9f1f845777f77f478f1ecd10dec6a019baba28a85ac
translation_route: zh-CN/多Agent协作/02-工程与质量/04-消息协议与共享状态
translation_default_route: zh-CN/多Agent协作/02-工程与质量/04-消息协议与共享状态
---

# Message Protocols and Shared State

## Goal

Separate messages, events, and authoritative state. Design collaboration data that can be correlated, deduplicated, and versioned instead of guessing progress from chat text.

## Do not mix three data types

- **Message** — a request or response from one participant to another.
- **Event** — a fact that has already happened, such as `task_started` or `tool_failed`.
- **State** — the current authoritative view derived from accepted events, such as a task being `running` with three budget units remaining.

A chat transcript is not a reliable state database. Messages can be duplicated, reordered, or lost, and natural language cannot provide concurrency control. Write key state to structured storage that the runtime updates; agents propose changes only.

## Message envelope

```json
{
  "message_id": "M-104",
  "trace_id": "R-7",
  "task_id": "T-20",
  "sender": "manager",
  "recipient": "researcher",
  "type": "task_request",
  "schema_version": "1",
  "created_at": "2026-07-13T04:00:00Z",
  "idempotency_key": "R-7:T-20:attempt-1",
  "payload_digest": "sha256:...",
  "payload": {"goal": "collect evidence"},
  "evidence_refs": []
}
```

- `message_id` uniquely identifies one message: has this message already been seen?
- `trace_id` joins the entire user request.
- `task_id` joins multiple attempts of one subtask.
- `schema_version` supports protocol evolution.
- `idempotency_key` identifies the same logical intent. `payload_digest` binds a payload or artifact under a **declared serialization algorithm, version, and numeric rules**. A duplicate delivery is ignorable only when both values match.
- `evidence_refs` point to primary evidence so repeated summarization does not destroy verifiability.

### A duplicate is not a conflict

A consumer must not silently keep the first result merely because a key repeats. Store `(task_id, idempotency_key, payload_digest, digest_scheme_version)`:

- Same key and same digest: record `duplicate` and reuse the accepted result.
- Same key and different digest: do not use last-write-wins. Freeze the task as `needs_review`, preserve both summaries or protected evidence references, state version, and arrival order, and clearly mark the external `result` as untrusted.
- A new key for a terminal task: record it as a late result without regressing state. If it would alter a validated business side effect, send it through reconciliation.

`needs_review` is a safety extension of this course runtime, not a claim that A2A defines the state. A2A only says that `Send Message` **can** use `messageId` to identify duplicates and defines interoperable task states such as `WORKING`, `COMPLETED`, `FAILED`, `INPUT_REQUIRED`, and `AUTH_REQUIRED`. An internal coordinator still needs its own result-conflict and human-reconciliation contract. The course simulator uses sorted-key Python JSON serialization for a local teaching digest; it is **not** a cross-language canonical-JSON standard. A cross-process implementation must pin and test its own digest scheme and version. See [A2A Specification](https://a2a-protocol.org/latest/specification/) (accessed 2026-07-22).

## Source of truth

Assign one authoritative location to each fact:

| Fact | Authoritative source | Non-authoritative copy |
| --- | --- | --- |
| Task state | Scheduler state store | Agent summary in conversation |
| Budget usage | Billing or runtime record | Agent self-report |
| File version | Repository hash or version | “Saved” message |
| User approval | Approval record | Model inference |

Several agents can read. Writes must be constrained by role permission and a state machine. For concurrent writes, use an expected version (compare-and-swap): a write succeeds only if the current version is still the version read; otherwise reread and merge.

## A state machine is safer than free text

A minimal task state can be:

```text
pending -> ready -> running -> succeeded
                       |-> retry_wait -> ready
                       |-> failed
                       |-> denied
                       |-> waiting_human
any state -> needs_review: one logical intent has conflicting result or receipt
needs_review -> ready or canceled: an authorized person decides from retained evidence
any nonterminal state -> canceled
```

Allow only a transition allowlist. For example, a late `failed` message must not overwrite `succeeded`. Yet when one idempotent intent is proven to have incompatible results, escalate to `needs_review` instead of hiding the contradiction. Record old state, new state, reason, executor, time, and `state_version` for each transition. When several workers recover the same run, use commit conditions consistent with the `lease_version` and `state_version` checks in [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency#lease-and-concurrent-recovery|Agent Core]].

## A2A and MCP levels

As of 2026-07-22, A2A's specification page lists 1.0.0 as its latest released version. It defines interoperable concepts including Agent Card, Task, Message, Part, and Artifact, and requires negotiation of `Major.Minor` protocol versions without using patch versions for compatibility negotiation. This fact will change. A2A targets discovery and task collaboration between independent agents; MCP mainly connects a model or agent to tools, resources, and prompts. Its data model can inform learning, but no protocol is a required dependency for every internal collaboration system.

## Failures and debugging

- **Repeated execution** — check for an idempotency key, a versioned payload or receipt digest scheme, a consumer deduplication table, and a side-effect commit record.
- **Same key, conflicting result was swallowed** — check whether the key was treated as a full intent; freeze and reconcile rather than retaining the first or last prose answer.
- **State regression** — verify that late events carry a version and that the state machine rejects illegal transitions.
- **Lost evidence** — check whether messages paraphrase conclusions without `evidence_refs`.
- **Sensitive-information spread** — minimize payload per recipient and redact log fields.

## Exercise and self-check

Design a message envelope for a researcher sending a fact table to a writer, and state where the fact table itself lives. Does a delivery acknowledgment mean the task completed? When replaying a message, how will you prove that publication cannot run twice?

## Next step

Continue with [[multi-agent-collaboration/engineering-and-quality/05-conflicts-synchronization-and-failure-recovery|Conflicts, Synchronization, and Failure Recovery]].

## References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification) and its [official changelog](https://github.com/a2aproject/A2A/blob/main/CHANGELOG.md) — accessed 2026-07-22.
- [OpenAI Agents SDK: Running agents](https://openai.github.io/openai-agents-python/running_agents/) — accessed 2026-07-22.
