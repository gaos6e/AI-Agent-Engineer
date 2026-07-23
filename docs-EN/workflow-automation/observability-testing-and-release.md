---
title: "Observability, Testing, and Release"
tags: [ workflow-automation, observability, testing, runbook ]
aliases: [ Workflow Testing and Operations ]
source_checked: 2026-07-22
lang: en
translation_key: 工作流自动化/07-可观测性、测试与发布.md
translation_source_hash: 06de05f7b83fd154ef72ff35b4b939ddfa23677f301ba8e78ca54aa381193bc9
translation_route: zh-CN/工作流自动化/07-可观测性、测试与发布
translation_default_route: zh-CN/工作流自动化/07-可观测性、测试与发布
---

# Observability, Testing, and Release

## Goal

Make one instance traceable, systemic degradation measurable, and failure paths reproducible; operate workflows safely through versioned release and a runbook.

## Three kinds of observability signal

- **Events/logs** answer “what happened to this instance?” Record transitions, step, attempt, error code, and acting subject.
- **Metrics** answer “is the system degrading?” Examples include queue age, success rate, compensation rate, tail latency, and cost.
- **Traces** answer “where was time spent and across which services?” Context propagation correlates trigger, message, step, API, LLM, and tool call.

OpenTelemetry is a vendor-neutral framework for generating, collecting, and exporting traces, metrics, and logs. The Semantic Conventions page is currently 1.43.0; its messaging-spans page was still marked Development on 2026-07-22. Pin and check stability before adoption; do not turn a draft field into a permanent contract. For async messaging, conventions use producer/consumer context propagation and span links. One trace is not necessarily a reliable parent-child chain, and batching must not force one parent.

## Event fields and privacy

Record correlatable fields in logs; only low-cardinality dimensions belong in metric labels:

`workflow.name`, `workflow.version`, `instance_id`, `step`, `attempt_id`, `operation_id`, `state_from/to`, `event_id`, `trace_id`, `error.code`, `duration`, `receipt_id`, `outcome.status`, `result_fingerprint`.

Do not log the full order, prompt, model response, secret, or tool parameters by default. High-cardinality values such as every user ID, instance ID, or full `operation_id` make poor metric labels because cost and query stability suffer; retain them in logs and correlate through controlled queries.

### Correlation is not trusted identity

`trace_id`, `traceparent`, message metadata, and a front-end tenant field are for correlation/diagnosis, never authorization input. After ingress verification, server-side code writes actor, authorization scope, policy version, and instance/resource relationship to controlled audit events; execution still checks current authorization. This retains cross-system causality without allowing forgeable observability values to cross a permission boundary.

## Essential metrics

| Dimension | Example metric | What it reveals |
| --- | --- | --- |
| Ingress | Trigger rate; deduplication/conflict rate | Upstream duplication or protocol issue |
| Queueing | Queue length; oldest-message age | Insufficient consumer capacity |
| Step | Success rate; attempts; error classification | Dependency or version regression |
| Recovery | Lease takeover; unknown-outcome reconciliation | Worker/network fault |
| Compensation | Trigger/failure rate; human backlog | Business consistency risk |
| Approval | Wait time; expiry/rejection rate | Human bottleneck and policy issue |
| End-to-end | p50/p95/p99 duration; deadline violation | User experience and tail latency |
| LLM | Task quality; invalid structure; tokens/cost | Model or prompt regression |

Alerts need a runbook and owner. A single error healed by automatic retry can be informational; exhausted retries, compensation failure, backlog age, and quality-gate degradation are operational alerts.

## Testing pyramid

1. Unit-test pure functions such as schemas, conditions, and idempotency keys.
2. Staticaly validate duplicate DAG names, unknown dependencies, cycles, and handler registration.
3. Run producer/consumer contract tests with old-version fixtures.
4. Integrate a step with mocked external dependencies.
5. Use virtual time for schedules, backoff, waits, and approval expiry.
6. Inject duplicate event, timeout, crash window, late result, and compensation failure.
7. Test ingress security: forged/expired signature, replay, same identity/different payload, revoked actor, and unauthorized resource.
8. Recover/replay compatible state from real redacted history.
9. Run end-to-end and capacity tests; give LLM nodes a fixed evaluation set.

