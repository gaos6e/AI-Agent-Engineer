---
title: "Annotation Guidelines and Edge Cases"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Annotation Guideline
source_checked: 2026-07-22
source_baseline:
  - Label Studio official project-settings documentation
  - Google People + AI Guidebook
lang: en
translation_key: 数据标注/02-标注指南与边界案例.md
translation_source_hash: 449357951c1372c6cdcd635e47c3298ca69a638fa64a4be0f37ace1fe0d5b850
translation_route: zh-CN/数据标注/02-标注指南与边界案例
translation_default_route: zh-CN/数据标注/02-标注指南与边界案例
---

# Annotation Guidelines and Edge Cases

## Objective

Write decision rules that unfamiliar annotators can execute in order. Use positive, negative, and boundary examples, plus abstention and escalation, to make ambiguity explicit and versioned.

## Minimum guideline structure

1. Task purpose and non-goals.
2. Annotation unit and visible context.
3. Definition, positive examples, and negative examples for each label.
4. A decision tree executed in order.
5. Edge cases, conflict rules, and abstention or exclusion conditions.
6. Rationale or evidence-entry requirements.
7. Privacy, safety, and escalation channels.
8. Guideline version and effective date.

Definitions should describe observable behavior, not personality judgments. “The answer is very poor” cannot be reviewed; “it claims to have called a tool, but the trajectory contains no such call” can be reviewed.

## Decision-tree example

~~~text
Is the sample complete and in scope? No → exclude
Does it contain advice that would lead to a dangerous action? Yes → unsafe
Is a key conclusion supported by the given evidence? No → not_helpful
Does it complete the user’s explicit request? No → not_helpful
Otherwise → helpful
Insufficient evidence → cannot_judge
~~~

Priorities must be explicit. Otherwise, a response that is both incomplete and unsafe invites arbitrary choice.

## Use a pilot to find gaps in the guideline

First draw a small batch that covers common, long-tail, difficult, and potentially risky samples, and have at least two people annotate independently. When discussing conflicts, do not merely standardize the answer; update the definition, example, or escalation rule. After a version change, record which old labels must be relabeled.

Guideline changes need a changelog: why it changed, affected labels or samples, backward compatibility, effective batch, and relabeling scope. Do not silently change a rule mid-batch and continue merging results.

## Do not turn examples into keyword rules

Positive and negative examples explain boundaries; they should not teach annotators to search only for keywords. Use paired examples to show why the same keyword differs in another context and how one label can have different expressions.

## Exercise

For “is this tool call appropriate?”, write three positive examples, three negative examples, and three boundary examples. Each must state its evidence and decision path, not just the label.

## Mastery check

- [ ] My guideline includes purpose, non-goals, unit, context, labels, decision tree, evidence, abstention, and escalation channels.
- [ ] Each label has paired positive and negative examples plus at least one boundary example, not a keyword list.
- [ ] I can use independent pilot annotation to locate rule gaps and turn conflicts into a changelog.
- [ ] I do not change a guideline mid-batch without a version or overwrite old labels.

Next: [[data-annotation/03-annotation-workflow-and-data-formats|Annotation Workflow and Data Formats]].

## References

Sources checked on 2026-07-22. Label Studio’s project-settings pages have changed; this lesson preserves the boundary between tool configuration and independently versioned guidelines. Verify exact UI behavior against current official documentation and a small round-trip sample.

- [Label Studio: Set up your labeling project](https://labelstud.io/guide/setup_project.html)
- [Google PAIR: Guidebook](https://pair.withgoogle.com/guidebook/)
