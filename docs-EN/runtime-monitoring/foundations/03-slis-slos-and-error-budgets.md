---
title: "SLIs, SLOs, and Error Budgets"
tags:
  - observability
  - reliability
aliases:
  - Service Level Objectives
source_checked: 2026-07-22
lang: en
translation_key: 运行监控/01-可观测性基础/03-SLI、SLO与错误预算.md
translation_source_hash: 532b7e3dc1ee814435f192f0c31515aef3cf4d9b34b57ee4eb8ce9a119eb6590
translation_route: zh-CN/运行监控/01-可观测性基础/03-SLI、SLO与错误预算
translation_default_route: zh-CN/运行监控/01-可观测性基础/03-SLI、SLO与错误预算
---

# SLIs, SLOs, and Error Budgets

## Goal

Define computable SLIs, windowed SLOs, and error budgets from user expectations so that they can guide release and reliability tradeoffs.

## Three concepts

- **SLI (Service Level Indicator)** — a quantitative measure of service behavior, such as “the proportion of eligible requests that return a usable answer within two seconds.”
- **SLO (Service Level Objective)** — a target for an SLI over a specified window, such as “99% over 28 days.” These values illustrate syntax only; they are not course-wide targets.
- **SLA (Service Level Agreement)** — an agreement with users or customers that has defined consequences. Do not confuse it with an internal SLO.

For an event-based SLI, the smallest formula is:

$$
SLI = \frac{\text{number of good events}}{\text{total number of eligible events}}
$$

The formula is easy; the meaning of “good” and “eligible” is hard. The SLI specification must say how it counts user cancellations, invalid upstream input, a correct safety-policy refusal, and a local timeout.

## Work backward from the user task

Ask “when does the user consider the task successful?” before choosing a computable proxy. An Agent application may need several complementary SLIs:

| User expectation | Possible SLI | Limitation |
| --- | --- | --- |
| It is accessible | Proportion of eligible requests returning a non-5xx, non-timeout result | HTTP 200 does not prove the answer is correct |
| Waiting is acceptable | First-visible-token and completion-latency distribution for valid requests | A fast first token in a stream can still have a slow total completion |
| The task is useful | Task-success rate or human-handoff rate among ground-truth samples | Labels may arrive days later and may have selection bias |
| It does not perform dangerous actions | Rate of audited unauthorized or high-loss events | “Not detected” is not “did not occur” |

Compute important slices separately so a high-volume, low-risk task cannot mask a small, high-risk one. Do not create unbounded slices: each needs a user loss, release decision, or feasible action behind it.

## Windows and error budgets

If an SLO target is $T$, the allowed bad-event share in its window is $1-T$. It is not permission to intentionally harm users. It is a management tool for measuring reliability headroom and deciding whether high-risk releases should pause.

Common windows:

- **Rolling window** — at each time, inspect the prior N days. It is sensitive to recent experience but more complex to calculate and explain.
- **Calendar window** — resets by month or week. It is easy to settle, but the same incident can be treated differently at a boundary.

Write the window start/end, time zone, data delay, and recomputation rules into the specification. In particular, never quietly move the observation endpoint to the timestamp of the last event received: a Collector can freshen old data successfully, so both business-event age and export age should be visible.

## Burn-rate intuition and alerts

An **error-budget burn rate** compares the current bad-event rate with the rate that would consume the budget evenly. A high rate means the budget will be consumed quickly if the trend continues. Production alerts can combine a short window (fast detection) and a long window (filter transient noise), but thresholds must fit this system's SLO, traffic, and on-call capability—not be copied from a tutorial.

For target $T$ and observed bad-event proportion $B$, this course uses:

$$
\text{burn rate} = \frac{B}{1-T}
$$

`1x` means consuming the allowed budget at its even rate; `5x` means the bad-event proportion is five times the allowed value. A short window detects a burst quickly, while a long one confirms sustained impact; paging only when both cross thresholds is a common noise-reduction approach. The Google SRE Workbook describes multi-window, multi-burn-rate patterns, but its values are not universal templates. This course's project uses explicitly labeled local teaching thresholds.

Burn rate is a **current consumption rate**, not a “remaining error-budget percentage.” The latter requires the allowed and consumed budget over the full SLO compliance window, including population and exclusion rules. A five- or sixty-minute incident window cannot calculate it honestly. Dashboards and release policy should name and source the two quantities separately.

## A reviewable SLI specification

```yaml
name: interactive_answer_within_budget # Reference this SLI by a stable name so dashboards and policies do not create their own names.
population: authenticated interactive production requests with valid input contracts # Define the denominator precisely; do not mix invalid input or unauthenticated traffic into it.
good_event: returns a non-technical-error result before the user's deadline # Define the numerator; a separate quality SLI still covers business success.
exclusions: user-initiated cancellation (must be distinguishable) # Exclude only when cancellation causes can be distinguished reliably.
source: edge request events # Name the raw event source so it can be audited and replayed.
window: rolling 28d # Fix the rolling observation window; do not compare different definitions directly.
dimensions: [release, task_type] # Retain release and task slices so an overall average does not hide a local regression.
owner: reliability-team # Name the team responsible for the definition, alerts, and improvement actions.
```

This is a structural example, not a configuration for a specific monitoring product. A user-initiated cancellation may be excluded only when the data reliably distinguishes it; otherwise a system timeout mislabeled as a cancellation would falsely inflate the SLI.

## Common mistakes

- **Deriving user expectations from existing metrics** — measurable CPU is not necessarily the behavior users care about.
- **Using 100% as a default target** — cost, innovation, and dependency boundaries often make that unrealistic. High-risk safety events need a separate zero-tolerance control, not inclusion in an ordinary availability budget.
- **Treating unlabeled samples as quality successes** — they are unknown; report label coverage too.
- **Continuing a historical line after changing the SLI definition** — values from different definitions are not directly comparable.

## Exercise and self-check

For “automatically classify tickets and send high-risk tickets to a person,” design availability, latency, and task-quality SLIs. For each, state the total events, good events, exclusions, window, data source, and slices. Answer:

1. Why can HTTP 200 indicate technical availability but not replace task quality?
2. Why is a success rate over labeled samples alone insufficient?
3. When the error budget is nearly exhausted, which releases may continue and which should pause? Who should approve that policy?

## Summary and next step

An SLI turns user expectations into a counting contract; an SLO and error budget turn it into action boundaries. AI applications must place technical signals alongside quality, safety, and cost; continue with [[runtime-monitoring/production-monitoring/03-quality-safety-and-cost-signals|Quality, Safety, and Cost Signals]].

## References

- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — checked 2026-07-21.
- [Google SRE Workbook: Implementing SLOs](https://sre.google/workbook/implementing-slos/) — checked 2026-07-21.
- [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) — checked 2026-07-21; redesign thresholds for the local SLO.
- [OpenTelemetry Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) — checked 2026-07-21.

