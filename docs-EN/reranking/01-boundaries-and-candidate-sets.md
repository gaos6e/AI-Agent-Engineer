---
title: "Boundaries and candidate sets"
tags:
  - ai-agent-engineer
  - reranking
  - retrieval
aliases:
  - Reranker candidate sets
  - Candidate sets for reranking
source_checked: 2026-07-14
source_baseline: BERT reranking and BEIR papers, plus current official reranking
  documentation, checked through 2026-07-14
lang: en
translation_key: Reranking/01-边界与候选集.md
translation_source_hash: 313d9936705e1fba4228e0c3ab52941b7c3530e7f00c3d8a3dcd818761ab877d
translation_route: zh-CN/Reranking/01-边界与候选集
translation_default_route: zh-CN/Reranking/01-边界与候选集
---

# Boundaries and candidate sets

## Goal of this lesson

Before selecting a model, define what the reranker may see, what it must return, and where it may fall back when it fails. You will learn to calculate candidate recall, distinguish four separate budgets, and establish input/output contracts that do not expand permissions when a model is unavailable.

## What a reranker can change

Given the same candidate set, a reranker can:

- improve query–document relevance near the top of the list;
- distinguish same-topic documents that do not answer the question and documents with conflicting numbers or negation;
- return model scores, grades, or pair/list ordering;
- apply auditable diversity or business policy after relevance; and
- remove low-scoring candidates or trigger an “insufficient evidence” result.

It cannot:

- recover documents that never entered the candidate window;
- repair documents that were not indexed, poor chunking, or incorrect permission metadata;
- prove that a document is factually correct, trustworthy, or currently valid;
- replace citation and answer validation in the generation stage; or
- make unauthorized documents visible because they seem highly relevant.

## Input contract

Every call should contain at least the following information:

| Category | Required fields |
| --- | --- |
| Query | Query ID, original/rewrite form, language, as-of time, and query revision |
| Identity and filtering | Tenant, authorization summary, and evidence that status/effective-time filtering has already run |
| Candidate | Stable ID, canonical source ID, title/body, and source revision |
| First stage | Channel, rank, score, and fusion/index/model revision |
| Reranking | Model/prompt/tokenizer revision, window, timeout, and batch policy |

Do not send unnecessary private metadata, credentials, or complete ACLs in the model input. Identity belongs in server-side filtering and auditing, not in natural-language text that a prompt can reinterpret.

## Candidate Recall sets the ceiling

First freeze the same data snapshot, test principal, time, and authorization-policy revision. Let $R_{\mathrm{eligible}}$ be the positive qrels that this principal **should be allowed** to access, and let $C_w$ be the window candidates after hard filtering:

$$
\operatorname{CandidateRecall@w}=\frac{|R_{\mathrm{eligible}}\cap C_w|}{|R_{\mathrm{eligible}}|}
$$

If a relevant document sits at first-stage rank 80 and the window is 20, no reranking model can put it in top-*n*. If $R_{\mathrm{eligible}}$ is empty, assert the safe no-answer or unauthorized-not-returned behavior instead of treating the correct empty result as zero candidate recall. During diagnosis, keep all three views:

- **End-to-end**: report final nDCG/MRR for every query.
- **Conditional**: inspect model ordering only for queries whose window contains a positive example.
- **Candidate recall**: show the reachable ceiling imposed by the first stage and window.

Conditional metrics alone hide upstream recall misses. End-to-end metrics alone can wrongly blame the model for upstream failures. Keep both, along with candidate recall.

## Do not call all four budgets “top-*k*”

```text
First-stage retrieval window: 100
        ↓
Rerank input window: 40
        ↓
Rerank output top-n: 10
        ↓
RAG evidence/context budget: 5 passages / 4000 tokens
```

In addition, every Cross-Encoder pair has a tokenizer maximum length, while an LLM listwise reranker has a total context limit. Each budget changes a different quality or cost trade-off, so name, record, and experiment with them separately.

## Hard filtering comes before the window

