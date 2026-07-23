---
title: "Data, Features, and Training Pipelines"
tags:
  - mlops
  - data-pipeline
aliases:
  - ML Training Pipeline
source_checked: 2026-07-14
lang: en
translation_key: MLOps/01-基础与生命周期/02-数据、特征与训练管线.md
translation_source_hash: c00fa04c62f4915dd322bd49a7e2044f8fa3e8ab515d9b69252ef4aab5400e90
translation_route: zh-CN/MLOps/01-基础与生命周期/02-数据、特征与训练管线
translation_default_route: zh-CN/MLOps/01-基础与生命周期/02-数据、特征与训练管线
---

# Data, Features, and Training Pipelines

## Goal

Understand how data contracts, feature consistency, and training pipelines together reduce the accident of “it runs on my machine.”

## From script to pipeline

A training script often mixes reading, cleaning, splitting, feature construction, training, evaluation, and export. A **pipeline** separates them into steps with inputs, outputs, and failure conditions. The steps form a directed acyclic graph (DAG); a downstream step needs rerun only when its upstream artifact changes.

```text
Raw snapshot → data validation → split → feature construction → training → offline evaluation → candidate artifact
```

## A data contract comes before a model

A data contract is a shared structural and semantic agreement between producer and consumer. At minimum, state:

- field name, type, and nullability;
- valid range, enum values, and units;
- which entity a row represents and whether a timestamp is event or processing time;
- label definition, generation delay, and revision rules;
- primary key, deduplication rule, and privacy level;
- compatibility strategy for adding an optional field, removing a field, or changing meaning.

Passing a structural check does not make data usable. An age field can remain integer while its unit changes from years to months and break the model. A contract needs semantics and units.

## Splits and leakage

**Data leakage** means training saw information unavailable at deployment. Common sources:

- calculate normalization statistics on all data before splitting;
- let near-duplicate samples from one user cross train and test;
- predict an outcome with a feature generated after that outcome;
- randomly split a time series so future information enters the past.

Split by business entity or time first; fit preprocessors only on training data, and save the same preprocessor as part of the model artifact.

## Training-serving feature consistency

Using one SQL implementation offline and handwritten logic online creates **training-serving skew**. Reduce it by:

1. sharing tested feature functions;
2. saving and loading preprocessors with the model;
3. building offline/online consistency tests for representative input;
4. stating feature freshness and missing-value fallback;
5. recording feature version for every prediction rather than sensitive raw values.

## Caching and idempotence

Pipeline steps should be **idempotent** where practical: repeating identical inputs and parameters produces an equivalent artifact rather than appending dirty state. A cache key derives from input content, code/config version, and step parameters; filename or date alone can reuse stale artifacts incorrectly.

Before retrying, distinguish:

- pure computations that are safe to retry;
- side-effecting steps that write a database, send a notification, or replace an alias;
- steps requiring a unique run ID or transaction guard.

## An auditable step contract

```yaml
name: build_features # Stable step name for logs and orchestration.
inputs: [validated_snapshot_id, feature_code_commit] # Only validated data and pinned feature code.
outputs: [feature_set_id, schema_report] # Immutable artifact and validation report traceable by downstream steps.
checks: [no_forbidden_nulls, no_split_overlap] # Block bad nulls and train/evaluation leakage before release.
retry: safe_before_publish # Only pure pre-publication computation may retry safely.
owner: data-team # Team accountable for the step and its exception path.
```

This is a conceptual example; it does not require YAML or a particular orchestration framework. Define the boundary first, then choose tools.

## Exercise and self-check

Draw a pipeline for predicting whether a customer-service record needs human escalation. Mark the step most vulnerable to label leakage, the output that must be immutable, checks that must block immediately, and fallback behavior when an online feature is absent. Why is an unchanged schema insufficient to reuse a model? Why must a cache key include feature-code or configuration version?

## Next step

Reliable pipelines make data semantics, split rules, and artifact boundaries explicit. After a candidate exists, manage its identity and promotion relation in [[mlops/foundations-and-lifecycle/03-model-registry-and-candidate-promotion|Model Registry and Candidate Promotion]].

## References

- [Google Cloud: MLOps continuous delivery and automation pipelines](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) — checked 2026-07-14; vendor architecture guidance.
- [Kubeflow Pipelines: Pipeline](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/) — checked 2026-07-14.
- [Kubeflow Pipelines: Artifacts](https://www.kubeflow.org/docs/components/pipelines/user-guides/data-handling/artifacts/) — checked 2026-07-14.
- [Google Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml) — checked 2026-07-14; validate engineering guidance against the current system.
