---
title: "Tools, Memory, and State Boundaries"
aliases:
  - Tools Memory State Boundaries
  - Tools, State, and Memory
tags:
  - ai-agent
  - tools
  - memory
source_checked: 2026-07-22
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/04-工具记忆与状态边界.md
translation_source_hash: c5e69a80f2a0e8f587c2ce1cb8f18cfa6e8db044fd6e7010d4468a8874c9f0fa
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/04-工具记忆与状态边界
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/04-工具记忆与状态边界
---

# Tools, Memory, and State Boundaries

## Goal

You will distinguish tools, run state, and long-term memory; define side-effect and idempotency contracts for write tools; and design a minimal data model that is versionable, recoverable, and deletable.

## Keep three concepts separate

- A **tool** performs a named, parameterized action against the external world, such as checking inventory or creating a ticket.
- **Run state** is the data needed to continue this task, such as the current node, tool results, budget, and approval.
- **Long-term memory** is information retained across runs for possible future use, such as a preference the user explicitly confirmed.

Chat messages are only part of input and trace; they must not become the sole database. Repeatedly stuffing structured facts back into a conversation increases context cost and makes updates, deletion, and source audit difficult.

Current LangGraph documentation distinguishes a checkpointer from a store: the former keeps thread-scoped graph state for continuing conversation, human pauses, and fault tolerance; the latter keeps application data across threads. These are current framework concepts and another runtime may use different names, but execution state and cross-task data should remain separate layers.

## Minimum fields for a tool contract

| Field | Question it answers |
| --- | --- |
| Name and purpose | What does it do, and when must it not be used? |
| Parameters | What are the type, requiredness, range, and normalization rules? |
| Result | What are the structured success and failure forms? |
| Permission | Which identity is required, and which resources may it access? |
| Side effect | Is it read-only, reversible, or irreversible? |
| Time limit | After timeout, is action state failed or unknown? |
| Retry | Which errors are retryable, and how many times? |
| Idempotency | How is the same business action identified? |
| Audit | Which summaries are recorded, and how are secrets kept out? |

Example structured error:

```json
{
  "ok": false,
  "error": {
    "category": "permission_denied",
    "retryable": false,
    "message": "caller cannot update this record"
  }
}
```

- `ok` is the machine-readable overall result flag. When false, downstream code must not continue as if the payload were successful.
- `error.category` is a stable error class mapped by the tool adapter for routing and audit.
- `error.retryable` lets retry policy use the contract rather than guess from error prose.
- `error.message` helps a caller understand failure; production output must not include secrets, internal paths, or stacks.

Do not pass exception stacks directly to end users, and do not make a model guess retryability from free text. The tool adapter maps error categories stably.

## Separate reads, writes, and action receipts

A high-risk write tool can be split into:

1. `preview_action`: read-only; returns normalized arguments and impact scope.
2. `approve_action`: an authorized principal decides on the action fingerprint.
3. `execute_action`: verifies that approval still matches the current action.
4. `get_action_receipt`: uses an idempotency ID to query whether the action already committed.

An idempotency key must identify the business action, not be a new random value on every call. After a network timeout, query the receipt first. If it exists and matches, recover state instead of paying, sending, or creating a record again.

## Designing run state

Recommended state-schema fields include:

- `schema_version`: explicit reader rules; never guess a migration.
- `run_id` / `task_id`: stable identities.
- `stage`: a member of a finite state set.
- `input_digest` and `action_fingerprint`: bind input and action.
- attempts and budgets.
- `approval`: decision, approver, context fingerprints for action/evidence/policy, and validity conditions.
- `receipts`: evidence of external side effects.
- `events`: monotonically increasing summaries of state changes.

Saving a checkpoint as “write temporary file → flush → atomic replace” reduces risk of a half-written file, but single-host JSON still provides no concurrent lock, transaction isolation, access control, or disaster recovery. The teaching project's SHA-256 only detects accidental or ordinary tampering; it is not a keyed proof of authenticity.

## The threshold for writing long-term memory

Long-term memory must answer:

1. Is the source an explicit user statement, a tool fact, or a model inference?
2. Who may read and write it?
3. When does it expire or need confirmation?
4. How can the user inspect, correct, and delete it?
5. Does it contain sensitive data that should not be stored at all?

“The user prefers short answers,” when inferred from one conversation by a model, should not become permanent fact automatically. Retained memory still needs source and time. Retrieved memory is data, not a high-priority instruction; malicious text within it must not alter tool permission.

