---
title: "Scheduling, Timeouts, Retries, and Backpressure"
tags: [ workflow-automation, scheduling, retries, backpressure ]
aliases: [ Workflow Scheduling ]
source_checked: 2026-07-22
lang: en
translation_key: 工作流自动化/04-调度、超时、重试与背压.md
translation_source_hash: 2314d653b2285d2b713a59badd45523f95fb4ff1ef0de07d21733c5fbc9555b1
translation_route: zh-CN/工作流自动化/04-调度、超时、重试与背压
translation_default_route: zh-CN/工作流自动化/04-调度、超时、重试与背压
---

# Scheduling, Timeouts, Retries, and Backpressure

## Goal

Define complete time semantics for scheduled triggers and external calls, then prevent duplicate execution and failure amplification with timeouts, finite retries, retry budgets, rate limits, and backpressure.

## Time semantics must be complete

“Run every day at 09:00” omits at least:

- a time zone, for example `Asia/Shanghai`;
- handling for duplicated or missing local time under daylight saving time;
- whether three missed runs during downtime catch up individually, coalesce once, or skip;
- whether a previous run permits overlap, is skipped, or is awaited serially; and
- allowable delay and the deadline beyond which the result has no business value.

RFC 3339 represents a timestamp related to UTC. It is suitable for an instant, but cannot alone express calendar rules such as “09:00 on every regional business day”; scheduling also needs an IANA time-zone name and a business calendar.

Use a structured schedule-deduplication key `(schedule_id, logical_fire_time)`. Do not use the time a worker happened to wake, or an unescaped delimiter-joined string: catch-up, late firing, or field characters can then be mistaken for new work. Keep the logical period's `operation_id` distinct from every claim/delivery `attempt_id`: catch-up, broker redelivery, and worker takeover can increase attempts without redefining the same business period.

## Five common timeouts

1. **Queue-wait timeout:** work has not yet been claimed by a worker.
2. **Single-attempt timeout:** maximum wait for one network/tool call.
3. **Step total timeout:** all attempts and backoff combined.
4. **External-event/approval waiting limit:** expiry routes to rejection, escalation, or human handling.
5. **Workflow total deadline:** after this, the whole result has lost business value.

A timeout means the caller stopped waiting; it does not prove downstream did not finish. After a payment timeout, query the idempotency key before deciding on retry. Charging again directly expands the unknown-result window.

## Retry only potentially recoverable errors

| Error | Usual strategy | Reason |
| --- | --- | --- |
| Short network interruption or busy service | Finite retry | Environment can recover |
| 429/503 with service instruction | Honor `Retry-After`, then retry | Downstream supplies its recovery pace |
| Invalid schema | Do not retry | Identical input will not repair itself |
| 401/403 | Usually do not retry | Credentials/authorization need intervention |
| TLS certificate/hostname failure or invalid inbound signature | Do not retry; investigate configuration/security | Retrying cannot repair identity or trust chain |
| Insufficient inventory or approval rejection | Business termination or compensation | Not a technical fault |
| Timeout with unknown downstream status | Query/reconcile first | Blind retry can duplicate a side effect |

An engineering default is exponential backoff:

$$
d_n = \min(d_{max}, d_0 \times 2^{n-1})
$$

Add random jitter so many instances do not retry synchronously. Microsoft's transient-fault guidance also recommends exponential backoff with jitter for background work, setting a timeout per call, limiting total attempts/duration, considering `Retry-After`, and maintaining a global retry budget.

With initial 2 seconds and cap 30 seconds, base waits after failures are 2, 4, 8, 16, and 30 seconds. The chosen jitter shape must be specified and tested; “exponential backoff” alone is incomplete without maximum attempts and total deadline.

## Calculate multi-layer retry amplification

If an HTTP SDK retries three times, a step permits four attempts, and the whole workflow replays twice, worst-case downstream calls can be $3 \times 4 \times 2 = 24$, not four. Different layers can define “times” as total attempts or extra retries, so verify each product's definition.

Prefer one policy owner—the layer that knows business idempotency and deadline. Lower layers can retain short network recovery, but every layer must not independently retry forever.

First pass each retry through a safety gate: fail closed for authentication, authorization, signature, resource-version, or policy mismatch; query/reconcile first for unknown external state; schedule another attempt only for recoverable transport/capacity error while the same idempotent intent, total deadline, and retry budget remain valid. Never classify certificate error, expired approval, or invalid output schema as transient merely to improve nominal success rate.

## Backpressure and retry budget

Backpressure deliberately slows or rejects upstream when downstream cannot keep up; it is not continued accumulation. Typical controls are:

- concurrency caps per tenant, workflow, step, and external dependency;
- bounded queues and maximum wait;
- token buckets/rate limits and provider quotas;
- low-priority degradation, deferral, or dropping policy;
- dead-letter/human queues for exhausted work; and
- a service-wide retry budget that prevents a storm of individually small retries.

A queue smooths peaks but is not infinite buffering. When arrival rate exceeds processing rate continuously, backlog grows; monitor oldest-message age, not only length, and throttle or scale when capacity is insufficient.

## Scheduling resources for LLM nodes

LLM calls also consume token/request rate, context length, cost budget, concurrency, and provider-region capacity. Make those workflow resources:

- scheduler allocates tokens and cost budget;
- node reports structured rate-limit/timeout errors;
- model switch is a versioned routing policy, never a silent quality change; and
- fallback to a smaller model first proves output contract and evaluation gate remain satisfied.

## Common mistakes and diagnosis

- **Retry storm:** check jitter, total deadline, global budget, and `Retry-After`.
- **Duplicate scheduled job:** check logical fire time and overlap policy rather than process lock.
- **Work stays queued forever:** inspect oldest-message age, consumer throughput, and dead-letter count.
- **Duplicate charge after timeout:** reconcile downstream idempotency records and distinguish not executed from unknown result.
- **New queue delivery treated as new business period:** retain `logical_fire_time` and `operation_id`; only increment `attempt_id`.
- **High-priority work starves others:** set fair quotas or maximum-wait promotion.

## Exercise

Design a daily 09:00 report in the Shanghai time zone.

1. State logical fire time, three-day outage catch-up policy, and overlap policy.
2. Set attempt/step/workflow timeouts for API fetch, LLM summary, and email.
3. Classify errors as transient, permanent, business rejection, or unknown result.
4. Compute worst-case calls across layers and converge to an explainable cap.
5. Give alerts for queue age, retry budget, and provider quota.

## Self-check

1. Why cannot an attempt timeout prove downstream did not execute?
2. What does jitter solve, and why is a total deadline still needed?
3. Does stable queue length prove there is no backlog risk?
4. How does a retry budget differ from a single request's maximum attempts?

## Next

Continue with [[workflow-automation/durable-state-recovery-and-idempotency|Durable state, recovery, and idempotency]].

## References

- [RFC 3339](https://www.rfc-editor.org/info/rfc3339/) (updated by RFC 9557)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [Microsoft: Transient Fault Handling](https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults)
- [Microsoft: Retry Storm Antipattern](https://learn.microsoft.com/en-us/azure/architecture/antipatterns/retry-storm/)
- [Microsoft: Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)
