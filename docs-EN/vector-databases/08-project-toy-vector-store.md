---
title: "Project: Toy Vector Store"
tags:
  - ai-agent-engineer
  - vector-database
  - project
aliases:
  - Toy Vector Store Project
source_checked: 2026-07-22
source_baseline: "This knowledge base's teaching implementation and tests;
  Faiss, pgvector, Qdrant, and PostgreSQL official material, checked through
  2026-07-22; 41 unittest cases were verified in normal and -O modes with -W
  error"
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 向量数据库/08-项目-玩具向量存储.md
translation_source_hash: 5add170cb0c3d6e17ecf4c9a4a725c9186bdfc55256a150724509271ea90bc5f
translation_route: zh-CN/向量数据库/08-项目-玩具向量存储
translation_default_route: zh-CN/向量数据库/08-项目-玩具向量存储
---

# Project: Toy Vector Store

## Project objective

This project uses no third-party dependency. It implements a minimal vector store in one strict JSON file and lets you verify these causal relationships directly:

- an embedding space needs an explicit contract that cannot be silently mixed;
- a point consists of a stable ID, vector, and auditable payload;
- upsert distinguishes creation, an entirely identical replay, expected-current CAS update, and different content under the same revision;
- tenant, ACL, publication status, and business filters take effect before scoring;
- a delete binds current source revision and delete event; even an unindexed point receives an intent fence, and a tombstone blocks late upsert by default;
- multiple-instance cached state checks disk revision before no-op, search, and summary, failing closed when it changes;
- exact search provides a small-scale correctness baseline;
- an atomically replaced JSON file is still far from a production database.

Project files:

- [[vector-databases/examples/toy_vector_store.py|toy_vector_store.py]]: implementation and demonstration entry point;
- [[vector-databases/examples/test_toy_vector_store.py|test_toy_vector_store.py]]: 41 tests for input, mathematics, security, CAS lifecycle, persistence fences, resource limits, stale reads across instances, and CLI behavior.

## Prerequisites

- Windows 11 and PowerShell 7;
- Python 3.11 or a compatible stable Python 3;
- run from the vault root;
- no network, API key, virtual environment, or third-party package.

For a real project, use **venv + pip** before installing dependencies. This example uses only the standard library; it uses **PYTHONDONTWRITEBYTECODE** so the vault does not receive **.venv** or **__pycache__**.

## Data contract

### Store contract

One file holds one vector space only:

| Field | Purpose | Project constraint |
| --- | --- | --- |
| **space_id** | logical identity of the space | nonempty stable string |
| **model** | vector origin | manually supplied vectors in this demonstration |
| **embedding_revision** | encoding-contract version | payload must match exactly |
| **dimension** | vector length | integer from 1 to 100000 |
| **metric** | ordering rule | cosine, dot, or euclidean |
| **normalized** | whether unit vectors are required | when true, validate L2 norm |
| **dtype** | declared storage type | float32 or float64 |

When opening an existing file, the script compares the complete contract. A model update needs a new **embedding_revision** or space even if dimension does not change. Equal dimension does not prove semantic coordinates are comparable.

This contract constrains persisted points only. The current **search()** accepts a bare vector and checks dimension, finiteness, norm, and store metric, but does not carry or validate query contract signature or encoding role. A query from another model with the same dimension and normalization can still be misused. The example therefore cannot claim end-to-end space binding.

### Point and payload

Every point contains:

- a stable **id** and finite, nonzero vector with correct dimension;
- **tenant_id**, **document_id**, and **source_revision**;
- **embedding_revision** and a normalized-body **content_sha256**;
- a nonempty, deduplicated, sorted ACL group list;
- **draft**, **published**, or **archived** status.

The project's **source_revision** is opaque: it is compared only for equality, never ordered by string value. A non-identical update supplies an **expected_source_revision** that exactly matches the current point. Different vector, payload, or hash under the same source revision raises **WriteConflictError**. The upstream canonical source/workflow determines the legal successor, and one point must not reuse an old identity through its whole lifecycle.

The toy store does not have a complete generation/history ledger, so it cannot prove an identity was never used before. If an upstream system permits **r1 → delete → r2 → delete → r1**, an old **delete(r1, d1)** can match again: ABA. The project cannot claim to prevent every historical stale event.

