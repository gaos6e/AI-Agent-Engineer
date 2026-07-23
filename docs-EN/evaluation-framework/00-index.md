---
title: "Evaluation Framework Learning Path"
aliases:
  - AI Evaluation
  - LLM and Agent Evaluation
tags:
  - ai-agent-engineer
  - evaluation
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "NIST, OpenAI, Anthropic, Google, MLflow, OpenTelemetry, IETF
  materials, and original evaluation papers through 2026-07-22; the OpenAI Evals
  retirement schedule was verified"
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 39
ai_learning_schema: 2
ai_learning_id: evaluation
ai_learning_domain: evaluation-reliability
ai_learning_catalog_order: 3900
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 1000
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 1300
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 1000
ai_learning_track_agent_platform_kind: core
ai_learning_track_multimodal_realtime_order: 800
ai_learning_track_multimodal_realtime_kind: core
lang: en
translation_key: 评测体系/00-目录.md
translation_source_hash: f792f40bb4390d58e5e305c6947b4582278e0388642a2019494795b5c9f3433a
translation_route: zh-CN/评测体系/00-目录
translation_default_route: zh-CN/评测体系/00-目录
---

# Evaluation Framework

## Course overview

Evaluation is not “running a model and getting a score.” It turns a product objective into repeatable tasks, data, grading, and decision evidence. Starting with an evaluation claim and its basic units, this course builds datasets; deterministic, human, model, and trace grading; layered RAG and Agent evaluation; statistical uncertainty; multi-dimensional release gates; and audit-and-governance workflows.

> [!info] Fact boundary
> Vendor evaluation APIs, grader types, and product interfaces change. This course extracts official methodology only. Sources were checked on 2026-07-22; the code project is entirely offline, uses no vendor API, and does not use marketing leaderboard figures. OpenAI announced the deprecation of its Evals platform on 2026-06-03. As of this page's verification date, its stated plan is for existing evals to become read-only on 2026-10-31 and for the dashboard and API to close on 2026-11-30; those future dates must be rechecked when they arrive. This course does not teach that legacy entry point. MLflow links point to the documentation labeled `latest` when checked and do not represent a pinned package version; its classic-ML and GenAI evaluation APIs have different objects, metrics, and migration boundaries and must not be mixed.

## Where this course fits

This course belongs to the “Production, Evaluation, and Governance” stage. Understand [[probability-and-statistics/00-index|Probability and Statistics]], [[rag/00-index|RAG]], and [[agent-core/00-index|Agent Core]] first, then turn quality objectives into release gates and regression evidence. For long-lived designs of public comparison tasks, continue to [[benchmark-design/00-index|Benchmark Design]].

## Learning objectives

- State the claim, decision, object, and success criteria that an evaluation must support.
- Build traceable datasets containing typical, boundary, failure, and adversarial scenarios.
- Combine deterministic assertions, rules, human review, model grading, and trace grading, while stating each method's boundary.
- Interpret confusion matrices, precision/recall/F1, means, percentiles, and confidence intervals, distinguishing task-population estimates from trial variation.
- Evaluate retrieval, generation, tool selection, parameters, traces, and final environment state separately.
- Correctly distinguish offline evaluation from online experiments, reporting sample size, variation, and intervals.
- Turn production failures into regression cases and control changes with versioned gates for safety, fairness, cost, latency, and quality.
- Produce auditable reports that record data, graders, harnesses, approvals, exceptions, and evidence boundaries.

## Prerequisites

- Intuition for means, proportions, sampling, variance, and confidence intervals.
- Ability to read JSON and run Python 3 standard-library scripts in PowerShell 7.
- Familiarity with RAG's retrieval-to-generation structure and an Agent's tool-calling loop.
- No specific evaluation platform is required; first learn transferable evaluation contracts.

## Recommended sequence

1. [[evaluation-framework/foundations-and-design/01-evaluation-objectives-and-basic-units|Evaluation Objectives and Basic Units]] — work backward from the decision an evaluation must support.
2. [[evaluation-framework/foundations-and-design/02-cases-datasets-and-stratification|Cases, Datasets, and Stratification]] — construct data that represents real use while retaining difficult tails.
3. [[evaluation-framework/methods-and-quality/03-deterministic-assertions-metrics-and-scoring-rules|Deterministic Assertions, Metrics, and Scoring Rules]] — let machines verify objectively decidable conditions first.
4. [[evaluation-framework/methods-and-quality/04-human-review-and-model-based-evaluation|Human Review and Model-Based Evaluation]] — define judge calibration, bias, and the human-reserved boundary.
5. [[evaluation-framework/methods-and-quality/05-layered-rag-generation-and-agent-evaluation|Layered RAG, Generation, and Agent Evaluation]] — locate the layer at which a system failed.
6. [[evaluation-framework/methods-and-quality/06-offline-online-statistics-and-regression|Offline, Online, Statistics, and Regression]] — move from a one-off score to reliable decisions.
7. [[evaluation-framework/methods-and-quality/07-evaluation-reporting-audit-and-governance|Evaluation Reporting, Audit, and Governance]] — turn multi-dimensional evidence into prioritized, reviewable release decisions.
8. [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]] — connect frozen evaluation, release gates, telemetry, and human triage in a one-way, auditable evidence chain.
9. [[evaluation-framework/project-and-self-check/08-offline-layered-evaluation-pipeline|Project: Offline Layered Evaluation Pipeline]] — run strict contracts, deterministic graders, slice gates, paired bootstrap, and a complete evidence summary.

