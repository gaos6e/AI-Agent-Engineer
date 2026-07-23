---
title: "Metrics, latency, cost, and fallbacks"
tags:
  - ai-agent-engineer
  - reranking
  - production
aliases:
  - Reranker evaluation and fallback
  - Reranker metrics and fallbacks
source_checked: 2026-07-22
source_baseline: BEIR and BERT reranking papers, plus Sentence Transformers and
  Elasticsearch documentation, checked through 2026-07-22
lang: en
translation_key: Reranking/06-指标延迟成本与降级.md
translation_source_hash: 6c247fc2c39cdf5a924eab45954f22f0729af14fb31178848a08341167a8f37b
translation_route: zh-CN/Reranking/06-指标延迟成本与降级
translation_default_route: zh-CN/Reranking/06-指标延迟成本与降级
---

# Metrics, latency, cost, and fallbacks

## Goal of this lesson

A reranker is worth deploying only when candidates contain answers, ordering improves, tail latency and cost are acceptable, and failures remain safe and usable. This lesson organizes quality, system, failure, and end-to-end metrics into release gates, and requires a fallback to be evaluated in advance as a normal traffic path.

## Layer quality metrics

| Layer | Metric | Question answered |
| --- | --- | --- |
| First stage/window | Candidate Recall@w | Did a positive enter the model’s view? |
| Ranking | MRR@k | How early does the first relevant evidence appear? |
| Ranking | nDCG@k | Are graded relevant documents near the top? |
| Output purity | Precision@k | What proportion of top-*k* is relevant? |
| Diversity | Canonical/source coverage | Is the result filled by near duplicates from one source? |
| Security | must-not / unauthorized count | Did tenant, ACL, status, or time constraints fail? |
| Downstream | Grounded correctness, citations, task success | Did RAG actually use the ordering benefit? |

Compare at least:

1. the original first-stage order;
2. the new reranker;
3. the old reranker, if one exists;
4. every fallback;
5. before and after deduplication/business rules; and
6. key query slices.

When candidate recall is low, repair recall or the window first. Conditional nDCG restricted to queries with a positive in the window can diagnose the model, but release decisions still use all-query end-to-end results.

> [!warning] An evaluator cannot add first-stage candidates
> When current Sentence Transformers `CrossEncoderRerankingEvaluator` is given `documents`, it can by default add every positive to the reranking list even if the positive was not among the supplied candidates. Such results diagnose an ordering upper bound only when positives are visible; they are not end-to-end release metrics. Freeze real first-stage candidate IDs and the `window`, report Candidate Recall first, and verify that the evaluation configuration does not add missed positives. Otherwise, a recall gap is misrepresented as reranker benefit.

## Analyze paired differences, not averages alone

Compare before and after for the same query:

- how many improve, stay equal, or regress;
- whether high-risk queries regress;
- which first-stage rank moves to which final rank for positives;
- whether failures cluster by language, length, numbers/negation, or source; and
- uncertainty in the difference from bootstrap or randomization.

An overall nDCG increase can come from many simple queries improving while a few important financial queries regress severely. Release gates need slices that must not degrade.

## Measure system metrics separately

End-to-end reranking latency includes:

```text
Candidate preparation/serialization
    + network/queue
    + tokenizer
    + model inference
    + output parsing/validation
    + post-processing/diversity
```

Report p50/p95/p99/max, timeouts, and queue depth, segmented by:

- candidate window;
- query/body token bucket;
- batch size and concurrency;
- model, hardware, and region;
- normal versus fallback path;
- cache hit or miss; and
- tenant or priority.

Offline pairs per second on one machine is not multi-tenant online p99.

## Cost model

Local Cross-Encoder deployment is mainly shaped by pairs × tokens, hardware, resident replicas, and peak redundancy. A hosted or LLM reranker may charge by request, document, or token and add network and retry cost. Estimate at least:

- average and peak query rate × window;
- input-token distribution;
- batch limit per call;
- retry, fallback, and shadow dual-run traffic;
- minimum replicas, disaster recovery, and warmup;
- cache hits and invalidation; and
- logging, evaluation, and data retention.

Prices and limits are dynamic product facts. Record the retrieval date and contract/version for a delivery; do not turn tutorial numbers into long-term capacity planning.

## Failure matrix

