---
title: "Evaluation Reporting, Audit, and Governance"
aliases:
  - Evaluation Reporting and Governance
tags:
  - evaluation
  - audit
  - ai-governance
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "OpenAI, MLflow, NIST, and IETF materials through 2026-07-22;
  the OpenAI Evals deprecation schedule and third-party-evaluation validity
  guidance were verified"
lang: en
translation_key: 评测体系/02-方法与质量/07-报告审计与治理.md
translation_source_hash: 97ef55998520dfc1b9f841dbd966706a9af3691d4f9960b98c3f6c2c11f67274
translation_route: zh-CN/评测体系/02-方法与质量/07-报告审计与治理
translation_default_route: zh-CN/评测体系/02-方法与质量/07-报告审计与治理
---

# Evaluation Reporting, Audit, and Governance

## Goal

Raise an evaluation from “there is a score in a terminal” to release evidence that can be reviewed, approved, held accountable, and reconsidered when it expires. Correctly handle constraints on quality, safety, fairness, cost, and latency that cannot simply be averaged together.

## What decision an evaluation report must support

Start a report with the **decision question**, such as “May `candidate-2026-07-14` enter a 5% progressive rollout?”, rather than a polished chart. A minimum report answers:

1. What was tested: the complete version of model, prompt, retrieval, tools, policy, harness, and budget.
2. What data was used: dataset version, source, split, coverage, deduplication, and freeze date.
3. How it was graded: grader and rubric versions, human calibration, unknowns, and failure priorities.
4. What evidence resulted: overall results, slices, sample counts, intervals, failure types, and representative cases.
5. What conclusion is supported: PASS, REVIEW, or BLOCK, and the scope to which it applies.
6. Who approved it, when exceptions expire, and how deployment will stop or roll back afterward.

A single average cannot answer these questions by itself. Raw per-case results, configuration, and change differences must be traceable. When evidence contains personal or sensitive content, retain authorized, minimized, de-identified evidence rather than placing full production prompts in the report.

## Multi-dimensional gates and priority

| Dimension | Typical evidence | Common gate | What it does not prove |
| --- | --- | --- | --- |
| Task quality | Success rate, precision/recall/F1, human rubric | Minimum overall and critical-slice thresholds | Does not automatically prove safety |
| Safety / privacy | Prohibited actions, disclosure, unauthorized access, and coverage | Severe singleton or critical-slice hard BLOCK | “Zero observed” does not mean detection is complete |
| Fairness / group impact | Business- or rights-relevant group slices and error differences | Risk review, gap investigation, regulatory process | A small-sample gap is not causal proof of discrimination |
| Cost | Per request, per successful task, worst-path estimate | REVIEW or budget cap | An estimate is not an invoice |
| Latency / reliability | Mean, p95, timeout, repeated trials | SLO-compatible threshold or progressive-rollout guardrail | Offline latency is not production latency |

State priority before seeing results. For example: `critical safety failure > critical-slice failure > overall quality > cost/latency optimization`. Otherwise a quality-average improvement can “offset” an unauthorized action during aggregation. Hard thresholds protect non-exchangeable risks. Soft thresholds enter human REVIEW and need a named owner, additional evidence, and a due date.

“Fairness” is not an automatic conclusion after calculating one difference per slice. Slice choice, potential harm, sample representativeness, statistical uncertainty, and lawful treatment of sensitive attributes require joint definition by domain specialists, affected parties, privacy/compliance, and engineering. This course's project demonstrates slice gaps only as signals for investigation.

## Failure classification and root-cause evidence

Classify the **symptom** before validating root cause:

- Data problem: incorrect answer, split leakage, stale document, or conflicting label.
- Grader problem: ambiguous rubric, program bug, judge bias, or reward loophole.
- Harness problem: missing tool, unequal budget, residual sandbox state, or dependency failure.
- System problem: retrieval, generation, tool selection or parameter, policy, or final-state failure.
- Statistical problem: too few samples, selection bias, correlated trials, or multiple comparisons.
- Reporting problem: unmarked metric-definition change, only a mean reported, or hidden unknowns and failures.

A trace can show “where it happened,” environment state can prove “what finally happened,” and a configuration diff can show “what changed.” Together they form a root-cause hypothesis. Correlated timing is not causal proof; after a fix, add a minimal regression case and retest under the same contract.

## Validity checks for a conclusion

A high score supports a conclusion only when the claim, harness, and validity checks all hold. Before aggregation, audit whether the task or grader is broken, the system exploits a reward loophole, a safe refusal is miscounted as failure, test content was discovered through training, prompting, retrieval, or browsing, submitters repeatedly adapted to hidden tests, or the system changes behavior after recognizing an evaluation environment (evaluation awareness or sandbagging risk). A black-box run may not prove or disprove every risk; retain unknowns as unknown.

Count confirmed, suspected, and indeterminate cases separately. Publish detection method, coverage, and error bounds. If a case is excluded or rescored, retain original and adjusted results plus the rationale. Do not silently delete “bad questions” to raise a score or turn “no contamination detected” into “there was no contamination.”

## Reproducibility and audit checklist

For every release-significant run, freeze or record at least:

- version or content digest of the suite, dataset, rubric, grader, and human-labeling guide;
- baseline and candidate model snapshot, prompt, code, tools, retrieval index, and policy versions;
- harness, timeouts, retries, turn and token budgets, concurrency, random seed, and environment dependencies;
- per-case results, failure evidence, excluded samples, unknowns, runtime, full SHA-256 evidence digest, digest algorithm/byte representation/version, and a display-only short fingerprint for terminal or dashboard comparison;
- runner, reviewers, approvers, conflicts of interest, exception rationale, and expiration;
- data authorization, access control, retention period, deletion process, and whether samples are synthetic or production-derived.

