---
title: "Cross-Encoder reranking"
tags:
  - ai-agent-engineer
  - reranking
  - cross-encoder
aliases:
  - Cross-encoder reranker
  - Cross Encoder Reranking
source_checked: 2026-07-14
source_baseline: BERT, monoT5, and RankT5 papers, plus Sentence Transformers and
  Elasticsearch documentation, checked through 2026-07-14
lang: en
translation_key: Reranking/02-Cross-Encoder重排.md
translation_source_hash: b5b4fcbeaa988b9ec8bfeb116a37dc5b949d991c2702a12a129485c631909600
translation_route: zh-CN/Reranking/02-Cross-Encoder重排
translation_default_route: zh-CN/Reranking/02-Cross-Encoder重排
---

# Cross-Encoder reranking

## Goal of this lesson

Understand why a Cross-Encoder can inspect query–document relationships closely, why it cannot scan an entire corpus directly, and how input truncation, output semantics, batching, and serving determine real quality. By the end, you should be able to write a replayable Cross-Encoder inference contract.

## Bi-Encoder versus Cross-Encoder

| Dimension | Bi-Encoder | Cross-Encoder |
| --- | --- | --- |
| Input | Encode query and document separately | Send a query and one document together |
| Document computation | Vectors can be cached offline | Compute every query–document pair online |
| Token interaction | Compare vectors after encoding | Interact across texts directly inside the Transformer |
| Typical role | Large-scale first-stage recall | Precise ranking over a limited window |
| Main bottleneck | Index/ANN and representation quality | Pair count, tokens, batching, and inference queue |

A Cross-Encoder can better distinguish negation, numbers, word order, and local evidence, but “usually stronger” is not a guarantee for your corpus. Reranking can degrade when its training domain, language, text length, or qrels definition does not match the target setting.

## Building the input

One traceable template could be:

```text
[QUERY] After a refund is approved, how long until the money arrives?
[TITLE] Refund arrival time
[BODY] After approval, a refund usually returns through the original payment method within one to three business days.
```

Freeze all of the following:

- model/provider/revision and tokenizer revision;
- the order, separators, and field labels for query, title, body, and metadata;
- maximum token count, special tokens, and padding;
- separate token budgets for query and document;
- truncation direction or chunking/sliding-window policy;
- input normalization, language, and source revision; and
- batch size, dtype, device, and inference-library version.

Concatenating tenant, ACL, or a system prompt into natural language does not replace server-side filtering. Irrelevant metadata also consumes window budget and can change model behavior.

## Truncation is hidden recall loss

The model can judge only the text that reaches its token window. If an answer occurs near the end of a document and is truncated, a Cross-Encoder turns “a positive document was retrieved” into “the model never saw the evidence.” Monitor:

- query and body token distributions;
- the truncation rate and fields that were truncated;
- whether answer spans in positives were retained; and
- the relationship between text length and nDCG or errors.

Prefer first-stage retrieval that returns citable passages. For long documents that must be handled, score sliding windows and aggregate them, but max, mean, and top-*m* aggregation each change the bias; see [[reranking/04-candidate-windows-long-documents-and-diversity|Candidate windows, long documents, and diversity]].

## What does the output score mean?

A model may output:

- a binary-classification logit;
- a probability after sigmoid;
- a regression relevance score;
- a generated score for true/false tokens; or
- probabilities over multiple relevance grades.

Its meaning comes from the training objective. A logit can rank candidates for the same query, but it is not automatically a probability across queries. Even a sigmoid output is interpretable only when the data distribution and calibration hold. Calibrate thresholds on an independent validation set by query type, language, and error cost, then repeat calibration after a model upgrade.

Define ranking explicitly:

1. Whether a larger or smaller score is better.
2. How missing or invalid scores are handled.
3. Whether ties use first-stage rank, stable ID, or another key.
4. Whether the model may discard candidates.
5. Whether output must cover every input ID or may be partial.

## Batching and dynamic batching

For a candidate window of *w*, there are *w* pairs. Batched inference can improve GPU or CPU utilization, but it introduces:

- queueing delay while a batch is filled;
- padding waste from mixed text lengths;
- peak memory and out-of-memory risk;
- a single large request slowing other queries in the same batch; and
- completed work wasted after a timeout.

Benchmark different windows, token lengths, concurrency levels, and batch policies. Report model computation, queueing, serialization/network time, and end-to-end p50/p95/p99. Single-batch throughput does not represent online tail latency.

## Serving contract

A request should contain at least a request/query ID, model revision, query, candidate IDs and text, deadline, and schema version. A response should contain a finite score for every ID, optional label/reason, model revision, duration, and error information.

The client validates:

- HTTP or transport success is not the same as a valid business result;
- the exact ID set, uniqueness, and count;
- score type and finiteness;
- response model/schema revision;
- time remaining before the deadline; and
- logs that do not expose unnecessary body text or credentials.

Retry only explicitly retryable errors, subject to the total deadline, idempotency, and capacity limits. Reranking is usually pure scoring, so repeat calls do not change outside state, but they still repeat cost and consume resources.

## Using current library and product facts

Current Sentence Transformers CrossEncoder documentation offers local inference entry points such as `predict` and `rank`, along with dedicated reranking examples. Current Elasticsearch semantic-reranking documentation describes a limited rank window, Cross-Encoder inference endpoints, and long-document handling options. Use them as implementation examples, not as proof that all model scores can be compared across queries or that default truncation suits your corpus.

## Common mistakes and how to investigate them

- **The model cannot see the answer span**: record tokens and spans; change the passage strategy or chunking.
- **The training and production templates differ**: freeze a template checksum.
- **Score direction is reversed**: unit-test with known positive and negative pairs.
- **Only one-request average latency is measured**: include concurrency, dynamic batching, and p99.
- **A response omits IDs but processing continues**: trigger invalid-output fallback.
- **An arbitrary threshold is reused across queries**: calibrate on the target distribution.
- **A model upgrade checks only an offline average**: inspect key slices, latency, and fallback capacity.

## Exercise

Design a pipeline that retrieves 100 candidates with a bi-encoder, reranks 30 with a Cross-Encoder, and returns 8:

1. Write the query/title/body template and token budgets.
2. Construct long-document tests whose answer is at the beginning, middle, and end.
3. Define output-score semantics and tie-breaking.
4. Design a benchmark across batch size × window × token length.
5. Validate empty, duplicate, unknown, NaN, and revision-mismatch responses.
6. Define timeout, retry, and safe fallback behavior.

## Mastery check

- [ ] The caching and computation boundary between Bi-Encoders and Cross-Encoders is clear.
- [ ] Input template, tokenizer, truncation, and model version are replayable.
- [ ] Score semantics come from the training objective rather than being guessed as probabilities.
- [ ] Batching evaluates throughput, queueing, and tail latency together.
- [ ] Provider output receives exact-ID, finite-number, and schema validation.
- [ ] Long documents and model upgrades have sliced regression and fallback tests.

Next: [[reranking/03-llm-rules-and-hybrid-reranking|LLMs, rules, and hybrid reranking]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Nogueira, Jiang & Lin, [monoT5](https://arxiv.org/abs/2003.06713)
- Zhuang et al., [RankT5](https://arxiv.org/abs/2210.10634)
- [Sentence Transformers: CrossEncoder API](https://www.sbert.net/docs/package_reference/cross_encoder/model.html)
- [Sentence Transformers: Cross-Encoder Applications](https://www.sbert.net/examples/cross_encoder/applications/README.html)
- [Elasticsearch: Semantic reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking)

Sources checked on 2026-07-14. Return to the [[reranking/00-index|Reranking course overview]].
