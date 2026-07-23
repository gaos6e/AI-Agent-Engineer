---
title: "Idempotency, Timeouts, and Observability"
tags:
  - ai-agent-engineer
  - tool-calling
  - idempotency
aliases:
  - Tool Calling Reliability
  - Tool Reliability
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: "Tool Calling（含 Function Calling）/06-幂等、超时与可观测性.md"
translation_source_hash: 3e650fbea9e53ac306461c1a2174f1dd3406966ee26c446fd6742070adf618a6
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/06-幂等、超时与可观测性
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/06-幂等、超时与可观测性
---

# Idempotency, Timeouts, and Observability

## Goals

- Prevent network retries, process recovery, and repeated model calls from creating duplicate side effects.
- Handle the uncertain state where a downstream system may have succeeded but its response was lost.
- Distinguish call, operation, approval, and idempotency identifiers.
- Build auditable traces, metrics, and failure recovery.

## The intuition behind idempotency

An idempotent operation has the same expected business effect whether it runs once or many times. RFC 9110 defines idempotent HTTP method semantics, but a business tool cannot rely only on its HTTP method:

- 'GET order' is usually naturally idempotent.
- 'POST create_refund' can create duplicates.
- 'send_email' sends another email even if the request is identical.
- 'set_status("closed")' can be idempotent while a notification it triggers is not.

Design for the business effect.

## Stable idempotency key and request digest

A write operation accepts an idempotency key created by the client or orchestrator. The service persists:

~~~text
idempotency_key
tenant / subject / action
canonical_argument_digest
status: in_progress | succeeded | failed
result reference
created_at / expires_at
~~~

Rules:

- define the key namespace by tenant, subject/service principal, and action/tool first; another tenant must not reserve a global key with the same string;
- same key + same request digest returns the original state/result and does not execute again;
- same key + different digest produces 'IDEMPOTENCY_CONFLICT';
- no key record atomically creates 'in_progress', then executes;
- if the result is too large, store a reference rather than copying all sensitive data;
- cache/record data must persist across processes; memory is suitable only for teaching.

The [[tool-calling-function-calling/07-tool-calling-evaluation-and-offline-project|Tool Result v2 dispatcher]] demonstrates only **sequential retries** within one runtime. Its in-memory mapping has no atomic 'in_progress' reservation, database unique constraint, or cross-connection recovery evidence. The [[tool-calling-function-calling/08-project-sqlite-persistent-idempotency-and-outbox-recovery|SQLite persistence project]] adds 'BEGIN IMMEDIATE', unique constraints, an operation ledger, transactional outbox, leases, receipt reconciliation, and multi-connection contention tests without changing v2 digest/call-binding semantics. It proves local constraints and recovery flow, not distributed exactly-once delivery.

Example digest:

$$
d_{\text{request}} = H(
tenant,\ subject,\ tool,\ canonical(arguments),
inputRev,\ outputRev,\ effectRev
)
$$

Canonical JSON must lock key order, Unicode, and number representation. The business request digest uses complete 64-character SHA-256 and excludes the temporary call ID and idempotency key: the first is provider correlation and the second is retry/execution identity, so neither should change the judgment of “same business intent.” A changed output/effect revision must produce a new digest, so an old result cannot be used as a cache for a new contract. The idempotency key must still enter a separate call binding so the same package cannot be moved to a call context under another key. For results that reached a downstream system, the call binding must also cover downstream request ID, receipt ID, and opaque 'status_ref'; otherwise an attacker could replace recovery evidence while retaining the request/result digests.

## Why “exactly once” is difficult

Scenario:

1. The downstream system creates a refund successfully.
2. The dispatcher crashes before storing the result.
3. The client sees only a timeout.
4. A retry can create another refund.

Common strategies:

- the downstream system accepts the same idempotency key itself;
- write business state and the outbox in one transaction;
- persist intent/'in_progress' before execution;
- query downstream operation status during recovery;
- use unique constraints to prevent duplication;
- escalate indeterminate states rather than retrying blindly.

A request timeout alone cannot prove that a side effect did not happen.

## A timeout is not one error code

Retry policy must carry evidence of how far execution got, not only an exception name:

| State | Known fact | Default action |
| --- | --- | --- |
| 'TIMEOUT_BEFORE_EXECUTE' | Deadline expired before handler/downstream submission and no side effect is proven | Controlled retry is possible after checking remaining overall deadline |
| 'OUTCOME_UNKNOWN' | Downstream may have committed, but a response or local write was lost | Use the dispatcher's opaque 'status_ref' for an explicit status query; use human review without evidence |
| Reconciled success | The receipt's principal, tool, request digest, and result match | Backfill the local record and return the original result; do not execute again |
| Reconciliation conflict | The same key has a different request digest or downstream state drift | Stop and escalate; do not selectively trust one result |

Therefore a single 'retryable=true/false' cannot express the recovery protocol. This project uses a finite 'recovery' value instead: 'retry_after' is only for known-not-started transient failures, 'query_status' for an unknown outcome, and 'human_review' for conflict. Production traces should also record timeout stage, downstream request/receipt ID, reconciliation source, and final resolution.

