---
title: "Evaluation Evidence and Feedback Loops"
tags:
  - ai-agent-engineer
  - ai-foundations
  - evaluation
aliases:
  - Introduction to AI evaluation evidence
  - Introduction to feedback loops
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/04-评测证据与反馈闭环.md
translation_source_hash: 5ebf978a4638c6f27fa5ba15e7da217a589d39a6ee69895ab224911647d6919e
translation_route: zh-CN/AI基础认知/01-概念地图/04-评测证据与反馈闭环
translation_default_route: zh-CN/AI基础认知/01-概念地图/04-评测证据与反馈闭环
---

# Evaluation Evidence and Feedback Loops

## Learning objective

After this lesson, you should be able to distinguish model metrics, task metrics, and system outcomes; combine offline tests, human review, pilots, and online monitoring; and explain why user feedback cannot directly become training ground truth.

## Evaluation first answers “for what?”

Evaluation is not a model grading itself. It uses predefined tasks, criteria, and evidence to decide whether a system meets its goals and risk tolerance. Before starting, write down at least:

1. Who uses the system and who may be affected.
2. Which outcomes count as success and which error consequences are most serious.
3. What the comparison baseline is.
4. Which time, languages, and situations the test data represents.
5. Who judges complex or high-risk results.
6. Which thresholds block a release, trigger human handling, or require rollback.

If metrics and thresholds are chosen only after seeing the results, it is easy to retain only favorable numbers.

## Do not mix the three layers of objectives

| Layer | Example | Primary use |
| --- | --- | --- |
| Model/component metric | Classification F1, retrieval Recall@k, JSON pass rate | Diagnose whether one component improves |
| Task metric | Whether action items are complete, evidenced, and non-fabricated | Decide whether the system completes the intended task |
| System outcome | User completion rate, human overrides, incidents, cost, latency | Decide whether deployment creates net value |

An improved component metric does not ensure a better end-to-end result. Higher retrieval recall can crowd the context; a structured-output pass can still contain incorrect business parameters. Evidence across the three layers should be traceable to one another, not reduced to a single aggregate score.

## Baselines and thresholds

A **baseline** is the current human process, simple rule set, or previous stable version. It answers whether a complex solution actually adds benefit. Without one, a number only shows that the system reached that number, not whether it is worth the extra cost and risk.

Define thresholds before formal testing, including:

- Minimum quality for the core task.
- Zero-tolerance errors or human gates for unacceptable outcomes.
- Critical languages, groups, and high-risk slices.
- Latency, cost, and dependency failures.
- Security, privacy, unauthorized access, and prompt injection.
- Existing capabilities that must not regress.

Thresholds are not universal constants. A task where a missed case can threaten safety has a different tolerance from one that drafts marketing copy.

## What five kinds of evidence can see

| Evidence | Best at finding | Main blind spots |
| --- | --- | --- |
| Unit and rule tests | Schemas, parsing, permissions, boundaries, and deterministic logic | Open semantics and real distributions |
| Frozen offline sets | Quality, safety, cost, and error slices across versions | New user behavior and dependency failures |
| Expert/human review | Complex correctness, context, harms, and usability | Expensive; reviewers can disagree |
| Shadow or limited-traffic pilot | Integration, latency, and human behavior under real traffic | Coverage remains limited; high-risk side effects should not be opened up |
| Online monitoring and incidents | Distribution changes, outages, misuse, and long-term effects | It can observe only signals recorded in advance |

**Shadow mode** means a new system receives real or near-real inputs and produces results, but its results do not directly affect users or business actions; the team compares it with the existing process. It reduces side effects, but does not make unauthorized data use acceptable or complete launch validation.

## Human review also needs design

Complex generation often needs a human rubric. A reproducible rubric should state:

- Whether the unit of evaluation is a full response, each factual item, or a tool trace.
- How “correct,” “complete,” “evidenced,” and “safe” are judged.
- Which equivalent expressions are allowed.
- How to handle insufficient evidence, conflicts, or ambiguity in the task itself.
- Whether reviewers can see the system name and candidate order.
- How reviewer disagreement is measured and escalated to expert adjudication.