A full SHA-256 digest can detect a change to the bound inputs only when the receiver reuses the same algorithm, version, and input-byte representation. A short fingerprint is convenient for people but cannot be the only binding key across releases, production windows, or approval systems. If JSON is hashed or signed across languages, explicitly exchange raw bytes or adopt and test a normalization scheme; do not describe one language's “sorted keys” as universal canonical JSON. Neither digest replaces signatures, access control, or source authenticity. If a grader, dataset, or harness version changes, establish a new comparison boundary rather than directly joining old and new curves as “continuous improvement.”

## Governance boundaries for offline evaluation, continuous evaluation, and monitoring

- **Offline and continuous evaluation** in this course repeats versioned cases under a contract for development, regression, and release gates.
- [[runtime-monitoring/00-index|Runtime Monitoring]] continuously observes real traffic, telemetry, SLOs, and incidents. Its output is a candidate for human triage, not an automatic addition to an evaluation set.
- [[benchmark-design/00-index|Benchmark Design]] fixes longer-term comparison protocols, task distributions, reporting rules, and maintenance practices so results across systems remain comparable.

The same scorer can be used offline and online, but online data includes sampling, label delay, privacy, and distribution shift. A monitoring curve cannot be treated as a frozen-test result. Production failures first need a controlled evidence reference, human triage, de-identification, deduplication, authorization, and minimal reproduction before the evaluation owner accepts them as cases in a new regression-dataset version. See [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]]. The whole process must also keep test answers out of development prompts and training data.

## Tool facts and version boundaries

As of 2026-07-22, OpenAI's official deprecations page records that the Evals platform was announced as deprecated on 2026-06-03, existing evals become read-only on 2026-10-31, and the Evals dashboard and API are planned to close on 2026-11-30. Its Graders page also states that graders are in a deprecation transition with the eval/fine-tuning workflow. This course therefore uses evaluation best practices and trace grading only as methodological references and **does not teach creating new Evals API resources or copying configurations about to become invalid**.

MLflow documentation labeled `latest` at the time of verification distinguishes classic ML's `mlflow.models.evaluate()` and `EvaluationMetric` from GenAI's `mlflow.genai.evaluate()` and `Scorer`; the two APIs are non-interoperable, and old `mlflow.evaluate` was deprecated in MLflow 3. Trace-based automatic evaluation is a third capability: it currently supports LLM judges only, not code-based scorers; creation or enabling of a judge can look back no more than one hour of traces or sessions, and **updating judge configuration alone does not reevaluate traces already evaluated**. These are product facts, not general evaluation theory. Pin the actual MLflow package, read that version's documentation, and run migration tests when adopting it. The offline project in this course does not depend on MLflow.

## Exercises

1. Write a one-page decision report for allowing a customer-service Agent candidate into a 5% progressive rollout: include hard gates, soft gates, approver, exception expiry, and an online stop condition.
2. Scenario: overall F1 rises from 0.82 to 0.87, but recall on a high-risk Chinese slice falls from 0.76 to 0.52 with only 20 samples. Separately state what is confirmed, what is not confirmed, the decision, and extra evidence needed.
3. Complete an old report that contains only a total score with data, grader, harness, interval, failure classification, privacy, and version fields.

## Self-check and mastery check

- [ ] I can explain why a safety or privacy hard failure cannot be offset by a quality average.
- [ ] I can distinguish a slice gap, statistical evidence, and a causal fairness conclusion.
- [ ] I can organize root-cause evidence from a case, trace, outcome, and configuration diff.
- [ ] I can list version, environment, and approval records needed to reproduce an evaluation.
- [ ] I can state the boundary among evaluation framework, Benchmark Design, and Runtime Monitoring.
- [ ] I can identify deprecated platform entry points and retain methods without copying an API about to expire.

## Summary and next step

Evaluation becomes a reliable engineering gate only when it enters versioning, approval, exception, rollback, and continuous-maintenance workflows. Read [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]], then complete [[evaluation-framework/project-and-self-check/08-offline-layered-evaluation-pipeline|the Offline Layered Evaluation Pipeline]] to verify why a critical safety case outranks an overall mean.

## References

- [OpenAI API Deprecations](https://developers.openai.com/api/docs/deprecations) — checked 2026-07-22; Evals announced deprecated on 2026-06-03, read-only on 2026-10-31, planned closure on 2026-11-30.
- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-22; methodological reference while the legacy Evals platform is in transition.
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading) — checked 2026-07-22; methodological reference, not a new Evals API tutorial.
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) — published 2026-05-29; claims, harnesses, validity checks, and reporting requirements.
- [MLflow GenAI Evaluation and Monitoring](https://mlflow.org/docs/latest/genai/eval-monitor/index.html) — documentation labeled `latest`, checked 2026-07-22, not a pinned package version.
- [MLflow Automatic Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/) — documentation labeled `latest`, checked 2026-07-22.
- [MLflow Evaluation APIs](https://mlflow.org/docs/latest/ml/evaluation/) — classic-ML and GenAI evaluation paths and old-API migration boundary, checked 2026-07-22.
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — checked 2026-07-22.
- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1) — 2024-07; checked 2026-07-22.
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html) — JSON byte-representation boundary for cross-system hashing and signing; informational RFC whose implementation still needs verification.
