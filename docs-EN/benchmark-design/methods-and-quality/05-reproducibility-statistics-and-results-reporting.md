---
title: "Reproducibility, Statistics, and Results Reporting"
aliases:
  - Reproducible Benchmark Reporting
  - Benchmark Statistics
tags:
  - benchmark
  - reproducibility
  - statistics
source_checked: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "NIST, MLPerf, and OpenAI primary materials plus original work
  on Model Cards and paired resampling through 2026-07-21"
lang: en
translation_key: Benchmark设计/02-方法与质量/05-复现统计与结果报告.md
translation_source_hash: efb373261c83e6a69b5c2b4a30af23ad1998d30265a9e324fc6b9c31f2e25077
translation_route: zh-CN/Benchmark设计/02-方法与质量/05-复现统计与结果报告
translation_default_route: zh-CN/Benchmark设计/02-方法与质量/05-复现统计与结果报告
---

# Reproducibility, Statistics, and Results Reporting

## Goal

Preserve inputs, protocol, outputs, and environment metadata sufficient to replay a run, then report candidate differences through paired comparisons, stratified results, and uncertainty.

## Intuition

“It scored 87 on my computer” is not an auditable result. Reproduction requires knowing which data version was measured, which code and conditions were used, how failures were handled, and how aggregates can be recomputed from per-item output. Statistical reporting must also state how much results can vary under finite samples.

## Core concepts

- **artifact:** data manifest, checksum, code, configuration, log, raw output, and score result.
- **fingerprint:** content hash over normalized data and protocol, used to identify whether “the same thing was measured.”
- **paired comparison:** compare candidate and baseline on the same case to reduce noise from case difficulty.
- **confidence interval:** an interval with repeated-sampling coverage under a predeclared method, not a subjective probability guarantee about truth in this run.
- **effect size:** magnitude of a difference, not merely whether it is “significant.”
- **multiple comparisons:** trying many candidates, metrics, or slices and choosing the best increases chance findings.

## Step-by-step method

1. Version the Benchmark card, data manifest, grader, and run configuration.
2. Retain every case ID, group, stratum, input, raw output, individual score, and error.
3. Record operating system, Python/dependencies, model snapshot, prompt hash, tool version, time window, and random seed.
4. Compute candidate-minus-baseline paired differences on the same cases.
5. Report sample count, mean/proportion, difference interval, stratified results, and critical-failure list.
6. Repeat stochastic systems independently by task; retain trial-level data rather than averaging it away.
7. Put every failure, timeout, and missing item in the denominator under frozen rules.
8. Publish the aggregate table with the raw result package. Sensitive input can be access-controlled, but a screenshot alone is insufficient.

## Pairing, repeated runs, and slice sample counts

If baseline and candidate run on the same case under the same trial protocol, construct paired difference $d_i$ by task before reporting average difference and interval. Do not treat two result sets as unrelated samples. A stochastic Agent must retain `task × trial` records: task count describes coverage; repeated trials describe run variation on one task. They cannot be merged into a false independent sample count.

Every slice reports `n`, success count, proportion, and an interval or explicit small-sample limitation. If many slices are checked and only the largest decline is published, chance variation is amplified. Predeclare critical slices and label post-result findings exploratory until retested.

## Harness and evidence fingerprint

A reproducibility package freezes more than data and result: it fixes harness version, environment image or fixture, setup, grader, reset, tool schema, budget, and failure handling. An evidence fingerprint should cover Benchmark spec, cases, protocol, and results. An equal fingerprint proves only that input contents match; it does not prove the runtime machine is trusted, the data lawful, or the design valid.

A minimum Benchmark report card includes claim and non-goals; target population; data version/source; protocol; tested systems; baselines; metrics and gates; overall and slice results; statistical method; resources; contamination/exposure/runtime discoverability; known limitations; reproduction state; approver; and expiration. It must also disclose each tested system's adaptation budget, submission count, and feedback granularity, distinguishing pre-frozen confirmatory analysis from exploration proposed after results appear.