LLM-as-a-judge can scale initial screening, but the judging model can also be affected by prompts, order, language, and version. It must be aligned with human samples and versioned; it does not automatically become ground truth.

## Feedback is not labels

Likes, accepting a suggestion, editing text, asking again, and complaints are observational signals, but they may be shaped by:

- Interface defaults.
- Users lacking time to verify.
- Feedback from only highly satisfied or highly dissatisfied users.
- Errors appearing much later.
- Users lacking access to the actual evidence.
- Automation bias causing mechanical acceptance.

A safe feedback loop separates raw events, user opinions, and reviewed labels; removes unnecessary sensitive information; slices by error type and context; lets authorized people decide whether a finding belongs in data, prompts, rules, or product process; and finally verifies changes with an independent regression set.

## A versioned loop

```text
Real requirement and risk hypotheses
  ↓
Frozen test set + rubric + baseline
  ↓
Candidate system version (model / prompt / knowledge base / tools / code)
  ↓ Offline thresholds
Shadow/limited-traffic pilot
  ↓ Online metrics, human overrides, incidents
Reviewed problem samples
  ↓
Fix data / rules / prompts / retrieval / model / process
  ↓
Full regression, approval, and rollback-ready release
```

Changing one major factor at a time makes attribution easiest. If you replace the model, rewrite the prompt, update the knowledge base, and change tools at once, changes in results become difficult to explain.

## A minimum example

For “meeting action-item extraction,” define:

- Baseline: keyword and date rules.
- Task metric: judge each task, owner, date, status, and evidence item.
- Safety metric: untrusted text must not disclose private information or trigger automatic sending.
- Slices: no action items, missing owner, conflicting dates, mixed English and another language, injection text.
- Threshold: every item of evidence maps back to original text, and key fields must not be completed without support.
- Pilot: generate drafts only; humans confirm them and record reasons for changes.
- Online signals: validation failures, human rejection, latency, cost, and sensitive-input events.

This is much closer to auditable evidence than “the model’s answers look good.”

## Common misconceptions

| Misconception | Problem | Improvement |
| --- | --- | --- |
| “The model with the highest average score is best.” | It can fail critical slices and cost more. | Compare quality, risk, latency, and cost together. |
| “Passing offline tests means full launch is safe.” | The real process and dependencies are still unobserved. | Use shadow mode, limited traffic, monitoring, and rollback. |
| “No user complaints means no problem.” | Harms may be invisible or impossible to appeal. | Sample proactively, use slices, and provide incident channels. |
| “A second LLM makes evaluation objective.” | The judging model can also be biased and drift. | Align it to humans and version it. |
| “Put every failure sample directly into training.” | It can contain privacy issues, bad labels, or selection bias. | Review, attribute, and minimize first. |

## Exercise

For an internal-policy question-answering system, design metrics at all three layers, one non-AI baseline, six test slices, one release threshold, and two rollback conditions. Explain which results can be rule-checked, which require human judgment, and which can only be observed online.

## Self-check

1. Why can a component metric and a system outcome move in opposite directions?
2. Why should thresholds be set before formal testing?
3. What does shadow mode solve, and what does it not solve?
4. Why does an LLM judge need human alignment?
5. Why can a user’s edit not directly become a training label?

## Scope and next step

This lesson only establishes how evidence closes the loop. For data independence, see [[ai-foundations/01-concept-map/03-generalization-data-splits-and-leakage|Generalization, Data Splits, and Leakage]]. Formal metrics, experiments, and review design continue in [[evaluation-framework/00-index|Evaluation Framework]]. To connect offline failures, online incidents, and release decisions into an auditable handoff, continue with [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]]. Operational signals continue in [[runtime-monitoring/00-index|Runtime Monitoring]].

Next, continue with [[ai-foundations/01-concept-map/05-how-llms-generate-answers|How LLMs Generate Answers]], which applies the general model lifecycle to a language-model data flow.

## References

Accessed **2026-07-22**.

- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
- Sculley et al., [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)
