---
title: "Similarity, Indexing, and Space Migration"
tags:
  - ai-agent-engineer
  - embedding
  - ann
  - migration
aliases:
  - Embedding version migration
  - Embedding space migration
source_checked: 2026-07-14
source_baseline: Sentence Transformers, Faiss, and provider official embedding
  documentation checked through 2026-07-14
lang: en
translation_key: Embedding/04-相似度索引与版本迁移.md
translation_source_hash: b1ccbf943a854f6ef333dd0b93830316188498d959d4aa75840a9d7088931814
translation_route: zh-CN/Embedding/04-相似度索引与版本迁移
translation_default_route: zh-CN/Embedding/04-相似度索引与版本迁移
---

# Similarity, Indexing, and Space Migration

## Objective

You will treat a vector space as versioned data product whose vectors cannot be mixed. Learn the distinct errors of exact and ANN search, verify metadata filtering, calibrate space-specific thresholds, and migrate models, dimensions, roles, or normalization with dual indexes.

## A complete contract determines space compatibility

Normalize the following fields and generate a contract signature:

$$
H(provider,model,revision,roles,prompts,pooling,dimension,dtype,metric,normalization,preprocessing)
$$

Compare vectors only when they belong to the same explicitly compatible space. Any of the following changes should create a new candidate space or at least force a compatibility review:

- model or immutable revision;
- query/document role, task instruction, or prefix;
- pooling, tokenizer, or truncation policy;
- output dimension;
- dtype or quantization;
- normalization;
- metric; or
- multimodal input organization.

Equal dimensions mean only that array shapes match; they do not mean coordinate axes have the same meaning. The first component of model A and model B has no common basis, so `A-query · B-document` normally has no retrieval semantics.

## Exact search is the evaluation baseline

For one query vector, exact search scores every authorized document with the same metric and determines their order. It is useful for:

- a small corpus or offline gold set;
- verifying scores and tie-breaking;
- ground truth for ANN approximation error; and
- diagnosing filtering, quantization, and index parameters.

Its cost grows with the candidate count, so it does not suit every large-scale online system.

## ANN improves speed; it does not prove relevance

Approximate Nearest Neighbor (ANN) uses index structures to reduce comparisons, commonly trading more memory/build time or some missed neighbors for lower latency. Libraries such as Faiss offer multiple exact and ANN structures; select concrete parameters from official documentation and local load testing.

Keep two questions separate.

### ANN recall

Freeze the same data snapshot, embedding space, security filter derived from trusted identity, query, and tie-breaking. Let $D_{\mathrm{eligible}}$ be the eligible candidates after filtering, and $K=\min(k, |D_{\mathrm{eligible}}|)$. Then compare ANN and exact top-$K$:

$$
\operatorname{ANNRecall@k}
=
\frac{|ANN_K\cap Exact_K|}{K}
$$

This asks whether the approximate index found exact neighbors; it needs no business relevance labels. When $K=0$, report `empty_eligible` or not applicable rather than recording a safe empty result as 0. If ANN actually returns too few results, preserve that as low recall or a service-failure signal.

### Business Recall@k

Compare retrieved results to human or behavior gold. Under a frozen test population, time, and policy revision, the relevant documents that should be accessible are $Relevant_{\mathrm{eligible}}$:

$$
\operatorname{BusinessRecall@k}
=
\frac{|Retrieved_K\cap Relevant_{\mathrm{eligible}}|}{|Relevant_{\mathrm{eligible}}|}
$$

It is affected by model, chunking, filtering, query role, and index behavior. If $Relevant_{\mathrm{eligible}}$ is empty, accept it separately as a no-answer or unauthorized-access case rather than combining the correct refusal with 0 recall. ANN recall can be high while an embedding model does not understand the domain and business Recall is poor. Conversely, a few exact-neighbor differences may not affect relevant documents.

## Metadata filtering must be tested in reality

Tenant, ACL, publication status, language, time, and document type must take effect fail-closed before candidates are returned. Different vector databases, indexes, and query modes can implement:

