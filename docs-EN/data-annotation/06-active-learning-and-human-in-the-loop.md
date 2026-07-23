---
title: "Active Learning, Weak Supervision, and Human-in-the-Loop Work"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Active Learning
  - Human-in-the-Loop Annotation
  - Weak Supervision
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Lewis and Gale 1994 active-learning paper
  - Ratner et al. 2017 weak-supervision paper
  - Label Studio ML-assisted labeling documentation
  - Google People + AI Guidebook
lang: en
translation_key: 数据标注/06-主动学习与人机协同.md
translation_source_hash: 67d9f72314187adf518cf4018d53fc284e555fff6ff8e7fb5d02db99297d1a3c
translation_route: zh-CN/数据标注/06-主动学习与人机协同
translation_default_route: zh-CN/数据标注/06-主动学习与人机协同
---

# Active Learning, Weak Supervision, and Human-in-the-Loop Work

## Objective

Design a loop of candidate selection, independent human judgment, review, and versioned retraining. Active learning, rule voting, model pre-labeling, and synthetic examples can all save effort, but can generate only **candidates or weak evidence**. They cannot make themselves gold labels, frozen evaluation results, or privacy and licensing conclusions.

## Separate four data flows first

~~~mermaid
flowchart LR
    U[Approved unlabeled pool] --> E[Frozen evaluation set<br/>Never used for selection, prompts, or tuning]
    U --> R[Random or stratified audit flow<br/>Estimate coverage and risk]
    U --> S[Candidate-selection flow<br/>Uncertainty, diversity, and business risk]
    W[Rules, models, or generators] --> S
    S --> B[Initial blind annotation<br/>Hide suggestions or record display order]
    B --> Q[Review and adjudication]
    Q --> V[New data version and training set]
    P[Online-failure or appeal candidates] --> T[Minimization, licensing, de-duplication, and root-cause triage]
    T --> S
~~~

The label distribution of the candidate-selection flow does not represent the natural online distribution. The random or stratified audit flow is also not a frozen evaluation set. Record their sources, sampling probabilities, time windows, group-level splits, and purpose separately.

## Active learning: what it selects, not what it proves

When an unlabeled pool is large, active learning can prioritize:

- **Uncertainty:** samples the current model finds most ambiguous.
- **Diversity or representativeness:** coverage of different regions instead of only one kind of hard example.
- **Expected value or risk:** high-harm, high-cost, or new-version scenarios.
- **Coverage gaps:** known missing language, source, time, or long-tail strata.

Selecting only uncertain samples concentrates noise, outliers, and inherently unjudgeable regions. Selecting only high-risk samples distorts population proportions. A practical batch should predeclare the quota or probability for random, stratified, risk, uncertainty, and new-version samples, then report annotation rate, conflict rate, cannot_judge or exclude proportion, and downstream performance separately.

An actively selected batch cannot directly estimate population prevalence, online accuracy, or fairness. If a population estimate is required, retain an independent probability sample and apply estimators appropriate to the sample design. Even then, uncovered sources and access-refused content define the boundary of extrapolation.

## Model pre-labeling and human anchoring

Pre-labeling can reduce repetitive work, but it can also make people accept the model, especially on difficult cases. Retain at least one preregistered blind-annotation control: within the same stratum, some people first see raw evidence and others see a suggestion in the established order. Record whether it was shown, the model or prompt version, initial human label, review, and final label. Do not infer “the human agreed with the model on the first judgment” from a final adjudication.

Controls include hiding confidence, delaying suggestions, randomly auditing high- and low-confidence predictions, and hiding identity and productivity data from adjudicators. Models may help with deduplication candidates, ranking, and format checks. People still hold responsibility under the task card for high-risk labels, harm judgments, and escalation rules.

## Weak supervision: rule votes are not human truth

Weak supervision encodes keywords, knowledge-base matches, heuristics, distant supervision, or existing-model output as labeling functions that can abstain or conflict. It is useful for quickly generating candidates, covering known patterns, or exploring the label ontology. Its outputs have unknown accuracy and correlation; multiple rules “voting the same way” can merely reproduce the same bias.

