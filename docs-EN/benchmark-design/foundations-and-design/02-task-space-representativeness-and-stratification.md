---
title: "Task Space, Representativeness, and Stratification"
aliases:
  - Benchmark Representativeness
  - Task Taxonomy and Strata
tags:
  - benchmark
  - representativeness
  - stratification
source_checked: 2026-07-14
lang: en
translation_key: Benchmark设计/01-基础与设计/02-任务空间代表性与分层.md
translation_source_hash: 8e4cad032424783029c968d4b3c3974b87a014d472a84a456823bd08cdf28214
translation_route: zh-CN/Benchmark设计/01-基础与设计/02-任务空间代表性与分层
translation_default_route: zh-CN/Benchmark设计/01-基础与设计/02-任务空间代表性与分层
---

# Task Space, Representativeness, and Stratification

## Goal

Decompose target use into a task space and stratification matrix, distinguishing a core set that represents the production distribution from a stress set that deliberately amplifies difficult conditions.

## Intuition

Sampling 100 people at a hospital entrance does not represent all patients; selecting only the hardest cases cannot estimate ordinary accuracy either. Representativeness is not “enough questions.” It is whether the sampling frame, coverage dimensions, weights, and gaps match the claim.

## Core concepts

- **target population:** users, tasks, and environments to which the result is intended to generalize.
- **sampling frame:** the actual source from which samples can be drawn, often narrower than the population.
- **stratum:** a business-meaningful layer that needs separate observation, such as language, intent, or risk.
- **core set:** approximates the target distribution for overall estimation and stable comparison.
- **challenge/stress set:** increases boundary, rare, or adversarial samples to find weaknesses.
- **coverage gap:** an area known to lack reliable samples; it must be disclosed rather than hidden by an average.

## Step-by-step method

1. From the Benchmark claim, list six axes: users, tasks, inputs, environment, difficulty, and risk. Define difficulty with observable factors such as step count, missing information, or tool failure, not retrospective model score labels.
2. Retain only dimensions that change system behavior or failure cost, avoiding combinatorial explosion.
3. Estimate core-stratum weights from historical traffic or domain evidence and record the evidence time window.
4. Establish independent stress strata for high-risk, low-frequency, and new capabilities; do not mix them into production weights.
5. Record sample count, source, expected failure cost, and minimum threshold for every stratum.
6. Maintain a coverage-gap table for no samples, uncertain labels, inability to run, or mismatched deployment conditions.
7. Report stratified results first, then aggregate with frozen weights; never retain only the overall average.

## Control coverage with task templates

A task template is not one prompt. It is the structure for generating a family of cases: objective, input variables, environment preconditions, allowed tools, expected final state, risks, and grader. Define templates first, generate concrete cases from real sources, expert construction, or synthesis, and retain a `family_id`. Surface rewrites of one template share a family, preventing memory of a template from being mistaken for generalization across splits.

Every slice must report sample count `n`. If a high-risk slice has only two tasks, `1/2=50%` is true but cannot support a stable population conclusion. State “the current sample signals a failure” and add cases or human review. Ten rewrites of one family do not equal ten independent scenarios.

## Example

A simplified order-Agent task matrix:

| Dimension | Core stratum | Stress stratum |
| --- | --- | --- |
| Intent | Status lookup, shipping lookup | Ambiguous multi-intent, conflicting objectives |
| Language | Simplified Chinese | Mixed Chinese/English, colloquial abbreviations |
| Input state | Complete ID, existing order | Missing ID, nonexistent order, duplicate ID |
| Permission | Read-only query | Refund inducement, unauthorized read |
| Environment | Healthy tool | Timeout, empty response, stale data |

If production traffic has 70% status lookup and 30% shipping lookup, the core set can aggregate using those weights. Even if unauthorized-action inducement comprises 50% of the stress set, label it separately as non-production-weighted.

## Common mistakes and diagnostics

- **Sample only easy-to-obtain data:** sampling frame differs from target population; record the difference and collect more.
- **Call equal counts per stratum “representative”:** balance aids diagnosis but does not equal the real distribution; report balanced macro average and production-weighted result separately.
- **Too many dimensions leave one sample per cell:** merge business-equivalent strata and prioritize critical interactions.
- **Look only at mainstream users:** critical minority groups can be drowned by an average; add separate thresholds.
- **Compare stress-set score directly with core-set score:** first state their different sampling purpose and weights.

## Exercises

1. Design a matrix of domain × question type × evidence state × risk for Chinese RAG.
2. Label every stratum as core, stress, or currently missing, and explain why.
3. Choose two dimensions most likely to interact and explain why cross-strata are needed.

## Self-check

1. Is finer stratification always better? No. Too few samples make estimates unstable and increase maintenance cost.
2. Can a stress set estimate production failure rate? Usually not, unless it was built with real sampling and weights.
3. If the overall score rises but a critical language stratum falls, can you claim a universal improvement? No. Apply predeclared thresholds and decision rules.

## Summary and next step

Representativeness means “representative for whom and under which conditions,” not a property of question count. After completing task space and gap table, continue to [[benchmark-design/foundations-and-design/03-data-splits-leakage-and-contamination|Data Splits, Leakage, and Contamination]] to protect independent comparison evidence.

## References

- [NIST AI 600-1: TEVV data representativeness, coverage, and cross-contamination guidance](https://doi.org/10.6028/NIST.AI.600-1) — retrieved 2026-07-14.
- [HELM original paper](https://openreview.net/forum?id=iO4LZibEqW) — retrieved 2026-07-14.
- [The Benchmark Lottery](https://arxiv.org/abs/2107.07002) — original paper, retrieved 2026-07-14.
- [Datasheets for Datasets](https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/) — original paper page, retrieved 2026-07-14.
