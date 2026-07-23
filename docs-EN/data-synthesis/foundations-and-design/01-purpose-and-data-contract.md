---
title: "Purpose and Data Contract"
aliases:
  - Synthetic Data Contract
  - Synthetic Data Requirements
tags:
  - synthetic-data
  - data-contract
source_checked: 2026-07-22
lang: en
translation_key: "数据合成/01-基础与设计/01-目标与数据契约.md"
translation_source_hash: 815c5a5da5b507cad4a6395606a1eb76adefbe4323d7a1274c2e0b9a5505e782
translation_route: zh-CN/数据合成/01-基础与设计/01-目标与数据契约
translation_default_route: zh-CN/数据合成/01-基础与设计/01-目标与数据契约
---

# Purpose and Data Contract

## Objective

Distinguish evaluation, training, simulation, and privacy-release purposes. Before generation, freeze target population, Schema, condition coverage, quality thresholds, and stopping rules.

## Intuition

The same “realistic-looking” customer-support conversations may suit a UI demonstration but not training. They may suit stress testing but not estimate online accuracy. Purpose determines which properties matter and which independent evidence is required for acceptance.

## Core concepts

- **Target use** — the exact decision or workflow the data supports.
- **Target population** — the real population of samples to approximate or cover.
- **Data contract** — fields, types, allowed values, constraints, source, and acceptance conditions.
- **Factor / condition** — a controlled task dimension such as intent, language, permission, or tool state.
- **Provenance** — how each record was produced, including inputs, model/template, and processing steps.
- **Source declaration** — technically known input class, source version, and whether real data was touched. It is an auditable factual record, not a conclusion about authorization, copyright, or anonymity.
- **Authorization / review-evidence reference** — a reference to a controlled approval, license, or privacy-review artifact. Possessing an ID does not prove approval: status, scope, expiry, and exception need separate records.
- **Release scope** — accessibility such as teaching, controlled internal use, partner sharing, or public release, including retention, withdrawal, and republication constraints.
- **Acceptance gate** — hard conditions that a sample or dataset must pass before advancing.
- **Stop rule** — stop generation once coverage and utility are reached rather than masking low quality with volume.
- **Unit of synthesis** — the smallest generated object: a table row, Q&A set, tool trajectory, or resettable environment task.

## Four purposes cannot share one acceptance criterion

| Purpose | Primary question | Required independent evidence | Common misuse |
| --- | --- | --- | --- |
| Evaluation / stress testing | Does it cover target failure modes and score stably? | Expert cases, deterministic oracle, real-failure replay | Estimating online incidence from an artificially balanced stress set |
| Supervised training | Does adding it improve the real task? | Real holdout excluded from generation, ablations, and slice results | Training and accepting on the same synthetic set |
| Simulation / system test | Do environment state and side effects follow rules? | Resettable simulator, state invariants, independent trials | Checking only the final natural-language sentence |
| Privacy release | Does the claimed privacy property hold? | Threat model and attack evaluation; for DP, parameters, accounting, and implementation review | Calling “not a raw row” anonymous |

One candidate pool may support multiple purposes after different processing, but every release artifact needs its own split, version, weighting, and acceptance report. In particular, real calibration samples used for prompting or generation must not enter the final test again.

## Method

1. State one primary use: evaluation boundary, supervised training, simulation test, or controlled release. Validate multiple uses separately.
2. State the target population and the populations, tasks, languages, and time ranges it cannot represent.
3. Define minimum Schema: sample ID, family ID, synthetic flag, generation run/version, source declaration, and generation lineage.
4. List a condition matrix and minimum candidate count per cell; label core, stress, and prohibited conditions.
5. Define sample-level gates: parseable, complete fields, no prohibited content, verifiable label.
6. Define dataset-level gates: coverage, duplicate rate, slice quality, real-holdout utility, and risk review.
7. Freeze generation budget and stop rule. Record remaining gaps as gaps; do not silently relax a gate.
8. For every release scope, define source/authorization/privacy state, evidence reference, owner, and withdrawal-impact graph. An unknown or pending state is not overwritten by a `synthetic` label.

The contract also needs failure semantics. Is parsing failure a rejection, `Unknown`, or retry? May an unverifiable label enter a human queue? Can a critical privacy case be offset by aggregate quality? Does unknown source/authorization always `BLOCK`? Freeze these decisions before seeing results, otherwise a team will unconsciously tune rules to the current output.

## Example

A contract for read-only order-Agent evaluation:

```json
{
  "purpose": "offline stress evaluation",
  "population": "Chinese and English read-only order requests",
  "required_fields": [
    "id",
    "family_id",
    "language",
    "scenario",
    "input",
    "expected_action",
    "synthetic",
    "generator_version"
  ],
  "required_conditions": {
    "language": ["zh-CN", "en"],
    "scenario": ["status", "missing-id", "write-request"]
  },
  "hard_gates": ["schema-valid", "no-real-identifiers", "label-verifiable"],
  "release_scope": "offline-teaching-only",
  "source_declaration": "author-designed fictional templates; no external or real records",
  "non_goal": "estimate production traffic accuracy"
}
```

The `write-request` condition is deliberately oversampled as stress. Its fraction cannot infer the production distribution.

## Common mistakes and diagnosis

- **Purpose says “improve the model.”** Replace it with a concrete task, metric, real holdout, and decision threshold.
- **Only text fields are specified.** Add family, provenance, version, and risk fields.
- **A source declaration is treated as authorization.** Store input class, authorization/review evidence reference, release scope, and pending items separately; block release at the relevant scope if rights are unclear.
- **Synthetic evaluation set is treated as a population sample.** State core and stress weights.
- **No stop rule.** Define minimum coverage, marginal additions, and human-pass rate.
- **Label meaning is chosen after generation.** Write rubric and verifiable answer first, then generate.

## Exercises

1. Write purpose and non-goals separately for RAG citation evaluation and intent-classification training.
2. Design the minimum JSON Schema for a tool-call case.
3. Write a stop rule for a condition matrix that avoids setting sample count as the only objective.

## Self-check

1. Can one dataset be reused directly for training and testing? Do not assume so; it contaminates independent evaluation.
2. Does Schema validity mean the label is correct? No: structure checks cannot verify semantics.
3. After a synthetic stress set covers more extreme conditions, can its aggregate score be compared directly with a production-core set? No: the sampling purpose and weights differ.

## Summary and next step

Synthetic data starts by defining purpose and acceptance, not a generator. Next, build the most transparent reproducible baseline with [[data-synthesis/foundations-and-design/02-template-and-programmatic-generation|Template and Programmatic Generation]].

## References

- [Datasheets for Datasets original paper](https://arxiv.org/abs/1803.09010) — accessed 2026-07-22.
- [Google Data Cards official paper page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/) — accessed 2026-07-22.
- [NIST AI RMF Core: Map and Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — accessed 2026-07-22.
