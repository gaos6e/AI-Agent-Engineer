---
title: "Vector Databases"
tags:
  - ai-agent-engineer
  - vector-database
  - rag
aliases:
  - Vector Databases index
  - Vector Database learning path
source_checked: 2026-07-22
source_baseline: pgvector, Qdrant, Faiss, and PostgreSQL official materials,
  plus the original HNSW and Faiss papers, checked through 2026-07-22
content_origin: original
content_status: dynamic
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 26
ai_learning_schema: 2
ai_learning_id: vector-database
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2600
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 900
ai_learning_track_rag_kind: core
lang: en
translation_key: 向量数据库/00-目录.md
translation_source_hash: 168341ba40b7097074d7cbb4f5a78e5ceeae397fd52fd54418554d83ff420f17
translation_route: zh-CN/向量数据库/00-目录
translation_default_route: zh-CN/向量数据库/00-目录
---

# Vector Databases

## Course overview

A vector database stores “vectors + stable IDs + filterable metadata” and returns neighbors subject to authorization, business conditions, and resource budgets. Its job is not to “understand text”; it is a data and indexing system that covers:

- space schemas, dimensions, metrics, and version isolation;
- CRUD for points/records and idempotent writes;
- exact kNN and Approximate Nearest Neighbor (ANN) indexes;
- filters for tenants, ACLs, status, time, and other conditions;
- sharding, replicas, consistency, and scaling;
- snapshots, backup, recovery, migration, and operational monitoring.

A vector store cannot repair bad chunking, incorrect query/document roles, or embeddings that do not fit the task. Nor does a neighbor automatically become citable evidence. Complete retrieval also needs query rewriting, keyword/hybrid retrieval, reranking, context assembly, and evaluation.

> [!important] Product-fact boundary
> Collection, filter, HNSW/IVF parameters, write consistency, snapshot scope, and defaults vary by product and version. This course uses pgvector, Qdrant, Faiss, and PostgreSQL as verifiable examples, but does not generalize any product's behavior into a guarantee for every vector database.

## Where this course fits

[[embeddings/00-index|Embeddings]] defines the vector-space contract, while [[chunking-strategies/00-index|Chunking Strategies]] and [[knowledge-base-construction/00-index|Knowledge Base Construction]] provide canonical points. This course owns storage, filtering, and neighbor queries. Then [[semantic-search/00-index|Semantic Search]] combines query encoding with multiple retrieval paths, [[reranking/00-index|Reranking]] refines candidates, and [[rag/00-index|Retrieval-Augmented Generation (RAG)]] builds answers with citations.

## Learning objectives

After completing this course, you should be able to:

- design a schema containing a space contract, point, vector, payload, source revision, ACL, and hash;
- distinguish exact kNN, ANN recall, and business Recall@*k*;
- explain the core intuition of HNSW, IVF, and quantization, including quality–latency–memory–build tradeoffs;
- make tenant/ACL/status filters fail closed before candidate scoring;
- implement stable IDs, explicit source CAS, idempotent upserts, delete-before-create fences, tombstones, and integrity reconciliation;
- state how shards, replicas, read/write acknowledgments, and concurrent updates can produce stale reads or conflicts;
- define RPO/RTO for a snapshot and prove it through an isolated restore drill;
- run a reproducible bake-off with real corpora, queries, filter distributions, and write mixes;
- identify the distinct responsibilities of a library, database extension, dedicated/managed vector store; and
- design dual-space/dual-read migration, shadow comparison, cutover, and rollback for a model or product move.

## Prerequisites

- [[vector-fundamentals/00-index|Vector Fundamentals]]: dot products, cosine, and Euclidean distance.
- [[embeddings/00-index|Embeddings]]: space contracts, dimensions, metrics, normalization, and model migration.
- [[json/00-index|JSON]]: strict structures and types.
- [[api/00-index|APIs]]: retries, idempotency, rate limiting, and error handling.

You do not need prior distributed-database experience. Lessons 5–6 start with why an old value can be read and why a backup must be validated by a restore.

## Core terms

| Term | Plain-language explanation | Critical boundary |
| --- | --- | --- |
| point / record | One record containing an ID, vector, and payload | It must belong to one explicit embedding space. |
| collection / index / table | A product's logical container | Names differ; isolation, transaction, and backup semantics differ too. |
| payload / metadata | Scalar data such as tenant, ACL, source, and status | It supports filtering and audit; it is not an arbitrary JSON junk drawer. |
| exact kNN | Compute distance against every candidate | A small-scale quality baseline. |
| ANN | Find approximate neighbors to reduce query cost | It can miss exact neighbors, so ANN recall must be measured. |
| scalar/payload index | An index on a filter field | It adds write/storage cost and should follow queries. |
| shard | A disjoint data partition of a collection | It affects routing, fan-out, and scaling. |
| replica | A copy of a shard | It improves availability/read capacity and introduces consistency tradeoffs. |
| tombstone | A logical record expressing the current deletion intent | Even an unindexed ID may need a fence; a current tombstone is not a permanent audit history. |
| snapshot / backup | A recoverable copy of state within a scope | Its scope, point in time, and inclusion of aliases/configuration must be explicit. |

## Recommended sequence

