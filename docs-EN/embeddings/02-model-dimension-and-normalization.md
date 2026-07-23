---
title: "Model, Dimension, and Normalization Selection"
tags:
  - ai-agent-engineer
  - embedding
  - model-selection
  - similarity
aliases:
  - Embedding model selection
  - Embedding space contract
source_checked: 2026-07-22
source_baseline: Sentence Transformers, MTEB, OpenAI, Gemini, Cohere official
  documentation, and the original Matryoshka paper, checked through 2026-07-22
lang: en
translation_key: Embedding/02-模型维度与归一化选择.md
translation_source_hash: 098b7dc13477c1555aafb99e0c9b29372af670ad3297426aea42436dc850447b
translation_route: zh-CN/Embedding/02-模型维度与归一化选择
translation_default_route: zh-CN/Embedding/02-模型维度与归一化选择
---

# Model, Dimension, and Normalization Selection

## Objective

You will turn “pick an embedding model” into a verifiable decision. First define the task and data; then record input roles, model revision, dimension, metric, normalization, limits, license, privacy, latency, and cost; finally compare candidates on your own gold set.

## Write a task card before reading model cards

At minimum, answer these questions:

| Question | Why it matters |
| --- | --- |
| What are the input language, domain, and length distribution? | A general English average score does not stand in for specialized Chinese corpus data. |
| Is this symmetric similarity or query-to-document retrieval? | It determines roles, instructions, and the evaluation task. |
| Is the content text, code, images, or multimodal? | Only modalities supported by model training can be compared. |
| How long are typical queries and document chunks? | They affect input limits, truncation, and recall granularity. |
| Do you need a cloud API or local deployment? | This changes data egress, license, GPU, operations, and latency. |
| Who consumes the top-*k* candidates? | Reranker and LLM budgets determine the recall window. |
| How often are data updated and deleted? | This determines encoding throughput, caching, and migration cost. |
| Which subgroups must not regress? | You need gates for language, domain, authorization, and critical business cases. |

Public leaderboards and MTEB are useful for discovering candidates, but their tasks, corpora, aggregation methods, and revisions may not represent your target queries. Make the final decision with fixed chunks, queries, gold data, a development set, and a held-out test set.

## Specify the complete space contract

Record at least the following for every candidate:

```yaml
space_id: candidate-2026-07  # A stable identifier for this non-interchangeable vector space, not merely a display name.
provider: <provider-or-local-runtime>  # The cloud provider or local runtime that actually generates the vectors.
model: <model-id>  # The official model ID, retained for later reproduction and traceability.
revision: <immutable-revision-or-date>  # Pin a model version, immutable commit, or verification date so an alias cannot drift silently.
query_role: <method-task-or-prefix>  # The official query method, task type, or input prefix.
document_role: <method-task-or-prefix>  # The corresponding document role; do not infer it from the query setting.
dimension: <integer>  # The actual output dimension, which determines the index field and vector-length validation.
dtype: float32  # The numeric type of each component; it affects storage, quantization, and numerical error.
metric: cosine  # The retrieval metric; it must agree with model guidance and index configuration.
normalized: false  # Whether L2 normalization has occurred; do not infer it from the score range.
tokenizer: <name-and-revision>  # Input counter and revision, retained to reproduce length budgets.
input_limit: <official-source-and-date>  # A source and verification date for the changing official limit, not a hard-coded dynamic number.
truncation_policy: reject  # The explicit overlength policy; this one rejects input and returns it to the chunking stage.
pooling: <if-local-model>  # A local model must record pooling; state that it is not applicable for a cloud API.
license: <model-or-service-terms>  # Model license or service terms for a pre-release compliance check.
data_policy: <approved-processing-boundary>  # Which data can be sent to or stored inside this processing boundary.
```

`space_id` is an index-isolation identifier, not just a display label. A changed revision, role, dimension, pooling method, normalization behavior, or task instruction can create a new candidate space.

## Query/document roles are a dynamic contract

In asymmetric retrieval, short queries and long documents can be trained differently. Common designs are:

1. two encoders;
2. one encoder with a query/document prompt or task type; or
3. one identical call with no role distinction.