Minimum controls:

1. Preserve weak_source_id, rule or model version, input version, vote or confidence information, and generation time for every weak label. Do not overwrite an initial human label.
2. Use independent human-annotated validation or audit samples that are not repeatedly used to tune rules. Check coverage, conflicts, and critical slice errors.
3. Treat correlated rules, source leakage, and error-prone strata as investigation targets. A label-model probability is neither gold nor a human-agreement rate.
4. If weak labels enter training, state the proportion, use, and limitation relative to human-adjudicated samples at release. A frozen evaluation set still relies on human or expert evidence from an independent protocol.

## Synthetic samples: coverage candidates, not real distribution

Templates, simulators, and generative models can construct rare combinations, adversarial conditions, and protocol test samples. Preserve origin=synthetic, generator or model plus prompt or template version, conditions, filtering or human-review records, and a reference to source or authorization status. Synthetic samples can expand coverage, but cannot prove their frequency, real-world utility, lack of copyright risk, or privacy safety. A generator’s self-evaluation cannot replace human adjudication.

Before synthetic samples enter training, check label correctness, near duplicates, group-level leakage, and utility on real holdouts. Before they enter evaluation, report them by strata separate from real or historical cases. See [[data-synthesis/00-index|Data Synthesis]] for fuller generation, privacy, and release boundaries.

## Production feedback is not automatic training

Online failures, appeals, human overrides, and anomalous trajectories can reveal gaps, but they are first controlled **candidates**. Before entering an annotation queue, triage them for minimization, access control, source and licensing, de-identification, deduplication, group-level leakage, and root cause. Then assign them under a new task card, blind annotation, review, and versioned release. Do not write logs, model suggestions, or end-user behavior directly as “true labels” for training or evaluation, and do not modify a frozen set in place.

For the relationship between release and feedback, see [[data-annotation/09-versioning-release-and-production-feedback|Versioning, Release, and Production Feedback]] and [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]].

## Exercise

For 100,000 Agent trajectories, design a 500-sample protocol for each round. State the proportions of random, risk, uncertainty, diversity, and new-version samples; list the selection probability or reason to record, frozen-set isolation rule, one blind-annotation control, and one triage path for an online candidate. Then specify validation samples and stop conditions for two weak-supervision rules.

## Mastery check

- [ ] I separate frozen evaluation, random audits, candidate selection, and production feedback into independent data flows.
- [ ] I can explain why an active-learning batch does not directly represent the online population and record its selection reason or probability.
- [ ] I use a blind-annotation control to assess pre-label anchoring instead of judging only annotation speed and agreement.
- [ ] I preserve weak-supervision and synthetic outputs as traceable candidates rather than writing their probabilities, votes, or self-evaluations as gold.
- [ ] I do not let production logs enter training or frozen evaluation sets automatically.

Next: [[data-annotation/08-data-governance-privacy-licensing-and-worker-safety|Data Governance, Privacy, Licensing, and Worker Safety]].

## References

Sources checked on 2026-07-22. Label Studio UI, pre-labeling, and sampling features vary by deployment version; tool settings do not substitute for this lesson’s data-flow, blind-annotation, and release protocol.

- Lewis, D. D., & Gale, W. A. (1994). [A Sequential Algorithm for Training Text Classifiers](https://aclanthology.org/P94-1019/)
- Ratner et al. (2017). [Snorkel: Rapid Training Data Creation with Weak Supervision](https://arxiv.org/abs/1711.10160)
- [Label Studio: Machine-learning pipeline integration](https://labelstud.io/guide/ml.html) and [project settings and task sampling](https://labelstud.io/guide/setup_project)
- [Google PAIR: People + AI Guidebook](https://pair.withgoogle.com/guidebook/)
- [NIST AI RMF Core: Data Selection, Human Oversight, and Continuous Monitoring](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
