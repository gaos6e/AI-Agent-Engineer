---
title: "Task-Level Multi-Trial Evaluation"
tags:
  - llm
  - evaluation
  - trials
aliases:
  - Model-candidate evaluation protocol
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/06-任务级多Trial评测.md
translation_source_hash: 4850909ba312af09f011c0725f4fb77d13e3c550e6211ebe618f85724f43ed51
translation_route: zh-CN/现代LLM能力与模型选择/06-任务级多Trial评测
translation_default_route: zh-CN/现代LLM能力与模型选择/06-任务级多Trial评测
---

# Task-Level Multi-Trial Evaluation

## Goal

Use the same task distribution, harness, and repeated runs to obtain comparable evidence, rather than treating one stochastic output as a model property.

## Core concepts

- `task`: the work to complete and its success standard;
- `case`: one frozen input, initial environment state, and expected evidence;
- `trial`: one independent candidate run on one case, with a globally unique `trial_id`. The same `case_id` may, and usually should, be repeated;
- `trace`: the model, tools, retries, usage, latency, and state changes;
- `outcome`: the result decided by an external grader or final environment state.

LLM services and Agent traces can be stochastic or subject to runtime variation. The aim of multiple trials is not to pretend all uncertainty has been removed, but to expose success rate, tail failures, and variance.

## Why this matters

A candidate can succeed twice and fail once on the same case; showing only its best output overstates it. A single average latency also conceals the tail. HELM’s standardization principle requires consistent scenarios and adaptation strategies across candidates. Private evaluation must additionally fix the provider adapter, prompt, tools, temperature, budget, and retries.

## How to implement it

### Frozen protocol

Record the dataset version and slices; requested model ID/alias; model/version actually returned in the response when the API provides it; endpoint/region; prompt/tool schema; sampling parameters; maximum tokens/steps; cache; concurrency; retries; grader; and code commit. Do not treat `latest`, a preview, or a convenience alias as an inherently fixed experiment unit. When the model lifecycle, version resolution, service region, or runtime control plane changes, create a new evaluation version and compare the regression.

### Run design

1. Warm up every candidate first; do not mix initialization into formal latency.
2. Randomize candidate execution order to reduce time-of-day bias.
3. Run every candidate on every case the preregistered number of times, distinguishing repeated runs with `trial_id`. `min_trials_per_case` cannot be replaced by a total count across different cases.
4. Retain timeouts, refusals, and parsing failures; do not drop “outliers.”
5. Report overall and critical slices separately, including p50/p95, usage, and unit task cost.

> [!warning] Small-sample quantile boundary
> The project uses nearest-rank p95 only to demonstrate deterministic aggregation. With only six teaching trials per candidate, p95 is actually the sample maximum. It describes only this set of recorded runs and cannot prove stable tail latency, an SLA, or statistical uncertainty. A production evaluation should preregister an adequate sample size and combine appropriate current-decision methods such as time windows, load stratification, confidence intervals, or bootstrap.

Prefer deterministic assertions. For subjective dimensions, use anchored rubrics and calibrate the grader against a human gold standard. For high-risk decisions, do not make an uncalibrated model judge the sole gate.

## Common failures

- Using different prompts, tools, or retries across candidates but attributing the difference to the model.
- Running once or showing only successful samples.
- Reporting only averages, not failure categories, slices, and tail latency.
- Changing cases, thresholds, or weights after seeing results without creating a new evaluation version.
- Leaking the test set into prompt optimization or manual selection.

## How to validate

Check that every result can be traced along `decision → candidate → case_id → trial_id → trace → grader → outcome`. Rerun a fixed small sample: if the variation exceeds the release threshold, add trials, isolate infrastructure variation, or investigate the model/service version.

## Practice task

For two candidates and 12 cases, run at least three trials each. Classify outcomes as success, schema, tool, timeout, or refusal; report overall and high-risk-slice success rates, p95 latency, and average cost. Do not manually remove failed trials.

## References

- [HELM](https://crfm.stanford.edu/helm/index.html)
- Liang et al., [Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- [Gemini API model version naming](https://ai.google.dev/gemini-api/docs/models)
- [Claude model IDs and versions](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- [[evaluation-framework/00-index|This knowledge base: Evaluation Systems]]
