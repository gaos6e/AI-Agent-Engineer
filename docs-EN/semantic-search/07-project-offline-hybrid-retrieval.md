---
title: "Project: Offline Hybrid Retrieval"
tags:
  - ai-agent-engineer
  - semantic-search
  - project
aliases:
  - Offline hybrid-retrieval project
  - Toy Hybrid Search Project
source_checked: 2026-07-22
source_baseline: "Teaching implementation and tests in this knowledge base;
  original BM25/RRF research and current official hybrid-retrieval documentation
  through 2026-07-22; 34 unittest cases verified in normal, -O, -W error, and -O
  -W error modes"
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 语义搜索/07-项目-离线混合检索.md
translation_source_hash: 021e539195c9ec9a847cabccce261316c7b0f10d6a4a9039e2e3f44eb8aca606
translation_route: zh-CN/语义搜索/07-项目-离线混合检索
translation_default_route: zh-CN/语义搜索/07-项目-离线混合检索
---

# Project: Offline Hybrid Retrieval

## Project objective

Build an explainable first-stage retrieval experiment without installing a model, accessing a network, or using secrets:

```text
strict JSON fixture
    ↓
tenant + ACL + status + language/product filter
    ↓
BM25 route ─┐
             ├─ RRF ─ graded Recall/MRR/nDCG + security gate
toy dense ───┘
```

The emphasis is pipeline contracts, fusion, and evaluation, not simulating real model performance.

## Project files

- [[semantic-search/examples/semantic-search-fixture.json|semantic-search-fixture.json]]: 10 fictional documents and 7 queries.
- [[semantic-search/examples/toy_semantic_search.py|toy_semantic_search.py]]: strict parsing, filtering, two-route recall, RRF, and metrics.
- [[semantic-search/examples/test_toy_semantic_search.py|test_toy_semantic_search.py]]: 34 checks.

The fixture root contains `schema_version`, `representation`, `documents`, and `queries`. The parser rejects duplicate JSON keys, NaN/Infinity, excessively large integers that overflow on conversion to float, unknown/missing fields, invalid types, duplicate IDs, incompatible dimensions, zero/non-unit vectors, and inaccessible qrels.

## Fixture design

### Representation

Seven-dimensional hand-authored unit vectors represent refunds, duplicate charges, upload, network, membership, accounts, and internal operations. They guarantee only deterministic mapping inside this teaching fixture:

- they are not trained embeddings;
- they have no tokenizer, model generalization, or cross-language capability;
- exact cosine does not represent ANN;
- current macro metrics cannot be compared with real models.

### Documents

Every record has a stable ID, title/text, tenant, sorted/deduplicated ACL, status, language, product, source revision, and vector. The fixture deliberately includes:

- a high-similarity private document for the beta tenant;
- a draft payment rule for the alpha tenant;
- an internal runbook visible only to the `platform` group;
- two upload documents with the same vector to demonstrate dense ties.

### Queries

Each query contains fixture-supplied tenant, subject groups, allow-list filters, query vector, qrels graded 1–3, and `must_not_return`. Positive qrels must satisfy every authorization and filter for that query. `must_not_return` must exist and be currently inaccessible, so tests cannot become a safety gate that never triggers. These are offline oracle/audit inputs, not a runtime caller’s declaration of trusted identity. Production tenant, groups, and authorization snapshots must come from host IAM.

## Two recall routes

### BM25

The teaching analyzer uses NFKC/casefold, preserves ASCII alphanumeric strings, and turns consecutive Chinese characters into overlapping two-character tokens. BM25 uses term-frequency saturation, document frequency, and length normalization, returning only positive-score documents.

This is not a production Chinese tokenizer. It intentionally makes “my money was charged twice” and “duplicate charge” share no two-character token, demonstrating lexical missed recall; it retains E042 as a whole, demonstrating the advantage of exact identifiers.

### Toy dense

It computes exact cosine/dot/negative-Euclidean on filtered documents and breaks ties stably by document ID. “My money was charged twice” and “duplicate charge” share a hand-authored topic dimension, so dense retrieval finds the correct document. E042 and a general upload document share a score, so dense cannot recognize the exact error code from the vector alone.

## RRF and metrics

Each route contributes only its rank-window results, with default constant 60. The report explicitly declares `report_schema_version=semantic-search-offline-audit-v1` and `visibility=protected_audit` and retains:

- document ID, rank, and score from each route;
- source ranks from BM25/dense for hybrid;
- Recall, MRR, and nDCG for each query;
- macro metrics;
- `security_violations`: audits the full candidate window of each route, recording query, channel, stage, candidate rank, document, and reason rather than checking final top-k only.

The guest query for internal operations has no positive qrels and is excluded from macro relevance averages, but all three routes must return empty and the internal document remains audited through `must_not_return`.

`protected_audit` means the output contains query text, the full candidate window, qrels, forbidden-return sets, and authorization-test material. It may enter only controlled offline evaluation/audit channels; it must not be returned directly to a public search or RAG user. The label does not enforce access control itself. A user-facing projection must be designed separately and exclude those oracle and candidate-window fields.

## Run

From the project root (containing `docs-CN/`, `docs-EN/`, and `.website/`), run without creating a virtual environment or cache:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$script = '.\docs-EN\semantic-search\examples\toy_semantic_search.py'
$fixture = '.\docs-EN\semantic-search\examples\semantic-search-fixture.json'

python -B -W error $script `
    --fixture $fixture `
    --top-k 3 `
    --rank-window 5 `
    --rrf-constant 60