The teaching API accepts query tenant and subject groups to illustrate filtering. In production, they must be derived from authenticated identity, not freely supplied by an end user.

### Persistent state

The top level records **schema_version**, monotonically increasing **store_revision**, contract, points, and tombstones. A schema-v2 tombstone strictly stores:

- **point_id** and **tenant_id**;
- **deleted_source_revision**;
- **delete_event_id**, the replay comparator for the current deletion state;
- **deleted_at_store_revision**.

The parser rejects extra or missing fields, duplicate JSON keys, NaN/Infinity, wrong types, duplicate point IDs, and a state in which one ID exists in both points and tombstones. Schema-v1 tombstones lack source/delete fences, so the script refuses automatic upgrade and requires rebuilding schema v2 from canonical source.

A tombstone is current deletion intent, not an append-only audit log: successful resurrection removes it from current state. Production must permanently record create, update, delete, and resurrection in an external lifecycle/audit ledger and use an unreusable generation or history fence against ABA.

Before one commit, the store checks **points + tombstones <= 100000**, then checks that actual UTF-8 serialized output is at most 20 MiB. Limit failures occur before temporary-file creation, replacement, or in-memory state change. It writes a temporary file in the target directory, calls **flush + fsync**, replaces with **os.replace**, and cleans up the temporary file. This reduces partial-write risk, but provides no directory fsync, WAL, cross-record transaction, process lock, or real concurrent control.

## Run the demonstration

Use a unique temporary path and clean it up regardless of outcome:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not write interpreter bytecode cache into the vault.
$script = Join-Path (Get-Location) 'Knowledge\AI Agent Engineer\docs-EN\vector-databases\examples\toy_vector_store.py'  # Build the teaching-script path from the vault root.
$db = Join-Path $env:TEMP ("toy-vector-store-" + [guid]::NewGuid().ToString("N") + ".json")  # Allocate one non-conflicting temporary database path.

try {
    python -B -W error $script --db $db demo  # Run the full strict-JSON lifecycle demonstration.
    if ($LASTEXITCODE -ne 0) {
        throw "The demo failed with exit code: $LASTEXITCODE"
    }
}
finally {
    Remove-Item -LiteralPath $db -Force -ErrorAction SilentlyContinue  # Delete only the exact temporary file created above.
}
~~~

A fresh run should satisfy this table; do not copy the dynamically generated contract hash:

| Observation | Expected |
| --- | --- |
| **a-1**, **a-2-initial**, **b-1** | **created** |
| **a-2-update** | **updated**, without increasing point count |
| **a-2-repeat** | **unchanged**, without increasing revision |
| **alpha_before_delete** | **a-1**, then **a-2**, by score |
| beta tenant's **b-1** | never occurs in alpha results |
| after deleting **a-1** | only **a-2** returns |
| final summary | revision 5, two points, one tombstone |

Why are there still two points? Beta's **b-1** remains in the store, but alpha has no authorization to see it. An empty or smaller result set does not prove that an underlying record was deleted.

## Trace one lifecycle in code

1. First upsert of **a-2**: the ID is absent, so the point is written and the result is **created**.
2. The same ID arrives with **source_revision=r2**, a new vector, and **expected_source_revision=r1**. Only a matching CAS replaces the old point; the result is **updated** and count is unchanged.
3. The same r2 is delivered again with the original expected current value r1. The store recognizes the entire retry before checking it as an update, returns **unchanged**, does not write disk, and does not increase revision. This makes “server succeeded but response was lost” observable.
4. An alpha query checks tenant, **status=published**, and ACL before cosine scoring. A more-similar beta record cannot enter candidates.
5. Deleting **a-1** requires current **expected_source_revision=r1** and a unique **delete_event_id**. The point is removed and a tombstone bound to alpha/source/event is written. If the point was not created/indexed yet, its first delete writes the same tombstone intent and returns true, blocking a late r1 upsert. Only replay with identical tenant, source, and event returns false without increasing revision; every other mismatch conflicts.
6. A tombstone rejects upsert by default. A test in alpha can resurrect only with a **ResurrectionToken** matching both deleted source revision and delete event, and a different new source revision. Beta cannot ever take over the ID.

