---
title: "Gateways, Quotas, and Resilience"
tags:
  - llmops
  - gateway
aliases:
  - LLM Gateway
source_checked: 2026-07-14
lang: en
translation_key: LLMOps/02-生产工程/02-网关、配额与弹性.md
translation_source_hash: 78081eb00846275537e7dbaad653ba3a4176b4b9eab4ff59807bc90a145a7ffa
translation_route: zh-CN/LLMOps/02-生产工程/02-网关、配额与弹性
translation_default_route: zh-CN/LLMOps/02-生产工程/02-网关、配额与弹性
---

# Gateways, Quotas, and Resilience

## Goal

Understand an LLM gateway's responsibilities and combine authentication, rate limiting, concurrency, timeout, retry, routing, fallback, and cost attribution correctly.

## What a gateway solves

When every product service integrates providers directly, retry, logging, rate limit, and secret management become scattered and inconsistent. An LLM gateway is a controlled call entry that can centralize:

- application authentication and least privilege;
- quota by user, team, project, and model;
- request/token rate limits and concurrency ceiling;
- timeout, retry, circuit breaking, and fallback;
- provider selection and versioned routing;
- structured `request_id`/`trace_id`, usage, cost, and error-class recording.

A gateway must not silently rewrite prompts or replace models. Any routing rule that changes behavior needs a version and belongs in the release manifest and Trace.

## Different kinds of limit

| Mechanism | What it limits | Purpose |
| --- | --- | --- |
| Request rate | Requests per time window | Prevent burst shock |
| Token rate | Input/output token usage | Control compute load and cost |
| Concurrency ceiling | In-flight requests | Protect threads, connections, and downstream |
| Queue ceiling | Waiting request count or wait duration | Prevent unbounded user waiting |
| Cost budget | Estimated project/user spend in a period | Prevent accidental cost expansion |

Provider rate-limit headers and quota are external constraints. An internal gateway also reserves capacity by business priority. Do not assign a provider's whole quota to one batch task and leave interactive requests unserviceable.

## Timeout is a budget

Decrease a total budget along the call chain:

```text
User total budget: 12 s
├─ Retrieval: 2 s
├─ Model: 8 s
├─ Tool: 1 s
└─ Network jitter and cleanup: 1 s
```

These numbers illustrate a method, not a universal recommendation. If every layer waits 12 seconds independently, final latency exceeds the user budget. On timeout, cancel cancellable downstream work where possible so token generation does not continue after the user leaves.

## Conditions for retry

Retry only transient errors that are safe to retry, such as some rate limits, timeouts, and server errors. Authentication failure, parameter error, and policy denial do not become correct by retrying. Use exponential backoff, randomized jitter, a total-attempt limit, and put every attempt in the same Trace.

Side effects need special attention. One agent request may have created a ticket even if its response was lost in the network. Retrying a whole chain can duplicate the tool action. Side-effecting tools require idempotency key, transaction, or check-before-write policy; a retryable LLM call does not make an agent task retryable.

## Routing, degradation, and fallback

Routing conditions can include task risk, data region, latency budget, and approved model set. Before fallback, answer:

- Has the alternative passed the same task regression suite?
- Does it support the same structured output and tool schema?
- May the data be sent to that provider or region?
- Does the user need a slower complete answer, or accept an explicit functional degradation?

Fallback is not merely “catch an exception and switch models.” It is product behavior requiring evaluation and versioning.

## Minimum gateway log fields

Prefer metadata: `request_id`, `trace_id`, release ID, actual provider/model version, attempt count, error class, latency, input/output tokens, cache usage, cost attribution, and routing-policy version. Do not log keys, Authorization headers, or raw sensitive prompts by default.

## Exercise and self-check

Design a quota plan serving online support and nightly batch summaries, with priority, concurrency, cost, and queue boundary. Why is requests-per-minute alone insufficient to control load? Why cancel downstream generation after upstream timeout? Why does a retryable model API not imply a retryable agent task?

## Next step

The gateway removes call policy from product code but is therefore a critical change surface. Continue with [[llmops/production-engineering/03-caching-latency-and-cost|Caching, Latency, and Cost]] to turn call evidence into optimization decisions.

## References

- [OpenAI Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) — accessed 2026-07-14; provider quotas, rate-limit responses, and retry requirements can change.
- [OpenAI Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices) — accessed 2026-07-14.
- [OpenAI API backwards compatibility](https://developers.openai.com/api/reference/overview#backwards-compatibility) — accessed 2026-07-14; boundaries for API/model behavior changes.
