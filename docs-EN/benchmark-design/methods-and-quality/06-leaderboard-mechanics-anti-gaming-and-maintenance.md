---
title: "Leaderboard Mechanics, Anti-Gaming, and Maintenance"
aliases:
  - Leaderboard Governance
  - Benchmark Anti-Gaming
tags:
  - benchmark
  - leaderboard
  - governance
source_checked: 2026-07-14
lang: en
translation_key: Benchmark设计/02-方法与质量/06-Leaderboard机制与维护.md
translation_source_hash: 1245cd3ca6696a111542987c855ff7103fbe43dff141d46780159f8f18d77cd2
translation_route: zh-CN/Benchmark设计/02-方法与质量/06-Leaderboard机制与维护
translation_default_route: zh-CN/Benchmark设计/02-方法与质量/06-Leaderboard机制与维护
---

# Leaderboard Mechanics, Anti-Gaming, and Maintenance

## Goal

Understand how a leaderboard changes participant incentives. Design submission, audit, disclosure, version-update, and retirement rules that reduce leaderboard gaming and test-set overfitting.

## Intuition

When one score controls reputation, procurement, or prizes, participants optimize it. Some optimization improves real ability; some recognizes the test, exploits a grading loophole, adds unfair resources, or probes hidden answers through repeated submission. Governance does not assume everyone is malicious. It makes the rules direct effort toward the intended goal.

## Core concepts

- **leaderboard gaming:** improving leaderboard score without improving utility in the target world.
- **Goodhart risk:** once a proxy becomes a strong target, it may cease to represent the original target.
- **benchmark detection:** a system recognizes that it is being tested and changes behavior.
- **submission budget:** limits submission count, rate, or feedback granularity to reduce adaptation to hidden sets.
- **audit:** checks whether implementation, data, logs, and result conform to the rules.
- **living benchmark:** a maintained Benchmark with owner, version, update signals, and migration mechanism.
- **saturation:** score approaches ceiling or stops distinguishing real ability; it does not mean the task is solved.

## Step-by-step method

1. State whom the leaderboard serves: research comparison, internal release, procurement filtering, or competition.
2. Publish stratified, risk, and resource results beyond the primary metric so all optimization does not land on one number.
3. Freeze allowed external data, adaptation, tools, hardware, and compute budget; group different tracks clearly.
4. With hidden test, question rotation, or controlled runtime, limit submission rate and feedback granularity.
5. Forbid special branches triggered by recognizing Benchmark input; retain code, logs, or an auditable interface.
6. Provide anomaly detection and random or focused audit; publish appeal, withdrawal, and correction processes in advance.
7. Regularly check saturation, contamination, real-distribution drift, grader loopholes, and material gaps.
8. On a new major version, preserve old results but state `no cross-version ranking`, provide a migration window, and publish change notes.

## Submission policy and private testing

An executable policy states at least who may submit; how systems and external data are disclosed; allowed adaptation; resource tracks; submission rate; feedback granularity; private-test access; log retention; audit sampling; conflicts of interest; appeal; correction; and delisting. Private tests lower direct-answer copying risk, but repeated submissions can still probe them. They need a submission budget, delayed feedback, or periodic rotation; `private` is not a permanent-secrecy guarantee.

## Report cards and maintenance process

Every release version keeps a Benchmark card: claim, target population, data/protocol version, task and slice coverage, scoring contract, baseline, resource conditions, results, contamination status, limitations, owner, and expiration. Maintainers repeat:

1. Collect error reports, production drift, and contamination evidence.
2. Decide whether the change is label repair, grader fix, or population/protocol change.
3. Validate change on an independent development set rather than repeatedly tuning against old private test.
4. Publish changelog, version number, migration window, and cross-version-comparability statement.
5. Retain old version for historical display only and state that it accepts no new submission.
6. Retire when task is saturated, contamination is uncontrolled, real distribution no longer matches, or maintenance capacity is insufficient.

Even a clear mislabel repair changes some results: recompute affected submissions and retain a correction record. Material task, weight, protocol, or grader-semantics change creates a new version; new and old scores must not be joined into one rank.

## Example

An internal leaderboard can display all of:

| Field | Purpose |
| --- | --- |
| Core-set success rate | Primary result close to the target distribution |
| Critical-risk gate | Any unauthorized action blocks release |
| Language/task strata | Prevent an average from hiding a weakness |
| P95 latency and call count | Show performance cost |
| Benchmark version | Prevent cross-version miscomparison |
| Submission count | Expose test-set adaptation |
| Reproduction status | Distinguish self-report from independent replay |

If a competing system calls a special answer table only after detecting a fixed prompt prefix, it can score highly without generalization. MLPerf Inference official rules checked for this course explicitly prohibit Benchmark detection and special optimization based on input content, and require reproducibility and audit. The general MLCommons policy repository separately maintains submission and result-expression rules. This is one concrete institutional example, not a requirement to copy one rule set for every task; current rules must be checked for real submission.

## Common mistakes and diagnostics

- **Publish test answers and allow unlimited submission:** create a new holdout, rate limit, and rotate versions.
- **Rank only by total score:** show Pareto dimensions, critical gates, and scope of applicability.
- **Change rules temporarily during a run:** version every change and apply it consistently to every participant.
- **Treat leaderboard first as production best:** inspect target population, cost, risk, and deployment differences.
- **Never retire an old Benchmark:** define retirement conditions for contamination, saturation, drift, and maintenance resources.

## Exercises

1. Write submission-rate, feedback-granularity, and audit rules for an internal Agent leaderboard.
2. Construct a gaming example where score improves while the real objective worsens, then change metric or rule.
3. Write a compatibility statement for a data-version upgrade: which results remain comparable, and which do not.

## Self-check

1. Does hidden testing conflict with transparent reproduction? It is a tradeoff. Publish specification and grading code while a controlled service retains some inputs.
2. Do multiple metrics automatically prevent gaming? No. Metrics and aggregation can still be exploited and need audit and update.
3. Does a perfect score prove a Benchmark is solved? Not necessarily; data may be easy, contaminated, or poorly covered, or the grader may have a loophole.

## Summary and next step

A leaderboard is an incentive and governance system, not only a sorting UI. Rules hold only when run conditions are reproducible. Continue to [[benchmark-design/methods-and-quality/07-agent-environment-state-and-repeated-runs|Agent Environments, State, and Repeated Runs]], then enter the integrated project.

## References

- [MLPerf Inference official rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) — master branch checked 2026-07-14.
- [MLCommons general policy repository](https://github.com/mlcommons/policies) — submission and result policies, master branch checked 2026-07-14.
- [BetterBench](https://openreview.net/forum?id=hcOq2buakM) — original paper, retrieved 2026-07-14.
- [The Benchmark Lottery](https://arxiv.org/abs/2107.07002) — original paper, retrieved 2026-07-14.
- [Dynabench](https://arxiv.org/abs/2104.14337) — original paper, retrieved 2026-07-14.
