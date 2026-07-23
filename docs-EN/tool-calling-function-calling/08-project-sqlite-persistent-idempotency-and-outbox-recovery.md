---
title: "Project: SQLite Persistent Idempotency and Outbox Recovery"
tags:
  - ai-agent-engineer
  - tool-calling
  - sqlite
  - idempotency
  - outbox
aliases:
  - Tool Calling SQLite Persistence Project
  - Persistent Tool Runtime
source_checked: 2026-07-21
source_baseline: "SQLite Transaction, WAL, UPSERT, and STRICT Tables; Python
  3.11 sqlite3/json documentation; and Stripe/AWS idempotency contracts, checked
  through 2026-07-21"
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: "Tool Calling（含 Function Calling）/08-项目-SQLite持久化幂等与Outbox恢复.md"
translation_source_hash: a9d288548b3d5dfbfbea62dfd9eb4a542ebf6714cc3f673f1fb3919cca4e2706
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/08-项目-SQLite持久化幂等与Outbox恢复
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/08-项目-SQLite持久化幂等与Outbox恢复
---

# Project: SQLite Persistent Idempotency and Outbox Recovery

## Project position

The [[tool-calling-function-calling/07-tool-calling-evaluation-and-offline-project|Tool Result v2 offline project]] already establishes proposal/context separation, input/output contracts, authorization, approval, status queries, dual projections, and triple digest binding, but it deliberately uses an in-memory map to teach sequential semantics. This project is its **Layer B persistence adapter**: it does not rewrite v2 'request_sha256' or 'call_binding_sha256', but uses SQLite to make idempotency records, an operation ledger, outbox, leases, and receipt reconciliation observable across connections and process restarts.

> [!important] This project does not claim exactly once
> SQLite unique constraints govern only the local ledger, and handling an expired lease can redeliver. A real downstream system must itself support idempotent execution under the same key or provide a bindable status query. The project implements **at-least-once-compatible building blocks**: durable intent/outbox, duplicate suppression, reclaimable leases, and receipt reconciliation. It has no scheduler that continually enumerates pending or expired events, so it does not prove delivery liveness. Only when an external worker keeps polling/retrying and alerts plus human recovery hold under explicit failure assumptions can a system claim at-least-once delivery. It still is not one atomic “exactly once” transaction across database, network, and business service.

## Learning goals

After completing the project, you should be able to:

- explain why a business request digest excludes an idempotency key while call binding must include it;
- atomically reserve '(tenant, subject, tool, key)' with 'BEGIN IMMEDIATE' and a unique constraint;
- identify a same-key/same-intent replay versus a same-key/different-intent conflict;
- write operation intent and an outbox event in one local transaction;
- use an expiring lease when a worker crashes after a claim;
- retain 'OUTCOME_UNKNOWN' when a downstream system committed but a local receipt was not stored;
- recheck business state on intent acceptance and before worker commit to avoid approval-time TOCTOU;
- reload claims through the same current-principal resolver before reservation, replay, and worker commit instead of persisting creation-time roles;
- redo current authorization and reconcile a receipt only through an independent, purpose-bound explicit status query;
- distinguish local uniqueness from distributed exactly once in multi-connection contention tests.

## Full pipeline and transaction boundaries

~~~mermaid
flowchart TD
    C["Tool Result v2 call<br/>principal + proposal + host context"] --> V["v2 schema / authorization / approval<br/>request digest"]
    V --> T1["BEGIN IMMEDIATE"]
    subgraph LocalTx["SQLite local transaction A"]
        T1 --> U["UNIQUE idempotency scope<br/>operation ledger"]
        U --> O["pending outbox"]
    end
    O --> W["worker claim + lease<br/>authorization + business-state recheck before execution"]
    W --> D["downstream idempotent commit<br/>offline receipt stand-in"]
    D --> Q{"local receipt stored?"}
    Q -->|"no: response lost/crash"| X["OUTCOME_UNKNOWN<br/>do not replay dispatch"]
    X --> S["explicit status query<br/>current-authorization recheck"]
    S --> T2["receipt binding + output-v2 validation"]
    Q -->|"yes"| T2
    subgraph ReconcileTx["SQLite local transaction C"]
        T2 --> R["local receipt"]
        R --> G["operation succeeded"]
        G --> E["outbox delivered"]
    end
    E --> P["Tool Result v2 package<br/>fresh / receipt_reconciled / local_replay"]