Official examples checked through 2026-07-22 include:

- Sentence Transformers recommends `encode_query()` and `encode_document()` for retrieval. If a model has no dedicated prompt or route, the two can be equivalent.
- Cohere documentation distinguishes the `search_query` and `search_document` input types.
- Gemini embedding generations express task instructions differently. `gemini-embedding-001` uses `task_type`, while `gemini-embedding-2` does not support that parameter. For plain-text retrieval with the latter, its current documentation requires query/document task instructions to be included in the actual input. The `001` and `2` vector spaces are incompatible: fully re-encode when moving between them; do not mix indexes or reuse old thresholds.
- OpenAI's current vector-embedding guide uses a common embeddings endpoint. Do not generalize that behavior to other models' role rules.

These are examples of a contract that varies by model and revision. Do not invent prefixes or copy a convention from another model. A role error often still returns a valid-dimensional vector, so retrieval regression tests must catch this silent failure.

## What dimension affects

For $N$ vectors of dimension $d$, with $b$ bytes per value, the theoretical raw-vector lower bound is:

$$
\text{raw bytes}=N\times d\times b
$$

For example, float32 has $b=4$. Actual storage also includes IDs, metadata, index graphs, alignment, and replicas; the formula is not a substitute for capacity testing.

Larger dimensions commonly increase:

- network-response and write volume;
- exact dot-product work;
- vector-field and ANN-index memory; and
- rebuild and backup cost.

A larger dimension does not guarantee better business quality. Training, data, task fit, and model capacity matter too.

## Variable dimensions are not arbitrary truncation

Matryoshka Representation Learning (MRL) trains representation prefixes so shorter prefixes retain useful structure. Some current services explicitly offer `dimensions`, `output_dimensionality`, or `output_dimension` parameters.

The correct rules are:

- shorten only when the model or official API explicitly supports it;
- prefer the official parameter to slicing a vector yourself;
- if official guidance requires renormalization, follow it for that model revision;
- treat every dimension as an independent candidate space and index field; and
- evaluate each one separately for business gold data, latency, memory, and cost.

Do not take the first 256 components of an arbitrary vector and assume equivalence. MRL is a training property, not a universal property of vector arrays.

## Cosine, dot product, and Euclidean distance

### Cosine similarity

$$
\operatorname{cos}(x,y)=
\frac{x\cdot y}{\lVert x\rVert_2\lVert y\rVert_2}
$$

It compares direction and ignores shared scale; it is undefined for a zero vector.

### L2 normalization

$$
\hat{x}=\frac{x}{\lVert x\rVert_2}
$$

For unit vectors:

$$
\operatorname{cos}(x,y)=\hat{x}\cdot\hat{y}
$$

and:

$$
\lVert\hat{x}-\hat{y}\rVert_2^2=2-2(\hat{x}\cdot\hat{y})
$$

Therefore, on the same set of unit vectors, cosine, dot product, and Euclidean distance produce the same ordering, though their numeric scores differ. Without normalization, dot product is affected by vector length and the ordering need not agree.

### Selection rules

- Start with the model card or official documentation for training and recommended metric.
- State whether vectors have already been normalized.
- Use the same configuration in the index and application.
- Reject zero vectors, NaN, Inf, and wrong dimensions.
- Calibrate score thresholds by space, task, and development set.

OpenAI's current guide states that its embeddings have unit length and that cosine can be computed with dot product. That is current behavior of that service, not a default to apply to every model.

## Input limits and truncation

Models can limit tokens, characters, item count, total payload, or modalities. Specific limits change, so retain an official link and verification date.

The safest baseline is:

1. use the model's tokenizer or official counting method;
2. control length during [[chunking-strategies/00-index|Chunking Strategies]];
3. explicitly reject or rechunk overlength input;
4. if truncation is genuinely required, retain the actual embedding input, its hash, truncation position, and a warning; and
5. never silently let the database body differ from the text actually embedded.