Passing all happy paths does not prove reliability. The most valuable cases are often “crash after side-effect commit,” “same key with different parameters,” “old approval used against new state,” and “compensation permanently fails.”

## Release strategy

Version workflow definitions, handlers, schemas, prompts, and model configuration. A new definition must not overwrite in-flight instances unconditionally:

- new instances use the new version;
- old instances retain old workers or recover through tested compatible code;
- migrations generate auditable migration events;
- validate in shadow, then canary a small number of new instances; and
- use error rate, backlog, compensation rate, task quality, and cost as rollback gates.

Rolling back code does not undo payment, notification, or publication already made. The release plan needs reconciliation and compensation paths for external side effects.

## Minimum secure-deployment bar

- Workflow definitions originate only from reviewed sources; CI validates schemas, links, tests, and dependencies.
- Workers use non-administrator service identities and least privilege.
- Secrets come from secure storage; logs and checkpoints receive sensitive-field checks.
- Server-side controls enforce network-egress, tool, and target-resource allowlists.
- Definitions, containers/packages, and migration scripts are traceable to a version.
- Approval/manual operations have verified identity, reason, and risk-appropriate audit evidence; ordinary logs do not automatically prove non-repudiation.

## Windows 11 / PowerShell 7 runbook template

```powershell
# 1. Enter the project and verify Python. Confirm environment before mistaking deployment failure for workflow logic.
Set-Location -LiteralPath 'D:\path\to\workflow' # Replace with your workflow project's absolute path; -LiteralPath never treats wildcards as patterns.
python --version # Record the actual interpreter version so release validation can be reproduced.

# 2. Validate definition and tests first; -B avoids pyc. Prove static contracts and offline behavior before release.
python -B .\examples\workflow_engine.py --validate # Validate DAG/contracts only; do not trigger real business work.
python -B -m unittest discover -s .\examples -p 'test_*.py' -v # Discover and run all example regression tests verbosely.

# 3. Inspect current definition hash and intended change without printing secrets.
Get-FileHash -Algorithm SHA256 .\examples\workflow.json # Record the definition digest for precise canary and rollback comparison.

# 4. After canary, inspect queue age, failure classifications, and compensation/approval backlog.
# 5. On rollback gate, stop new triggers and drain or pin old instance versions. Rollback is controlled state migration, not deletion of historical runs.
```

On Linux, place equivalent steps in CI and controlled deployment scripts. Also check systemd/container stop grace, read-only filesystem, non-root user, health checks, and signal handling.

## Failure runbook

| Alert | Confirm first | Safe action | Prohibited action |
| --- | --- | --- | --- |
| Queue age rising | Arrival rate, consumption rate, dependency rate limit | Reduce ingress, scale, defer low priority | Infinite retry increase |
| Duplicate side effect | Idempotency table; key/parameter hash | Pause the step and reconcile | Delete state and rerun directly |
| Compensation failure | Main outcome; compensation attempt | Human queue and retain evidence | Force status to completed |
| High new-version error rate | Slice by definition version | Stop new instances on new version | Auto-follow `latest` for old instances |
| Approval backlog | Expiry rate, owner, risk class | Escalate/reassign/safely expire | Bulk automatic approval |

## Exercise and self-check

List at least 15 order-workflow tests covering duplicate trigger, same key/different amount, competing claim, approval expiry, late result, main-action crash window, compensation failure, old checkpoint, and new definition. Then write a one-page runbook for “payment-step exception.”

Self-check:

1. What do logs, metrics, and traces each answer?
2. Why is arbitrary instance ID unsuitable as a metric label?
3. Why cannot a definition rollback undo external side effects?
4. What historical compatibility test is most valuable before a new worker release?

## Next

Continue with [[workflow-automation/project-offline-dag-workflow|Project: offline DAG workflow]].

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Semantic Conventions 1.43.0](https://opentelemetry.io/docs/specs/semconv/)
- [OpenTelemetry: Messaging Spans](https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/) (still marked Development)
- [NIST SP 800-218: SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
- [Temporal Platform Documentation](https://docs.temporal.io/)
