---
title: "Evaluation and Migration Project"
tags:
  - ai-agent-engineer
  - embedding
  - retrieval-evaluation
  - migration
  - project
aliases:
  - Embedding evaluation project
  - Embedding Space Lab
source_checked: 2026-07-22
source_baseline: Hand-authored vector exercise using the Python 3.11 standard
  library; 32 unit tests verified on 2026-07-22 in normal, -O, -W error, and -O
  -W error modes
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: Embedding/05-评测与迁移项目.md
translation_source_hash: 977702e80acc93acd01c275c2d118254d12ce41f754f0b03ac10103b01a5a910
translation_route: zh-CN/Embedding/05-评测与迁移项目
translation_default_route: zh-CN/Embedding/05-评测与迁移项目
---

# Evaluation and Migration Project

## Project objective

This project uses two fully isolated hand-authored vector spaces to practice four things:

1. space contracts and vector-input validation;
2. exact similarity search after ACL filtering;
3. Recall@k, MRR, nDCG, and subgroup reporting; and
4. inventory/canonical reconciliation and top-*k* change audits for model migration.

It does not download or run a real embedding model, and its output explicitly says `hand-authored vectors`. That can validate code and gates; it does not represent the business effectiveness of any model.

## Project files

- [[embeddings/examples/evaluate_embedding_space.py|evaluate_embedding_space.py]]: strict loading, mathematical functions, retrieval, metrics, inventory, and migration audit.
- [[embeddings/examples/embedding-fixture.json|embedding-fixture.json]]: two spaces, 20 in-space items, and four query cases with graded relevance.
- [[embeddings/examples/test_evaluate_embedding_space.py|test_evaluate_embedding_space.py]]: 32 standard-library `unittest` cases.

The script outputs only IDs, scores, metrics, and contract summaries; it does not print real credentials. The fixture contains only teaching text and hand-authored vectors.

## The two spaces are deliberately incompatible

| Field | toy-v1 | toy-v2 |
| --- | --- | --- |
| provider/model | local-fixture / toy-bi-encoder | Same teaching name |
| revision | v1 | v2 |
| dimension | 4 | 5 |
| metric | cosine | dot |
| normalized | false | true |
| dtype | float32 | float32 |
| items | 6 documents + 4 queries | Same canonical items |

Even though both spaces use the same text and item IDs, their revision, dimension, metric, and normalization differ, so their vectors cannot be compared across spaces. `migration_audit` consequently reports `vectors_directly_comparable=false`.

Within each space, query and document roles are explicitly `query` and `document`. A real model might use different methods, task types, or prompts; write the actual values into its contract.

## Strict input gates

The fixture top level permits only `contracts/items/queries`. The loader rejects:

- duplicate JSON keys, NaN/Infinity, and fixtures larger than 5 MiB;
- extra or missing fields;
- duplicate spaces or items;
- an unknown space or wrong role;
- booleans masquerading as numbers, wrong dimensions, zero vectors, NaN/Inf, and oversized integers that overflow on float conversion;
- `normalized=true` vectors whose norm is outside tolerance;
- empty text, duplicate ACLs, and invalid source revision;
- missing query/gold references and grades outside 1..3; and
- a gold document that is not authorized for the query principal.

Text is normalized to LF and Unicode NFC before `content_sha256` is calculated. Migration audit compares canonical data by role, text, ACL, source revision, and hash.

## Retrieval flow

For one space, `search`:

1. finds the query item in that space;
2. verifies it uses `contract.query_role`;
3. returns empty fail-closed results when the principal has no groups;
4. retains only same-space, document-role documents whose ACL intersects the principal's groups;
5. calculates an exact score with that space's `contract.metric`;
6. breaks ties stably by descending score then ascending item ID; and
7. returns top-*k*.

An unauthorized document is not even admitted to scoring candidates when its vector is identical to the query vector. The project demonstrates group OR semantics only, not a complete tenant or IAM implementation.

There is no score threshold, so low- or zero-score authorized documents can fill top-*k*. This is intentional: nearest-neighbor retrieval does not mean an answer is available. Calibrate a no-answer threshold by space on real development data; this fixture does not evaluate end-to-end abstention.

## Three retrieval metrics

