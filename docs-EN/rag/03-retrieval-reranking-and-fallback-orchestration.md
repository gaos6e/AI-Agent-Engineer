---
title: "Retrieval, Reranking, and Fallback Orchestration"
tags:
  - ai-agent-engineer
  - rag
  - retrieval
aliases:
  - RAG Retrieval Orchestration
  - RAG Retrieval Pipeline
source_checked: 2026-07-22
lang: en
translation_key: RAG/03-检索重排与降级编排.md
translation_source_hash: 38e93f2dbac6475fc5af4b03077b18fb69a47c46a2c8c313472c7372065b7b75
translation_route: zh-CN/RAG/03-检索重排与降级编排
translation_default_route: zh-CN/RAG/03-检索重排与降级编排
---

# Retrieval, Reranking, and Fallback Orchestration

## Learning objectives

- Separate hard filtering, recall, fusion, reranking, and evidence selection into observable stages.
- Distinguish the candidate window, rerank window, and final evidence.
- Design safe fallbacks for timeouts, empty responses, and dependency failures.
- Use a total deadline to control parallelism, retries, and tail latency.

## A correctly ordered candidate chain

```text
Trusted identity → tenant/ACL/status/validity filters
                 → sparse and dense recall
                 → fusion and canonical deduplication
                 → bounded-window reranking
                 → context selection
```

Two kinds of “ordering” are involved:

1. **Hard-constraint priority**: exclude unauthorized, deleted, unpublished, or expired documents first.
2. **Relevance ranking**: compare only the legal set to decide which document best answers the question.

A reranker's low score cannot substitute for an ACL, and a highly relevant document cannot cross a permission boundary.

### Filters must limit the searchable set

Make tenant, role, resource state, validity period, and authorization revision trusted constraints of the retrieval request. Do not return whole-corpus nearest neighbors to the application and filter them only in the presentation layer. Acceptable implementations include retrieval-engine metadata filters, collections/namespaces isolated by authorization domain, or a controlled server-side computation of retrievable IDs; the right choice depends on scale and policy complexity. Whichever approach you use, recheck before reranking, context construction, and citation rendering because ACLs, tombstones, and validity periods can change during a request or cache lifetime.

If a third-party reranker sees candidate bodies, it is also a data processor: send only the smallest text window the current principal may read and the service is allowed to process, and record the model, region, and retention policy. “The ranking service needs input” is never grounds for expanding the visible data domain.

## Multi-channel recall

### Sparse

BM25/keywords are usually strong for proper names, identifiers, error codes, and verbatim phrases. They are explainable and can serve as a baseline when a model service fails.

### Dense

Embedding retrieval is good at semantic paraphrases, but may rank content about the same topic that does not answer the question very highly. Model, normalization, distance, dimension, and index versions must agree.

### Structured retrieval

Time, category, product, document type, and entity relationships may be better handled with a database, inverted-index filters, or graph queries. RAG does not require all knowledge to become vectors.

## Do not directly mix scores during fusion

Raw scores from different retrievers are usually not on the same scale. RRF (Reciprocal Rank Fusion) fuses ranks:

$$
\operatorname{RRF}(d)=\sum_i\frac{1}{k+r_i(d)}
$$

Here, `r_i(d)` is document `d`'s rank in channel `i`, and `k` is a smoothing constant. It reduces dependence on score calibration, but `k`, channel weights, and candidate depth still require local evaluation.

Save the following for every candidate:

- source/document/chunk/canonical ID;
- channel and original rank/score;
- filter revision and index revision;
- fusion rank/score;
- ranks before and after reranking, plus the reranker revision.

## Candidates are not evidence

| Name | Purpose | Typical scale |
| --- | --- | --- |
| recall window | Candidates returned by first-stage retrieval. | Larger; prioritize recall. |
| rerank window | Candidates sent to an expensive model. | Limited by latency/cost. |
| output top-n | Leading results after reranking. | Smaller. |
| selected context | Evidence that actually enters generation context. | Limited by budget, deduplication, and coverage. |

If a gold document is absent from the recall window, the reranker cannot create it. If it is high after reranking but dropped by the context budget, the problem is in the context layer.

## Fallback is not “return anything”

| Failure | Acceptable candidate strategy | Must retain |
| --- | --- | --- |
| Dense timeout | Use authorized sparse results only. | A `degraded` flag and the missing channel. |
| Sparse failure | Use authorized dense results only. | The risk for identifier-heavy queries. |
| Reranker timeout/malformed output | Use an evaluated fusion order. | The same safe candidate set. |
| One shard fails | Choose partial results or abstention by product policy. | coverage/partial flag. |
| All retrieval unavailable | State that retrieval is temporarily unavailable. | Never freely generate internal facts. |
| Generation service fails | Return authorized original excerpts or abstain. | Product policy and source links. |

