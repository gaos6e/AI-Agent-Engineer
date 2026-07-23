---
title: "Continuous Evaluation, Provider Drift, and Governance"
tags:
  - llmops
  - continuous-evaluation
  - provider-drift
aliases:
  - LLM Continuous Evaluation
  - Provider Drift Governance
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: LLMOps/02-生产工程/08-持续评测、供应商漂移与治理.md
translation_source_hash: e29923a0c4dc78626fd35082bfe6f33b33fa2659a3628855927b15a9b9daca9c
translation_route: zh-CN/LLMOps/02-生产工程/08-持续评测、供应商漂移与治理
translation_default_route: zh-CN/LLMOps/02-生产工程/08-持续评测、供应商漂移与治理
---

# Continuous Evaluation, Provider Drift, and Governance

## Goal

Learn to turn production Traces, user feedback, and provider state into auditable evaluation evidence; recognize provider, API, behavioral, and pricing drift; and set clear boundaries for continue, investigate, pause, fallback, rollback, and human review.

## Why passing offline evaluation is not enough

An offline regression suite represents only distributions already collected and labeled. After deployment, new tasks, holiday peaks, delayed labels, tool-state changes, provider-capacity problems, and unseen attacks can appear. Deployment is therefore not the end of evaluation; it opens a new evidence window.

**Continuous evaluation** does not mean “ask another model to score every production request.” It is a repeated loop:

```text
Production requests and Traces
  → stratified sampling by risk and task
  → minimization, redaction, and authorized access
  → deterministic checks / human labels / calibrated automated scoring
  → comparison with fixed release, rubric, grader, and policy
  → continue, investigate, pause, fallback, rollback, or human review
  → reviewed failure samples enter the next regression-suite version
```

Changing any component in this chain can change the meaning of a score. Do not combine a grader upgrade and an application upgrade in one comparison, or you cannot tell whether the score changed because application behavior changed or because the ruler changed.

## Five common forms of drift

| Drift | Example | Evidence to examine first | Possible action |
| --- | --- | --- | --- |
| API or contract drift | Changed fields, error codes, SDK, or deprecation timeline | Contract tests, SDK lock file, official change notice | Block release; adapt and retest |
| Service drift | Changed error rate, throttling, time-to-first-token, or tail latency | Gateway Metrics, provider request ID, cross-release comparison | Pause expansion; use a prevalidated degradation path |
| Behavioral drift | Task or tool-selection distribution changes while the model name does not | Fixed regression suite, Trace trajectory, human review | Investigate, roll back, or reapprove |
| Economic drift | Changed price, cache charging, or retry amplification | Pricing-policy version, token/cache/retry ledger | Pause; redo the cost gate |
| Data and control-plane drift | Changed retention capability, data region, or policy configuration | Current contract, control-plane export, approval record | Stop sensitive traffic; governance review |

A drift score is only a clue; it cannot explain root cause by itself. For example, changed output length may come from the prompt, user distribution, model, or tool output. Examine it with manifest differences, a timeline, and controls.

## Bringing online signals into a decision

At minimum, bind each observation window to `release_id`; the full SHA-256 of the release manifest and candidate gate; the window; sample size; task/risk slices; Trace completeness; data-handling policy; quality and safety results; latency; cost; provider errors; and degradation-path state. Keep auditable numerators and denominators for quality, safety, and critical-slice results. A zero denominator means unknown, not zero failures; a rate without its count cannot verify coverage or aggregation. Use a short digest only for display. Only a full digest can be verified across a release gate, audit, and online window, and it belongs in a Trace or controlled log—not a Metric label.

One risk-priority decision order is:

1. **Privacy, unauthorized action, or clear safety failure:** stop expansion; roll back or disable functionality when necessary.
2. **Material regression in the task or a critical-risk slice:** roll back the complete manifest and preserve evidence.
3. **Provider error or behavioral drift:** fall back only if the alternate path was validated on the same task suite, tool contract, and data boundary, and the current candidate window has enough samples, label/critical-slice coverage, safety checks, and freshness to support automation. Otherwise require human review or pause expansion.
4. **Latency or cost outside policy:** pause expansion and decompose retries, queueing, output length, and caching first.
5. **Insufficient samples or labels not returned:** hold scope and investigate; never report “no failure found yet” as success.
6. **Every gate passes:** continue by the preregistered step and retain continuous observation.

Signals can conflict. Escalate actions by risk rather than a majority vote. For example, normal quality does not justify continuing after a redaction failure merely because five performance metrics look good.

## Feedback is not ground truth by default

Online feedback can be biased:

- Only very satisfied or very dissatisfied users may click feedback.
- A user whose task failed may leave without a label.
- “The user copied the answer” does not prove the answer was correct.
- Refund or human-takeover outcomes can arrive days later.
- Automated graders can be affected by prompt injection, writing style, and length.
- Human annotators may interpret a rubric differently.

