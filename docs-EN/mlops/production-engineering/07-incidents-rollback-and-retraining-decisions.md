---
title: "Incidents, Rollback, and Retraining Decisions"
tags:
  - mlops
  - incident-response
aliases:
  - Model Incident Handling
source_checked: 2026-07-14
lang: en
translation_key: MLOps/02-生产工程/07-故障、回滚与再训练决策.md
translation_source_hash: 5cf4537b96f407b647b88b2af93ecdcb3cba6245d558411b33e7d14bab7a452b
translation_route: zh-CN/MLOps/02-生产工程/07-故障、回滚与再训练决策
translation_default_route: zh-CN/MLOps/02-生产工程/07-故障、回滚与再训练决策
---

# Incidents, Rollback, and Retraining Decisions

## Goal

When production is abnormal, contain damage and preserve evidence before choosing rollback, data repair, rule repair, or retraining.

## Triage before training

“The metric got worse” can have different causes:

| Observation | Possible cause | First action |
| --- | --- | --- |
| Many 5xx responses or timeouts | Service, dependency, resource, configuration | Rate limit, degrade, or roll back service |
| Schema or missingness anomaly | Upstream data or feature pipeline | Isolate bad data and restore contract |
| Only a new version degrades | Model, preprocessor, or configuration | Stop rollout and roll back the complete release unit |
| Several versions degrade together | External environment, label definition, or shared dependency | Broaden investigation; do not blindly roll back one model |
| Drift but labeled quality is stable | True input change while model remains applicable | Keep observing; no automatic retraining needed |
| Conditional relation changed with enough new labels | Model is stale | Evaluate retraining or redesign |

Retraining is not a universal repair. If the root cause is a unit error, retraining on bad data creates a harder-to-detect failure.

## Minimal incident-response flow

1. **Declare and classify** — record start time, impact, owner, and communication channel.
2. **Contain** — stop expansion, switch to an older version, disable a high-risk feature, or enter human handling.
3. **Preserve evidence** — freeze release, model, configuration, feature version, and redacted request samples.
4. **Diagnose** — trace data → feature → model → service → downstream decision.
5. **Recover** — validate an alternative path and monitoring before gradual recovery.
6. **Review** — write timeline, root cause, contributing factors, detection gap, and verifiable improvements.

NIST SP 800-61 Rev. 3 places incident response in organizational risk management. In practice cover preparation, detection, response, and recovery, not only a post-incident report.

## Rollback criteria

Fast rollback fits when impact clearly comes from the new release, an old version remains compatible and lower risk, and artifact and data contract are available. Be more careful when:

- old and new versions share damaged upstream data;
- database or feature state changed irreversibly;
- the old version has a known security issue;
- the environment changed so much that the old model is worse.

Rehearse rollback regularly rather than executing it for the first time during an incident.

## When to retrain

Before retraining, confirm at least:

- the new label definition is stable and label-coverage bias is acceptable;
- data change relates to target performance rather than mere correlated drift;
- training pipeline, baseline, and slice evaluation are still applicable;
- new data will not indefinitely amplify bad decisions made during the incident;
- the new candidate still passes a complete quality gate and progressive release.

If task objective, label, or input meaning changed, redesigning the problem may be needed rather than extending the old training script.

## Blameless review does not erase responsibility boundaries

Focus on how the system allowed the failure instead of stopping at “an operator was careless.” Still name decision owner, approval responsibility, and due condition for remediation. A good action item is verifiable — “add a production contract test for units and block before Canary” — not “be more careful.”

## Exercise and self-check

Scenario: after a new-model release, rejection rate rises in one region; input missingness also rises and overall latency is normal. Write the first 30 minutes of containment and investigation. When do you roll back a model, and when repair data first? Which evidence must be frozen? Which facts support retraining, and which remain only clues?

## Next step

Incident response protects users, preserves evidence, restores service, then improves the model. Continue with [[mlops/production-engineering/08-platform-security-and-governance|Platform Security and Governance]] to put identity, supply chain, audit, and accountability across the lifecycle.

## References

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — published 2025-04; checked 2026-07-14.
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — checked 2026-07-14.
