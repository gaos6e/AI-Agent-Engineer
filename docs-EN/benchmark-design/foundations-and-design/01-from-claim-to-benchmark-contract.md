---
title: "From Claim to a Benchmark Contract"
aliases:
  - Benchmark Contract
  - Benchmarking Contract
tags:
  - benchmark
  - evaluation-design
source_checked: 2026-07-14
lang: en
translation_key: Benchmark设计/01-基础与设计/01-从声明到Benchmark契约.md
translation_source_hash: 406a52fdf98e71a5f2603203dfff02eb252ab9bdfca8bee637be020183d36c02
translation_route: zh-CN/Benchmark设计/01-基础与设计/01-从声明到Benchmark契约
translation_default_route: zh-CN/Benchmark设计/01-基础与设计/01-从声明到Benchmark契约
---

# From Claim to a Benchmark Contract

## Goal

Work backward from a real decision to a Benchmark's claim, system under test, non-goals, success criteria, and version boundary. Do not collect questions first and guess later what a score represents.

## Intuition

A thermometer is meaningful only when its range, calibration, and conditions of use are clear. The same “85 points” can arise from different users, prompts, tool permissions, and graders, so it cannot be compared directly. A contract freezes measurement conditions before the run and states how far the evidence reaches.

## Core concepts

- **Benchmark claim:** the falsifiable comparative conclusion the Benchmark is meant to support.
- **system under test (SUT):** the actual tested boundary, which may be a bare model or an application combining prompt, retrieval, tools, and retry.
- **scenario:** a combination of task, user, environment, and adaptation method.
- **protocol:** how the system runs, including input, prompt, budget, randomness, timeout, repetition, and failure handling.
- **non-goal:** a capability the Benchmark explicitly does not test or cannot infer.
- **validity:** whether the present design supports its intended interpretation rather than merely producing a number.

## First distinguish three engineering objects

| Object | Primary question | Data time scale | Typical output |
| --- | --- | --- | --- |
| [[evaluation-framework/00-index\|Evaluation Framework]] | Does a product change meet development, regression, or release goals? | Rapidly changes with the product | PASS/REVIEW/BLOCK and failure diagnosis |
| Benchmark Design | Which system is better under a frozen, long-lived protocol, and can teams reproduce the result? | Stable versions with explicit replacements | Comparable results, report cards, and leaderboard |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | Is real production traffic healthy now, drifting, or experiencing an incident? | Continuous stream | SLOs, alerts, events, and feedback samples |

The same case can first serve product regression and later enter a mature Benchmark. A de-identified production failure can become a new case too. But natural production traffic, delayed labels, and dynamic environments in runtime monitoring must not be presented directly as a frozen cross-system comparison.

## Decompose the claim into capabilities and measurement objects

“Customer-service capability” is too broad. Decompose it into observable capabilities such as intent recognition, information retrieval, tool choice, parameter correctness, final state, safe refusal, and error recovery. Then select a **measurement object** for each: output text, tool trace, database state, or resource record. This is not to create more scores; it localizes evidence. If final state is correct but an unauthorized read occurred, task quality and safety must be graded separately.

## Step-by-step method

1. State the decision, for example, “choose a candidate Agent for read-only Chinese customer-service queries.”
2. Specify target users, time range, language, tool permissions, and deployment environment.
3. State compared objects and the SUT boundary: the same model with different prompts, or different complete systems.
4. Write critical benefit, unacceptable risks, and operational constraints.
5. State evidence source: real holdout, expert-authored cases, synthetic stress set, or online replay.
6. Write at least three non-goals, for example no refund writes, no English, and no production-satisfaction inference.
7. Map capabilities to verifiable output, trace, or environment state; define treatment of Unknown and failure.
8. Assign a contract version. Any change that changes score interpretation must increment it.

An operational claim:

> In 2026-Q3 Chinese order-query scenarios, under the same read-only tools and call budget, compare candidate and frozen baseline for task success, unauthorized-action risk, P95 latency, and call count. Evidence comes from a frozen offline set stratified by intent and input state. The result does not represent refund writes, other languages, or real online conversion.

## Example

This Benchmark-card skeleton turns a “question bank” into a contract:

~~~yaml
id: order-agent-readonly # Stable Benchmark identity for results, reports, and version migration.
version: 1.0.0 # Increment when task meaning, protocol, or scoring changes.
claim: compare task success and risk for Chinese read-only order queries # The sole conclusion this Benchmark can support.
system_boundary: prompt + model + tools + retry_policy # Freeze the tested system; do not conflate a model with a complete application.
population: 2026-Q3 Chinese customer-service queries # Population, time, and language boundary covered by the evidence.
primary_metric: task_success # The leaderboard's primary quality metric; it cannot hide other metrics.
critical_gates:
  - no_write_action # A write action is a safety hard gate that an average cannot offset.
resource_metrics:
  - latency_ms # Record end-to-end latency cost.
  - tool_calls # Record tool-use scale and reveal unnecessary execution paths.
non_goals:
  - refund writes # Do not extrapolate read-only evidence to side-effecting tasks.
  - English tasks # State the language-coverage boundary.
  - production-satisfaction inference # Offline testing cannot directly prove online business effect.
~~~

## Common mistakes and diagnostics

- **It is named a “general intelligence Benchmark”:** target users and task space cannot be listed; narrow the claim.
- **Models and applications are mixed:** one system has RAG and another does not, yet the result claims to compare model knowledge; redefine the SUT.
- **Weights are changed after viewing results:** this tunes against the test; freeze metrics before running candidates.
- **One total score carries everything:** make critical risk a gate and report other metrics separately.
- **Only a data filename changes with version:** protocol or grader changes alter meaning too and must enter the version record.

## Exercises

1. Rewrite “compare which of two RAG systems is better” with population, corpus time, citation requirement, and non-goals.
2. Draw distinct SUT boundaries for a bare model and a complete customer-service Agent.
3. List three conclusions an OCR Benchmark score cannot support.

## Self-check

1. Why can two scores on the same data still be incomparable? Prompt, budget, tools, decoding, or grader can differ.
2. Is a non-goal only a disclaimer? No. It prevents users from extrapolating limited evidence to untested conditions.
3. Does correcting prose require a version increment? A patch can correct prose without changing input, output, or scoring meaning; a change in interpretation requires an explicit version change.

## Summary and next step

A Benchmark begins with its claim and contract; questions and metrics must serve the intended decision. Continue to [[benchmark-design/foundations-and-design/02-task-space-representativeness-and-stratification|Task Space, Representativeness, and Stratification]] to expand target scenarios into auditable coverage.

## References

- [NIST AI RMF Core: Map and Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — retrieved 2026-07-14.
- [HELM original paper](https://openreview.net/forum?id=iO4LZibEqW) — retrieved 2026-07-14; methodological source.
- [HELM official repository](https://github.com/stanford-crfm/helm) — retrieved 2026-07-14; states maintenance mode from 2026-06-01.
- [BetterBench](https://openreview.net/forum?id=hcOq2buakM) — original paper, retrieved 2026-07-14.
