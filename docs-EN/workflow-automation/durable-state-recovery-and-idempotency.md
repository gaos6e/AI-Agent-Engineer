---
title: "Durable State, Recovery, and Idempotency"
tags: [ workflow-automation, durable-state, idempotency ]
aliases: [ Durable Workflows ]
source_checked: 2026-07-22
lang: en
translation_key: 工作流自动化/05-持久状态、恢复与幂等.md
translation_source_hash: 6d1bdf067600204d718fae68cd1726b08dc512081983792650e31acd2fbb49dd
translation_route: zh-CN/工作流自动化/05-持久状态、恢复与幂等
translation_default_route: zh-CN/工作流自动化/05-持久状态、恢复与幂等
---

# Durable State, Recovery, and Idempotency

## Goal

Understand why durable execution needs state history, leases, and idempotency records, and analyse the crash window where a side effect commits before workflow state does.

## What durable execution solves

An ordinary function loses local variables when its process crashes. A durable workflow writes enough execution facts to reliable storage for a new worker to resume:

- workflow definition and input versions;
- per-step state, attempt, result reference, and error classification;
- timers, pending approvals, and deadlines;
- registered compensation actions;
- state version, lease, and run events; and
- idempotency records corresponding to external side effects.

Product implementations differ. Temporal documentation describes recovery of a Workflow Execution through event history and replay, and requires deterministic workflow code. That is a **Temporal product contract**. Other systems can save explicit state snapshots or use database state machines; do not treat replayable code as every orchestrator's specification requirement.

## A state machine, not booleans

A step needs at least:

`pending -> running -> succeeded`

It can also enter `waiting_approval`, `retry_scheduled`, `failed`, `compensating`, `compensated`, `cancelled`, and `manual_intervention`. A single `done: true/false` cannot express “committed, outcome unknown” or “main action succeeded, compensation failed.”

Use a transaction or compare-and-set for transitions: only a worker holding a valid lease and observing expected `state_version` may commit. Lease expiry allows takeover, but an old worker's late result must be rejected or merged through an idempotency record.

### Commit fences after lease takeover

A lease says only who may try work now; it cannot make already-issued old requests disappear. Following the terminology in [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency#leases-and-concurrent-recovery|Agent Core]], durable state needs at least `owner_worker`, `lease_version`, `expires_at`, and `state_version`. Every state commit performs atomic compare-and-set on `(expected_state_version, expected_lease_version)`: a late write from the old worker fails rather than overwriting the new owner.

External writes need a commit fence too (often called a fencing token). If downstream supports conditional update, resource revision, or monotonic operation token, send current `lease_version`/target revision and reject stale versions. If it cannot, a local lease is not a cross-system mutex: query the authoritative receipt by stable idempotency key before choosing replay. This separates three gates: **runtime ownership**, **state commit**, and **external side effect**.

The offline project simulates state-machine and idempotency records only inside one process. It does not implement durable leases or atomic compare-and-set, so passing tests do not prove race safety between two recovery workers. Temporal event history/replay and versioning are product mechanisms of one durable runtime; they do not mean arbitrary external systems naturally support fencing.

## The most dangerous crash window

Consider inventory reservation:

1. A worker calls the inventory system.
2. The inventory system commits successfully.
3. The worker crashes before writing `succeeded`.

Recovery that reads only workflow state believes the step did not complete. The solution is not a claim of distributed exactly-once:

- generate a stable idempotency key before the call;
- make downstream store intent fingerprint and result by that key;
- query or replay the same key on recovery;
- return the old result for same key/same intent and conflict for same key/different intent; then
- commit workflow step state.

This provides “no duplicate logical side effect within the boundary of shared, reliable idempotency storage.” A record held only in worker memory vanishes on restart.

## Designing an idempotency key

A practical key binds:

`business instance + step + resource + intent version`

For example, `order-42:charge:payment-v1`. Store a canonical parameter hash too. If the same key later requests a different amount, reject a conflict; do not return the old result as apparent success.

Use separate key domains:

- trigger deduplication: `source + event_id`;
- step side effect: instance + step + resource + version;
- compensation: instance + original step + compensation version; and
- notification: instance + notification type + recipient-target version.

Never use a random request ID per retry: downstream will see each retry as new intent.

## Recovery process

1. Validate checkpoint format, integrity, and definition fingerprint.
2. Confirm current code can read the definition/schema version.
3. Reacquire instance lease and state version.
4. Do not rerun succeeded steps; keep wait nodes waiting.
5. Query idempotency results for `running/unknown` side effects.
6. Reschedule only incomplete nodes whose dependencies are met.
7. Reject late state commits from old workers.

A checkpoint integrity hash detects accidental corruption, not authentication. An attacker able to change both data and an unkeyed hash can forge it. Production requires access control, encryption, signature/MAC, or protected database audit.

## Deterministic replay cautions

Event-history replay runtimes generally forbid workflow code from reading current time, random values, filesystem, or network directly, because the same history could then issue different commands. Use the runtime's deterministic time/random API; place network, LLM, and tool calls in activity nodes and record their results in history.

Even outside a replay runtime, recovery should not depend on implicit environment. Time zone, default ordering, current model alias, and unpinned configuration can make an old instance take a new path.

## Exercise

Draw two workers racing for one step: lease claim, downstream call, lease expiry, second-worker takeover, and old-worker late arrival. Design:

1. Which state commit succeeds?
2. How do both downstream calls share an idempotency key?
3. How does same key/different amount fail?
4. Do incompatible checkpoint definition versions migrate or go to human handling?

## Self-check

1. Why cannot a lease alone prevent duplicate external side effects?
2. Which system boundaries must an exactly-once claim name?
3. Why store a parameter hash with an idempotency key?
4. Why can a replayable workflow not call an LLM directly?

## Next

Continue with [[workflow-automation/compensation-approvals-and-human-handling|Compensation, approvals, and human handling]].

## References

- [Temporal Workflow Execution](https://docs.temporal.io/workflow-execution) (event-history/replay product mechanism)
- [Temporal Python Workflow Versioning](https://docs.temporal.io/develop/python/workflows/versioning)
- [RFC 9110: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [Microsoft: Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