Record label source and delay; report coverage by task and risk slice; calibrate automated graders against expert samples; and measure annotator agreement regularly. Production samples first enter controlled human triage, then may enter the next regression-suite version only after deduplication, redaction, permission, leakage checks, and minimal reproduction. Do not automatically turn every log or alert into training data or a frozen test.

## Why a provider failure does not justify switching models at will

An alternative model may be “more capable” yet still:

- fail to support the same structured-output or tool-calling contract;
- use different refusal or formatting behavior with the same prompt;
- reside in a disallowed data region or have different retention terms;
- count tokens differently or impose different context, caching, and cost rules;
- have failed critical-risk-slice or side-effect-tool tests.

Maintain a **fallback manifest** beforehand: a fixed alternative provider/model, prompt adaptation, tool schema, data boundary, task regression suite, cost gate, and approver. Runtime may switch only to that validated unit. With no safe alternative, clearly degrading to read-only mode, retrieval-result display, or a human workflow is usually safer than “temporarily choosing another model.”

## Minimum record for evaluation governance

Retain at least the following for every continuous evaluation:

- release, dataset, rubric, grader, code, and policy versions;
- sample-selection rule, coverage, exclusions, and data-handling basis;
- automated and human scores plus calibration/agreement evidence;
- sample-level failure categories, critical slices, and uncertainty;
- decision, rationale, approver, time, and evidence digest;
- traffic action taken, rollback/fallback target, and review time.

Human approval is not an exemption button. The approver must see the fixed manifest and evidence, and the system must record what was approved—not merely a person's name.

Distinguish evidence fingerprints clearly: a full SHA-256 binds data across systems, while a short prefix is only human-readable. A hash proves that bound content did not change; it does not prove the content is true, its source is trusted, access was authorized, or approval occurred.

## Current tools and version cautions

As of 2026-07-22, OpenAI's Evaluation best practices emphasize task-specific evaluation, real distributions, continuous evaluation, and using human feedback to calibrate automated scoring. The documentation also marks the older Evals platform as deprecated, planned to become read-only on 2026-10-31 and shut down on 2026-11-30; the Graders documentation describes related workflows as deprecated as well. These dates are a provider's current announcement, not permanent facts: recheck the official deprecation page when migrating.

Current MLflow documentation distinguishes classic-ML `mlflow.models.evaluate()` / `EvaluationMetric` from GenAI `mlflow.genai.evaluate()` / `Scorer`; the two object families are not interoperable. Automated Trace evaluation currently supports only an LLM judge, normally runs through sampling or asynchronous jobs, and does not automatically reevaluate all historical records. It cannot replace deterministic checks, human checks, or controlled updates to a frozen regression suite. OpenTelemetry's GenAI semantic conventions moved to a separate official repository. They can unify Trace fields, but compatibility still needs a pinned actual revision/schema URL, contract tests, and a migration record. Do not silently bind an observability-standard upgrade to an application release.

## Hands-on practice

Use `online_observations.json` from [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|Offline Release Gate Project and Self-Check]]:

1. Run the healthy, insufficient-sample, provider-drift, quality-regression, and cost-degradation observations.
2. Explain why the script produces different actions.
3. Change `fallback_evidence` in the provider-drift case to `null` and verify that the result moves from `FALLBACK` to `HUMAN_REVIEW`; then tamper with one digest and verify that incorrect binding is rejected as a contract error.
4. Add an observation with normal quality but a failed redaction check and verify that privacy failure takes priority.
5. For every action, write its executor, evidence-preservation step, and review time.

## Self-check

1. Why is continuous evaluation not the same as model scoring for every online output?
2. Why cannot you compare a new grader's score directly with an old score?
3. If the model name is unchanged, what evidence can still support a claim of behavioral drift?
4. Which conditions must hold before an automatic provider switch is allowed?
5. Why should insufficient samples lead to `investigate` rather than `continue`?

## Mastery checklist

- [ ] I can distinguish API, service, behavioral, economic, and data/control-plane drift.
- [ ] I can list version, sample, quality, safety, performance, and data-boundary evidence for one observation window.
- [ ] I can explain feedback-selection bias, label delay, and grader drift.
- [ ] I can design a validated fallback manifest and a functional degradation when no fallback exists.
- [ ] I can write a continuous-evaluation conclusion as an auditable action rather than a dashboard score alone.

## Summary and next step

The value of continuous evaluation is not continually generating more scores. It controls online change with fixed evidence and risk priority. If user impact or uncontrollable drift appears, move into [[llmops/production-engineering/07-incident-response-and-continuous-improvement|Incident Response and Continuous Improvement]].

## References

The following dynamic sources were checked on 2026-07-22:

- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [OpenAI Graders](https://developers.openai.com/api/docs/guides/graders)
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)
- [OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)
- [MLflow for GenAI applications](https://mlflow.org/docs/latest/genai/overview/)
- [MLflow evaluating production traces](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)
- [MLflow Evaluation APIs](https://mlflow.org/docs/latest/ml/evaluation/)
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)
- [NIST AI 600-1: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