## From score to valid conclusion

A strong conclusion checks claim, harness, and validity together. At minimum, count and review broken or ambiguous tasks, grader errors, reward loopholes, safe refusals mistakenly penalized, train/test contamination, Agents finding public answers at runtime, repeated-submission adaptation, and evaluation-awareness or sandbagging risk. Report confirmed, suspected, not-detected, and unknown separately; do not upgrade “not found” to “absent.”

Every exclusion, rescoring, or protocol repair must retain original result, adjusted result, case count, and rationale. If a repair changes task meaning, tool, budget, or scoring rule, create a new version and comparison boundary rather than quietly adding adjusted score back to an old leaderboard.

## Example

A result record contains at least:

~~~json
{
  "benchmark_id": "order-agent-readonly",
  "benchmark_version": "1.0.0",
  "benchmark_fingerprint": "sha256:...",
  "system_id": "candidate-2026-07-14",
  "run_config": {"seed": 23, "max_attempts": 1},
  "sample_count": 120,
  "primary_score": 0.81,
  "paired_delta_vs_baseline": 0.04,
  "interval_method": "paired bootstrap",
  "limitations": ["offline fixture", "does not cover refund writes"]
}
~~~

Strict JSON cannot have comments at line ends or a reader rejects it. `benchmark_id` and `benchmark_version` jointly lock the task; `benchmark_fingerprint` binds frozen protocol; `system_id` identifies the compared implementation; `run_config` freezes randomness and retry conditions that affect results; `sample_count` supplies the denominator; `primary_score` and `paired_delta_vs_baseline` report absolute result and paired difference; `interval_method` identifies uncertainty computation; and `limitations` states boundaries that cannot be extrapolated.

If candidate and baseline outcomes for the same case are 0 or 1, first obtain each $d_i$, then aggregate $\bar d$. The teaching project resamples these $d_i$ with replacement under a fixed seed; real research must check sample independence, stratification, repeated trials, and method applicability.

## Common mistakes and diagnostics

- **Save only total score:** localization and rescoring become impossible; retain per-item raw output.
- **Report only a p value:** add effect size, interval, sample count, and real failure cost.
- **Say systems are exactly the same when interval crosses 0:** current data only fail to establish a clear direction.
- **Keep trying candidates and report only winner:** record every comparison or use an independent final holdout.
- **Record random seed but data/API changes:** freeze or version external dependencies too.
- **Use one Boolean for contamination status:** disclose training exposure, runtime discoverability, developer adaptation, and detection uncertainty separately.

## Exercises

1. List minimum reproducibility files for one RAG Benchmark run.
2. Hand-calculate the average difference for paired 0/1 results on eight cases.
3. Explain why “two independent-sample proportion intervals” usually discard same-case pairing information.

## Self-check

1. Can a content hash prove data are correct? No. It only helps prove content consistency.
2. Does one successful reproduction prove a universal result? No. Reproduction is not external validity.
3. Can many samples remove stratification bias? No. Systematic sampling bias does not disappear merely through count.

## Summary and next step

A trustworthy result package answers “what was measured, how, what happened per item, how large is the difference, and what limitations remain.” Continue to [[benchmark-design/methods-and-quality/06-leaderboard-mechanics-anti-gaming-and-maintenance|Leaderboard Mechanics, Anti-Gaming, and Maintenance]].

## References

- [MLPerf Inference official rules: reproducibility, fixed input, and audit](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) — master branch checked 2026-07-21.
- [Model Cards for Model Reporting](https://research.google/pubs/model-cards-for-model-reporting/) — original paper page, retrieved 2026-07-21.
- [Koehn 2004: Statistical Significance Tests for Machine Translation Evaluation](https://aclanthology.org/W04-3250/) — original paper, retrieved 2026-07-21.
- [NIST/SEMATECH: Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm) — retrieved 2026-07-21.
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) — published 2026-05-29; claims, harnesses, validity checks, and results reporting.
