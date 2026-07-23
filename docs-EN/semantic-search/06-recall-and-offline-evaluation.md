---
title: "Recall and Offline Evaluation"
tags:
  - ai-agent-engineer
  - semantic-search
  - evaluation
aliases:
  - Offline retrieval evaluation
  - Retrieval Evaluation
source_checked: 2026-07-21
source_baseline: "MS MARCO, BEIR, and MTEB original papers and TREC official
  resources through 2026-07-21"
content_origin: original
content_status: dynamic
lang: en
translation_key: 语义搜索/06-召回与离线评测.md
translation_source_hash: 9e9798de400de4ee3dc7dc5849168e230557214cddcad341ff27a752f9c7e73c
translation_route: zh-CN/语义搜索/06-召回与离线评测
translation_default_route: zh-CN/语义搜索/06-召回与离线评测
---

# Recall and Offline Evaluation

## Learning objective

Retrieval optimization must answer: “for which queries, under which authorization and time conditions, against which baseline, and what improved?” This lesson builds a query/qrels dataset, four core metrics, sliced error classification, and release gates. It also explains why a public benchmark, ANN recall, or an overall average cannot independently decide a production rollout.

## What an evaluation set should represent

The query set should cover:

- high-frequency online intents and their natural frequency;
- high-risk but low-frequency authorization, financial, medical, and safety queries;
- short questions, long descriptions, colloquial phrasing, typos, and abbreviations;
- error codes, model numbers, numbers, dates, negation, and conditions;
- paraphrases, cross-language queries, and domain terminology;
- multi-hop, multi-intent, and clarification-needed queries;
- no-answer, unauthorized, unpublished, and indexing-delay cases;
- new documents, new tenants, and distribution drift.

Randomly sampling online queries preserves frequency but can drown out high-risk long tails. Human templates can fill boundaries but may be overly neat. Combine both and record sampling sources and weights.

## Avoid data leakage

If adjacent chunks from the same original fall into train and test separately, a model can earn inflated results from near-duplicate content. Split by canonical source/document groups; time-sensitive systems should also validate forward in time:

- train: tune models or learn fusion;
- validation: select windows, thresholds, weights, and query policy;
- test: report once after freezing decisions;
- shadow/online: observe real distribution and business effects.

Do not repeatedly inspect test results and tune. That turns the test set into validation.

## Qrels and the judgment pool

Qrels commonly use grades 0–3. Build them by:

1. collecting pooled top-k from BM25, dense, hybrid, the old system, and candidate new systems;
2. deduplicating and hiding system origins;
3. independently annotating under a fixed guideline;
4. adjudicating conflicting cases;
5. adding online failures, hard negatives, no-answer cases, and authorization boundaries;
6. saving the guideline, pool, annotators, adjudication, and source revision.

Documents outside the pool are unjudged, not necessarily irrelevant. When systems differ substantially, sample high-ranked candidates unique to the new system so innovative candidates are not systematically penalized.

## Four core metrics

Let R be the set of relevant documents for a query, and let $S_k$ be its first k results.

### Hit@k

$$
\operatorname{Hit@k}=\mathbb{1}(|R\cap S_k|>0)
$$

It asks only “was at least one relevant result hit?” It is intuitive when one piece of evidence suffices, but cannot reflect missed additional evidence.

### Recall@k

$$
\operatorname{Recall@k}=\frac{|R\cap S_k|}{|R|}
$$

The denominator is all judged-relevant documents. Incomplete qrels also affect recall. For multi-evidence/multi-hop tasks, state whether it is computed by document, canonical source, or evidence group.

### MRR@k

If the first relevant result among the first k has rank r:

$$
\operatorname{RR@k}=
\begin{cases}
1/r,& \text{if a relevant result is found}\\
0,& \text{otherwise}
\end{cases}
$$

MRR is the average of RR across queries. It emphasizes the earliest relevant evidence and ignores whether later relevant documents are complete.

### nDCG@k

For graded relevance:

$$
\operatorname{DCG@k}=
\sum_{i=1}^{k}\frac{2^{rel_i}-1}{\log_2(i+1)},
\qquad
\operatorname{nDCG@k}=\frac{\operatorname{DCG@k}}{\operatorname{IDCG@k}}
$$

nDCG accounts for both grade and position, so it suits distinctions such as “direct answer” versus “only topically related.” State the gain and discount formulas because implementations can differ. Before evaluation, also verify ranked IDs are unique and qrels grades are valid. Repeating a high-grade document repeats its gain and can make a faulty implementation report nDCG greater than 1.

## No-answer and safety gates

Queries with no positive qrels should not be mechanically put in Recall/MRR/nDCG denominators, because the meaning of “0/0” is unclear. Report separately:

- no-answer precision/recall or correct-refusal rate;
- no-result rate and weak-related-result rate;
- `must_not_return` and unauthorized-safety counts;
- draft, expired, deleted, and cross-tenant leakage;
- whether system faults are misreported as no-answer.