if ($LASTEXITCODE -ne 0) {
    throw "Semantic-search experiment failed; exit code: $LASTEXITCODE"
}
```

## Current reproducible results

With the original fixture, top-k=3, rank-window=5, and RRF constant=60:

| Channel | Macro Recall@3 | Macro MRR@3 | Macro nDCG@3 |
| --- | ---: | ---: | ---: |
| BM25 | 0.750000 | 0.833333 | 0.819553 |
| Toy dense | 1.000000 | 1.000000 | 0.951635 |
| Hybrid RRF | 1.000000 | 1.000000 | 1.000000 |

The following must also hold:

- `document_count=10` and `query_count=7`;
- BM25 is empty for q-double-charge, while dense/hybrid rank d-04-double-charge first;
- dense ranks the general-format document first for q-e042, while hybrid ranks the exact E042 document first;
- all three routes are empty for q-ops-guest;
- `security_violations` is an empty array;
- the beta private document and draft document never enter alpha guest candidates.

These values prove deterministic behavior of the current code and fixture only. They do not prove that hybrid is always better than dense on a real corpus.

## Run the tests

All four interpreter modes must pass. Project correctness must not depend on bare `assert` statements that Python `-O` removes, and it must not ignore warnings in normal mode:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$project = '.\docs-EN\semantic-search'

Push-Location $project
try {
    python -B -m unittest discover -s .\examples -p 'test_toy_semantic_search.py' -v
    if ($LASTEXITCODE -ne 0) {
        throw "Normal-mode tests failed; exit code: $LASTEXITCODE"
    }

    python -B -O -m unittest discover -s .\examples -p 'test_toy_semantic_search.py' -v
    if ($LASTEXITCODE -ne 0) {
        throw "Optimized-mode tests failed; exit code: $LASTEXITCODE"
    }

    python -B -W error -m unittest discover -s .\examples -p 'test_toy_semantic_search.py' -v
    if ($LASTEXITCODE -ne 0) {
        throw "Warnings-as-errors tests failed; exit code: $LASTEXITCODE"
    }

    python -B -O -W error -m unittest discover -s .\examples -p 'test_toy_semantic_search.py' -v
    if ($LASTEXITCODE -ne 0) {
        throw "Optimized warnings-as-errors tests failed; exit code: $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
```

The tests cover strict JSON; representation/vectors (including controlled rejection of large integers); document/query schemas; qrels/authorization consistency; analyzer behavior; three vector metrics; BM25; RRF; filtering; graded metrics; duplicate ranked IDs; leaks across a full candidate window; the protected audit envelope; no-answer; CLI errors; and consistent output in all four interpreter modes.

## Hands-on tasks

### Task A: Observe lexical and semantic complementarity

Add an error-code document/query, then add a synonym query that shares no lexical form. Predict BM25/dense/hybrid rankings independently, then run the check. If results differ from the prediction, explain with analyzer tokens and source ranks.

### Task B: Build hard-filter gates

Add a same-vector document from another tenant, an archived document, and a query with empty subject groups. Test that none appears in BM25, dense, or hybrid—not merely that it is absent from the final result.

### Task C: Change the rank window

Change each route’s window to 1, 2, and 5. Compare source ranks and nDCG for q-e042. Explain why RRF cannot recover a candidate truncated before fusion.

### Task D: Implement Hit@k

Add Hit@k without changing Recall’s definition. Write a test with two qrels and only one hit, proving Hit=1 while Recall=0.5.

### Task E: Migrate real components

List the migration work:

1. analyzer/search engine and index revision;
2. real query/document encoder, batching/cache, and space contract;
3. exact ground truth and ANN parameters;
4. real tenant/ACL identity source;
5. production queries/qrels and a blind pool;
6. p95/p99, cost, freshness, recovery, and rollback.

## Project acceptance

- [ ] Can explain each primary BM25 term and the analyzer’s effect.
- [ ] Can prove filtering takes effect before scoring in both routes.
- [ ] Can identify the gap between toy-dense hand-authored semantics and real embeddings.
- [ ] RRF retains source ranks and does not add raw scores directly.
- [ ] Denominators and no-answer treatment for Recall, MRR, and nDCG are explicit.
- [ ] 34 tests pass in normal, `-O`, `-W error`, and `-O -W error` modes.
- [ ] Fixture, script output, and tests contain no credentials, caches, or network dependency.
- [ ] Do not generalize current metrics into a product-performance conclusion.

## Self-check

1. Why is q-e042 dense nDCG lower than hybrid?
2. Why does an empty BM25 result for q-double-charge not make BM25 useless?
3. Why should q-ops-guest not count as Recall=0?
4. Why must `must_not_return` inspect the full rank window of every recall route rather than only final top-k?
5. Why can duplicate document IDs make nDCG exceed 1?
6. Why is rank fusion still affected by within-channel tie-breaking?
7. After replacing toy vectors with real embeddings, which data must be regenerated?

When finished, return to the [[semantic-search/00-index|Semantic Search index]] and continue with [[reranking/00-index|Reranking]].

## References

- Robertson & Zaragoza, [The Probabilistic Relevance Framework: BM25 and Beyond](https://ir.webis.de/anthology/2009.ftir_journal-ir0anthology0volumeA3A4.0/)
- Cormack, Clarke & Buettcher, [Reciprocal Rank Fusion](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)
- [Elasticsearch: Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [Qdrant: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

Sources were obtained/checked on 2026-07-22. Teaching behavior is defined by the current fixture, script, and tests; dynamic product capability must be rechecked for the locked version.