- pre-filtering;
- filtering integrated during ANN;
- post-filtering; or
- a mixture or refill strategy.

Post-filtering can leave fewer than *k* results, while pre-filtering can alter performance and ANN recall at high selectivity. Do not infer execution semantics from an API name alone.

Acceptance tests should at least include:

1. an unauthorized document whose vector is identical to the query vector;
2. an authorized document with lower similarity;
3. proof that the unauthorized item never appears in candidates, score logs, or parent expansion;
4. explicit behavior when too few results remain; and
5. rejection, rather than global visibility, when tenant or ACL data is missing.

[[vector-databases/00-index|Vector Databases]] and [[semantic-search/00-index|Semantic Search]] develop these concerns further.

## A threshold is not a universal constant

Nearest-neighbor search can generally return something even when all results are irrelevant. If a system uses a score threshold to reject low scores, it must:

- calibrate it separately for every space;
- use development data containing answerable and unanswerable queries;
- define false-positive and false-negative costs;
- inspect language, domain, and query-type slices;
- redo calibration after a model, role, metric, normalization, quantization, or dimension change; and
- evaluate the final policy only once on an independent test set.

Cosine 0.8 does not represent the same relevance probability in two models. Do not repeatedly tune thresholds on a test set and then present the result as a final test score.

## Why an in-place mixed-write upgrade is unsafe

Suppose an index already contains documents from model A. If you write new documents from model B directly into it:

- an A query can compare correctly only with A documents;
- a B query can compare correctly only with B documents;
- one top-*k* mixes two incomparable score scales;
- threshold, metric, and dimension can conflict; and
- a failure cannot be rolled back by only half.

Even if a vector database accepts writes of the same dimension, this is semantic data corruption.

## Dual-index migration process

### 1. Freeze the old space

Record the contract signature, published alias, canonical source revision, item count, deletion watermark, gold/test sets, and current metrics. Stop changing old-contract defaults.

### 2. Create the new space

Create a new collection, index, or namespace under a distinct `space_id`; pin dimension, dtype, metric, normalization, role, and metadata schema. Do not overwrite an old alias by reusing it.

### 3. Rebuild from canonical input

Re-encode the same chunk revision and query fixtures. Do not apply an unsupported transform to old vectors. Validate every write and retain source/input hashes.

### 4. Perform mechanical reconciliation

- item-ID sets match;
- document/query/tenant/ACL/source revision match;
- no zero vector, NaN/Inf, or wrong dimension;
- norm distribution matches the new contract;
- deletions and tombstones have propagated; and
- new-vector count closes against cache hits and failed-item differences.

Mechanical reconciliation establishes data completeness, not sufficient quality.

### 5. Run offline quality and system evaluation

With fixed queries and gold data, search the A index with A queries and the B index with B queries. Compare:

- Recall@k, MRR, nDCG, and per-query delta;
- critical language, domain, and authorization subgroups;
- top-*k* Jaccard and old/new result changes;
- exact and ANN differences;
- P50/P95, throughput, memory, rebuild duration, and cost; and
- no-answer false positives and false negatives at the threshold.

Never use one query vector to search both spaces.

### 6. Shadow and canary rollout

Without affecting user results, have online requests generate two query vectors, search independently, and log de-identified differences. After confirming traffic, cost, and privacy authorization, let a small user percentage read the new alias.

### 7. Switch atomically

Switch the application's published pointer or alias, not hand-edited configuration on individual instances. Record switching revision, time, operator, and rollback condition.

### 8. Keep rollback, then govern deletion

Retain the old space read-only for a defined window. After verifying stability, remove its index, cache, and backups according to retention/deletion policy. A data-subject deletion or ACL revocation cannot wait for migration to finish; it must propagate to every active space.

## Example migration gates

