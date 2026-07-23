---
title: "Candidate windows, long documents, and diversity"
tags:
  - ai-agent-engineer
  - reranking
  - context-selection
aliases:
  - Reranking windows and diversity
  - Rerank window
source_checked: 2026-07-14
source_baseline: BERT reranking and Lost in the Middle papers, plus
  Elasticsearch long-document reranking documentation, checked through
  2026-07-14
lang: en
translation_key: Reranking/04-候选窗口长文与多样性.md
translation_source_hash: b88fbc728fb28aab0e6b3b87c89019f1425765347f75f450c7a066a11ab05b9b
translation_route: zh-CN/Reranking/04-候选窗口长文与多样性
translation_default_route: zh-CN/Reranking/04-候选窗口长文与多样性
---

# Candidate windows, long documents, and diversity

## Goal of this lesson

Reranker quality is determined not only by model weights, but also by which candidates enter the window, which tokens from each text are visible, and how many places one source may occupy. Use quality–latency curves to choose a window, handle long documents and duplicate candidates, and avoid treating diversity as an unconditional optimization.

## The window determines the reachable ceiling

For windows 10, 20, 50, and 100, record:

- Candidate Recall@window.
- Reranked nDCG/MRR/Precision@top-*n*.
- Pair and token counts; model and queue p95/p99.
- Timeout/fallback rate, throughput, and cost.
- Key query slices and the original first-stage rank of the answer.

If candidate recall barely grows after 20, expanding the window only adds computation. If many positives appear after rank 80, diagnose the first stage before asking the most expensive model to scan more noise.

The [[reranking/examples/reranker-fixture.json|project fixture]] contains all 4 of 4 positive examples at `window=6`, so candidate recall is 1. At `window=3`, it contains only 1 of 4, so candidate recall is 0.25. No rule or model can find the three positives at ranks 4 through 6 when the window is 3.

## Why a long document can be “retrieved but unseen”

A Cross-Encoder or LLM has a token window. Its input commonly contains a query, title, body, and special tokens. Frequent failures include:

- the query or title consumes budget and truncates the end of the body;
- every document is truncated from the same end even though answers do not always occur near the beginning;
- HTML or navigation noise fills the window;
- multiple chunks are merged, then later candidates are silently truncated; and
- training uses passages while production sends whole documents.

Record each pair’s original character and token counts, actual input, truncation flag, and whether the answer span was retained. A document ID alone cannot reproduce what the model actually saw.

## Three strategies for long documents

### 1. Produce passages upstream

Use [[chunking-strategies/00-index|Chunking Strategies]] to produce citable, semantically complete passages, then have the reranker judge query–passage pairs directly. This is easiest to explain, but adjacent chunks can repeat.

### 2. Sliding windows or structural chunks

Split a long candidate into passages, score them separately, then aggregate them into a document score:

- **max** preserves the strongest local evidence, but one false match can inflate it;
- **mean** is stable but can dilute a local answer;
- **top-*m* mean** is a compromise that requires choosing *m*; and
- **learned aggregation** is expressive but adds training work and bias.

Preserve the winning passage or span for RAG citation and error analysis.

### 3. Two-stage reranking

First use a cheaper model or rules to select passages within a document, then use a stronger model on the reduced set. This lowers token cost, but the second stage cannot recover an answer that the first stage missed.

Current Elasticsearch semantic-reranking documentation provides product-level examples for long-document and chunk reranking. Details such as `chunk_rescorer`, truncation, and defaults are current product behavior, not a general protocol.

## Chunk ranking and document ranking

Qrels and output units must agree:

- If RAG consumes passages, evaluate passage relevance.
- If the UI displays documents, define chunk-to-document aggregation first.
- If multiple passages from one document are evidence, do not retain only one automatically.
- If slices are near duplicates, do not let them crowd out independent sources.

Report candidate/chunk recall, canonical-document recall, and evidence-set coverage. A system can have high passage nDCG while returning five adjacent excerpts from one original document.

## Canonical cap

Limit each source to at most *m* results by `canonical_document_id`:

```text
model order: A-1, A-2, A-3, B-1, C-1
cap=1:       A-1, B-1, C-1
cap=2:       A-1, A-2, B-1, C-1
```

Choose *m* for the task:

- One or two excerpts are often enough for a single-fact question.
- A multi-step procedure may need several adjacent passages from one document.
- A multi-hop question may need several independent sources.
- Citation auditing may require the most specific span.

After applying the cap, continue down the ranking to fill vacant positions; do not return fewer than top-*n* simply because items were skipped. Preserve `canonical_cap` as the reason for every skipped item.

## Diversity is not “the less similar, the better”

Methods such as MMR trade query relevance against similarity among candidates. Excessive diversity can elevate low-relevance documents merely because they discuss different topics; too little repeats the same evidence. When tuning, inspect all of the following:

- query relevance;
- canonical/source coverage;
- whether required evidence sets are complete;
- final RAG correctness and groundedness; and
- token use and the number of conflicting documents.

Never relax hard permissions or effective-time constraints for the sake of diversity.

## Downstream position effects

First place in a reranker does not guarantee that an LLM will use the correct evidence. Information position affects how some long-context models use evidence; the Lost in the Middle study demonstrates this effect. In engineering work:

- test end-to-end with the real evidence budget;
- put the strongest evidence early, but do not game the result by duplicating it;
- check whether context assembly reorders content by source or time afterward;
- record reranking order and final prompt order; and
- handle conflicting evidence explicitly instead of relying on position to suppress it.

## Stable ordering

When model scores tie, break ties with first-stage rank and then a stable ID. LLM listwise ranking also needs candidate permutations. Measure:

- top-*n* overlap;
- rank correlation such as Kendall or Spearman;
- position variance for key positives; and
- output-parsing failure rate.

Replays must lock candidate text and revision, model and prompt, batch policy, window, tie-break, and post-processing.

## Common mistakes and how to investigate them

- **The window grows but quality does not**: check whether candidate recall has already saturated.
- **A positive is in the window but still scores low**: verify that its answer span was not truncated.
- **One source fills the context**: introduce a canonical ID and cap experiments.
- **The cap leaves fewer than top-*n***: continue filling from later candidates.
- **Diversity damages relevance**: report relevance together with evidence coverage.
- **Reranking and prompt order differ**: record both stages of ordering.
- **Listwise ranking is unstable**: run permutations and repeats, then limit the use case.

## Exercise

1. Design a table of candidate recall, nDCG, p99, and cost for windows 10, 30, and 100.
2. Construct three positive examples whose answers occur at the beginning, middle, and end of long documents.
3. Compare max, mean, and top-2-mean aggregation.
4. Give one document five adjacent chunks and three independent sources; test caps of 1, 2, and 3.
5. Define an exception that requires two passages from the same document to answer.
6. Compare reranking order and final prompt order end to end.

## Mastery check

- [ ] The window is chosen from quality–latency curves, not intuition.
- [ ] Truncation, actual input, and matched spans are traceable.
- [ ] Passage/document qrels agree with the aggregation unit.
- [ ] A canonical cap fills vacant positions and preserves skip reasons.
- [ ] Diversity is evaluated for both relevance and evidence coverage.
- [ ] Reranking order, prompt order, and permutation stability are recorded.

Next: [[reranking/05-training-data-and-hard-negatives|Training data and hard negatives]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Liu et al., [Lost in the Middle](https://arxiv.org/abs/2307.03172)
- [Elasticsearch: Semantic reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking)

Sources checked on 2026-07-14. Return to the [[reranking/00-index|Reranking course overview]].