Fallback itself must be tested for relevance, authorization, latency, and capacity. If it first runs during an incident, it is not reliable.

### A cache is also a fallback path

Semantic, candidate, and answer caches can reduce latency, but also send old retrieval decisions back online. A cache value must at least retain the `authorization_revision`, source/index generation (or equivalent snapshot), route/output mode, and expiry policy used to create it; before a hit, verify the caller's visible scope again. Revocation, deletion, policy tightening, and high-risk source updates must invalidate relevant entries or reject their hits. If a cache cannot be reliably isolated by authorization and version, prefer a miss over an answer that may belong to another principal or an old knowledge snapshot.

## Total deadline and retry budget

Suppose the end-to-end budget is two seconds. Allocate it rather than hard-coding it:

| Stage | Example budget | Timeout strategy |
| --- | ---: | --- |
| routing/rewrite | 150 ms | original query |
| sparse+dense in parallel | 350 ms | retain successful channels |
| rerank | 250 ms | fusion order |
| context and validation | 100 ms | deterministic local processing |
| generation | 900 ms | abstain/controlled retry |
| remaining budget | 250 ms | network jitter and serialization |

These numbers are allocation examples only; measure your own p50/p95/p99. Retries must respect the remaining deadline; synchronized retries without jitter amplify traffic during dependency failures.

## A diagnosable trace example

```json
{
  "retrieved": [
    {"id": "S8", "channel": "dense", "rank": 1, "score": 0.82},
    {"id": "S1", "channel": "bm25", "rank": 1, "score": 12.7}
  ],
  "reranked": [
    {"id": "S1", "rank": 1, "model_revision": "ce-v3"}
  ],
  "selected": [
    {"id": "S1", "reason": "top_relevant_current"}
  ],
  "fallback": null
}
```

JSON cannot contain legal trailing comments. `retrieved` retains each recall channel's own rank/score, `reranked` retains the post-model order and revision, `selected` records why evidence actually entered context, and `fallback` makes degradation explicit. Do not compare numeric values from different channels directly across fields.

Score fields have meaning only in their own model/query contexts; do not see `12.7 > 0.82` and conclude that BM25 is more relevant.

## Hands-on exercise

1. Write your own stage table for a two-second budget and justify it.
2. Run the [[rag/08-project-offline-cited-qa|offline project]]:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Avoid writing Python caches into the knowledge base while running the exercise.
$script = '.\docs-EN\rag\examples\offline_cited_qa.py'  # Store the offline RAG project script path.
$fixture = '.\docs-EN\rag\examples\rag-fixture.json'  # Store the reproducible strict-fixture path.

python -B $script --fixture $fixture inspect --query-id Q-refund --operator-view  # Inspect the protected stage trace without a failure.
python -B $script --fixture $fixture inspect --query-id Q-refund --failure reranker_error --operator-view  # Simulate reranker failure and confirm that the authorized fusion order is used.
python -B $script --fixture $fixture inspect --query-id Q-refund --failure retrieval_error --operator-view  # Simulate retrieval failure and confirm that internal facts are not freely generated.
```

3. In the protected `audit_trace`, compare `retrieved`, `reranked`, `selected`, `degraded`, and `fallback`. A real service must verify operator identity and audit authorization first; a CLI flag is not permission by itself.
4. Explain why `retrieval_error` returns an abstention rather than asking the generator to answer from memory.

## Common mistakes

- Retrieve an unauthorized whole corpus before filtering.
- Mix BM25, cosine, and model logits without calibration or rank fusion.
- Trust a reranker's unknown or duplicate IDs.
- Make a fallback use a broader ACL or stale index.
- Let every parallel branch retry independently and exceed the total deadline.
- Monitor only average latency and ignore p99 and fallback rate.

## Self-check

1. Why must hard filtering precede relevance scoring?
2. What upper bound does Candidate Recall@window place on a reranker?
3. What does RRF solve, and what does it not solve?
4. Why is retaining fusion order usually more reasonable than returning nothing when a reranker fails?
5. When should the system stop answering instead of degrading?
6. Why check the current principal, authorization revision, and knowledge generation before a cache hit?

## Summary and next step

The aim of retrieval orchestration is a high-recall, authorized, degradable, diagnosable candidate chain. Candidates still cannot be poured wholesale into a prompt; the next lesson handles budget, deduplication, order, and conflict: [[rag/04-context-selection-and-assembly|Context Selection and Assembly]].

## References

- Karpukhin et al., [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- Cormack, Clarke & Büttcher, [Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html): emphasizes chunk-level ACL inheritance, authorization at retrieval time, and the cross-user disclosure and stale-policy risks created by caches.

Sources accessed: 2026-07-22. Specific performance numbers in papers depend on their datasets and implementations; this lesson does not extrapolate them as local conclusions.
