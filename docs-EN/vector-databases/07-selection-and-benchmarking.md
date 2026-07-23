---
title: "Selection and Benchmarking"
tags:
  - ai-agent-engineer
  - vector-database
  - benchmarking
aliases:
  - Vector Database Selection
  - Vector-store selection
source_checked: 2026-07-22
source_baseline: "Faiss, pgvector, Qdrant, and PostgreSQL official material,
  checked through 2026-07-22"
lang: en
translation_key: 向量数据库/07-选型与基准评测.md
translation_source_hash: 4fa90cf542836c58b6cf58c1443f363b2d891e022a7cea984a534ae5039d7e7e
translation_route: zh-CN/向量数据库/07-选型与基准评测
translation_default_route: zh-CN/向量数据库/07-选型与基准评测
---

# Selection and Benchmarking

## Learning objectives

Turn “which vector database should we choose?” into a set of verifiable questions. Complete a small bake-off using your own data rather than selecting from vendor rankings or popularity. The deliverables are a requirement list, test protocol, results table, and Architecture Decision Record (ADR) with exit conditions.

## Decide whether you need a vector database

“We need semantic search” does not mean a dedicated vector database must be deployed immediately. Answer first:

1. How many searchable points exist, and how will they grow in the next 6–12 months?
2. Are tenant, ACL, time, status, or complex business filters required?
3. How frequent are writes, updates, and deletions, and how soon after a write must it be searchable?
4. Is exact linear scan acceptable, or is ANN required for latency and throughput?
5. Does the team already operate PostgreSQL or another database whose transactions, backups, and monitoring can be reused?
6. Do region, compliance, or private-deployment constraints apply?

For only tens of thousands of static vectors, one user, and acceptable seconds-level queries, an in-process exact baseline can be enough. Evaluate database extensions, dedicated databases, or managed services systematically only when growth, tail latency, frequent updates, strict filtering, replication, or disaster recovery demand them.

## Hard-constraint checklist

Write each constraint as a number or explicit semantic before selection. “Fast,” “large scale,” and “high availability” are not acceptance criteria.

| Dimension | What to record | Example |
| --- | --- | --- |
| Data | point count, growth, dimensions, dtype, payload size | 2,000,000 × 768 float32; 1% daily increment |
| Query | QPS, concurrency, top-k, hybrid/batch query | 30 steady QPS; 100 peak QPS |
| Filtering | fields, combinations, selectivity, ACL group size | 50% / 5% / 0.1% selectivity |
| Writes | upsert, update, delete, batch size, searchable latency | P95 searchable within 30 seconds |
| Quality | ANN recall and business-relevance floor | evaluate exact top-k and human gold separately |
| SLO | p50/p95/p99, error rate, availability | never report mean latency alone |
| Failure | RPO, RTO, region/node failure scope | up to five minutes lost; restore within two hours |
| Security | tenant, ACL, encryption, audit, data residency | unauthorized query must fail closed |
| Operations | deployment, upgrade, monitoring, backup, on-call ability | who responds to index/replica alerts on weekends |
| Cost | compute, storage, replicas, snapshots, network, people | monthly and per-million-query estimate |

These values are a template, not recommended defaults. They must come from your traffic, regulations, and budget.

## Responsibility boundaries for four candidate types

### 1. Exact scan or ANN library

