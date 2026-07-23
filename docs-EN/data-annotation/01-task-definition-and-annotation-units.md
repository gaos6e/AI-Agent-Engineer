---
title: "Task Definition and Annotation Units"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Annotation Task Definition
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Google People + AI Guidebook
  - Datasheets for Datasets
  - NIST AI RMF
lang: en
translation_key: 数据标注/01-任务定义与标注单元.md
translation_source_hash: fb9e09573b5ee9e0f45291b35b2db3808bda6e866aa0ba3a162e661123725521
translation_route: zh-CN/数据标注/01-任务定义与标注单元
translation_default_route: zh-CN/数据标注/01-任务定义与标注单元
---

# Task Definition and Annotation Units

## Objective

Turn an abstract construct into units, context, labels, and evidence rules that annotators can observe and reviewers can verify. At the same time, freeze the target population and prediction time so that information unavailable at deployment cannot leak into the label definition.

## A label is a measurement, not inherent truth

“Answer quality,” “relevance,” and “harmful” are constructs, not self-explanatory facts. A label has meaning only after you specify **which decision it informs, who makes that decision, when it is made, which evidence is visible, and what an error costs**. The same label string can measure different things in different tasks, versions, or populations.

For example, do not write “annotate answer quality.” Write: “Before a user acts, a reviewer judges only from the user question, permitted tool results, and final answer whether a material factual error would change that action.” This excludes later support tickets, later click-through rates, and invisible internal data.

> [!warning] Outcome labels and leakage
> “The user later requested a refund” can be a well-defined **post hoc outcome**. But if a predictor must decide before the refund, that outcome cannot enter the contemporaneous features, retrieval context, sample split, or human prompt. State whether the label is an operational risk assessable at that time or a result observed later before designing the data flow.

## Write a task card before the first annotation

| Field | Question it must answer | Common failure |
| --- | --- | --- |
| Decision and user | Which decision will the label trigger or support? Who bears the consequence of an error? | Replacing a specific use with “improve the model” |
| Target population and time window | Which online or offline samples, languages, sources, and times are in scope? | Labeling only an easy-to-obtain batch and calling it representative |
| Annotation unit and context | Is one judgment a query, span, query–chunk pair, tool call, or whole trajectory? Which neighboring evidence may be seen? | A unit that combines unrelated questions, or annotators who see different context |
| Label ontology | What are the definitions, mutually exclusive or multilabel relations, priorities, cannot_judge, exclude, and derivation rules? | Silently turning abstention or a bad sample into the negative class |
| Visible evidence and time | Which documents, tool results, timestamps, sources, or logs are visible? Which must be masked? | Using future outcomes, adjudicated answers, or model confidence |
| Evidence and escalation | What rationale or span is saved for each important judgment? When must the case escalate? | Saving only a bare label that cannot be adjudicated |
| Risks and stop conditions | What harm can mislabeling cause? Which data or content cannot be assigned? When must work pause? | Deferring safety, privacy, and labor risk until launch |
| Version and release boundary | How are source_revision, guidelines, label space, UI or schema, splits, and releases recorded? | Recording only “v1,” making the actual input unreproducible |

The task card is the shared contract for later guidance, sampling, quality control, adjudication, and release. Without one, do only a small exploratory exercise; do not mix exploratory labels into a formal release set.

## Annotation units, context, and label spaces

An annotation unit is the smallest object of one independent judgment:

- Text classification: one complete query or message.
- Entity extraction: a character or token span plus entity type.
- RAG relevance: one query–document or query–chunk pair together with permitted context.
- Agents: one tool call, one state transition, or an entire run.
- Generated answers: the whole answer, or separately observable dimensions such as factuality, task completion, citation support, and safety.

An overly large unit combines multiple errors; an overly small one loses the context required to judge. When an aggregate label derives from multiple dimensions, freeze the derivation rule first. For example, assess factual correctness, citation support, constraint completion, and safety separately; only when all four pass does the aggregate pass. Do not disguise a later, subjective 1-to-5 adjustment as the same measurement.

A minimal nominal label space could be:

~~~text
helpful: Within the given evidence and scope, the answer is correct, relevant, and actionable.
not_helpful: It is relevant but has a material omission, error, or impractical element.
unsafe: The advice creates a clear safety, authorization, or harm risk.
cannot_judge: The provided evidence is insufficient for the task-required judgment.
exclude: The sample is corrupted, duplicated, withdrawn, or outside this task’s scope.
~~~

cannot_judge is a valid judgment about evidence; exclude is a process decision about sample eligibility. Neither may silently become a negative class in a training, reporting, or evaluation projection.

## Decide samples, population, and splits before annotation

A sample pool is not automatically a miniature target population. The task card should first record dimensions that can affect judgment, such as source, time, language, length, risk, subject, or document group, and then design random, stratified, or focused sampling. For training and evaluation, the same user, session, document version, near-duplicate cluster, or business entity must use a group-level split. Isolate a frozen evaluation set before active learning, pre-labeling, prompt writing, or tuning.

If long-tail or high-risk samples are oversampled to find errors, report them as a separate stratum. Do not use their label proportions to estimate population prevalence. The availability of visible data, refusal rates, and uncovered populations are themselves quality evidence.

## Evidence boundary and governance entry point

Attach a citation span, tool-step ID, controlled document reference, or concise rationale to each important label where possible. source_revision points to the input snapshot the annotator actually saw. It supports review, but does not prove that the source was licensed, the data was anonymized, or the conclusion was true.

Before assigning content to people, complete the minimization, access, licensing, and content-risk review in [[data-annotation/08-data-governance-privacy-licensing-and-worker-safety|Data Governance, Privacy, Licensing, and Worker Safety]]. For freezing and feedback rules related to evaluation or training, later use [[data-annotation/09-versioning-release-and-production-feedback|Versioning, Release, and Production Feedback]] rather than rewriting historical labels ad hoc in a task card.

## Exercise

Turn “judge whether a RAG answer is good” into a task card. Include the target population, unit, visible evidence, labels, exclusion conditions, evidence fields, two error costs, group-level split unit, and one rule for sensitive content that cannot be assigned.

## Mastery check

- [ ] I can state the decision, user, time, target population, and error cost that a label serves.
- [ ] I distinguish an operational label assessable at the time from a later observed outcome, and avoid future-information leakage.
- [ ] I can select single-label, multilabel, or dimension-level labels and write the aggregate-label derivation rule.
- [ ] I limit visible evidence and freeze group-level splits to prevent context differences, near duplicates, and future outcomes from contaminating labels.
- [ ] I know that source_revision provides input traceability, not a conclusion about licensing, privacy, or correctness.

Next: [[data-annotation/02-annotation-guidelines-and-edge-cases|Annotation Guidelines and Edge Cases]].

## References

Sources checked on 2026-07-22.

- [Google PAIR: People + AI Guidebook](https://pair.withgoogle.com/guidebook/)
- Gebru et al. (2021). [Datasheets for Datasets](https://arxiv.org/abs/1803.09010)
- Bender & Friedman (2018). [Data Statements for Natural Language Processing](https://aclanthology.org/Q18-1041/)
- [NIST AI RMF Core: Data Selection, Construct Validation, and Human Oversight](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