Both the v2 and SQLite projects require an explicit 'query_operation_status(status_ref, expected_request_sha256)' before a caller can backfill an original result when the receipt is queryable. When the receipt is not yet available, the query still returns unknown until external reconciliation or human disposition. Calling the original write tool again keeps returning unknown: it does not reconcile silently and certainly does not execute again. The status query rechecks tenant/resource authorization, request digest, effect/producer revision, receipt, and strict-format 'status_ref', and binds provider call identity to the 'query_status' purpose so it cannot be reused for a new dispatch intent. Lesson 07 demonstrates the control flow with in-memory markers; lesson 08 persists ledger/outbox/receipt state in SQLite and tests restart and multi-connection semantics.

If a write handler raises or returns data that cannot pass the output contract, the host cannot conclude that no side effect occurred. The v2 example marks that idempotency scope unknown, returns a recovery reference, and blocks dispatch replay; only external evidence can resolve it to success, failure, or human disposition. An exception from a read-only handler can safely become a tool error because its example contract explicitly has no write side effect.

## Call ID, operation ID, and key

| Identifier | Stable across model retries? | Primary purpose |
| --- | --- | --- |
| Call ID | Usually not guaranteed | Correlate one call/result |
| Operation ID | Should be stable | Trace the whole task/workflow |
| Idempotency key | Stable for the same business intent | Suppress duplicate side effects |
| Approval ID/digest | Binds the exact action | Human authorization and audit |
| Downstream request ID | Generated downstream | Dependency troubleshooting |

Do not make one ID carry every responsibility.

## Deadlines and retries

Budget layers:

- connection, read, and single-attempt timeouts;
- a single-tool deadline;
- a single-model-turn deadline;
- the overall operation deadline;
- approval-wait expiry.

Retry rules:

- retry only errors classified as transient;
- use exponential backoff and jitter;
- obey 'Retry-After';
- check remaining overall deadline;
- query idempotency state before a write;
- limit attempts and concurrency;
- circuit-break persistent failing dependencies;
- include the retry budget itself in metrics.

Argument errors, authorization denial, invalid approval, and idempotency conflict are not retried automatically by default.

## Ordering approval and idempotency

First write:

~~~text
schema/auth → idempotency conflict/local-record/uncertain check
            → approval binding for new execution → execute → persist result

OUTCOME_UNKNOWN → explicit query_operation_status(status_ref)
                → auth + request/effect/source binding + receipt check
~~~

A same-key/same-digest retry after success can return the cached result after confirming that the current principal may still read it. It neither creates another side effect nor replays one-time approval. If permission has been revoked, the cache cannot leak data just because it exists. If the record remains uncertain, it can only reconcile or escalate; it cannot be treated as first execution and bypass approval again.

## Observability

### Trace fields

- operation ID, provider response ID, and call ID;
- tool/schema/adapter/handler revisions;
- redacted identifiers for tenant/subject;
- idempotency-key hash and request digest;
- approval ID/policy revision;
- start/end, queue, attempt, and deadline;
- result/error code, outcome, delivery, and recovery;
- request/result/call-binding digests and validation-failure category;
- downstream request ID, receipt ID, and opaque status reference;
- argument digest and data classification;
- model turn, tokens/cost, and terminal reason.

Do not record secrets, authentication headers, complete sensitive arguments, or tool results whose necessity has not been assessed.

### Metrics

- tool-selection and argument conformance;
- authorization denied, approval required/expired;
- idempotency hit/conflict;
- duplicate side effect (should be 0);
- timeout stage, outcome unknown, receipt reconciliation, rate limit, retry exhausted;
- p50/p95/p99;
- partial success/compensation;
- per-tool success, cost, and task completion.

An average hides the tail. Slice by tool, tenant, risk, and version.

## Practice

Design persistent tables and recovery flow for 'create_refund', covering:

1. first success;
2. same key, same arguments, retry;
3. same key, different amount;
4. downstream success followed by a crash before the result is stored;
5. approval expiry;
6. user permission revoked before retry;
7. downstream 429 with 'Retry-After'.

For each step, write the state transition, whether it can retry, and the user-visible state.

Then run [[tool-calling-function-calling/08-project-sqlite-persistent-idempotency-and-outbox-recovery|SQLite persistence, idempotency, and outbox recovery]] and compare your paper design with its atomic intent/outbox, unique scope, lease expiry, downstream receipt, and explicit reconciliation.

## Common mistakes

- Treating an in-memory dictionary as production idempotency storage.
- Failing to compare argument digests for the same key.
- Including a temporary call ID in the digest.
- Sending a write request again directly after timeout.
- Monitoring only success rate, not duplicate suppression and conflict.
- Skipping current authorization because a cache was hit.
- Logging complete tool arguments and credentials.

## Self-check

1. Why cannot an idempotency key be just a call ID?
2. How should the same key with different arguments be handled?
3. Why query status first after a timeout?
4. Which failures cannot an in-memory cache cover?
5. Which trace fields prove that a retry did not cause a second side effect?

Next: [[tool-calling-function-calling/07-tool-calling-evaluation-and-offline-project|Tool-calling evaluation and offline project]].

## References

- [RFC 9110: HTTP Semantics — Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [OpenAI API: Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [SQLite: Transaction](https://www.sqlite.org/lang_transaction.html)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite: UPSERT](https://www.sqlite.org/lang_upsert.html)
- [Stripe API: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [AWS ECS: Ensuring idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)

Sources accessed: 2026-07-21. Downstream idempotency headers, retention periods, and retry rules must follow the official documentation for the relevant service.
