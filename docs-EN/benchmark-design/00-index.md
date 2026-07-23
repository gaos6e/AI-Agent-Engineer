---
title: "Benchmark Design Learning Path"
aliases:
  - AI Benchmark Design
  - Benchmark Design
tags:
  - ai-agent-engineer
  - benchmark
  - learning-path
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: "NIST, MLPerf, and HELM official materials plus original
  Benchmark papers through 2026-07-21; HELM maintenance-mode status was
  verified"
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 42
ai_learning_schema: 2
ai_learning_id: benchmark-design
ai_learning_domain: evaluation-reliability
ai_learning_catalog_order: 4200
ai_learning_hard_prerequisites:
  - evaluation
ai_learning_track_agent_platform_order: 1100
ai_learning_track_agent_platform_kind: core
lang: en
translation_key: Benchmark设计/00-目录.md
translation_source_hash: 2cfc5e43c444c3cb662939e3774961e74c218299dc0eabf128b3a9c3482c756e
translation_route: zh-CN/Benchmark设计/00-目录
translation_default_route: zh-CN/Benchmark设计/00-目录
---

# Benchmark Design

## Course overview

A Benchmark is a versioned, repeatable evaluation contract used for comparison. It is not “a set of questions plus an average.” It must also define the claim it supports, target population and task space, data sources and splits, run protocol, baselines, metrics, statistical reporting, submission rules, and maintenance ownership.

This course is for engineers designing a team Benchmark for the first time. The intended deliverable is not a polished leaderboard, but an evidence system that can answer: “Who performs better, under which conditions, on which tasks, and at what cost?”

> [!info] Fact and version boundary
> Public leaderboards, models, and platforms change continuously. This course does not record rankings or performance figures that expire quickly; methods and sources were checked on 2026-07-21. MLPerf rules use the current content of the official repository at that check date as an example; actual submissions must verify the then-current rules. Stanford CRFM's official repository states that HELM entered maintenance mode on 2026-06-01. This course continues to cite the original HELM paper for methodology, but does not describe the framework as a default tool actively receiving new functionality.

## Where this course fits

This course belongs to the “Production, Evaluation, and Governance” stage. Complete [[evaluation-framework/00-index|Evaluation Framework]] first to learn cases, graders, and regression, then learn to freeze them into a fair, reproducible, maintainable Benchmark for long-term comparison. [[data-synthesis/00-index|Data Synthesis]] can provide synthetic stress samples, but must not replace evidence about the real distribution.

## Learning objectives

- Write a Benchmark claim, scope, and explicit non-goals from the decision it must support.
- Check representativeness with task spaces, stratification matrices, and gap tables rather than question count.
- Design group-level splits, frozen test sets, and a contamination register; distinguish training contamination, runtime discoverability, development adaptation, and maintenance-chain leakage.
- Freeze baselines, prompts, decoding, tools, budgets, and environment so comparison conditions are equivalent.
- For Agent tasks, freeze initial/final state, side effects, reset, timeout, retry, and multi-trial rules.
- Report primary metrics, risk thresholds, stratified results, resource cost, and statistical uncertainty together.
- Recognize leaderboard gaming, repeated tuning, and Benchmark saturation, and maintain evidence boundaries through report cards, version changes, and retirement.

## Prerequisites

- Ability to read JSON and run Python 3 standard-library scripts in PowerShell 7.
- Basic intuition for accuracy, means, proportions, sampling, and confidence intervals.
- Understanding of task, trial, grader, outcome, and suite from [[evaluation-framework/00-index|Evaluation Framework]].
- Neither model training nor a real API is required.

## Recommended sequence