| Failure | Detection | Default action | Record |
| --- | --- | --- | --- |
| Total deadline insufficient | Remaining-time gate | Do not call; fall back directly | `deadline_exhausted` |
| Timeout | Client/server timeout | Limited retry or fallback | `timeout` |
| Rate limit/overload | Explicit status code or queue | Do not amplify retries; circuit break | `rate_limited` |
| 5xx/model not loaded | Error code or health check | Fall back and alert | `provider_error` |
| Empty response | Schema validation | Invalid-output fallback | `empty_output` |
| Missing/duplicate/unknown ID | Exact-set validation | Invalid-output fallback | `id_contract` |
| NaN/Inf/wrong type | Numeric validation | Invalid-output fallback | `score_contract` |
| Revision mismatch | Response metadata | Reject and fall back | `revision_mismatch` |
| All candidates hard-filtered | Safe window is empty | Return a safe empty result | `empty_safe_window` |

Different failures may share one fallback order, but monitoring must distinguish them so capacity, code, provider, and data problems can be separated.

## Fallback design

The most common path is safe first-stage ranking:

1. Hard filters have already run.
2. Take the same candidate window.
3. Preserve first-stage rank and stable tie-breaking.
4. You may continue to run deterministic canonical caps.
5. Return `rerank_applied=false` and `fallback_reason`.
6. Do not disguise missing model output as a normal low score.

Evaluate fallback MRR/nDCG, end-to-end answers, security, p99, and peak capacity too. If a model-service outage pushes all traffic back to search or another service, rehearse that capacity.

## Retries, caching, and circuit breaking

- Respect one total request deadline rather than letting every layer consume its own full timeout.
- Retry only explicitly transient errors, with jitter and a bounded count.
- Scoring requests usually have no external write effect, but they repeat cost and resource use.
- Circuit breakers prevent a queue avalanche during failure.
- Cache keys include query, candidate IDs plus source revisions, model/prompt/schema, rules, and required authorization summary.
- Do not reuse responses containing sensitive candidates across permission boundaries.
- Warm a model before upgrade traffic arrives so the first batch does not time out together.

## Release process

1. **Offline**: freeze queries/qrels, first-stage snapshot, and candidate text.
2. **Replay**: exercise normal operation, every failure, and different windows, lengths, and concurrency levels.
3. **Shadow**: run the new model without affecting users; compare score, order, and latency.
4. **Canary**: send a small amount of real traffic while monitoring key slices and fallback.
5. **Progressive expansion**: confirm queue behavior, cost, and downstream benefit.
6. **Rollback**: restore model, prompt, rules, and switches independently.

A release-gate table should include candidate recall, overall and key-slice nDCG, non-regression slices, p95/p99, timeout/fallback rate, cost per query, zero security violations, and end-to-end answer metrics. Thresholds come from local SLOs, not assumptions in this lesson.

## Common mistakes and how to investigate them

- **Only reranked nDCG is reported**: add first-stage, fallback, and candidate recall.
- **Average latency meets target but p99 explodes**: bucket by token/window/queue.
- **A model failure returns an empty list**: compare a safe first-stage fallback.
- **Retries amplify a failure**: use a total deadline, jitter, circuit breaking, and capacity protection.
- **Cache hits use old body text**: include source/model/prompt revisions in the key.
- **Offline quality improves but RAG does not**: inspect evidence budget and prompt order.
- **A key slice regresses but the average hides it**: set hard gates.

## Exercise

Write a release-gate table with:

1. Candidate Recall@30 and nDCG/MRR/Precision@8.
2. No regression for financial, permission, negation, and long-document slices.
3. p95/p99, timeout, fallback, and cost per query.
4. Exact validation for four invalid-output types.
5. A fallback-capacity rehearsal when the circuit is open.
6. Shadow/canary triggers and one-click rollback conditions.

## Mastery check

- [ ] Quality metrics are layered by window, ranking, security, and downstream behavior.
- [ ] First-stage, new model, old model, and every fallback are compared together.
- [ ] Latency is separated into queue, tokenizer, inference, parsing, and post-processing.
- [ ] Cost includes peaks, replicas, retries, shadow traffic, and cache.
- [ ] Empty, unknown, duplicate, NaN, and revision mismatch have validation.
- [ ] Fallback is safe, deterministic, observable, and rehearsed for capacity and quality.
- [ ] Release gates include key slices and end-to-end benefit.

Next: [[reranking/07-project-fallback-capable-rule-reranker|Project: a fallback-capable rule reranker]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- [Sentence Transformers: Cross-Encoder Applications](https://www.sbert.net/examples/cross_encoder/applications/README.html)
- [Sentence Transformers: Cross-Encoder Training Overview](https://www.sbert.net/docs/cross_encoder/training_overview.html)
- [Elasticsearch: Ranking and reranking](https://www.elastic.co/docs/solutions/search/ranking)

Sources checked on 2026-07-22. Return to the [[reranking/00-index|Reranking course overview]].
