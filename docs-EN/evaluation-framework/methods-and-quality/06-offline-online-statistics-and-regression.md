---
title: "Offline, Online, Statistics, and Regression"
aliases:
  - Offline Online Evaluation and Regression
tags:
  - evaluation
  - statistics
  - regression-testing
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "NIST, Anthropic, OpenAI, and MLflow primary materials, plus
  original work on paired resampling, through 2026-07-22"
lang: en
translation_key: 评测体系/02-方法与质量/06-离线在线统计与回归.md
translation_source_hash: ea7dd0c7e2e6b5aa28cc5a78286e635ab671f72b600dbd7d512524900af8eacb
translation_route: zh-CN/评测体系/02-方法与质量/06-离线在线统计与回归
translation_default_route: zh-CN/评测体系/02-方法与质量/06-离线在线统计与回归
---

# Offline, Online, Statistics, and Regression

## Goal

Combine offline and online evidence correctly, constrain release decisions with paired comparisons and uncertainty, and continuously capture regressions.

## Intuition

An offline set is like a repeatable laboratory; an online progressive rollout is observation in the real environment. The former is good at quick localization and regression, while the latter reveals real distributions and interactions. Either one alone leaves blind spots.

## Offline and online answer different questions

| Type | Strength | Limitation | Suitable use |
| --- | --- | --- | --- |
| Offline | Repeatable and fast; suitable per commit | Data can become stale; environment is approximate | Unit tests, regression, candidate screening |
| Online progressive rollout / A-B | Real users and traffic | Cost, risk, confounders | Verify business effect and discover new failures |
| Production monitoring | Continuous drift and incident observation | Metrics are often proxies; no counterfactual | Alerting and new-case discovery |

Offline passing is a condition for online validation, not a guarantee of online success. Before an online experiment, define safety guardrails, exposure range, stop conditions, and rollback; minimize sensitive data in logs.

## Sample variation and confidence intervals

One result of 82% versus another of 80% may be sample variation. Report sample count, per-case results, and an interval for the difference. The frequentist interpretation of a confidence interval is that, if the same interval-construction method were repeatedly sampled, the specified proportion of intervals would cover the true parameter. It is not “this particular interval has a 95% chance of containing the truth.”

When comparing candidate and baseline on the same tasks, use paired differences: compute `candidate - baseline` per task, then estimate the mean difference and its interval. A bootstrap can sample these paired differences with replacement, which is appropriate for this course's intuitive demonstration. Small samples, correlated trials, stratification imbalance, and multiple comparisons all limit interpretation.

The minimal fixed-seed bootstrap procedure retains `n` per-case paired differences; draws `n` differences with replacement and takes their mean; repeats a pre-frozen number of times; then uses the distribution's tail quantiles for a percentile interval. A fixed seed makes identical inputs reviewable; it does not remove sampling assumptions. If cases are not approximately independent because they share a session, document family, or failure, resample by family or cluster instead of treating rows as independent.

Define the estimand and sampling unit before results: is it “average difference over the target task population” or “reliability when a fixed task is repeatedly run”? The former usually resamples tasks or families; the latter retains the `task × trial` hierarchy. Treating multiple trials of one task as extra independent tasks artificially narrows intervals.

Freeze the primary metric, critical slices, practically important difference threshold, and stopping rule before looking at results. Repeatedly checking intervals, trying many candidates or slices, and reporting only the winner introduces multiple-comparison and optional-stopping bias. Use an independent final holdout, an appropriate adjustment, or explicitly label findings exploratory and retest them. An interval crossing zero only means the current evidence does not clearly distinguish direction; it does not prove equivalence. Equivalence requires a predeclared acceptable-difference bound and an appropriate design.

## Stochastic systems need multiple trials

Run the same task repeatedly from a clean environment and record success rate and failure modes. Shared caches, residual files, and the same external outage make trials non-independent. For Agents, fix or record model settings, tool version, budget, retries, and time window as well.