## Hands-on entry points

- Main project: [[evaluation-framework/project-and-self-check/08-offline-layered-evaluation-pipeline|Offline Layered Evaluation Pipeline]]. Using only the Python 3 standard library, it validates strict dataset/rubric/prediction JSON contracts, split leakage, confusion matrices, slice gates, fixed-seed bootstrap, complete SHA-256 evidence summaries, display-only short fingerprints, and CLI exit codes. Observation fields in its fixtures are only offline teaching inputs; they do not constitute candidate self-attestation or real environment results.
- RAG layered practice: [[rag/08-project-offline-cited-qa|Offline Citable Question Answering]] produces a versioned evaluation artifact with retrieval/context/citation fact recall, status accuracy, critical slices, and non-disclosure gates. It does not mistake a self-reported Boolean such as `evidence_present=true` for complete RAG evidence.
- Reporting practice: use the [[data-visualization/07-project-agent-evaluation-dashboard#generated-result|generated Agent evaluation dashboard]] to inspect multi-trial proportion intervals, tail latency, routing confusion, and the cost-success tradeoff. Keep charts, fixtures, generator scripts, exact-dimension tests, and textual alternatives together.
- Practical task: derive input, expected environment state, critical assertions, and failure severity from one real failure log.
- Review exercise: have two reviewers blind-score the same output set, analyze disagreement first, and only then decide whether to introduce a model grader.

## Mastery checklist

- [ ] I can distinguish a task, trial, grader, assertion, trace, outcome, harness, and suite.
- [ ] I can explain what claim a total score supports and what it cannot support.
- [ ] I can document dataset source, stratification, version, privacy treatment, and freezing policy.
- [ ] I can prefer deterministic checks and write anchored rubrics for subjective dimensions.
- [ ] I can calibrate graders against a human gold standard and report agreement, disagreement, position/length/adversarial sensitivity, and adjudication.
- [ ] I can diagnose retrieval, answer, tool parameter, and final-state failures separately rather than looking only at terminal text.
- [ ] I can calculate and interpret a confusion matrix, precision, recall, F1, p95, and a confidence interval correctly.
- [ ] I can make safety and critical-slice BLOCK outcomes take precedence over an overall mean and report fairness, cost, and latency limits.
- [ ] I can report paired differences and uncertainty, add failure cases to regression candidates after human triage, and retain full audit evidence.

## Relationships to other courses

- [[benchmark-design/00-index|Benchmark Design]] fixes long-term comparison protocols, task distributions, and reporting rules; this course first solves the claims, graders, data, and release gates for a particular product.
- [[data-synthesis/00-index|Data Synthesis]] can supplement rare cases, but synthetic samples must be labeled separately and their value validated against real data.
- [[runtime-monitoring/00-index|Runtime Monitoring]] continuously observes production telemetry, SLOs, and incidents. This course only turns candidates that have been human-triaged, de-identified, deduplicated, and confirmed reproducible into repeatable cases; it never writes monitoring curves or alerts directly into a frozen test set.
- [[llmops/00-index|LLMOps]] integrates evaluation gates into versioning, release, and rollback workflows.

## Primary references

All sources below are official materials, standards, or original papers and were retrieved or checked on 2026-07-21:

- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [OpenAI API Deprecations](https://developers.openai.com/api/docs/deprecations) — Evals-platform retirement timeline.
- [OpenAI Graders](https://developers.openai.com/api/docs/guides/graders) — the page explicitly sits in a deprecation transition and is used only as a methodological reference.
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Google Cloud: Evaluate a judge model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluate-judge-model)
- [MLflow GenAI Evaluation and Monitoring](https://mlflow.org/docs/latest/genai/eval-monitor/index.html) — documentation labeled `latest`; pin the actual package version when adopting it.
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html) — cross-system JSON hashing or signing needs an explicit byte representation; this course's examples do not claim to implement this standard.
- [Original RAGAS paper](https://aclanthology.org/2024.eacl-demo.16/)
- [NIST/SEMATECH: Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm)
