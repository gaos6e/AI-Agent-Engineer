---
title: "Long-Running Agent Checkpoints, Recovery, and Idempotency"
tags:
  - agent-core
  - checkpoint
  - recovery
  - idempotency
aliases:
  - Long-Running Agent Recovery
  - Agent Durable Execution
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: Agent 核心/05-长任务检查点、恢复与幂等.md
translation_source_hash: 53d34a8aede4c24f4ccf280d0cbf77b9d25a8f468f1f9a32893299ef236805ec
translation_route: zh-CN/Agent-核心/05-长任务检查点、恢复与幂等
translation_default_route: zh-CN/Agent-核心/05-长任务检查点、恢复与幂等
---

# Long-Running Agent Checkpoints, Recovery, and Idempotency

## Objective

After this lesson, you should be able to:

- Identify the crash window where an external action has committed but state has not yet been recorded.
- Design verifiable, migratable checkpoints and a recovery protocol.
- Avoid duplicate side effects with an idempotency key, intent digest, and receipt.
- Distinguish retry, resume, replay, compensation, and the illusion of exactly once.

## Why long tasks always interrupt

Long-running work crosses:

- Model/API timeouts and rate limits.
- Worker restarts, deployments, and machine failures.
- Human approval waits.
- Temporary third-party-service unavailability.
- Context compression or provider-session expiry.
- User cancellation and budget pauses.

Therefore, “the process stays alive and the object remains in memory” is not an acceptable assumption. The aim of durable execution is that, after control state is persisted, a new worker can continue from a known point and determine whether an external action actually occurred.

## What a checkpoint stores

Save after model turns, tool side effects, approval boundaries, and important subgoals. A checkpoint should include:

- State or checkpoint schema version.
- Run, tenant/user, goal, and phase.
- State version and last event sequence.
- Plan summary plus completed and pending work.
- Full pending-action parameters or a safe reference, fingerprint, and idempotency key.
- Approval decision, scope, version, and expiry.
- Completed action IDs and external receipts.
- Used and remaining budget plus deadline.
- Observation provenance, hash, and controlled reference.
- Runner, tool, model, and schema versions.
- Next eligible time and retry count.

Do not depend on serializing a provider’s complete internal object. Rebuild context from state, events, and external content.

## Atomicity and integrity

Write checkpoints atomically: temporary write → fsync or transaction → rename or commit. A partial JSON file must never be treated as newest state. During recovery:

1. Parse strictly and reject duplicate keys and non-finite numbers.
2. Validate envelope, fields, and schema version.
3. Validate a hash or signature.
4. Check business invariants.
5. Acquire the run lease.
6. Only then advance the run.

Business invariants require more than field types. Event sequence and state version should be continuous. A waiting_approval state must contain a frozen pending action and the observation that justified it. A nonwaiting state must not retain a still-executable pending action. A completed state must match an explicit completion-evidence path: a completed write needs both action and external receipt, while an already-satisfied goal needs current external read evidence. Otherwise a state that parses and has a matching hash can still skip read, approval, or verification.

An ordinary SHA-256 detects accidental corruption only. An attacker who can alter a payload can recompute its hash. Defend against adversarial tampering with protected storage, MACs or signatures, access control, and audit.

## Four crash windows

| Crash location | External side effect | State record | Recovery strategy |
| --- | --- | --- | --- |
| Before action | None | May contain a pending intent | Safe retry |
| Request sent, result unknown | Unknown | Pending | Use idempotency key or query state; do not retry blindly |
| External commit, receipt not in checkpoint | Present | Still appears pending | Query receipt or target state and recognize completion |
| Receipt and state durably recorded | Present and recorded | Completed action | Continue from the next step |

The third row is the crash window simulated by this course project.

## Exactly once is usually an illusion across systems

A local database transaction cannot atomically cover an arbitrary third-party API. A realistic objective is:

- At-least-once delivery plus an idempotent effect.
- A stable idempotency key for every side effect.
- Server-side persistence of key, intent digest, and result or receipt.
- Replaying the same key with the same intent returns the cached result.
- The same key with a different intent conflicts.
- Unknown results are queried and reconciled first.

~~~text
idempotency_key = run_id + logical_action_id + normalized_target + contract_version
intent_digest  = hash(tool + normalized arguments + target)
~~~

Do not use a fresh random retry ID. It makes each retry look like a new action.

## Intent and receipt

Persist intent before execution:

~~~jsonc
{ // Frozen intent for an external write.
  "action_id": "close-current-ticket", // Stable runtime action identifier; recovery must not replace it.
  "tool": "close_ticket", // Controlled write tool, still subject to allowlist and authorization.
  "target": "ticket-7", // Exact target; untrusted observation cannot change it at execution time.
  "idempotency_key": "run-42:ticket-7:close:v1", // Reuse for retries of this intent so the tool can deduplicate.
  "intent_digest": "sha256:..." // Digest of canonical intent; detects same-key, different-intent reuse.
}
~~~

> [!note] JSONC teaching notation
> Slash comments are for reading only. Remove them before sending the object to a strict JSON API or file.

After completion, record:

~~~jsonc
{ // Minimum receipt from the tool side for crash recovery.
  "idempotency_key": "run-42:ticket-7:close:v1", // Must echo the original key to link the intent safely.
  "intent_digest": "sha256:...", // Must equal the frozen intent digest; prevents receipt reuse from another write.
  "receipt_id": "receipt-123", // Auditable receipt identifier in the external system.
  "target_version": 9, // Target version after write, useful for concurrent-update checks.
  "status": "closed" // Final state confirmed by the external system, not model prose.
}
~~~

Recovery may reuse a receipt only when the digest matches. The same key pointing to ticket-8 is a severe conflict, not something to overwrite “in order to continue.”

If a write may have been sent but an adapter returns malformed data, the connection closes before response, or a receipt cannot be proven, the result is **unknown**, not “failed and safe to resend.” Persist action, target, idempotency key, and error class, then query or reconcile using the same key; never replay under a new key. The example labels this tool_result_uncertain and fails closed. A real system normally needs a controlled human reconciliation and recovery path as well.

## Retry is not resume

- **Retry**: Attempt one failed and explicitly retryable call again.
- **Resume**: Continue an entire run from persistent state.
- **Replay**: Rebuild deterministic state from event history. External I/O must be isolated so replay cannot produce a side effect again.
- **Compensation**: Perform a semantically opposite action; it is not a database rollback.

Durable-workflow platforms such as Temporal supply orchestration through persistent events and deterministic replay. You still need to understand activity timeout, retry, and idempotency. A framework cannot automatically implement business exactly once for a third-party API.

## Retry policy

Retry only explicitly transient cases, such as rate limits, short network outages, or service 5xx. Normally do not retry:

- Schema or parameter errors.
- Permission or business rejection.
- User rejection.
- Idempotency conflict.
- Unsupported tool or version.

A retry policy needs:

- Maximum attempts per error class.
- Exponential backoff plus jitter for real networks.
- Per-call and total deadlines.
- Respect for Retry-After.
- The same idempotency key.
- Observable attempts and final stop reason.

An Agent’s choice to “try another parameter” creates a new intent and must not reuse the old idempotency key.

## Lease and concurrent recovery

Two workers may both see a recoverable run. Use an expiring lease:

~~~text
run_id, owner_worker, lease_version, expires_at
~~~

After acquiring a lease, still use optimistic state-version locking. Lease expiry permits takeover, but an old worker must verify that it still has a valid lease before every state write or external action. A single running boolean cannot handle worker death.

## Outbox and compensation

### Transactional outbox

When the state database and message queue do not share one transaction:

1. Write state and an outbox event in the state transaction.
2. Send asynchronously from a relay.
3. Process idempotently in the consumer.
4. Mark delivered.

This prevents committing state while losing the event.

### Saga and compensation

For several non-atomic steps:

~~~text
reserve inventory → charge payment → create shipment
~~~

If shipment fails, compensation might refund payment and release inventory. Compensation can fail too, so it needs independent state, idempotency, and human reconciliation. Do not promise users a traditional transactional full rollback.

## Version migration

Long-running work can cross deployments. A checkpoint records:

- State or checkpoint schema.
- Tool schema or contract.
- Policy or runner.
- Model or provider if it affects reproducibility.
- Capability or authorization policy.

New code must:

1. Migrate an old checkpoint explicitly.
2. Or reject safely and provide human recovery.
3. Never interpret a missing field as approved=true by default.
4. Test upgrade and rollback with historical checkpoint fixtures.

## How this course project demonstrates the protocol

The [[agent-core/08-integrated-agent-project-and-self-test|Integrated Agent Project]]:

1. Saves a hashed checkpoint in waiting_approval.
2. Binds approval to action fingerprint, state version, target scope, and expiry.
3. Commits the close operation and keeps an in-memory receipt in the tool host.
4. Simulates a crash before state is written back.
5. Restores from the old checkpoint.
6. Queries the receipt with the same idempotency key and confirms intent equality.
7. Does not close again; records evidence and completes.

Limitation: the example tool store is still in the same Python process, simulating an external system that survives the worker. A real receipt must live in independent reliable storage. In one uninterrupted run, the sample counts lookup, receipt query, and write against its tool budget. If a process crashes before a new counter checkpoint is persisted, an old checkpoint still cannot know about the in-flight call. Production must persist attempt and intent before external I/O and combine provider-side limits, audit, and reconciliation; an in-memory count cannot prove cross-crash quotas.

## Exercise

Design a state machine for “send 100 notifications in batches.” The process crashes after notification 20 succeeds but before its checkpoint is written:

- How is the idempotency key formed?
- Where is the receipt stored?
- What is queried first when result 20 is unknown?
- When may notification 21 start?
- If the downstream system lacks idempotency support, how do intent, query, and human reconciliation work?
- How do you report cancellation after notifications 19 or 20 were sent?

## Self-check

1. Why is storing only current_index=20 insufficient?
2. Why must the same idempotency key with different parameters conflict?
3. Why cannot a SHA-256 checkpoint prevent malicious tampering?
4. What are the differences among retry, resume, and replay?
5. What races do a lease and state version solve separately?

You have mastered this lesson when you can draw all four crash windows and give recovery evidence for each.

## Next

Continue to [[agent-core/06-human-in-the-loop-and-control|Human-in-the-Loop and Control]] so a long human wait is also durable state.

## References

The following are first-party engineering sources, obtained or rechecked on 2026-07-21.

- [Temporal: Workflow concepts](https://docs.temporal.io/workflows)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
