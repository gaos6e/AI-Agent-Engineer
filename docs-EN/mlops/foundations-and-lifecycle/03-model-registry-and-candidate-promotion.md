---
title: "Model Registry and Candidate Promotion"
tags:
  - mlops
  - model-registry
aliases:
  - Model Registry
source_checked: 2026-07-14
lang: en
translation_key: MLOps/01-基础与生命周期/03-模型注册与候选晋级.md
translation_source_hash: dc60d0859c91bbe713e5f3522b9abe889b09aeaf8a3eb7b86d810d0146cdc708
translation_route: zh-CN/MLOps/01-基础与生命周期/03-模型注册与候选晋级
translation_default_route: zh-CN/MLOps/01-基础与生命周期/03-模型注册与候选晋级
---

# Model Registry and Candidate Promotion

## Goal

Understand model versions, aliases, signatures, and promotion evidence. Avoid mistaking “uploaded a model” for “safe to release.”

## What a registry manages

A **model registry** is a controlled catalog of model artifacts and their metadata. A registered model can have several versions that cannot be confused, and each version should relate to:

- source run and training-data snapshot;
- model artifact and content digest;
- dependency environment and preprocessor;
- input/output signature;
- offline evaluation report and applicability boundary;
- creator, approval, risk note, and current status.

A registry answers “what is it, where did it come from, and how is it used?” It does not automatically answer “is it correct?” An incorrect model can be perfectly registered.

## Versions and aliases

A **version** points to a fixed artifact. An **alias** is a movable, human-readable pointer such as `candidate` or `champion`. Before a release system reads an alias, resolve and record its actual version and digest so an alias change cannot silently alter a running task.

Current MLflow documentation recommends model aliases, tags, or separate registered models by environment for lifecycle management; old fixed Stages are deprecated. UIs will change, but “immutable version plus auditable pointer” is more stable.

## Input/output signature

A model signature describes its accepted and returned data shapes, types, and fields:

```text
Input: age: integer, region: string, events_30d: integer
Output: risk_score: number in [0, 1]
```

A signature catches missing fields and type errors but cannot prove semantics. If `events_30d` changes from “events in the last 30 days” to “the latest 30 events,” type stays the same; a data contract and semantic version are still required.

## Candidate-to-release evidence

Candidate promotion needs four layers:

1. **Integrity** — data, code, environment, signature, and artifact are traceable.
2. **Correctness** — unit tests, data tests, and inference smoke tests pass.
3. **Effectiveness** — a frozen evaluation set and critical slices meet project-defined gates.
4. **Operability** — latency, resource, dependencies, rollback artifact, and owner are ready.

Do not copy thresholds from a tutorial. Allowed regression for a critical slice and latency budget come from business loss, risk tolerance, baseline variance, and measurement uncertainty, and belong in a versioned policy.

## Champion and challenger do not mean new automatically replaces old

- **Champion** — the current trusted reference version.
- **Challenger** — a candidate awaiting offline or online comparison.

A challenger can be rejected because a critical slice degrades even if the overall metric improves. For tasks with delayed labels, run shadow traffic first to collect comparison evidence without affecting a user.

## Common mistakes

- A version name contains `latest` but is never resolved to a fixed digest.
- Model and preprocessor update separately, misaligning input semantics.
- Only overall average metrics are considered, ignoring high-risk groups.
- Registry status substitutes for independent approval and evaluation evidence.
- Old artifact is deleted after an alias switch, making rollback nominal only.

## Exercise and self-check

Design a registry entry for a house-price model, including signature, training snapshot, critical slices, and rollback data. May a candidate with lower RMSE but much worse error in one city promote directly? Is a `champion` alias enough for an audit record, or what else must be preserved? Why cannot a registry replace artifact-repository integrity checks?

## Next step

A registry supplies identity and lineage; a promotion gate supplies decision evidence. Automate those checks next in [[mlops/production-engineering/04-ci-cd-and-automated-quality-gates|CI, CD, and Automated Quality Gates]].

## References

- [MLflow Model Registry workflow](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/) — checked 2026-07-14; the page says Model Stages are deprecated since MLflow 2.9.0.
- [MLflow Model Deployment](https://mlflow.org/docs/latest/ml/deployment) — checked 2026-07-14.