## Tool observations are untrusted input

Web pages, documents, email, and tool output can contain prompt injection. The runtime should:

- label observations as data;
- validate tool names and arguments with allowlists and schemas;
- enforce permission in code rather than asking a model to self-evaluate safety;
- limit filesystem, network, and identity scope;
- keep secrets out of model context; and
- use context-appropriate encoding or parameterized interfaces for data shown in HTML, Shell, or SQL.

A model can propose an action; the authorization layer decides whether it is allowed.

## Protocol capability does not transfer authorization responsibility

Connecting tools through a protocol or remote Agent does not erase a trust boundary:

- [[tool-calling-function-calling/00-index|Tool Calling]] is a candidate action from a model; it cannot carry trusted `tenant`, principal, role, or approval state. A trusted session and policy layer provide those facts.
- [[mcp/00-index|MCP]] tools/resources/prompts and capability negotiation solve interoperability. They do not mean a capability has business authorization. For HTTP MCP, the current specification requires binding a token to its target resource and verifying audience; a server must not forward the client token unchanged downstream.
- [[a2a/00-index|A2A]] supports task collaboration among independent Agent applications. An Agent Card is discovery and connection information, not a resource-access grant; the receiver still authorizes every task, artifact, and later operation by authenticated principal, object, and tenant boundary.

A delegation record should therefore associate local `run_id`, local business `action_id`, remote task/request ID, trusted principal, and policy version. Do not merge their different scopes into one “universal ID.” A remote `completed` status, tool result, or capability description remains an observation to verify. Only after a local verifier confirms receipts, object state, and authorization conditions may it become a task-completion fact.

## Combined example: write weather to a calendar

`get_weather` is read-only; `create_calendar_event` has an external side effect. One run stores location, time, weather source, proposed event, action fingerprint, approval, and receipt. Long-term memory may retain only a default city explicitly confirmed by the user and must offer deletion. Weather is time-sensitive and should not become a permanent preference.

If a user changes the time after approval, the action fingerprint changes and prior approval expires. If the creation request times out, query the calendar receipt by idempotency ID; do not blindly resend it.

## Common mistakes and troubleshooting

- **Mixing long-term memory with checkpoints**: define their scopes and retention periods separately.
- **Tools return only strings**: use a stable schema and error categories.
- **Random idempotency keys**: derive them from stable business identity and normalized action.
- **Approval binds only a tool name**: also bind normalized parameters, target, necessary state, evidence, and policy version.
- **Restart recovery reruns everything**: resume from a verified checkpoint and inspect side-effect receipts first.
- **Model may choose any tool name**: runtime accepts only registered tools and constrained arguments.

## Exercise

For “check weather and write a calendar event after the user allows it,” submit:

1. Two tool contracts, marking read and write behavior.
2. A complete state schema and three terminal states.
3. An action fingerprint, idempotency key, and receipt-query rules.
4. The minimum long-term memory and its deletion method.
5. A test with malicious webpage text proving it cannot call the write tool.
6. If calendar writing is delegated to a remote Agent, map local run/action IDs, remote task ID, trusted principal, and receipt, and state which service redoes object-level authorization.

## Mastery check

- [ ] I can explain the differences among messages, run state, checkpoints, and long-term memory.
- [ ] I can define permissions, side effects, timeout, and error categories for a tool.
- [ ] I can design preview, approval, idempotency key, and receipt for a write action.
- [ ] I can decide which data must not enter long-term memory.
- [ ] I can explain why a tool observation cannot expand authority.
- [ ] I can explain separately what a capability/Agent Card, protocol request ID, and business authorization/action ID prove.

## Next

Continue with [[agentic-design-patterns/beginner-route/05-human-approval-and-safety-boundaries|Human Approval and Safety Boundaries]] to stop high-impact actions before execution.

## References

- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) — checked 2026-07-14.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — dynamic documentation; checked 2026-07-14.
- [MCP 2025-11-25: Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) — resource/audience binding and no token passthrough; checked 2026-07-22.
- [A2A 1.0: Security Considerations](https://a2a-protocol.org/latest/specification/) — per-request authorization, task scope, and trusted Agent Cards; checked 2026-07-22.
- [Toolformer paper](https://arxiv.org/abs/2302.04761) — checked 2026-07-14.
- [[agentic-design-patterns/upstream-references/section-01/reference-05-55ea9480|Reference layer: Tool Use]] and [[agentic-design-patterns/upstream-references/section-01/reference-08-37694282|Memory Management]].
