---
title: "Baselines, Metrics, and Comparable Runs"
aliases:
  - Comparable Benchmark Runs
  - Baselines Metrics and Protocol
tags:
  - benchmark
  - metrics
  - comparability
source_checked: 2026-07-14
lang: en
translation_key: Benchmark设计/02-方法与质量/04-基线指标与可比运行.md
translation_source_hash: 658b3669a900f5de1cf1507ec85b80e785ee1c02679d6e0fe88e3b015f1b4394
translation_route: zh-CN/Benchmark设计/02-方法与质量/04-基线指标与可比运行
translation_default_route: zh-CN/Benchmark设计/02-方法与质量/04-基线指标与可比运行
---

# Baselines, Metrics, and Comparable Runs

## Goal

Choose interpretable baselines and metrics, then freeze prompts, tools, budget, randomness, and environment so differences between systems come from candidates rather than run conditions.

## Intuition

Giving one contestant a calculator and another mental arithmetic, then comparing answer speed, cannot show whose algorithm is stronger. Benchmark runs must control adaptation resources too: few-shot examples, retrieval corpus, tools, retries, context length, and hardware can all change results.

## Core concepts

- **baseline:** a comparison reference such as random/majority class, a simple rule, a published implementation, or current production version.
- **primary metric:** the indicator most directly connected to the core claim.
- **guardrail / gate:** a risk or quality threshold that other gains cannot offset.
- **macro average:** calculate each stratum first, then average with equal weight to keep large strata from dominating.
- **micro / weighted result:** aggregate all samples or frozen production weights.
- **run protocol:** complete rules for model/application version, prompt, adaptation, budget, environment, and failure handling.
- **resource metric:** cost such as latency, call count, tokens, VRAM, or currency.

## Step-by-step method

1. Provide at least one simplest baseline and one current usable baseline; an absolute score without baseline makes improvement hard to judge.
2. Choose one primary metric, but also list critical strata, risk gates, and resource metrics.
3. Freeze normalization, missing-value, timeout, abstention, and partial-credit rules before viewing candidate results.
4. Give every system the same input, tool definition, permissions, external state, maximum turns, and time window.
5. Record prompt template, few-shot examples, decoding parameters, random seed, model snapshot, and dependency versions.
6. Run stochastic systems for multiple trials from clean environments and report success probability rather than selecting the best run.
7. If architectural differences prevent a fully shared protocol, disclose the difference and change the claim to a “complete-system utility comparison”; do not claim a bare-model capability difference.

## Freeze the scoring contract

Before running candidates, state:

- numerator, denominator, and aggregation level for the primary metric;
- whether critical safety/privacy tasks require every trial to pass;
- how partial success, abstention, timeout, exception, parse failure, and `Unknown` score;
- whether a missing case is a contract error or a failure in the denominator;
- how cost, mean/p95 latency, and tool calls are measured;
- which conditions produce BLOCK, REVIEW, or `INCOMPARABLE`.

**Missing is not Unknown:** a missing record means the submission did not cover frozen test and normally rejects the whole result package. Unknown means a record exists but its state cannot be decided; under the predeclared rule it either fails or enters human review. Neither may disappear silently from the denominator.

## Fair comparison and incomparable conclusions

Equal resources do not require identical hardware models forever, but they must satisfy the claim's equivalent constraints. Comparing end-to-end systems may freeze maximum time and cost. Comparing model capability must additionally freeze prompt, tools, retrieval, and adaptation data. If a candidate gains retries, tool permissions, or private data, place it in another track or mark it `INCOMPARABLE`; do not calculate a higher score and hide the difference in a footnote.

## Example

Binary-classification accuracy:

$$
Accuracy=\frac{\text{correct samples}}{\text{all samples}}
$$

If stratum A has 90 samples and 90% accuracy while stratum B has 10 samples and 20% accuracy, micro result is 83%; equal-stratum macro result is $(90\%+20\%)/2=55\%$. They answer different questions: the first is closer to the current sample distribution, and the second emphasizes balance across strata. Reports need stratum sample counts and the reason for the choice.

One run checklist:

~~~yaml
model_snapshot: exact-provider-or-local-id # Freeze model snapshot or local-model identity; do not compare floating aliases.
prompt_version: sha256-or-git-id # Lock the prompt by content digest or commit ID.
temperature: 0 # Freeze randomness; a stochastic experiment must separately declare repetitions and seeds.
max_attempts: 1 # Control retry budget so a candidate does not receive hidden extra opportunities.
tool_set: readonly-v2 # Freeze allowed tools and versions; otherwise capability boundary differs.
timeout_seconds: 30 # Use one timeout definition; protocol must also decide whether timeout is failure.
external_state: frozen-fixture-v1 # Freeze external state to keep dynamic data from destroying reproducibility.
missing_output: fail # State how missing output scores; do not decide after seeing results.
~~~

## Common mistakes and diagnostics

- **Compare only with a weak baseline:** add current production or a publicly reproducible implementation.
- **Metric misaligned to task:** string similarity cannot prove factual correctness; write outcome assertions.
- **Candidate receives more context or retries:** either constrain equivalently or report both gain and added cost.
- **Delete timed-out samples:** timeout is system behavior; score it under frozen rule and report it separately.
- **Provide only weighted total:** add every stratum, critical risk, and resource cost.

## Exercises

1. Select a simple baseline, production baseline, primary metric, and two gates for a mail-classification Agent.
2. List five conditions that must be fixed when comparing the same model with different RAG.
3. Design trial count and environment-reset rules for a stochastic generation task without inventing a universal “best number.”

## Self-check

1. Is macro always fairer than micro? No. They encode different weighting assumptions and must match the claim.
2. Which system is better if a candidate is higher quality but doubles cost? Quality alone cannot decide; apply predeclared resource constraints.
3. Does temperature 0 guarantee full determinism? No. Service, hardware, tool, and implementation details can remain nondeterministic.

## Summary and next step

Comparability comes from explicit baselines, equivalent protocols, and multi-dimensional reporting, not from “running the same button.” Continue to [[benchmark-design/methods-and-quality/05-reproducibility-statistics-and-results-reporting|Reproducibility, Statistics, and Results Reporting]] to turn one run into an auditable evidence package.

## References

- [HELM original paper](https://openreview.net/forum?id=iO4LZibEqW) — retrieved 2026-07-14; methodological source.
- [HELM official repository](https://github.com/stanford-crfm/helm) — retrieved 2026-07-14; in maintenance mode from 2026-06-01.
- [MLPerf Inference official rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) — master branch checked 2026-07-14; verify current rules when adopting them.
- [NIST AI RMF Core: Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — retrieved 2026-07-14.