A library such as [Faiss](https://github.com/facebookresearch/faiss) provides vector-index and search primitives. It fits offline experiments, a single-node service, or an exact/ANN baseline. It does not automatically provide a business API, authorization, tenant isolation, transactions, backup, replication, or online schema evolution. The application team retains those responsibilities.

### 2. A vector extension for an existing database

[pgvector](https://github.com/pgvector/pgvector) adds vector types and distance queries to PostgreSQL, making SQL, relational fields, transactions, and current operations reusable. It does not remove benchmarking: validate ANN indexes, filter selectivity, index build, write amplification, delete bloat, vacuum, and upgrades against actual load.

### 3. A self-hosted dedicated vector database

Dedicated systems commonly combine collections, payload filters, shards, replicas, and snapshots, which fits retrieval as an independent platform component. The cost is another distributed system to capacity-plan, upgrade, monitor, recover, and harden. When using [Qdrant documentation](https://qdrant.tech/documentation/) to verify concepts, record current product behavior separately from general database principles.

### 4. Managed service

A managed service may reduce node, patch, and some backup work. It does not define embedding space, data quality, ACL, evaluation, cost limits, vendor-exit path, or incident response for you. Verify data residency, import/export, backup visibility, network charges, and limits.

## Build a reproducible bake-off

### Step 1: freeze test assets

- Sample representative vectors, payloads, tenants, and deletion states from the production distribution, and de-identify them.
- Freeze a query set, human or behavioral relevance gold, and authorized identities.
- Record filter conditions and selectivity for every query.
- Retain frequent, long-tail, no-answer, multilingual, near-duplicate, and authorization-boundary cases.
- Generate ANN ground truth by exact full search, but do not mistake exact neighbors for human relevance ground truth.

Version data, queries, gold labels, generation scripts, and checksums. Every candidate uses the same input.

### Step 2: lock experiment conditions

Record hardware/instance, CPU/GPU, memory, disk, region, client and server versions, index type/parameters, replication factor, shard count, batch size, concurrency, warm-up procedure, and test duration. Measure cold start, warmed steady state, and long stress separately. Do not place results from different hardware or cache state side by side as a fair comparison.

### Step 3: measure quality and system metrics together

| Category | Report at least | Why |
| --- | --- | --- |
| ANN quality | Recall@k against exact top-k | Shows how many exact neighbors approximation misses |
| Business quality | Recall@k, MRR, nDCG, or task success | Exact neighbors can still be irrelevant |
| Latency | p50, p95, p99 by query type/selectivity | Averages hide tail congestion |
| Throughput/stability | QPS, concurrency, error/timeout rate | Avoid optimizing one-request latency only |
| Resources | memory, disk, CPU/GPU, network | Quality gain can consume more resources |
| Lifecycle | build, load, upsert, delete, searchable latency | Online data is not a read-only snapshot |
| Operations | scale, rebuild, backup, recovery, failover duration | Normal queries are one part of lifecycle |

For each frozen data snapshot, trusted identity, and filter, let $K=\min(k, |D_{\mathrm{eligible}}|)$. Then:

$$
\mathrm{ANN\ Recall@k}
=
\frac{|ANN\ top\text{-}K\cap exact\ top\text{-}K|}{K}
$$

If **K=0**, record **empty_eligible** or not-applicable. Do not count a secure empty result as zero. If ANN returns fewer than the available K, the gap remains a quality or availability problem. The metric measures preservation of exact ranking by the approximate algorithm only. Business gold must also be limited to items the subject should access under the current time and policy revision. Use [[evaluation-framework/00-index|Evaluation Framework]] for gold and online metrics.

### Step 4: make filtering first-class

The same index can behave very differently with no filter, half the candidates retained, and only one thousandth retained. At each selectivity tier test:

- whether filtering happens before candidate generation, during generation, or after top-k;
- whether enough authorized results return;
- how p99 and ANN recall change;
- whether tenant/ACL boundaries always fail closed;
- storage and write cost of payload indexes.

Testing random vectors without filtering cannot prove a production RAG query works.

### Step 5: test updates, failures, and recovery

Mix queries, upserts, deletes, and index maintenance. Induce client-timeout retries, process restarts, node unavailability, and disk pressure. Recover in isolation as described in [[vector-databases/06-backup-recovery-and-migration|Backup, Recovery, and Migration]], then check space contract, point/tombstone count, ACL, and gold queries. If a candidate cannot meet RPO/RTO, record it directly in the decision rather than postponing it until after release.

## Cost is not a unit price

Total cost includes at least:

- vectors, payload, indexes, WAL/logs, replicas, and snapshot storage;
- continuous service, batch rebuild, backup/recovery, and inter-region network;
- monitoring, upgrades, capacity planning, security audit, and on-call labor;
- data migration, dual write/read, and vendor-exit engineering.

Compare under the same reliability and retention conditions. Do not directly compare self-hosting with one replica/no backup to a managed price with replicas and backup.

## Decision matrix and ADR

First set non-negotiable elimination gates, then score remaining candidates. Weights come from the business; do not back-solve them to make a preselected product win.

| Condition | Type | Candidate A | Candidate B | Evidence |
| --- | --- | --- | --- | --- |
| Zero ACL escapes | Must pass | pass/fail | pass/fail | security-test report |
| Meets p99 latency | Must pass | value | value | cold/warm results |
| Recovery meets RTO | Must pass | duration | duration | recovery rehearsal |
| Business nDCG | Weighted | value | value | gold-query evaluation |
| Three-year total cost | Weighted | value | value | cost model |

An ADR states at least: problem and constraints, candidates, experiment version, choice, reasons not chosen, known risks, migration/exit condition, review date, and owner. “Re-evaluate at a stated point-count, p99, or filtering-failure threshold” is actionable; “switch later when scale grows” is not.

## Common mistakes

- Using random vectors and single-thread mean latency as the business workload.
- Reporting QPS but not ANN or business quality.
- Comparing latency after tuning indexes to different recall.
- Ignoring filter selectivity, updates, deletion, and searchable latency.
- Treating a vendor public benchmark as evidence for your workload.
- Claiming disaster recovery is validated without a recovery rehearsal.
- Wrapping a prototype library as a database without authorization, concurrency, backup, or audit.

## Practice

For an internal RAG system with two million chunks, 2% daily updates, department ACLs, 80-QPS peak, and data required to stay on the organization's network:

1. Define at least five must-pass gates and five weighted conditions.
2. Compare an exact/library route, pgvector, and a dedicated vector database.
3. Design fifty authorization-boundary queries and three filter-selectivity tiers.
4. Explain the difference between exact ground truth and business gold.
5. State fault injection, isolated recovery, and exit conditions.
6. Do not invent performance numbers that have not been measured.

## Mastery check

- [ ] I can decide whether a new system is needed before comparing products.
- [ ] Every gate has an executable test and pass condition.
- [ ] Candidates use the same data, hardware, versions, cache state, and concurrency.
- [ ] I report ANN recall, business quality, tail latency, throughput, and resources together.
- [ ] I cover filtering, tenants, writes, deletes, failures, and recovery.
- [ ] The ADR records evidence, risk, exit conditions, and review date.

## Next step

Continue to [[vector-databases/08-project-toy-vector-store|Project: toy vector store]].

## References

- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [pgvector official repository](https://github.com/pgvector/pgvector)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/)
- [Qdrant: Distributed deployment](https://qdrant.tech/documentation/scaling/distributed_deployment/)
- [PostgreSQL: Backup and Restore](https://www.postgresql.org/docs/current/backup.html)
- [PostgreSQL: High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html)

Sources were retrieved on 2026-07-22. Revalidate product functionality, defaults, hosted terms, and performance under the locked version and your environment.
