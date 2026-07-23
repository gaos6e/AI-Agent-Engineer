---
title: "Training data and hard negatives"
tags:
  - ai-agent-engineer
  - reranking
  - training-data
aliases:
  - Reranker training data
  - Training data for rerankers
source_checked: 2026-07-14
source_baseline: DPR, BERT reranking, monoT5, and BEIR papers, checked through 2026-07-14
lang: en
translation_key: Reranking/05-训练数据与Hard Negatives.md
translation_source_hash: 0ce96ba00e16a4ede8858690967ae7146fe682a5d7a963829bf017f710c11c1a
translation_route: zh-CN/Reranking/05-训练数据与Hard-Negatives
translation_default_route: zh-CN/Reranking/05-训练数据与Hard-Negatives
---

# Training data and hard negatives

## Goal of this lesson

A reranker does not learn “truth.” It learns from its training queries, candidate pools, labeling rules, and negative distribution. After this lesson, you should be able to choose pointwise, pairwise, or listwise data, mine hard negatives from real retrieval, avoid treating unlabeled candidates as negatives or leaking near duplicates, and maintain an auditable data loop.

## Three forms of supervision

| Form | Example | Best suited to | Common risk |
| --- | --- | --- | --- |
| Pointwise | `(q, d, label/grade)` | Classification, regression, independent scoring | Class imbalance and cross-query scale |
| Pairwise | `(q, d+, d−)` | Learn that positives outrank negatives | Pair explosion and non-transitive ordering |
| Listwise | `(q, [d…], ranking/qrels)` | Optimize a list directly | Fixed-window/position bias and cost |

The data form must agree with the model loss, production output, and evaluation. If qrels use grades 0 through 3 but training uses binary labels, document the mapping and the lost grade information.

## Why random negatives are too easy

For a positive about “when a refund arrives,” a random negative about “membership renewal” can be separated by topic alone. The model has not learned genuine relevance. Production failures are harder:

- a same-topic document explains how to apply but not when money arrives;
- an old policy gives conflicting numbers;
- the same error code belongs to another product;
- a document contains every keyword but gives a negative answer;
- a near-duplicate passage omits a critical condition; or
- a first-stage candidate ranks high but receives human grade 0.

These are hard negatives: candidates that the current retriever or model can easily confuse with positives, but that annotation has confirmed to be irrelevant.

## Absence from qrels does not mean negative

Qrels are incomplete in large corpora. Treating every unjudged top-*k* candidate as negative penalizes a model for discovering a new positive. A safer process is:

1. Pool candidates from several retrievers and rerankers.
2. Label high-ranked candidates unique to a new system.
3. Distinguish judged negatives from unjudged candidates.
4. Treat them differently in training according to confidence and provenance.
5. Sample high-loss or frequently selected negatives for inspection.

The “hardest negative” mined by a model may actually be a missing positive label, so it particularly needs human review.

## The hard-negative mining loop

```text
Freeze a first-stage/reranker snapshot
        ↓
Collect high-ranked errors and production failures
        ↓
Deduplicate, redact, and isolate by permission
        ↓
Blind annotation and adjudication against guidelines
        ↓
Create a versioned point/pair/list dataset
        ↓
Train → validate → archive the test set
        ↓
Shadow/canary → feed new failures into the next round
```

Record query ID, candidate/source revision, retriever/model revision, first rank/score, label/evidence, and sampling reason. Without them, you cannot explain the training distribution after a new model is released.

## Mixing negatives

A training batch can combine:

- **random negatives** to preserve broad topic discrimination;
- **in-batch negatives**, which are cheap but may be relevant to another query;
- **BM25 hard negatives** that are lexically similar;
- **dense hard negatives** that are semantically similar;
- **previous-reranker errors** that most closely resemble production; and
- **adversarial negatives** involving numbers, negation, expiry, or prompt injection.

Tune proportions on a validation set; do not use only the hardest examples. Excessive hard mining can hurt simple queries or overfit an old retriever.

## Splits and leakage

At minimum, group by canonical source or document so adjacent chunks cannot cross train and test. Also check:

- whether rewrites of the same query cross splits;
- near duplicates from the same template or FAQ;
- future-information leakage through time;
- whether a label-generating model saw the benchmark;
- whether test failures enter training every round; and
- exposure-position and old-model bias in click logs.

Each active-learning round should create new train and validation versions. The archived test set does not participate in selection.

## Click and behavioral logs

Clicks, dwell time, and task success add scale, but they are not direct relevance labels:

- users can click only candidates they were shown;
- first position naturally gets more exposure;
- no click can mean no need to click or a failed page;
- sensitive-query collection has privacy and compliance constraints; and
- the old ranker determines which candidates become visible.

Randomized exploration, propensity correction, human samples, and multiple signals can reduce these effects, but their assumptions must remain documented. Do not treat click=1 and no-click=0 as unbiased truth.

## LLM-synthesized and distilled labels

An LLM can generate queries, negatives, or relevance rationales; work such as RankGPT also explores teacher ranking and distillation. Guard against:

- teacher preferences becoming student “truth”;
- generated query language becoming unnaturally regular;
- labels that hallucinate facts outside the source;
- dataset or benchmark contamination;
- label drift after prompt/model changes; and
- sending private candidates to an unauthorized service.

Keep the generation prompt, model, revision, input source, output, and human audit. Critical tests and safety boundaries still require confirmation by people or rules.

## Versions and data cards

For every version, record at least:

- task, language, domain, and time range;
- query/candidate counts, label distribution, and source groups;
- negative types and proportions;
- annotation guidelines, agreement, and adjudication;
- deduplication, redaction, and permission handling;
- train/validation/test split checksums;
- known gaps, prohibited uses, and retention period; and
- associated model, code, and feature schema.

## Common mistakes and how to investigate them

- **Random-negative scores look high but production does not improve**: add real first-stage errors.
- **A hard negative is actually relevant**: label it and adjudicate.
- **Adjacent chunks leak**: group by canonical source.
- **Sampling uses only the old retriever**: pool several systems and exploration samples.
- **Clicks are used directly as labels**: address exposure and position bias.
- **The test set enters training every round**: archive it and create a diagnostic set.
- **LLM labels have no provenance**: freeze prompt/model/source and audit samples.

## Exercise

For “refund arrival time,” construct:

1. one grade-3 positive and one grade-1 partially relevant example;
2. three hard negatives: an expired number, an application-only document, and a negated condition;
3. one dense hard negative and one random negative;
4. pointwise, pairwise, and listwise representations;
5. a canonical-source-grouped split; and
6. a data card with sampling reason, retriever revision, and annotation evidence.

## Mastery check

- [ ] Data form agrees with loss, output, and metrics.
- [ ] Hard negatives come from real confusion and receive confirmed labels.
- [ ] Unjudged candidates are not automatically negatives.
- [ ] Random, retriever, and adversarial negatives have controlled proportions.
- [ ] Source/query rewrites and time-based near duplicates do not cross splits.
- [ ] The bias, provenance, and privacy of click and LLM labels are understood.
- [ ] The test set is archived and the training loop is versioned.

Next: [[reranking/06-metrics-latency-cost-and-fallbacks|Metrics, latency, cost, and fallbacks]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Nogueira, Jiang & Lin, [monoT5](https://arxiv.org/abs/2003.06713)
- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)

Sources checked on 2026-07-14. Return to the [[reranking/00-index|Reranking course overview]].