Some APIs can automatically truncate input. For example, the Gemini API exposes automatic-truncation configuration. A successful response does not prove that the entire source body was embedded. Choose rejection, rechunking, or truncation explicitly in the space contract and record request settings. If a provider reports truncation status, include it in audits and retrieval regressions. Do not treat provider defaults as a length policy.

The same model can recommend different query and document lengths or instructions; record them separately.

## Version both normalization and quantization

Float16, int8, binary, and other compression methods can save storage and increase speed, but introduce numerical and ranking changes. Support from a provider or library does not mean your index, metric, and quality gates are automatically compatible.

Distinguish during comparison:

- representation error from the model;
- dimension-reduction error;
- dtype or quantization error; and
- ANN approximation error.

Change one layer at a time. First use raw float exact search as ground truth, then measure compression and ANN top-*k* agreement or recall.

## Candidate-model experiments

Hold fixed:

- canonical chunks, queries, and relevance labels;
- query/document roles;
- exact search or the same ANN configuration;
- metric, `k`, filtering, and reranking;
- development/test split; and
- machine, batch size, and concurrency when comparing performance.

Report:

| Quality | Subgroups | System |
| --- | --- | --- |
| Recall@k, MRR, nDCG, hard negatives | Chinese/English, domain, short/long queries, code, numbers | P50/P95, throughput, failures, raw/index storage, cost |
| No-answer threshold plus false positives/negatives | Authorization, critical business cases, low-resource languages | Cold start, rebuild duration, cache hit rate |

When overall means are close, critical subgroups, stability, cost, and governance constraints may determine the choice.

## Common mistakes and investigation

- **Looking only at leaderboard totals:** return to business queries and critical subgroups.
- **Omitting a role without an error:** print the space contract, not source text, and add query/document regressions.
- **Mixing vectors because dimensions match:** validate the provider/model/revision/role/dimension/metric signature.
- **Normalizing every vector by force:** first verify model training and official guidance.
- **Silent truncation:** compare the source-body hash with the actual embedding-input hash.
- **Declaring a new model worse because its score is lower:** score scales are not comparable across spaces; compare order and business metrics.
- **Shipping the MTEB leader directly:** a leaderboard is screening evidence, not target-domain acceptance.

## Exercises

1. Fill in a complete space contract for “question answering over Chinese operations manuals.” Write “verify official documentation” for unknown dynamic fields; do not guess values.
2. Compute the raw vector bytes for 1,000,000 float32 vectors of dimension 768, then list five overhead types excluded by the formula.
3. Prove that Euclidean-distance and dot-product orderings are equivalent for unit vectors.
4. Design four smoke queries for role errors, including short-question-to-long-document retrieval and code retrieval.
5. Design a fair experiment for three officially supported dimensions—256, 768, and 1536—and list variables that must not change at the same time.
6. Explain why cosine scores from old and new models cannot share one threshold directly.

## Mastery check

- [ ] I define task and data before consulting a model leaderboard.
- [ ] Every space has a complete, unambiguous provider/model/revision/role contract.
- [ ] I change dimension only when a model explicitly supports it, then reevaluate.
- [ ] I can derive the relationship among cosine, dot product, and Euclidean distance for unit vectors.
- [ ] Metric, normalization, and index configuration agree.
- [ ] Overlength input follows an explicit reject, rechunk, or truncation policy, with auditable truncation status.
- [ ] My model decision covers quality, subgroups, latency, storage, cost, license, and privacy.

## Summary and next step

Model selection defines only what vectors to generate. Next, ensure that thousands or millions of inputs remain reconciled item by item through failures, rate limits, and reruns; can be cached; and do not produce stale vectors: [[embeddings/03-batching-caching-and-reliability|Batching, Caching, and Reliability]].

## References

- [Sentence Transformers Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)
- [MTEB Overview](https://docs.mteb.org/overview/)
- [MTEB original paper](https://arxiv.org/abs/2210.07316)
- [Kusupati et al., Matryoshka Representation Learning](https://arxiv.org/abs/2205.13147)
- [OpenAI: Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Gemini API: Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Cohere: Introduction to Embeddings](https://docs.cohere.com/docs/embeddings)

Sources were obtained on 2026-07-22. Return to [[embeddings/00-index|Embeddings]].