`pass@k` answers “at least one success in `k` attempts”; `pass^k` answers “all `k` attempts succeed.” They correspond to a decision only when the product truly allows multiple attempts or requires consecutive reliability. Deriving `1-(1-p)^k` or `p^k` from a one-run success probability `p` assumes identically distributed independent Bernoulli trials; shared state, retry adaptation, and vendor outages break that assumption. Engineering reports should retain per-trial results, the actual retry policy, and cost needed for success instead of showing only an optimistic `pass@k`.

## Regression gates

1. Turn every confirmed incident into a minimal, de-identified, deterministic case.
2. Divide cases into fast smoke, critical risk, and complete quality suites.
3. Freeze baseline, data, and grader versions; run candidates under the same conditions.
4. Check critical gates before paired differences and stratum results.
5. When uncertain, increase samples or review manually; do not present “almost” as an improvement.
6. After deployment, feed back new distributions and failures while retaining historical versions for trend interpretation.

## The continuous-evaluation loop

Continuous evaluation is not “run the same total score on every commit”:

1. Run fast deterministic smoke checks on every change.
2. Run a frozen regression set at merge or candidate-build time.
3. Run more expensive human or model graders according to risk and a sampling plan.
4. After offline gates pass, use an online progressive rollout with independent safety, quality, cost, and latency guardrails.
5. New failures found by [[runtime-monitoring/00-index|Runtime Monitoring]] are only controlled triage candidates first. After human confirmation, de-identification, deduplication, authorization, and a minimal reproduction, the data or evaluation owner decides whether they enter the development or regression set; see [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]].
6. When a dataset, rubric, or grader version changes, rerun a comparable baseline and mark a discontinuity in the curve.

MLflow documentation labeled `latest` currently distinguishes two non-interoperable evaluation paths: classic ML uses `mlflow.models.evaluate()` and `EvaluationMetric`, while GenAI uses `mlflow.genai.evaluate()` and `Scorer`; old `mlflow.evaluate` was deprecated in MLflow 3. Trace-based automatic evaluation is another capability: it currently supports LLM judges but not code-based scorers; when a judge is created or enabled, it can look back at most one hour of traces or sessions; **updating judge configuration alone does not reevaluate already evaluated traces**. New records are still processed asynchronously under the judge's filtering and sampling configuration. These are product facts, not a general rule that online evaluation can only use models. Pin a version and verify migration when adopting a tool.

## Common mistakes and diagnostics

- Going to full traffic immediately after offline passing: first set online guardrails, stopping, and rollback.
- Comparing two aggregate means while ignoring per-case pairing: retain per-case differences.
- Fixing a production failure without adding it to regression: de-identify it, create a minimal reproduction, and version it.
- Trying many candidates while peeking continuously at the test: freeze the primary comparison, reserve an independent final holdout, or mark the conclusion exploratory.

## Exercises

1. Hand-calculate the mean paired difference for candidate and baseline 0/1 results on ten tasks.
2. List two environmental factors that can break trial independence.

## Self-check

Does an interval crossing zero prove the two systems are exactly the same? No. It only says the current design and sample do not establish a clear direction.

## Summary and next step

Continue first to [[evaluation-framework/methods-and-quality/07-evaluation-reporting-audit-and-governance|Evaluation Reporting, Audit, and Governance]], then to [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]], and finally complete the offline project.

## References

- [NIST/SEMATECH: What are confidence intervals?](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm) — checked 2026-07-22.
- [NIST AI RMF Core: Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — checked 2026-07-22.
- [MLflow Automatic Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/) — documentation labeled `latest`, checked 2026-07-22; the one-hour lookback and no-reevaluation-on-configuration-update boundaries.
- [MLflow Evaluation APIs](https://mlflow.org/docs/latest/ml/evaluation/) — classic-ML and GenAI API boundaries and old-API migration, checked 2026-07-22.
- [Anthropic: isolate trials and maintain evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; checked 2026-07-22.
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) — published 2026-05-29; system budget, validity checking, and cost per successful task.
- [Koehn 2004: Statistical Significance Tests for Machine Translation Evaluation](https://aclanthology.org/W04-3250/) — original paper, checked 2026-07-22.