Safety violations are usually zero-tolerance gates; high average nDCG cannot offset them. Gates must inspect the complete candidate/rank window entering fusion for every recall route, not only final displayed top-k. An unauthorized document that is later truncated has already polluted trace, fusion, or cache boundaries. The project assigns a guest query for an internal runbook no qrels and requires full candidates from all three routes to be empty.

## Separate ANN recall from business recall

| Metric | Ground truth | Question |
| --- | --- | --- |
| ANN Recall@k | Exact vector top-k | How many geometric neighbors did approximate indexing miss? |
| Business Recall@k | Human/behavior qrels | Did relevant evidence enter candidates? |
| Reranker nDCG | Graded qrels among candidates | How well are candidates ranked? |
| End-to-end task success | Answer/action outcome | Did the user complete the task? |

Optimizing ANN parameters can improve the first row without changing the latter three. Replacing an embedding can change exact neighbors and business quality, so old exact top-k is not ground truth for the new space.

## Macro, micro, and slices

Macro calculates each query first, then averages, so queries with long qrels sets do not dominate. Micro aggregates hit/relevant totals, so large sets carry more weight. Both are useful when labeled explicitly.

At a minimum, slice by:

- high-frequency/long-tail and high-risk queries;
- error codes/entities, paraphrases, numbers/negation;
- language, query length, and document length;
- tenant, ACL size, and filter selectivity;
- new/old documents and source revision;
- BM25-only, dense-only, and both routes hitting.

Report sample count and confidence intervals/resampling uncertainty. A 0.1 improvement on ten queries can be one changed sample, not a stable gain.

## System metrics matter too

Alongside offline relevance, record:

- p50/p95/p99 end-to-end and per-route latency;
- timeout, error, partial, and fallback rate;
- QPS, concurrency, resources, and per-query cost;
- time from write to searchable state, and deletion/authorization-revocation propagation time;
- rank window, candidate count, and near-duplicate ratio;
- query-rewrite count and cache hits;
- index/model/analyzer/qrels revision.

At equal quality, a slower, costlier, or less recoverable system may not be ready to launch.

## Error classification

Inspect each failed query at every layer:

1. **Corpus:** does the correct source exist, remain published, and not deleted?
2. **Chunk:** does the answer exist in a returnable unit?
3. **Representation:** did analyzer/encoder preserve the key meaning?
4. **Filter:** was a positive wrongly excluded, or did a negative cross authorization?
5. **Exact/ANN:** did approximate indexing miss a candidate?
6. **Fusion:** did a weak channel, window, or deduplication suppress a positive?
7. **Qrels:** is a candidate actually relevant but unjudged?
8. **Downstream:** did reranking/generation misuse recalled evidence?

This classification directs repairs more effectively than simply increasing top-k.

## Release gates

An executable gate may require:

- overall and critical-slice Recall@k/nDCG not below baseline;
- zero violations on high-risk/authorization tests;
- no material regression in no-answer/refusal behavior;
- p99, error rate, cost, and candidate budget within targets;
- freshness and deletion propagation within targets;
- reproducibility from locked fixture, parameters, and versions;
- rollback thresholds for shadow/canary operation.

After launch, use clicks, task success, human review, and complaints for monitoring, but clicks are biased by presentation position and existing ranking and cannot directly be treated as unbiased relevance.

## Exercise

Construct 30 queries:

1. 10 real high-frequency, 10 high-risk long-tail, 5 no-answer, and 5 authorization-boundary queries.
2. Write tenant/groups/filters and 0–3 qrels for each.
3. Pool top-10 from BM25, dense, and hybrid, then annotate blindly.
4. Report Hit/Recall/MRR/nDCG@5 and sample count by category.
5. Separately report `must_not_return`, p95/p99, and no-result.
6. Trace one failure through the eight-layer error classification.
7. Write explicit go-live/rollback gates.

## Mastery checklist

- [ ] Train/validation/test split by source group with no near-duplicate leakage.
- [ ] Qrels guideline, pool, adjudication, and revision are traceable.
- [ ] Denominators and purposes of Hit, Recall, MRR, and nDCG are clear.
- [ ] No-answer and safety gates are not forced into ordinary relevance averages.
- [ ] ANN recall and business recall are reported separately.
- [ ] Overall results, critical slices, latency, cost, and freshness jointly decide release.

Next: [[semantic-search/07-project-offline-hybrid-retrieval|Project: Offline Hybrid Retrieval]].

## References

- Nguyen et al., [MS MARCO](https://arxiv.org/abs/1611.09268)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- Muennighoff et al., [MTEB](https://arxiv.org/abs/2210.07316)
- [NIST TREC Data](https://trec.nist.gov/data.html)

Sources were obtained/checked on 2026-07-21. Return to the [[semantic-search/00-index|Semantic Search index]].

