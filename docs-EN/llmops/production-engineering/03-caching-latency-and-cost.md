---
title: "Caching, Latency, and Cost"
tags:
  - llmops
  - performance
aliases:
  - LLM Caching and Cost Optimization
source_checked: 2026-07-14
lang: en
translation_key: LLMOps/02-生产工程/03-缓存、延迟与成本.md
translation_source_hash: 6252f4afee1838b417e9aed24569edb3f31b1a87a63a8670594039c43c62d901
translation_route: zh-CN/LLMOps/02-生产工程/03-缓存、延迟与成本
translation_default_route: zh-CN/LLMOps/02-生产工程/03-缓存、延迟与成本
---

# Caching, Latency, and Cost

## Goal

Use a measure-first, optimize-second method. Understand the hit conditions and risks of prefix caching, exact-answer caching, and semantic caching.

## Three goals are not the same

- **Latency** — how long a user waits; separate time to first byte/first token, completion time, and P95/P99 tail latency.
- **Throughput** — tasks completed per time unit; batching can increase it while making one user wait longer.
- **Cost** — more than token price: retrieval, tools, evaluation, storage, operations, and failed retries.

Define the user task and quality floor before optimizing. A cheaper model can reduce per-call API cost but raise end-to-end cost when it causes rework or human takeover.

## Decompose total latency with a Trace

```text
Total latency
= queue + gateway + retrieval + model first token
+ model generation + tool loop + post-processing + retry
```

This is a diagnostic decomposition, not a fixed formula for every architecture. Use a Trace to find the largest or most unstable component first. If waiting is dominated by one slow tool, shortening the prompt does not solve the issue.

## Three caches

### Prefix or provider prompt cache

It reuses intermediate computation for an identical input prefix, not normally a final answer. Put stable instructions/examples first and user-variable content later to improve generic hit opportunity. Minimum token count, price, retention time, and explicit cache parameters are dynamic provider details and must not be hardcoded from a tutorial.

### Exact-answer cache

Return a saved answer when normalized request is exactly the same. Its key includes every version that can alter output:

```text
hash(tenant + permission + normalized input + release_id
     + knowledge snapshot + language + safety policy)
```

Omitting tenant or permission can leak data across users; omitting knowledge snapshot can return stale rules indefinitely. A cache value must undergo the same safety handling as normal output.

### Semantic cache

Embed a request and reuse a prior answer when similarity is high enough. It turns lexical similarity into a business-interchangeability decision and is far riskier than a prefix cache. “How do I cancel an order?” and “How do I cancel an already shipped order?” may be vector-similar but governed by different rules. Validate it separately on a task-level regression suite, permission partition, knowledge expiry, and uncertain fallback.

## Cost ledger

For every task record input/cache read-write/output tokens, model/tool calls, retry count, billing-policy version, and project/user attribution. A price table has effective time or version; do not recompute historical requests at today's price and call that their actual historical cost.

Optimization order normally starts by removing valueless work: solve without a call, avoid duplicate retrieval, bound agent loops, and prevent retry storms. Only then shorten prompts, choose a smaller model, or batch. Return every change to the same evaluation suite.

## Common misconceptions

- **Look only at mean latency** — tail latency is often the real pain for many users.
- **Streaming reduces total time** — it mainly improves first-visible-token experience and may not shorten completion.
- **High cache-hit rate means success** — if hits are stale or cross-permission answers, the system merely fails faster.
- **Record full prompt to calculate cost** — token count and versions are usually enough; raw text needs an independent necessity case.

## Exercise and self-check

Design a cache key and invalidation rule for internal policy Q&A that updates weekly and has department-specific access. Why cannot a semantic-similarity threshold be copied from another project? Why does lower current model price not lower historical actual cost? Which Trace spans reveal a retry storm?

## Next step

Caching and routing jointly decide quality, cost, freshness, and privacy. Use [[llmops/production-engineering/04-traces-and-privacy-boundaries|Traces and Privacy Boundaries]] next to collect evidence that is detailed enough but not excessive.

## References

- [OpenAI Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) — accessed 2026-07-14; supported models, hit conditions, and pricing change.
- [OpenAI Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) — accessed 2026-07-14.
- [OpenAI Cost optimization](https://developers.openai.com/api/docs/guides/cost-optimization) — accessed 2026-07-14.