### Recall@k

Treat every document with relevance grade greater than 0 as relevant:

$$
\operatorname{Recall@k}
=
\frac{|Retrieved_k\cap Relevant|}{|Relevant|}
$$

It asks whether necessary candidates were all found, not how relevant items are ordered among themselves.

### MRR

For each query, find the rank $r$ of the first relevant item, record $1/r$, use 0 for a miss, and average across queries. MRR emphasizes how early the first relevant item appears, but cannot guarantee that all needed evidence is present.

### nDCG@k

The project permits grades 1..3. Gain at rank $i$ is:

$$
DCG@k
=
\sum_{i=1}^{k}
\frac{2^{rel_i}-1}{\log_2(i+1)}
$$

Then divide by the ideal ordering's `IDCG@k`. nDCG penalizes high-grade evidence ranked below low-grade evidence. Every item ID in one ranked list must be unique: repeating a high-grade ID repeats its gain and can even fabricate nDCG above 1. The project therefore rejects duplicate IDs at the shared Recall, MRR, and nDCG entry point and verifies that qrels grades are non-boolean integers from 1 through 3. Metrics still need to be read together: Recall 1.0 can coexist with lower nDCG.

## Run the project

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not write Python bytecode caches, keeping the project directory reproducible.
python -B -W error '.\docs-EN\embeddings\examples\evaluate_embedding_space.py'  # Run offline exact retrieval and migration audit with default k=3.
```

You can specify `k` or the fixture explicitly:

```powershell
python -B -W error '.\docs-EN\embeddings\examples\evaluate_embedding_space.py' --k 2  # Override the default and retain only the first two authorized candidates per query.
```

A non-positive integer `k` fails rather than silently reverting to a default.

## Current deterministic results

As of 2026-07-22, at default `k=3`:

| Space | Item count | Theoretical raw-vector bytes | Mean Recall@3 | MRR | Mean nDCG@3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| toy-v1 | 10 | 160 | 1.0 | 1.0 | 1.0 |
| toy-v2 | 10 | 200 | 1.0 | 1.0 | 1.0 |

`estimated_raw_vector_bytes = item_count × dimension × 4`; it excludes IDs, metadata, indexes, alignment, and replicas.

The migration report says:

- inventory match: true;
- canonical match: true;
- mechanical gates pass: true;
- all three mean quality deltas: 0;
- mean top-*k* Jaccard: 0.875; and
- quality decision required: true.

Why are all mean quality metrics equal while Jaccard is not 1? For `image-example`, both spaces rank the first relevant document correctly, but the other two zero-score candidates change because coordinates and tie-breaking differ. Business metrics did not regress, yet the candidate set changed. A real migration must inspect per-query changes and downstream impact rather than only three averages.

Passing mechanical gates does not automatically authorize production release. License, privacy, latency, cost, critical subgroups, and rollback still require a decision, which is why the report always retains `quality_decision_required=true`.

## Run the tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not leave test-generated cache files in the course directory.
python -B -m unittest discover -s '.\docs-EN\embeddings\examples' -p 'test_evaluate_embedding_space.py' -v  # Run every unit test normally and show each case.
python -B -O -m unittest discover -s '.\docs-EN\embeddings\examples' -p 'test_evaluate_embedding_space.py' -v  # Repeat under optimized mode to prove no dependency on bare assert.
python -B -W error -m unittest discover -s '.\docs-EN\embeddings\examples' -p 'test_evaluate_embedding_space.py' -v  # Promote warnings to errors to reveal deprecations or resource problems.
python -B -O -W error -m unittest discover -s '.\docs-EN\embeddings\examples' -p 'test_evaluate_embedding_space.py' -v  # Combine optimized mode and strict warnings for the strongest execution mode.
```

Tests cover:

- contract signatures and invalid dimension, metric, role, and dtype;
- normalization, cosine, dot product, Euclidean distance, and invalid numeric values;
- strict JSON, exact fields, duplicate IDs, and wrong spaces;
- vector dimension, booleans, zero vectors, and normalized norms;
- query/gold existence, grade validity, and authorization;
- expected rankings in two spaces, pre-score ACL filtering, and fail-closed empty principals;
- known Recall/MRR/nDCG cases and fail-closed handling for duplicate rankings and invalid grades;
- subgroups, inventory bytes, and norms;
- migration inventory and canonical drift;
- byte-for-byte identical normal and `-O` CLI output; and
- rejection of non-positive `k` with UTF-8 stderr.