~~~

There are three commit points that cannot be hand-waved away:

| Commit point | Durable fact | Safe interpretation after a crash |
| --- | --- | --- |
| A: intent + outbox | The system accepted one pending intent | It is not business success; query status or let an external scheduler enumerate and send it to a worker |
| B: downstream receipt | A side effect may have occurred | Local state cannot guess success or failure; it must remain unknown |
| C: local receipt + ledger + outbox | Local, recomputable success evidence exists | Later same-intent calls can replay, but current resource authorization is still rechecked before return |

## Why 'BEGIN IMMEDIATE'

SQLite documentation explains that several read transactions may coexist while only one write transaction exists. 'BEGIN IMMEDIATE' acquires the write transaction at the beginning rather than reading first and upgrading while writing. The project therefore does this in one transaction:

~~~sql
BEGIN IMMEDIATE; -- Acquire SQLite's write transaction immediately so two workers cannot reserve the same idempotency key.

INSERT INTO operations (...) -- Record operation intent after schema/authorization/approval gates.
VALUES (...) -- Values must include tenant, subject, tool, argument digest, and contract revisions.
ON CONFLICT (tenant_id, subject_id, tool_name, idempotency_key) -- Detect replay under the caller's and tool's key scope.
DO NOTHING; -- Do not create another side effect for an existing row; compare the digest afterward rather than treating it as success.

-- Recompute and compare request digest and contract revisions for an existing row to prevent substitution under the same key.
-- Write an outbox event for a new intent in the same transaction so operation record and pending delivery remain consistent.
COMMIT; -- Commit only after every database write succeeds; exceptions should roll back the transaction.
~~~

'ON CONFLICT DO NOTHING' does not mean “a conflict is success.” The code must next read the authoritative row and compare every item:

~~~text
request_sha256
input/output/effect/handler/producer/policy revisions
canonical arguments JSON
tenant / subject / tool / idempotency key
approval provider / API family / adapter revision
~~~

Any mismatch is a conflict or storage-contract violation. Do not selectively trust the new request or old record.

## WAL and the real multi-connection boundary

WAL mode lets readers and a writer proceed concurrently, but there is still only one writer. Every worker thread in this project uses its own SQLite connection configured as:

~~~text
PRAGMA journal_mode = WAL
PRAGMA synchronous = FULL
PRAGMA foreign_keys = ON
PRAGMA busy_timeout = 5000
~~~

> [!warning] WAL is not network-filesystem coordination
> SQLite's WAL documentation explicitly requires participating processes to share the WAL index on the same host. Do not put a local '.sqlite3' file on a network filesystem and call it a distributed idempotency service. For multi-host deployment, use a database or queue that supports the required consistency model.

## Strict JSON and database boundaries

The project does not treat “'json.loads' worked” as trusted evidence:

- a fixture must be UTF-8 and no more than 65,536 bytes; before the recursive decoder, a linear scan limits container nesting to 32 levels. A deeply nested but byte-bounded file becomes a controlled fixture-contract error and does not expose 'RecursionError' or a traceback through the CLI;
- the fixture also rejects duplicate keys, 'NaN/Infinity', extra fields, unregistered provider profiles, and Boolean timestamps;
- JSON stored in the database first passes the v2 supported JSON domain, then receives project-local canonical form through sorted keys, compact separators, and UTF-8;
- on database read, it is parsed strictly, encoded again, and compared with the original; noncanonical JSON never reaches a handler or result;
- SQLite tables use 'STRICT', 'NOT NULL', 'CHECK', 'UNIQUE', and 'FOREIGN KEY';
- SQL values use placeholders only; model input is never concatenated;
- both local and downstream receipts rerun the v2 per-tool output schema and input-binding checks.

This is deterministic JSON within the project, not an RFC 8785 claim. If services in several languages share digests, first lock a cross-language canonicalization protocol and test vectors.

## Idempotency and call binding are not one digest

The project directly calls v2 'request_digest()':

$$
d_{request}=H(tenant,subject,tool,arguments,inputRev,outputRev,effectRev)
$$