| Type | Gate | Action on failure |
| --- | --- | --- |
| Inventory | Canonical item/ACL/revision reconciliation has zero differences | Block publication and rerun missing items. |
| Numeric | Dimension, finite values, norm, and dtype are all compliant | Quarantine abnormal vectors. |
| Quality | Critical subgroups meet predefined floors | Analyze queries; do not hide regression behind a mean. |
| Security | Unauthorized-access tests show zero leaks | Block immediately. |
| System | P95, error rate, and capacity fit budget | Retune or scale, then retest. |
| Operations | Alias switch, monitoring, and rollback drill pass | Do not enter canary rollout. |
| Governance | Deletion, retention, license, and data processing are approved | Pause migration. |

“The new model has higher average Recall” cannot override a critical ACL or language-subgroup regression.

## Layered experiments for dimension, quantization, and ANN

A migration can change model, dimension, quantization, and index parameters simultaneously. To keep attribution possible:

1. new model, full-dimension float, exact search;
2. same model, reduced-dimension float, exact search;
3. same dimension, quantized exact or approximate search;
4. ANN parameters on the same representation; and
5. only then the combined end-to-end RAG system.

At each layer, compare per-query top-*k* agreement and business metrics with the preceding layer. Otherwise, when quality regresses, you cannot tell whether to revert the model, dimension, quantization, or ANN configuration.

## Runtime drift and integrity

An embedding model normally gives a stable representation for fixed input, but a system can still drift because of aliases, SDK defaults, preprocessing, model deployment, or data distribution. Monitor:

- contract signature and deployment revision;
- canary input dimension, norm, hash or tolerance, and top-*k*;
- input language, length, and domain distribution;
- query no-result or low-score rate;
- top-*k* diversity and repeated parents;
- gold replay and critical queries; and
- index count, tombstones, and cache reconciliation.

Do not put random online source text into ordinary monitoring. Use authorized canaries and aggregate statistics.

## Common mistakes and investigation

- **Old and new models write to one collection:** stop writes immediately, inventory by space ID, and do not try to repair it from scores.
- **ANN recall falls, so the model is replaced:** first separate index approximation error from business relevance.
- **Top-*k* is too short after filtering:** inspect pre/post-filter semantics and refill configuration.
- **False positives grow after migration:** the score scale changed; recalibrate on a development set.
- **A canary cannot roll back:** read alias, write jobs, and caches lack one version switch.
- **The old space is deleted too early:** there is no stable observation window or rollback drill.
- **The old space is never deleted:** cost and data-deletion obligations keep accumulating.

## Exercises

1. Draw a dual-index data flow from A (768d cosine) to B (1024d normalized dot), marking where the query must be encoded twice.
2. Construct a filter test in which the unauthorized vector is most similar, and explain why checking only the final UI is insufficient.
3. Give two counterexamples in which ANN recall and business Recall are high and low in opposite directions.
4. Write eight switch gates that cover mechanical, quality, security, system, and governance concerns.
5. Design a layered experiment that leaves the model unchanged but changes quantization and ANN.
6. Define propagation and reconciliation for an ACL revocation across old/new indexes, caches, and backups.

## Mastery check

- [ ] I use the complete contract signature, rather than only dimension, to decide space compatibility.
- [ ] I distinguish exact ground truth, ANN recall, and business relevance.
- [ ] I verify actual filtering semantics and unauthorized-access boundaries.
- [ ] I calibrate score thresholds separately for each space.
- [ ] I do not mix old and new vectors; a query is encoded separately for both spaces.
- [ ] Migration includes canonical rebuilding, mechanical reconciliation, offline evaluation, shadow/canary rollout, atomic switching, rollback, and governed deletion.
- [ ] I layer model, dimension, quantization, and ANN experiments so results remain attributable.

## Summary and next step

Space isolation and dual indexes make migration operationally controllable. Whether a switch is worthwhile still depends on fixed queries and gold data, subgroups, and system cost. Next, run the complete offline project: [[embeddings/05-evaluation-and-migration-project|Evaluation and Migration Project]].

## References

- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [OpenAI: Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Gemini API: Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Cohere: Introduction to Embeddings](https://docs.cohere.com/docs/embeddings)

Sources were obtained on 2026-07-14. The filtering and ANN behavior of a particular vector store must be verified against that product's current official documentation and with unauthorized-access and recall tests. Return to [[embeddings/00-index|Embeddings]].
