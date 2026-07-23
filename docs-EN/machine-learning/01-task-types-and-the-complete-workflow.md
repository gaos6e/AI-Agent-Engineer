---
title: "Task Types and the Complete Workflow"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Machine Learning Task Types
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/01-任务类型与完整流程.md
translation_source_hash: d1ebe73f93447bd1f76e7b7ccd2297d3404d10365d13cd63ed747333385703bd
translation_route: zh-CN/机器学习/01-任务类型与完整流程
translation_default_route: zh-CN/机器学习/01-任务类型与完整流程
---

# Task Types and the Complete Workflow

## Objectives

Turn a vague request such as “solve it with AI” into a trainable, evaluable machine-learning task.

## Start with examples, features, and labels

An example is one independently observable object, such as a ticket, a query, or one Agent run. A **feature** is information the model may see at prediction time; a **label/target** is the answer the model should learn to predict.

For example, route customer-service tickets into refund, technical-failure, or account-issue queues. Each ticket is an example, its text is a feature, and the category confirmed by a human is its label. Information unavailable at prediction time cannot enter features, such as an “outcome after handling.”

## Identify the task type first

| Question | Output | Typical task | Agent-engineering example |
| --- | --- | --- | --- |
| Which finite category does it belong to? | discrete category | classification | intent routing, unauthorized-access risk detection |
| What numeric value is it? | continuous value | regression | predicted latency, task-cost prediction |
| Which examples are similar? | group or distance | clustering | failure-log topic discovery |
| How can structure be retained in fewer dimensions? | low-dimensional vector | dimensionality reduction | embedding visualization, noise compression |

**Supervised learning** needs examples with answers. **Unsupervised learning** has no target labels and uses only data structure. Algorithmic cluster groups do not automatically equal real business categories.

## A complete workflow

1. **Define the decision**: who uses the prediction, when, and what an error costs.
2. **Define examples and labels**: state what one row is, when its label arises, and whether the judgment is reproducible.
3. **Establish data boundaries**: split training, validation, and test first, then fit preprocessing.
4. **Build a simple baseline**: classification can begin with a majority class, rule, or linear model.
5. **Train and validate**: fit only on training data and choose a solution from validation results.
6. **Test after locking**: use the test set for one production-like estimate, never repeated tuning.
7. **Analyze errors**: inspect false positives, false negatives, short texts, rare classes, and shifted examples.
8. **Deliver and monitor**: preserve code, dependencies, feature rules, thresholds, and data version.

When a prediction affects people, funds, access rights, or safety handling, step 1 should also state the scope of automation, conditions for human escalation, traceable records, and dispute-resolution path. Group-sliced metrics can reveal risk candidates, but alone cannot prove that a system is “fair” or suitable for automated decisions.

## Write a task card first

Before coding, complete:

```text
Decision: whether to route a ticket automatically to the refund queue
Example: one ticket first submitted by a user
Available features: title and body at submission time
Label: target queue ultimately confirmed by a human
Primary error: send a non-refund ticket to the refund queue (false positive)
Offline metrics: refund-class precision, recall, and confusion matrix
Production fallback: send low-confidence cases to a human; never issue refunds automatically
```

The task card should also state which sensitive fields must not be used at prediction time. If a class of attributes is necessary for compliance review or risk measurement, specify who may access it, its purpose, and retention duration. These are context-specific governance questions, not questions a single classification metric can answer automatically.

## Common errors

- **Start from a model name**: choosing “XGBoost/LLM” before defining the problem ignores decision constraints.
- **Ambiguous labels**: if two annotators interpret a definition differently, label noise caps the model.
- **Treat correlation as causation**: a prediction model finds co-occurrence; it does not prove changing a feature changes the outcome.
- **Replace product outcomes with offline metrics**: high F1 does not prove end-to-end task success, low cost, or safety.

## Exercise and self-check

Choose one Agent scenario, write a task card, and answer:

1. Which fields are already available when the prediction occurs?
2. Is a false positive or false negative more expensive?
3. Who confirms the label, and how are disputes resolved?
4. What is one rule baseline?

Next: [[machine-learning/02-data-splitting-and-data-leakage|Data Splitting and Data Leakage]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Supervised learning](https://scikit-learn.org/stable/supervised_learning.html)
- [scikit-learn: Unsupervised learning](https://scikit-learn.org/stable/unsupervised_learning.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