It excludes the idempotency key because the key is execution/retry identity rather than business intent. Yet v2 'call_binding_sha256' still binds provider turn, call, operation, idempotency key, tool contract, request/result digest, and downstream request/receipt/status reference. Therefore:

| Request | Result |
| --- | --- |
| Same scope/key + same request digest/contract | 'local_replay' or continued unknown; no new intent |
| Same scope/key + different digest/contract | 'IDEMPOTENCY_CONFLICT' |
| Same business intent + different key | Two execution identities; two side effects are possible |
| Legal package substituted onto another key/call | Recomputed call binding fails |

### Durable approval semantics

A new intent may be stored only when v2 approval binds current subject, provider/API family/adapter revision, call/operation/response, idempotency key, request digest, contract revisions, an eligible 'approver_id', and has not expired. The ledger stores 'approval_id', 'approver_id', 'approval_digest', 'approval_expires_at', 'approved_at', and first provider/API/adapter/call/response identifiers. Before an external effect, the worker recomputes the approval digest from these durable identities; a well-formed value substituted for another provider, API family, adapter revision, or digest fails closed. Validity uses the half-open boundary 'approved_at < approval_expires_at'.

### Current claims are not ledger fields

'operations' stores only tenant/subject scope, not creation-time 'roles'. Every preflight reads the current principal; the reservation transaction rereads it with the **same** resolver, and the worker rereads it a third time before the downstream effect. When the example has no injected resolver, roles are fixed empty and access is owner-only. Only a deployment that explicitly connects a current-claims resolver lets 'support_admin' access another person's same-tenant order. If a role is revoked after intent acceptance, the worker leaves operation/lease recoverable and returns 'authorization_denied'; it creates no downstream receipt. This offline implementation does not place an external IAM query inside the SQLite write transaction. Production still needs to narrow the window between this check and commit using the target IAM/policy's consistency semantics.

> [!note] This project defines atomic acceptance of an immutable intent under valid approval as approval consumption
> 'approval_expires_at' must cover 'approved_at/intent commit', but delivery of an already accepted outbox does not automatically become another intent just because a worker queue lasts past that time. If business policy requires approval to remain valid at actual downstream submit, put that rule in the policy revision and persist 'reapproval_required' or a human state at expiry; do not silently recreate the intent.

## Outbox, lease, and recovery

### Atomically write intent + outbox

For a new key, 'operations' and 'outbox' must commit in the same local transaction. Otherwise there can be “business intent with no event ever” or “event with no authoritative intent.”

### Expiring lease

Within 'BEGIN IMMEDIATE', a worker moves an outbox item from 'pending' to 'processing' and stores 'lease_owner/lease_until/attempt_count'.

- Before lease expiry, another worker cannot claim it.
- After expiry, another worker can reclaim it.
- Reclaim can redeliver, so the downstream system must remain idempotent under the same execution scope.
- Production also needs heartbeat/renewal, maximum attempts, dead-letter or human disposition, and backlog metrics.

> [!warning] Teaching time is not a production trust boundary
> To make failure tests reproducible, the example accepts 'now' as a caller-injected deterministic control input. That does not prove clocks across processes are trustworthy or consistent. Production claim/reclaim should use controlled wall-clock or database time, monitor clock skew, and combine fencing tokens or state-conditioned updates. A monotonic clock is good for a single process's elapsed intervals but cannot simply be persisted and compared by different processes; lease expiry alone can still let an old worker and a new owner execute concurrently.

> [!warning] This project has no outbox poller
> 'process_operation(status_ref, ...)' handles only an operation known to the caller, and the CLI offers only targeted 'dispatch', 'status', and 'audit'. The code proves that an event can persist, be claimed, be reclaimed after expiry, and reconcile safely; it does not enumerate backlog by itself or guarantee that a pending event is eventually scheduled. Production must add a continual poll/claim/retry loop, process supervision, backoff, DLQ or human disposition, and a lag SLO.

A successful claim is not permission to execute. Before downstream submission, the worker recomputes request digest plus current input/output/effect/handler/producer/policy revisions from the registry, calls the current authorization resolver with ledger tenant/subject/resource, and reruns the current business-state validator. Neither model arguments nor a creation-time role snapshot is current authority or business fact. Contract drift, revoked authorization, or an order that is no longer refundable all fail closed and create no downstream receipt; the operation retains an unknown, auditable lease state. The teaching default resolver and order state are local mocks; production must use current IAM/policy and an authoritative business transaction.