The correct order is:

1. Derive tenant and ACL constraints from a trusted identity.
2. Exclude draft, expired, deleted, and wrong-tenant documents.
3. Rank the safe candidates in the first stage.
4. Take the reranking window.
5. Rerank the same set of IDs with the model.
6. Apply controlled canonical caps or business rules.

If you take a global top 20 before filtering, authorized candidates can be pushed out of the window by unauthorized ones. The model service, logs, and cache may already have seen sensitive text as well. Revalidating at the reranker entry point is defense in depth; it does not make upstream filtering optional.

## Output contract

A normal response must satisfy all of the following:

- Every input candidate ID appears exactly once, unless the contract explicitly defines partial-output semantics.
- It contains no unknown, duplicate, or omitted IDs.
- Scores are finite numeric values; NaN, Infinity, and booleans disguised as numbers are invalid.
- Features and reasons use an allowlist and are serializable.
- The model, prompt, tokenizer, and schema revisions are explicit.
- Ties use a stable first-stage rank, stable ID, or another declared key.
- The output can be associated with a request or trace ID.

Do not interpret an empty model list as “everything is irrelevant” unless the API defines that meaning and you have calibrated it. A safer default is `invalid output → fallback`.

## A fallback is a first-class product path

A common fallback is the first-stage order of the **same safe window**. It must:

- never query unauthorized candidates again;
- preserve hard filters and validity-time rules;
- be deterministic, fast, and evaluated offline;
- set `rerank_applied=false` together with a reason;
- limit retries so they do not amplify latency after the deadline is already exhausted; and
- count timeouts, 5xx responses, rate limits, and empty or malformed responses separately.

Returning no result can be safer than using the first-stage fallback, but it can sharply reduce availability. Choose according to business error cost and local evaluation evidence.

## Transparent auditing

Keep the following for every final candidate:

- first-stage rank, score, and channel;
- reranker input position;
- model score or label;
- final rank;
- canonical grouping or business-rule reason;
- whether fallback was used and why; and
- every relevant revision and duration.

Do not overwrite the first-stage score. Otherwise you cannot tell whether an improvement came from retrieval, the model, or post-processing rules.

## Common mistakes and how to investigate them

- **Answers often lie outside the window**: improve recall or enlarge the affordable window first.
- **The model returns unknown IDs**: enforce a strict schema and exact-ID-set validation.
- **Fallback queries the full corpus again**: reuse the already filtered window only.
- **Conditional evaluation looks good while overall quality does not move**: inspect candidate recall.
- **The body is truncated before the model sees it**: record token counts and truncated fields.
- **First-stage provenance is overwritten**: retain three separate rank/score layers.
- **Too many timeout retries**: use a total deadline, per-attempt budget, and circuit breaking.

## Exercise

Given 100 candidates and four positive qrels at ranks 2, 18, 47, and 80:

1. Calculate candidate recall for windows 10, 20, 50, and 100.
2. Design an input schema and exact-output-ID validation.
3. Define the reranking top-*n* separately from the RAG evidence budget.
4. Specify fallbacks for a timeout, empty response, duplicate ID, and unknown ID.
5. Show that the fallback contains only authorized candidates.
6. List the three rank/score layers that must be retained.

## Mastery check

- [ ] The reranker’s boundary and upstream/downstream responsibilities are clear.
- [ ] Candidate recall, conditional metrics, and end-to-end metrics are reported together.
- [ ] The four candidate/context budgets have independent names.
- [ ] Permissions, status, and time are enforced before windowing.
- [ ] IDs, counts, scores, versions, and tie-breaking have strict output contracts.
- [ ] The fallback reuses only the safe window and is observable.

Next: [[reranking/02-cross-encoder-reranking|Cross-Encoder reranking]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- [Elasticsearch: Ranking and reranking](https://www.elastic.co/docs/solutions/search/ranking)

Sources checked on 2026-07-14. Return to the [[reranking/00-index|Reranking course overview]].
