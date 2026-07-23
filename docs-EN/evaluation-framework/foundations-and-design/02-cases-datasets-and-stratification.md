---
title: "Cases, Datasets, and Stratification"
aliases:
  - Evaluation Dataset Design
tags:
  - evaluation
  - datasets
source_checked: 2026-07-14
lang: en
translation_key: 评测体系/01-基础与设计/02-用例数据集与分层.md
translation_source_hash: a2d607d96dd21076f95ed3774025e9df988e0c01b609f63bedde43f91fb4a02c
translation_route: zh-CN/评测体系/01-基础与设计/02-用例数据集与分层
translation_default_route: zh-CN/评测体系/01-基础与设计/02-用例数据集与分层
---

# Cases, Datasets, and Stratification

## Goal

Turn real requirements into traceable cases while retaining both production representativeness and difficult-scenario coverage.

## Intuition

An evaluation set is both a sample survey and a fault test. Its core set should approximate real use, while a stress set deliberately amplifies rare and high-risk conditions. Both matter, but their results cannot be interpreted with the same weights.

## What every case should record

```json
{
  "id": "order-zh-edge-003",
  "input": "Please check where order A-102 is.",
  "initial_state": {"order_exists": true, "refunded": false},
  "expected_outcome": {"looked_up_order": "A-102", "refunded": false},
  "strata": ["zh", "implicit-intent", "read-only"],
  "severity": "high",
  "source": "redacted-production-failure",
  "dataset_version": "2026-07-14"
}
```

This is strict JSON, so do not append comments to its lines. The `id` is a stable identity for locating a regression; `input` is controlled input; `initial_state` and `expected_outcome` record the runtime precondition and verifiable end state; `strata` enables stratified reporting; `severity` determines risk priority; `source` describes provenance; and `dataset_version` binds the case to a reproducible dataset version.

Retaining input, initial and expected state, strata, severity, source, and version makes a failure reproducible and coverage explainable. Production data must be de-identified and handled under authorization and retention policy.

## Combine data sources

- **Production or historical logs:** closest to the real distribution, but affected by privacy, selection bias, and historical-version behavior.
- **Domain-expert authored cases:** useful for rules, risks, and rare failures, but costly.
- **Public data:** convenient for comparison, but it can differ from the product's user distribution or already be contaminated.
- **Synthetic data:** rapidly covers combinations; label its generation method and calibrate it against real samples.
- **Failure replay:** turn each incident into a minimal reproduction for a regression set.

OpenAI's guidance recommends mixing production, historical, domain, and synthetic data and including typical, boundary, and adversarial scenarios. NIST emphasizes recording the similarity among the test set, tools, and deployment conditions.

## Stratify instead of reading only the overall average

Stratify by real risk, such as language, task type, input length, tool, permission, user group, data freshness, and failure severity. An overall score of 90% can hide a severe “20% on Chinese refund tasks” problem. Report all of:

- sample count and pass rate for every stratum;
- minimum gates for critical strata;
- an overall estimate weighted by production distribution;
- stress-set results with explicitly non-production weights.

Stress sets discover capability boundaries; they must not be presented as natural-traffic proportions.

## Freeze, develop, and regress

- The training set changes model parameters or builds example libraries, so it cannot also be independent validation evidence.
- The development set tunes prompts, rules, and graders.
- A frozen validation or test set is for stage decisions, preventing repeated answer inspection from becoming “teaching to the test.”
- A regression set continuously receives confirmed failures, but needs deduplication, versioning, and protection from unbounded bias toward old problems.
- Never place the same user session, source-document chunks, or near-duplicate samples on both the development and test sides.

**Leakage** occurs when test information that should be unknown reaches the system under test through training, prompts, a retrieval corpus, graders, or human tuning. A random row split is insufficient: a session, document, template, user, or `family_id` created from the same source sample must be assigned as a group to one split. After frequent inspection, a test set gradually becomes a development set even if no file moved; create a new hidden holdout and record its transition date.

## Version, coverage, and a data card

For every release-significant evaluation, record:

- dataset version, content digest, creator, authorization, time range, and deduplication rule;
- case count, source, language, task, risk, tool, and difficulty coverage per split;
- proportions of real, synthetic, public, and incident-replay samples, and whether production weights were used;
- label definitions, adjudication state, unknown proportion, and last-review date;
- target populations and failure modes with no samples, so conclusions are not extrapolated to them.

“A sample exists” in a coverage matrix does not mean there are enough samples. For critical slices, report count, pass rate, and uncertainty together. Rare high-loss events can use stress sets or singleton hard-gate tests, but must not be presented as a natural occurrence rate.

## Common mistakes and diagnostics

- Collecting only easily available thumbs-up/down samples: record the selection mechanism; conditional samples are not a population estimate.
- Mixing synthetic boundary samples into production weights: label a separate stress stratum.
- Splitting related documents or sessions across splits: group by source or family ID.

## Exercises

1. List five production strata and three stress strata for document question answering.
2. Explain why collecting only negative user feedback in production cannot estimate overall satisfaction: it is a conditionally selected sample.

## Self-check

Does adding many synthetic boundary examples and lowering the overall score necessarily mean the product regressed? No. The data distribution changed; compare fixed versions and stratify.

## Summary and next step

Continue to [[evaluation-framework/methods-and-quality/03-deterministic-assertions-metrics-and-scoring-rules|Deterministic Assertions, Metrics, and Scoring Rules]].

## References

- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-14; its methodological guidance remains useful, while the linked Evals platform is in a deprecation transition.
- [MLflow Evaluation Dataset concepts](https://mlflow.org/docs/latest/genai/concepts/evaluation-datasets/) — documentation labeled `latest`, checked 2026-07-14; pin the actual package version when adopting it.
- [NIST AI RMF Core: Measure 2.1–2.5](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — checked 2026-07-14.
- [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1) — 2024-07; checked 2026-07-14.