### Crash points

| Failure | Durable state | Return / recovery |
| --- | --- | --- |
| 'after_intent_commit' | Ledger + pending outbox, no downstream receipt | 'OUTCOME_UNKNOWN'; wait for an external scheduler to enumerate and call a worker |
| 'after_claim' | Processing + unexpired lease | 'OUTCOME_UNKNOWN'; reclaim after expiry |
| 'after_downstream_commit' | Downstream receipt exists, local receipt does not | Still 'OUTCOME_UNKNOWN'; reconcile with an explicit status query |

'dispatch()' returns only the original 'status_ref' and unknown when it sees an unfinished ledger. It does not opportunistically run the worker, query a receipt, or execute again. That makes “call a tool” and “observe a committed operation” two auditable actions.

## Secure order of an explicit status query

~~~text
strict call + current principal
  → registry / input schema
  → current resource authorization
  → independent provider response/call identity + query_status purpose binding
  → opaque status_ref and tenant/subject scope
  → recompute expected_request_sha256
  → bind idempotency key + contract revisions
  → downstream receipt + per-tool output contract
  → one transaction writes local receipt / succeeded / outbox delivered
  → Tool Result v2 receipt_reconciled
~~~

Even when the ledger is already 'succeeded', a status query and replay first redo current resource authorization. After revocation, they return the same-shaped 'NOT_FOUND' as a nonexistent resource and cannot read data through an idempotency cache. Replay and status query must retain the approved operation's provider/API family/adapter revision; a cross-context request conflicts and cannot move approval or result from one provider path to another. The teaching helper derives independent, host-owned provider identity from the original call and 'status_ref'; the identity fingerprint is fixed to 'query_status' and cannot later be reused for dispatch.

## Project files

| File | Role |
| --- | --- |
| [[tool-calling-function-calling/examples/persistence/persistence-case.json\|persistence-case.json]] | A strict UTF-8 JSON scenario for one write operation |
| [[tool-calling-function-calling/examples/persistence/persistent_tool_runtime.py\|persistent_tool_runtime.py]] | SQLite ledger/outbox/lease/receipt runtime and PASS/BLOCK CLI |
| [[tool-calling-function-calling/examples/persistence/test_persistent_tool_runtime.py\|test_persistent_tool_runtime.py]] | 94 regression tests for JSON/database, v2 compatibility, current-principal/approval context, idempotency, crashes, authorization/contract drift, time boundaries, audit/CLI redaction, tampering, multi-connection behavior, and CLI |

The implementation uses only the Python 3.11 standard library. It was exercised with SQLite 3.45.1 and requires SQLite 3.37.0+ because that release introduced 'STRICT' tables.

## Run the PASS path

Run from the repository root:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1' # Prevent the CLI from creating __pycache__ and mixing machine state into the course.
$env:PYTHONIOENCODING = 'utf-8' # Keep structured output UTF-8 in PowerShell.
$project = '.\docs-EN\tool-calling-function-calling\examples\persistence' # SQLite project directory.
$db = Join-Path $env:TEMP ("tool-persistence-pass-{0}.sqlite3" -f [guid]::NewGuid()) # Create a unique database in the system temporary directory.

python -B -W error "$project\persistent_tool_runtime.py" --db $db --fixture "$project\persistence-case.json" dispatch # Dispatch against the temporary database and offline fixture.
~~~

The result must contain:

~~~json
{
  "code": "OK",
  "delivery": "fresh",
  "gate": "PASS",
  "status": "succeeded"
}
~~~

## Run BLOCK and explicit reconciliation

Use a fresh database to inject “downstream committed but the local response was lost”:

~~~powershell
$unknownDb = Join-Path $env:TEMP ("tool-persistence-unknown-{0}.sqlite3" -f [guid]::NewGuid()) # Separate temporary database for the unknown-outcome experiment.
$blockedJson = python -B -W error "$project\persistent_tool_runtime.py" --db $unknownDb --fixture "$project\persistence-case.json" dispatch --failure after_downstream_commit # Deliberately fail after downstream commit to model the dangerous crash window.
$blocked = $blockedJson | ConvertFrom-Json # Parse controlled JSON output to inspect state fields.