1. [[benchmark-design/foundations-and-design/01-from-claim-to-benchmark-contract|From Claim to a Benchmark Contract]] — decide what decision a score must support.
2. [[benchmark-design/foundations-and-design/02-task-space-representativeness-and-stratification|Task Space, Representativeness, and Stratification]] — expand real use into a coverage matrix.
3. [[benchmark-design/foundations-and-design/03-data-splits-leakage-and-contamination|Data Splits, Leakage, and Contamination]] — protect independent evidence and document contamination risk.
4. [[benchmark-design/methods-and-quality/04-baselines-metrics-and-comparable-runs|Baselines, Metrics, and Comparable Runs]] — freeze system boundaries and the run protocol.
5. [[benchmark-design/methods-and-quality/05-reproducibility-statistics-and-results-reporting|Reproducibility, Statistics, and Results Reporting]] — report uncertainty, per-item results, and reproducibility materials.
6. [[benchmark-design/methods-and-quality/06-leaderboard-mechanics-anti-gaming-and-maintenance|Leaderboard Mechanics, Anti-Gaming, and Maintenance]] — limit speculation with submission policy, private testing, and version governance.
7. [[benchmark-design/methods-and-quality/07-agent-environment-state-and-repeated-runs|Agent Environments, State, and Repeated Runs]] — freeze tools, initial/final state, side effects, reset, and multi-trial protocol.
8. [[benchmark-design/project-and-self-check/08-build-a-maintainable-benchmark|Project: Build a Maintainable Benchmark]] — run strict JSON, protocol comparability, critical-task gates, and paired intervals.

## Hands-on entry points

- Main project: [[benchmark-design/project-and-self-check/08-build-a-maintainable-benchmark|Build a Maintainable Benchmark]]. The fully offline project demonstrates PASS, a critical-task BLOCK, INCOMPARABLE protocol, and data-contract error separately.
- Design exercise: choose one real Agent task and write a one-page Benchmark card with its claim, non-goals, task space, risk thresholds, and update conditions.
- Audit exercise: take a public leaderboard and list at least five questions that rank alone cannot answer.

## Mastery checklist

- [ ] I can distinguish an evaluation suite, Benchmark, competition, and leaderboard.
- [ ] I can state the target population, task distribution, critical strata, and coverage gaps.
- [ ] I can create group-level splits based on a generating unit such as user, document, template, or time.
- [ ] I can explain why public tests become contaminated, distinguish `not-detected` from `unknown`, and state why contamination detection provides only risk evidence.
- [ ] I can freeze equivalent protocols for all systems and report quality, risk, cost, and latency together.
- [ ] I can define environment, tools, initial/final state, side effects, reset, budget, and multiple trials for an Agent case.
- [ ] I can produce a result package with a version fingerprint, sample count, per-item results, intervals, and limitations.
- [ ] I can design rules for submission rate, private tests, audit, report cards, retirement, and migration to a new version.

## Relationships to other courses

- [[evaluation-framework/00-index|Evaluation Framework]] provides cases, graders, human review, and regression methods; this course owns the fair comparison contract across versions or systems.
- [[probability-and-statistics/00-index|Probability and Statistics]] supplies foundations for intervals, sampling, and hypothesis testing.
- [[data-synthesis/00-index|Data Synthesis]] can fill combinatorial conditions and rare risks, but must retain a synthetic label and be calibrated against real holdouts.
- [[ai-governance/00-index|AI Governance]] determines who approves scope, metrics, public disclosure, and high-risk conclusions.
- [[runtime-monitoring/00-index|Runtime Monitoring]] provides distribution drift and failure samples that trigger a Benchmark update rather than indefinite static reuse.

Keep the boundary clear: [[evaluation-framework/00-index|Evaluation Framework]] mainly supports development, release, or regression decisions for one concrete product. Benchmark Design fixes a longer-lived comparison protocol across systems. [[runtime-monitoring/00-index|Runtime Monitoring]] observes actual production traffic, SLOs, and incidents. They can feed data back to one another, but a production monitoring curve must not be presented as a frozen-Benchmark result.

## Primary references

All sources below are official materials, standards, or original papers, retrieved or checked on 2026-07-21:

- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
- [HELM official repository](https://github.com/stanford-crfm/helm) — states that it entered maintenance mode on 2026-06-01.
- [Holistic Evaluation of Language Models](https://openreview.net/forum?id=iO4LZibEqW) — original paper.
- [BetterBench](https://openreview.net/forum?id=hcOq2buakM) — original paper.
- [The Benchmark Lottery](https://arxiv.org/abs/2107.07002) — original paper.
- [MLPerf Inference official rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc)
- [MLPerf general submission and results policies](https://github.com/mlcommons/policies)
- [Datasheets for Datasets](https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/) — original paper page.
- [Model Cards for Model Reporting](https://research.google/pubs/model-cards-for-model-reporting/) — original paper page.
- [OSWorld](https://arxiv.org/abs/2404.07972) — original paper.
