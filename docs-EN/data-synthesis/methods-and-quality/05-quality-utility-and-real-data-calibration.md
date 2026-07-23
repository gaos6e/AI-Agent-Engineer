---
title: "Quality, Utility, and Real-Data Calibration"
aliases:
  - Synthetic Data Quality and Utility
  - Synthetic Data Utility Evaluation
tags:
  - synthetic-data
  - quality
  - utility-evaluation
source_checked: 2026-07-14
lang: en
translation_key: "数据合成/02-方法与质量/05-质量效用与真实数据校准.md"
translation_source_hash: 4147bd61d59978a5e2fe8984cbafd86dd2e28c2349505c267510d0e2b3e1e8ce
translation_route: zh-CN/数据合成/02-方法与质量/05-质量效用与真实数据校准
translation_default_route: zh-CN/数据合成/02-方法与质量/05-质量效用与真实数据校准
---

# Quality, Utility, and Real-Data Calibration

## Objective

Evaluate synthetic data across structural validity, semantic correctness, coverage, diversity, distribution fidelity, downstream utility, and risk, then validate claims against an independent real holdout.

## Intuition

Synthetic data can be highly fluent while covering only a few easy patterns. It can look statistically similar to real data but provide no value in training the target model. Quality must be defined against a purpose; no general “synthetic-quality score” replaces downstream validation.

## Core concepts

- **Validity** — Schema and business rules hold.
- **Fidelity** — synthetic distribution is close to a real reference in target statistics or structure.
- **Coverage** — areas of a planned condition space that are covered.
- **Diversity** — nonredundant sample variation; surface vocabulary variation is not task diversity.
- **Downstream utility** — whether data improves the target decision after training, evaluation, or simulation.
- **TSTR** — a train-on-synthetic, test-on-real utility check; applicable only to the corresponding training task.
- **Calibration set** — an independent, authorized, real small sample excluded from generation/tuning, used to calibrate metrics or human judgment.

## Quality dimensions cannot offset one another

100% structural validity cannot offset incorrect labels; high fidelity cannot offset privacy risk; better aggregate utility cannot offset degradation in a critical safety slice. Make privacy/source/critical correctness hard gates first, then report coverage, diversity, cost, and utility as a Pareto view. If a team must aggregate a score, show hard failures and every dimension separately so an average cannot hide nonexchangeable risk.

A training-utility comparison should include at least no synthetic data, real only, synthetic only, and real plus synthetic. Keep training budget, model, hyperparameters, and real holdout constant; report several seeds and slices rather than one best run. Evaluation-oriented synthetic data instead asks whether it stably recreates expert-confirmed failures, distinguishes frozen baselines, and aligns with real cases in system ranking/error type.

## Method

1. List quality dimensions and hard thresholds by purpose; do not average every dimension.
2. Sample-review every condition stratum, generator, and rejection boundary.
3. Report Schema pass rate, label agreement, duplicate rate, and condition coverage—not only retained count.
4. Compare length, categories, key fields, correlation structure, and failure modes against a real reference; state public reference sample size.
5. For training, compare real training, synthetic training, mixed training, and a simple baseline on fixed real tests.
6. For evaluation, use real failures/expert cases to check system ranking and error-pattern alignment.
7. Check whether adding synthetic data changes small groups, rare slices, and risk failures—not aggregate results alone.
8. Recalibrate whenever generator, filtering, or model version changes.

A real holdout must be independent enough to support the claim: it cannot be a generator seed, prompt example, judge calibration, and final utility evidence. With little real data, cross-validation or bootstrap can express uncertainty, but resampling cannot supply missing populations. State sample size, selection method, authorization boundary, and uncovered slices in the report.

## Example

An evaluation-dataset dashboard can use:

| Dimension | Evidence | Does not establish |
| --- | --- | --- |
| Schema validity | Parsing and field rules | Correct label |
| Condition coverage | Per-cell count and gap | Real-distribution proportion |
| Human correctness | Stratified blind review and disagreement | Every unreviewed sample is correct |
| System discrimination | Difference across frozen baselines | Production effect |
| Real-failure recall | Recreates known failures | Every unknown risk is covered |
| Privacy risk | Attack/similarity review or formal guarantee | Zero risk |

NIST's SDNist v1.4 tool compares utility and privacy metrics for particular tabular-data settings and illustrates multidimensional reporting. Its official page lists its last software update as 2022-02-01. It is not a general certifier for text/Agent data, and its values cannot be copied into this course.

## Common mistakes and diagnosis

- **Generator judge is the sole quality truth.** Add rules, experts, and a real holdout.
- **Compare only word frequency or Embedding distance.** Add task labels, behavior, and downstream utility.
- **Generate and calibrate on the same real samples.** Create an independent holdout to avoid circular proof.
- **Look only at overall averages.** Slice by language, condition, risk, and source.
- **One synthetic-training improvement remains valid forever.** Revalidate after distribution or model change.

## Exercises

1. Write two validity, coverage, and utility metrics for synthetic RAG questions.
2. Design a small real holdout excluded from prompting, generation, and filter tuning.
3. Explain how high diversity can still lower label quality, then design a Pareto report.

## Self-check

1. Does similarity to a real distribution prove training utility? No; run a fixed downstream task.
2. Can synthetic data reveal boundaries absent in real data? Yes, but that proves coverage, not incidence rate.
3. What if the real holdout is very small? Report uncertainty, thin slices, and human evidence; do not overclaim.

## Summary and next step

Synthetic quality is defined by target utility and independent evidence. Continue with [[data-synthesis/methods-and-quality/06-privacy-memorization-bias-and-copyright|Privacy, Memorization, Bias, and Copyright]] to review risks that can remain unacceptable even when data is useful.

## References

- [NIST SDNist Synthetic Data Report Tool](https://www.nist.gov/services-resources/software/sdnist-synthetic-data-report-tool) — page lists v1.4 and last update 2022-02-01; accessed 2026-07-14.
- [NIST PETs Testbed](https://www.nist.gov/itl/applied-cybersecurity/privacy-engineering/pets-testbed) — accessed 2026-07-14.
- [Data Cards original paper and official page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/) — accessed 2026-07-14.