$blocked.gate # Expected: BLOCK; the runtime does not pretend an unknown result is success.
$blocked.code # Expected: OUTCOME_UNKNOWN; explicit reconciliation is required.
$blocked.status_ref # Save this reference; the next step can query with it but cannot retry under a different key.

python -B -W error "$project\persistent_tool_runtime.py" --db $unknownDb --fixture "$project\persistence-case.json" status --status-ref $blocked.status_ref # Query explicitly rather than dispatching another write.
~~~

The exit-code contract is: '0' for verified success or a passing audit; '1' for expected business/audit 'BLOCK' such as 'OUTCOME_UNKNOWN'; and '2' for fixture, SQLite, persistence-contract, or local-I/O failure. Code 2 writes only a stable, path-free 'error.code' summary to stderr, such as 'FIXTURE_IO_ERROR' or 'SQLITE_ERROR'; it does not echo raw 'OSError', the database path, or fixture path. Do not treat 2 as business denial, and do not change unknown into fake success merely to make the shell green.

## Test matrix

~~~powershell
python -B -m unittest discover -s $project -p 'test_persistent_tool_runtime.py' # Run SQLite/outbox regressions in normal mode.
python -O -B -m unittest discover -s $project -p 'test_persistent_tool_runtime.py' # Verify runtime gates do not depend on bare assert.
python -B -W error -m unittest discover -s $project -p 'test_persistent_tool_runtime.py' # Turn resource and SQLite warnings into failures.
python -O -B -W error -m unittest discover -s $project -p 'test_persistent_tool_runtime.py' # Run the full persistent suite under both strict modes.
~~~

The 94 tests cover:

| Layer | Executable counterexamples / invariants |
| --- | --- |
| JSON fixture | Duplicate keys, nonfinite numbers, non-UTF-8, oversized input, 4,096-level nesting below 65,536 bytes, extra fields, provider revision |
| SQLite schema | WAL, FULL synchronous, STRICT, foreign keys, CHECK, 'persistent-tool-runtime-v3'; audit uses one explicit read transaction for an integrity/FK/semantic/count snapshot and includes FULL in its gate; portable UTC/approval/lease overflow is rejected before reservation; injected failures roll back intent/outbox and receipt/ledger/outbox together; an orphan receipt audit emits only an opaque reference |
| v2 compatibility | Fully reused request digest; key and downstream evidence enter call binding; package recomputation passes; approver identity and provider/API/adapter context persist and recompute; status-query purpose cannot be reused for dispatch |
| Idempotency | First fresh execution, same-intent replay, cross-provider/API/adapter replay conflict, different-intent conflict, post-restart replay, and post-revocation denial |
| Crash recovery | Intent commit, claim, lease expiry, current authorization/business-state/contract-revision rechecks through one resolver at reservation and worker, downstream commit, explicit reconciliation |
| Tampering | Noncanonical/duplicate-key JSON, receipt digest, output/input binding |
| Multiple connections | Eight connections contending for same-intent reservation, different-intent contention, eight worker claims, and cross-connection replay |
| CLI | 'PASS', 'BLOCK → status → PASS', database audit, and stable path-free error codes for fixture/database failures |

Passing '-O' means key checks do not depend on bare 'assert'; passing '-W error' exposes resource or deprecation warnings. Neither proves power-loss durability, network partitions, or real downstream API idempotency.

## Verified and unverified project boundaries

### Verified

- Python 3.11 standard library and SQLite 3.45.1; 94/94 in normal, '-O', '-W error', and '-O -W error' modes.
- Ledger and outbox share one local transaction, as do receipt/ledger/outbox reconciliation; trigger-injected mid-path failures verify rollback as a unit on both paths.
- Same-key/same-intent replay works across runtime restart; different intent conflicts.
- An unexpired lease cannot be reclaimed; it can be recovered after expiry.
- When a downstream receipt committed but local state has not reconciled it, repeat dispatch remains unknown.
- Reservation and outbox worker both reload current claims through the same current-principal resolver; default is owner-only, and regression covers a 'support_admin' success path and no-receipt path after role revocation. Before downstream effect, the worker recomputes current contract revision and reruns current resource authorization and business state; contract drift, revocation, or changed order state produces no receipt.
- Approval digest and durable recomputation cover provider, API family, and adapter revision. Cross-context replay conflicts, and tampering with any persistent context fails closed before worker side effect.
- An explicit status query uses independent purpose-bound call identity and returns 'receipt_reconciled' only after current authorization plus request/contract/receipt/output binding.
- Database-audit integrity, foreign keys, semantic rows, and counts come from one read snapshot, and WAL plus FULL synchronous enter the CLI PASS gate.

