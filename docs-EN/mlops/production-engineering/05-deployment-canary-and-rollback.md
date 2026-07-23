---
title: "Deployment, Canary, and Rollback"
tags:
  - mlops
  - deployment
aliases:
  - Progressive Model Release
source_checked: 2026-07-14
lang: en
translation_key: MLOps/02-生产工程/05-部署、Canary与回滚.md
translation_source_hash: 5ace53910154ede04a8280ad592c9f80d7338316989f63d39f5f6f140e8727dc
translation_route: zh-CN/MLOps/02-生产工程/05-部署、Canary与回滚
translation_default_route: zh-CN/MLOps/02-生产工程/05-部署、Canary与回滚
---

# Deployment, Canary, and Rollback

## Goal

Choose deployment form from task shape, then control change risk with shadow, Canary, blue-green, and rollback.

## Choose the service form first

| Form | Suitable setting | Principal risk |
| --- | --- | --- |
| Batch | Hourly or daily scoring where waiting is acceptable | Snapshot mismatch, interrupted jobs, duplicate writes |
| Online request | A prediction is needed immediately after user action | Tail latency, traffic spikes, dependency failure |
| Streaming | Continuous events with low-latency update | Ordering, duplicate events, state recovery |
| Edge or device | Network-limited, privacy-sensitive, or real-time work | Device variation, difficult upgrade, resource limits |

“Deploy a REST API” is not the default answer. When batch meets the need, it is normally easier to reproduce and roll back.

## Four release strategies

### Rolling update

Replace old instances with new ones gradually. It fits routine compatible updates with controllable risk. Old and new versions may coexist briefly, so the input/output contract must be compatible.

### Shadow run

Copy real requests to the candidate model but never return its result to users. Shadow compares latency and prediction distribution, but cannot fully prove a candidate's business effect in the real decision loop.

### Canary

Send a candidate a limited, identifiable slice of real traffic, observe it, then expand. Percentage and observation duration derive from traffic volume, risk, and metric stability; never copy tutorial numbers. Kubernetes examples use separate stable and Canary Deployments with labels for parallel operation; finer traffic control often needs a gateway or service mesh.

### Blue-green

Maintain two switchable environments: one serving and one awaiting validation. Switching and fallback are fast but resource cost is higher; database and feature-state compatibility still need separate handling.

## Health checks do not prove model correctness

- **Liveness** — is the process alive?
- **Readiness** — has the instance loaded the artifact and can it receive requests?
- **Prediction smoke test** — does representative input produce output matching the signature?
- **Quality observation** — are user SLIs, model slices, drift, and business outcomes normal?

HTTP 200 says a request was processed, not that a prediction is useful.

## Roll back the full release unit

A rollback inventory includes:

- model and preprocessor version;
- feature definition and online-computation version;
- service code and dependency environment;
- input/output schema;
- configuration, policy, and resource specification;
- compatibility plan for database or state changes.

Rolling back only a model while retaining incompatible new feature code preserves the failure. Old artifacts must remain readable and have their loading rehearsed periodically; otherwise “rollback supported” is only a documentation claim.

## Release decision table

| Observation | Possible action |
| --- | --- |
| Technical error or clear tail-latency degradation | Stop expanding; roll back immediately if needed |
| Overall stability but critical-slice degradation | Keep small traffic and investigate; normally do not expand |
| Input distribution changed but no quality label yet | Collect more evidence; do not assert model decline |
| Candidate looks normal but monitoring lacks data | Pause expansion and restore observability first |

## Exercise and self-check

Choose service form and release strategy for “generate a customer-churn list nightly” and “intercept a real-time payment,” and explain the difference. Why cannot shadow measure all user-behavior effect? Does a silent Canary automatically justify expansion? What else must be confirmed? Why can application rollback fail when database schema is not backward compatible?

## Next step

Progressive release limits blast radius; monitoring decides whether it can continue. Continue with [[mlops/production-engineering/06-model-monitoring-drift-and-feedback|Model Monitoring, Drift, and Feedback]].

## References

- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — checked 2026-07-14.
- [Kubernetes Canary Deployments](https://kubernetes.io/docs/concepts/workloads/management/#canary-deployments) — checked 2026-07-14.
- [KServe documentation](https://kserve.github.io/website/) — checked 2026-07-14; a Kubernetes model-serving option.
- [MLflow Model Deployment](https://mlflow.org/docs/latest/ml/deployment) — checked 2026-07-14.
