---
title: "Experiment and Reproducibility Tracking"
tags:
  - mlops
  - experiment-tracking
aliases:
  - ML Experiment Tracking
source_checked: 2026-07-14
lang: en
translation_key: MLOps/01-基础与生命周期/01-实验与可复现追踪.md
translation_source_hash: 0205f6c7eabdf1da860525abee6dac4d3ef02b3906fd7ee9a0ab61a0394ad72b
translation_route: zh-CN/MLOps/01-基础与生命周期/01-实验与可复现追踪
translation_default_route: zh-CN/MLOps/01-基础与生命周期/01-实验与可复现追踪
---

# Experiment and Reproducibility Tracking

## Goal

Turn “a notebook produced a good result” into an explainable training record, and understand the boundary of reproducibility.

## Why track experiments?

A model metric is a result, not evidence. Two runs can both report `0.91` while using different splits, feature code, or dependency versions. Saving only a model file cannot tell which run is trustworthy or support a safe rollback.

## Version the problem, not only the model

Before the first run, write a short **problem contract**:

- who uses a prediction, when, and for which final decision;
- the prediction object, time range, and data forbidden to use;
- label definition, arrival time, and who may revise it;
- business cost of errors and critical slices that need separate observation;
- when the system must decline to predict or hand off to a person;
- separate versions for the current problem definition, label, and evaluation policy.

If a label changes from “refund within seven days” to “refund within 30 days,” the training code can be identical while the problem version is different. MLOps lineage must track that semantic change; otherwise a registry version says only that files differ, not whether they still solve the same problem.

A **run** is a set of experimental facts that must not be confused:

| Category | Record | Question answered |
| --- | --- | --- |
| Data | Snapshot ID, time range, split rule, label version | Which samples were used? |
| Code | Git commit, entry script, dirty-worktree note | Which code ran? |
| Parameters | Hyperparameters, seed, feature flags | How was it trained? |
| Environment | Python and library versions, OS, container-image digest if used | In which environment? |
| Results | Overall and critical-slice metrics, runtime, resource use | How did it perform? |
| Artifacts | Model, preprocessor, I/O signature, evaluation report | What was produced? |
| Responsibility | Runner, purpose, status, approval record | Who decided what and why? |

## Tracking does not copy every file

Large datasets and model weights normally live in object storage or an artifact repository. A tracking system records stable identifier, digest, and location. The record must locate the right object and detect silent replacement. `model.pkl` alone is insufficient; a content digest, version ID, or immutable URI is stronger evidence.

For example, MLflow Tracking organizes runs in experiments and records parameters, metrics, tags, and artifacts. It stores evidence, but it cannot automatically prove data is correct or an experiment design sound. “Registered” does not replace review.

## Three strengths of reproducibility

1. **Rerunnable** — inputs and environment are available and the process can run again.
2. **Statistically reproducible** — after accounting for randomness, core metrics fall in an expected range.
3. **Bitwise identical** — output bytes match exactly, requiring tighter control of algorithms, hardware, and dependencies.

GPU operators, parallel order, and hardware differences can introduce nondeterminism. State the strength required by the task. Most promotion decisions care more about statistical reproducibility and stable conclusions than blindly pursuing bitwise equality.

## Build a run record from scratch

For a spam classifier:

1. generate snapshot IDs for raw data and labels;
2. fix the split rule and record the seed to prevent train/test overlap;
3. record the Git commit and explicitly mark uncommitted worktree changes;
4. save parameters and environment dependencies;
5. report both overall accuracy and critical-slice recall, such as recall by language;
6. save model, preprocessor, input fields, and prediction-output definition;
7. mark the run as exploratory, candidate, or rejected to avoid misuse.

## Common mistakes and debugging

- **Only keeping the best metric** — lost failed experiments cause repeated mistakes and selection bias.
- **Mutable data path** — `data/latest.csv` is overwritten later. Use immutable snapshots or content digests.
- **Code commit is traceable but environment is not** — a dependency upgrade blocks reproduction. Preserve a lock file or image digest.
- **A seed exists but results still differ** — inspect multi-process behavior, GPU nondeterminism, and data-loading order; record remaining differences.
- **Treating a tracking platform as quality assurance** — the platform records; leakage and wrong metrics still need tests and review.

## Exercise and self-check

Write a problem contract for an analysis you have done, then design a run checklist covering all seven categories. Is an input the same when the data snapshot matches but labels were revised? Does the same Git commit prove identical training code when a worktree is dirty? When is bitwise identity worth its additional cost?

## Next step

Experiment tracking makes a conclusion locatable, reviewable, and comparable. Continue with [[mlops/foundations-and-lifecycle/02-data-features-and-training-pipelines|Data, Features, and Training Pipelines]] to produce this evidence automatically.

## References

- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) — checked 2026-07-14.
- [MLflow Model Registry workflow](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/) — checked 2026-07-14.