### Unverified

- No real provider SDK, HTTP API, queue, or business database is connected.
- 'downstream_receipts' is a separately committed stand-in in the same SQLite file, not a distributed downstream system.
- There is no real process kill, power loss, full/corrupted disk, WAL-checkpoint stall, or network partition injection.
- There is no lease heartbeat, maximum-attempt policy, dead-letter queue, retention/cleanup policy, or database-migration tool. An old 'persistent-tool-runtime-v1' database is explicitly rejected by the current v3 runtime; it cannot be silently upgraded in place.
- 'now' is a caller-injected deterministic test control; no cross-process trusted clock, clock-skew monitoring, or fencing is verified.
- There is no continuous outbox enumerate/poll/retry scheduler, so pending-event eventual-delivery liveness is not proven.
- There is no multi-host concurrency; the project claims neither exactly once, linearizable external effects, nor multi-database atomicity.

## Production extension checklist

- [ ] Connect the authorization resolver to current IAM/policy revision; do not use a creation-time role snapshot as current authorization.
- [ ] Confirm whether the downstream system accepts same-key idempotent requests or only supplies a status/receipt API.
- [ ] Record downstream key scope, TTL, different-argument conflict semantics, and which errors persist.
- [ ] Use controlled wall-clock or database time and monitor clock skew; design lease heartbeat, worker fencing token, or state-conditioned updates so an expired worker cannot overwrite a new owner.
- [ ] Put outbox lag, claim attempts, lease expiry, unknown age, receipt conflict, and duplicate effects in metrics and alerts.
- [ ] Define retention periods for keys, ledgers, and receipts; reuse after cleanup is an explicit business policy.
- [ ] Drill database backup, WAL checkpoint, schema migration, disk capacity, and recovery time.

## Self-check

1. Which local race does 'BEGIN IMMEDIATE' solve, and which external race does it not solve?
2. Why must a request digest be reread and compared after 'ON CONFLICT DO NOTHING'?
3. Why can 'after_downstream_commit' return neither failure nor fake success?
4. Why does lease-expiry redelivery require the downstream system to understand the same idempotency scope?
5. Why must local replay and status query still run current resource authorization?
6. What can, and what cannot, eight SQLite-connection contention tests prove?

## Content provenance and copyright boundary

The course text, Mermaid diagram, SQLite table design, Python implementation, fixtures, and tests are original project material. Third-party documentation was used only to verify product/database behavior and engineering boundaries; its prose, examples, and images were not copied.

## Core references

- [SQLite: Transaction](https://www.sqlite.org/lang_transaction.html)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite: UPSERT](https://www.sqlite.org/lang_upsert.html)
- [SQLite: STRICT Tables](https://www.sqlite.org/stricttables.html)
- [Python 3.11: sqlite3 — DB-API 2.0 interface for SQLite](https://docs.python.org/3.11/library/sqlite3.html)
- [Python 3.11: json — JSON encoder and decoder](https://docs.python.org/3.11/library/json.html)
- [Stripe API: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [AWS ECS: Ensuring idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)
- [RFC 9110: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)

Sources accessed: 2026-07-21. SQLite pages and Python 3.11 documentation were used to verify transaction, WAL, UPSERT, STRICT, DB-API transaction control, and untrusted-JSON resource boundaries; Stripe/AWS pages compare concrete API contracts for “same key and same arguments replay; different arguments conflict.” The 65,536-byte and 32-level limits are testable teaching limits for this project, not universal production thresholds derivable from Python documentation. Do not infer downstream retention, saved-error, or retry rules from these examples; consult the current documentation for the target service.

Return to [[tool-calling-function-calling/00-index|the Tool Calling index]]; next, proceed to [[agent-core/00-index|Agent Core]] to place recoverable tool operations in an agent loop with budgets, stopping conditions, and human nodes.