| Order | Lesson | Learning outcome |
| --- | --- | --- |
| 1 | [[vector-databases/01-boundaries-and-data-model\|Boundaries and the data model]] | A point/collection schema that is filterable, migratable, and auditable. |
| 2 | [[vector-databases/02-distance-exact-search-and-ann-indexes\|Distance, exact search, and ANN indexes]] | Exact ground truth and ANN-parameter experiments. |
| 3 | [[vector-databases/03-filtering-and-multitenancy\|Filtering and multitenancy]] | Identity-derived tenant/ACL filters and unauthorized-access tests. |
| 4 | [[vector-databases/04-writes-updates-deletes-and-versioning\|Writes, updates, deletes, and versioning]] | Source CAS, idempotent upserts, tombstone fences, publication switching, and deletion propagation. |
| 5 | [[vector-databases/05-consistency-sharding-and-replicas\|Consistency, sharding, and replicas]] | Read/write semantics, shard keys, and fault tests. |
| 6 | [[vector-databases/06-backup-recovery-and-migration\|Backup, recovery, and migration]] | RPO/RTO, snapshot manifests, and isolated restore drills. |
| 7 | [[vector-databases/07-selection-and-benchmarking\|Selection and benchmarking]] | A requirements matrix, reproducible bake-off, and ADR. |
| 8 | [[vector-databases/08-project-toy-vector-store\|Project: toy vector store]] | Strict CRUD, source CAS, deletion intent, stale-read fail-closed behavior, and tests in a single-process JSON store. |

The first four lessons solve “is the data correct and safe?”; lessons 5–7 solve “what about scale, failures, and decisions?”; the final project turns the boundaries into code.

## Hands-on entry point

- [[vector-databases/examples/toy_vector_store.py|toy_vector_store.py]]: strict space contracts, persistence, source CAS, delete-before-create fences, explicit resurrection, stale-read checks, ACL/tenant filtering, and exact search.
- [[vector-databases/examples/test_toy_vector_store.py|test_toy_vector_store.py]]: 41 tests for math, inputs, lifecycle, security, conflicts, persistence fences, resource boundaries, multi-instance stale reads, and the CLI.

The project uses only the Python standard library. From the vault root, create the teaching database in the system temporary directory:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent the interpreter from creating __pycache__ in the course directory.
$db = Join-Path $env:TEMP ("toy-vector-store-" + [guid]::NewGuid().ToString("N") + ".json")  # Generate a unique JSON database path in the system temporary directory.
python -B -W error '.\docs-EN\vector-databases\examples\toy_vector_store.py' --db $db demo  # Run the toy store's create, update, search, and delete demonstration.
Remove-Item -LiteralPath $db -Force  # Remove the explicitly created temporary database file after a successful demonstration.
```

This project is not a production database: it has no multiprocess lock, complete transactions, ANN, authentication, replication, permanent lifecycle/audit ledger, or production disaster recovery. It validates file revision before public reads/no-ops and fails closed for stale instances, but a TOCTOU window still exists between the check and an actual read/write. Do not infer database-level consistency from it.

## Mastery checklist

- [ ] Every collection/index has a complete space contract; incompatible vectors are never mixed.
- [ ] Point IDs, source revisions, content hashes, tenants, ACLs, statuses, and deletion states are traceable.
- [ ] I can distinguish exact search, ANN recall, and business relevance.
- [ ] An ANN benchmark reports quality, tail latency, throughput, memory, build cost, and update cost together.
- [ ] Tenant/ACL scope is derived from trusted identity and filtered before scoring; empty permission fails closed.
- [ ] An identical upsert can be replayed idempotently; a nonidentical update uses the expected-current source revision for CAS, and same-revision/different-content becomes a conflict.
- [ ] A delete records a source/event fence even when it precedes creation; a tombstone blocks resurrection by default, and resurrection requires an explicit matching fence and real authorization.
- [ ] A source identity for one point cannot be reused across lifecycles; a permanent generation/history ledger, not the current tombstone, carries ABA and audit history.
- [ ] Multi-instance cached state checks the revision before search, summary, and no-op behavior; a change fails closed instead of returning stale ACL or deletion state.
- [ ] Deletion propagates to vectors, sparse indexes, caches, old spaces, and backup policy.
- [ ] Shard, replica, and consistency choices implement explicit business read/write semantics.
- [ ] A snapshot is restored in isolation and checked for permissions and gold queries.
- [ ] Selection follows the target data, SLOs, team, and exit conditions—not a vendor's single leaderboard.

## Relationship to other courses

| Course | Relationship |
| --- | --- |
| [[chunking-strategies/00-index\|Chunking Strategies]] | Produces the source spans and content hashes represented by points. |
| [[embeddings/00-index\|Embeddings]] | Defines dimensions, metrics, normalization, model, and revision. |
| [[knowledge-base-construction/00-index\|Knowledge Base Construction]] | Provides canonical revisions, an outbox, published pointers, and deletion events. |
| [[semantic-search/00-index\|Semantic Search]] | Organizes queries, filters, vector/keyword retrieval, and offline relevance. |
| [[reranking/00-index\|Reranking]] | Consumes first-stage candidates; it does not replace database retrieval. |
| [[rag/00-index\|RAG]] | Packages and cites authorized evidence, then produces an answer. |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | Observes latency, errors, capacity, replication, indexing, and recovery. |
| [[ai-safety/00-index\|AI Safety]] | Covers unauthorized access, data poisoning, log risk, and backup risk. |

## Primary references

- [pgvector official repository](https://github.com/pgvector/pgvector)
- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant: Points](https://qdrant.tech/documentation/manage-data/points/)
- [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/)
- [Qdrant: Distributed deployment](https://qdrant.tech/documentation/scaling/distributed_deployment/)
- [Qdrant: Snapshots](https://qdrant.tech/documentation/snapshots/)
- [PostgreSQL: Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [PostgreSQL: Backup and Restore](https://www.postgresql.org/docs/current/backup.html)
- [Malkov & Yashunin, HNSW](https://arxiv.org/abs/1603.09320)
- [Johnson, Douze & Jégou, Billion-scale similarity search with GPUs](https://arxiv.org/abs/1702.08734)

Sources retrieved on 2026-07-22. Dynamic product configuration, defaults, and guarantees must be rechecked against the pinned version.