> [!warning] ResurrectionToken is not authorization
> It proves only which tombstone fence an operation uses for concurrency/replay control. It does not prove that a caller may restore data. Delete-before-create can establish a tombstone for an unknown ID; exposing that directly to an unauthenticated caller enables malicious ID squatting. Production must derive tenant/source from trusted identity and canonical mapping, then enforce permission, approval, and audit.

## Why exact search matters

The project calculates cosine, dot, or negative Euclidean distance point by point, sorts score descending, and breaks ties stably by point ID. This O(N) exact search is unsuitable for low-latency service at scale, but useful to:

- validate score direction, normalization, and order;
- create ANN top-k ground truth;
- verify filtering applies before scoring;
- regression-test updates and deletions on a small fixture.

Business relevance still needs human or behavioral gold. Exact top-k proves only that ANN did not omit a nearest neighbor; it does not prove the candidate answers the question.

## Run tests

Both the normal interpreter and **python -O** must pass so correctness does not depend on **assert** statements removed in optimized mode:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Keep interpreter caches out of the course directory.
$project = Join-Path (Get-Location) 'Knowledge\AI Agent Engineer\docs-EN\vector-databases'  # Keep a stable project path for unittest.

Push-Location $project
try {
    python -B -W error -m unittest discover -s .\examples -p 'test_toy_vector_store.py' -v  # Run all mathematics, lifecycle, and security tests normally.
    if ($LASTEXITCODE -ne 0) {
        throw "Normal-mode tests failed with exit code: $LASTEXITCODE"
    }

    python -B -O -W error -m unittest discover -s .\examples -p 'test_toy_vector_store.py' -v  # Repeat with optimization and strict warnings.
    if ($LASTEXITCODE -ne 0) {
        throw "Optimized-mode tests failed with exit code: $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
~~~

The suite covers strict JSON; rejection of schema-v1 automatic migration; contracts; three distances; dimensions and non-finite values; unit vectors; identical-upsert replay; expected-current CAS; opaque revisions; conflicts for same-revision different vector/payload/hash; delete-before-create; late upsert; stale delete; delete-event idempotency conditions; cross-tenant ID defense; persistent tombstone/resurrection fences over restart; total-record and UTF-8-byte write limits; ACL/status/filter; empty authorization fail-closed; stale writer/no-op/search/summary conflicts; atomic LF JSON; CLI output; and **-O** equivalence.

## Concurrency boundary: why this is not a transaction

Each **ToyVectorStore** instance remembers **store_revision** at load time. Commit, identical-upsert no-op, delete-replay no-op, search, and snapshot summary first reread disk revision. If another instance has committed, the store raises **WriteConflictError** instead of claiming success or returning an old ACL/deletion state. The caller must reopen/reload before deciding whether to retry.

This detects state committed before the check starts. A time-of-check/time-of-use race remains between checking revision and actual scoring, summary construction, or **os.replace**: two instances can still pass the check together. The project promises only single-process teaching and a fail-closed illustration, not snapshot isolation. Production needs database transactions/compare-and-swap, reliable locking, WAL, crash recovery, explicit read/write acknowledgement, and concurrency stress tests. A retry loop around this script does not create those guarantees.

## Gaps from a production vector database

The project explicitly lacks:

1. ANN indexes, compression, memory mapping, and capacity control;
2. multi-process/multi-node transactions, WAL, and crash recovery;
3. authentication, authorization policy, encryption in transit/at rest, and audit log;
4. shards, replicas, failover, scaling, and read/write consistency guarantees;
5. incremental backup, point-in-time recovery, retention, and isolated recovery rehearsal;
6. schema migration, rolling upgrades, and multi-version client compatibility;
7. production payload indexes, hybrid retrieval, rate limits, and resource quotas;
8. metrics, traces, alerts, SLOs, and incident response;
9. unreusable generation, permanent lifecycle/audit ledger, tombstone retention, and purge policy;
10. a query-vector envelope containing contract signature/encoding role plus server-side space verification.

Also, 20 MiB measures total serialized state in UTF-8 bytes, and 100000 counts live points plus tombstones. Both are teaching guardrails, not capacity commitments. Full-file rewrite and full reparse before every public read become slow as data grows.

## Extension tasks

Complete these in order, adding tests before implementation.

### Task A: secure filters

Design explicit schema and allowlist for a date or numeric range. Reject unknown fields, wrong types, and empty authorization. Add a regression proving that a highest-scoring unauthorized point never appears.

### Task B: batch CAS and conflict queue

Give every batch item its own expected source revision, event ID, and input hash. Return per-item created/updated/unchanged/conflict outcomes. Simulate partial success and client timeout; prove only unknown items retry, and route same-revision different-content items to a conflict queue. Explain why application CAS still cannot solve cross-process TOCTOU in this JSON file.

### Task C: export, recovery, and deletion propagation

Design a checksum export manifest, recover it in a new temporary directory, and reconcile contract signature, point/tombstone sets, ACL, and gold queries. Demonstrate how a deleted point returns from an old snapshot if tombstones are omitted.

### Task D: exact versus approximate candidate comparison

Intentionally search only one candidate subset and compute ANN Recall@k against exact top-k. Cover several top-k values and filter selectivity tiers. Do not call this simplified algorithm a usable ANN index.

### Task E: migration design

Copy a fixture into a new **space_id**, change embedding revision, compare dual reads, and switch explicitly. Prove old- and new-space vectors cannot be ranked together directly.

### Task F: generation and permanent lifecycle ledger

Give each point an unreusable generation/row version. Write create, update, delete, and resurrection to an append-only ledger. Construct **r1 → delete → r2 → delete → r1** and prove that an old delete is rejected by generation/history fence even if source identity becomes equal again. Then design ledger retention, audit query, and tombstone-purge interactions.

### Task G: query-space proof

Define **QueryVector(vector, contract_signature, encoding_role)**. Make **search()** verify signature against current store contract before computing distance and reject a document role masquerading as query role. Add a same-dimension, unit-norm vector from another space to prove dimension/norm checks cannot replace space identity.

## Project acceptance checklist

- [ ] I can explain every contract field and why equal dimension can still be incompatible.
- [ ] An identical upsert is a no-op; non-identical update explicitly matches expected current state; different content under one revision conflicts.
- [ ] Tenant, ACL, status, and allowlist filter apply before similarity computation.
- [ ] Empty authorization fails closed; neither cross-tenant point nor tombstone ID can be taken over.
- [ ] A delete before create stores a source/event fence; a current tombstone blocks upsert by default; explicit resurrection matches both old source and event fence.
- [ ] I can explain that **ResurrectionToken** controls concurrency/replay only and does not replace authorization.
- [ ] I can distinguish nonreusable source identity, current tombstone, permanent audit ledger, and ABA prevention.
- [ ] A stale store fails closed before no-op/search/summary; 20 MiB is UTF-8 bytes and 100000 is point+tombstone total.
- [ ] I know that bare query vectors do not yet implement end-to-end space binding.
- [ ] Normal and **-O** tests pass with equivalent output.
- [ ] Temporary files, databases, caches, and virtual environments do not remain in the vault.
- [ ] I can name at least eight production gaps instead of presenting this project as a database product.

## Self-check

1. Why is **a-2-repeat** easier to audit when it does not increase revision than when a duplicate write merely succeeds?
2. Why cannot filtering top-k results replace pre-scoring ACL constraint?
3. Why must a normalized contract reject non-unit vectors rather than accept them silently?
4. Why is **os.replace** not a database transaction or reliable disaster recovery?
5. Why does a tombstone bind tenant, deleted source, and delete event, and why can another tenant not reuse the ID?
6. Why does matching a **ResurrectionToken** not authorize restoration?
7. Why cannot a current tombstone replace permanent audit history, and how does identity reuse cause ABA?
8. Why is pre-read revision checking still not snapshot isolation?
9. What separate questions do exact top-k and human relevance gold answer?

After answering, return to the [[vector-databases/00-index|Vector Databases index]] and continue to [[semantic-search/00-index|Semantic Search]].

## References

- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [pgvector official repository](https://github.com/pgvector/pgvector)
- [Qdrant: Points](https://qdrant.tech/documentation/manage-data/points/)
- [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/)
- [PostgreSQL: Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [PostgreSQL: Backup and Restore](https://www.postgresql.org/docs/current/backup.html)

Sources were retrieved on 2026-07-22. The teaching implementation was verified on Python 3.11 in normal and **-O** modes with **-W error**. Recheck product behavior and defaults under the locked version.