## Reading the migration audit

### Mechanical gates

- `inventory_match`: the old and new item-ID sets are identical.
- `canonical_match`: for the same ID, role, text, ACL, source revision, and hash match.
- `mechanical_gates_pass`: both preceding conditions pass.

These gates detect missed encoding, wrong source text, and ACL drift. They do not compare vector values; a new space should normally produce different vectors.

### Quality delta

For the same queries and gold data, subtract the old mean from the new mean. A delta of 0 does not mean the spaces are identical or no critical query regressed. Inspect `details`, subgroups, and `per_query_agreement`.

### Top-k Jaccard

$$
J(A,B)=\frac{|A\cap B|}{|A\cup B|}
$$

It measures candidate-set change, not which side is more relevant. Interpret it with human relevance, reranking, and final answers.

## Required practice

### A. Create an explainable regression

Change the vector for `q-retry` or `doc-retry` in toy-v2 so a high-grade relevant document falls to second or fourth position. Predict which of Recall, MRR, and nDCG changes, then run the check. Do not change gold labels to fit the result.

### B. Test canonical drift

Change only the toy-v2 body text of `doc-timeout`, retaining its item ID. Inspect `canonical_mismatches` and the mechanical gate. Explain why successful vector generation still must not permit switching.

### C. Test role and normalization errors

Independently:

- change a document role to `query`;
- give a `normalized=true` vector norm 2; and
- replace one numeric value with a boolean.

Record which loader layer fails and how the unblocked error would pollute an index.

### D. Add a subgroup

Add a proper-name, numeric, English, or code query without changing existing queries. Assign each a grade 1..3 and compare overall and subgroup metrics. Ensure gold documents are visible to the principal.

### E. Design a no-answer threshold experiment

Do not write a “universal 0.8 threshold” directly into the script. First prepare answerable and unanswerable development sets, calibrate toy-v1 and toy-v2 separately, record precision/recall or false-positive/false-negative outcomes, then evaluate on an untuned test set.

## Minimal changes to use a real model

Keep `QueryCase`, relevance, and metric layers unchanged, then add a provider adapter:

1. pin canonical texts and input hashes;
2. retain official model/revision/role/dimension/metric/normalization/SDK/verification date;
3. encode documents and queries separately according to the official contract;
4. reconcile each response by ID, dimension, finite values, and norm;
5. write a new `space_id` without overwriting toy or old production space;
6. compare candidate models with exact float retrieval first;
7. then independently test dimension reduction, quantization, ANN, and reranking; and
8. keep raw per-query results as auditable artifacts without committing sensitive source text or large vector data.

When keys or network access are unavailable, record “not executed” explicitly; never present fixture results as real-model scores.

## Release acceptance checklist

- [ ] Gold data, development data, and held-out test data have separate purposes.
- [ ] Canonical items, ACLs, revisions, and deletion watermark are reconciled.
- [ ] Every space has a complete signature and physical or logical isolation.
- [ ] Query/document roles follow current official documentation.
- [ ] The quality report includes per-query results, critical subgroups, and multiple metrics.
- [ ] Score threshold is calibrated separately on each space's development set.
- [ ] Latency, throughput, storage, rebuild time, and cost are within budget.
- [ ] Unauthorized access, empty-principal, and parent-expansion tests fail closed.
- [ ] Shadow/canary rollout, atomic aliasing, monitoring, and rollback drill pass.
- [ ] License, privacy, retention, and deletion policy are approved.
- [ ] Fixture results are not described as real-model effectiveness.

## References

- [MTEB Overview](https://docs.mteb.org/overview/)
- [MTEB original paper](https://arxiv.org/abs/2210.07316)
- [Sentence-BERT](https://arxiv.org/abs/1908.10084)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)

Sources were obtained on 2026-07-22. When finished, return to [[embeddings/00-index|Embeddings]] and continue with [[vector-databases/00-index|Vector Databases]].
