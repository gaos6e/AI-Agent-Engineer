---
title: "Timeouts, Errors, Rate Limits, and Retries"
tags:
  - llm-api
  - retries
  - rate-limits
aliases:
  - LLM API Error Handling
source_checked: 2026-07-21
source_baseline:
  - RFC 9110 HTTP Semantics
  - OpenAI API errors and Rate limits guides
  - Anthropic API errors and Rate limits documentation
  - Google Gemini API troubleshooting and Rate limits documentation
  - openai-python 2.46.0 retry and timeout behavior
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/05-超时、错误、限流与重试.md
translation_source_hash: 488a306cae5700fc4ba8a1ed67df1c3ac1d9a73db1d2cd76c98c2b4f88a1bf70
translation_route: zh-CN/LLM-API集成/05-超时、错误、限流与重试
translation_default_route: zh-CN/LLM-API集成/05-超时、错误、限流与重试
---

# Timeouts, Errors, Rate Limits, and Retries

## Objectives

Classify errors as permanent, temporary, or unknown, and bound automatic retries with jitter, deadlines, and side-effect protection.

## Classify before deciding

- **Usually do not retry**: authentication failures, missing permission, invalid request/schema, context-limit violations, or an explicit content refusal. Fix configuration, permission, or input instead.
- **May retry**: broken connections, partial timeouts, rate limits, and temporary server failures. Prefer server `Retry-After` information or an explicit SDK policy.
- **Unknown**: a new error type, in-stream exception, or uncertain result state. Fail conservatively by default and retain the request ID; never treat unknown as success.

Specific status codes and error classes follow each provider's current documentation. Do not match error-message strings.

| Outcome evidence | Default decision | Precondition for automation |
| --- | --- | --- |
| 401/403 or invalid request/schema | permanent failure | Fix credentials, permission, or request; do not consume retry budget |
| 429 for excessive request rate, connection error, or some 5xx | candidate temporary failure | A structured subtype confirms it is temporary, attempts/deadline remain, and no duplicate side effect is possible |
| 429 for exhausted quota/billing | configuration-related permanent failure | Restart through an external process after quota or account state changes |
| A stream breaks after a partial is received | uncertain result | Mark the old partial failed; continue only under an explicit provider recovery protocol, otherwise start an independent attempt |
| Unknown code/type/terminal state | fail closed | Retain raw type and request ID; classify after upgrading the adapter |

The same HTTP status can carry different semantics. OpenAI's current error guide places both “request rate too fast” and “quota/billing exhausted” under 429, but only the former may recover after waiting; the latter requires a quota or configuration change. Google's `RESOURCE_EXHAUSTED` likewise needs interpretation based on concrete quota information. Prefer SDK exception classes and structured `error.code/type`, then combine them with the status code; do not implement “retry every 429.”

Split timeouts at least into connection, read/stream-idle, single-call, and business deadlines. A per-attempt timeout prevents one network call from waiting forever; a retry deadline decides whether enough time remains for another attempt. Both are required, and both must leave time for parsing, validation, and later business actions. Calculate deadlines with a monotonic clock; use wall time only for logging. A user cancellation or upstream deadline must propagate to the SDK/HTTP stream and close resources rather than waiting for a default timeout to elapse.

## Exponential backoff and jitter

In a simple form, local waiting after the `n`th failure can be `min(cap, base × 2^(n-1))` plus bounded random jitter. If a response supplies a valid `Retry-After`, treat it as the server's minimum wait. If waiting would exceed the retry deadline, fail immediately. RFC 9110 permits delta-seconds or an HTTP-date: treat parse failure as absent; never pass negative values, infinity, or arbitrary far-future dates directly to a sleeper. Convert an HTTP-date using controlled current time and cap it with a local maximum wait.

Jitter prevents many clients from retrying simultaneously and causing a thundering herd. Also bound maximum attempts and the total deadline; do not continue once queueing has exceeded the user's request deadline. Tests should inject the clock, sleeper, and randomness so deadline, jitter, and `Retry-After` behavior can be verified reproducibly to the millisecond without real waits.

Retrying 429s can itself count against a limit. Concurrency control, queues, token buckets, and gradual traffic ramp-up are usually more important than blind retries. When reading rate-limit headers, remain compatible with missing headers and semantic changes.

## Idempotency and side effects

Plain-text generation can be recomputed, but charges, emails, database writes, and tool actions around a request may not be idempotent. Generate a stable `operation_id` for one business operation and retain execution state. If a provider supports an idempotency key, use it according to current documentation, but still prevent duplicate side effects at the application layer.

After a timeout, the server may already have completed the request while the response was lost. Before retrying, ask: “Will executing again produce a second action?” Separate model generation from external side effects, and commit side effects through trusted code with a unique key.

## Multi-layer retry budgets

SDKs, gateways, job queues, and applications can all retry. Designate one owner or calculate the total bound, and record actual attempts. Total transport attempts are the product of each layer's “maximum sends per invocation,” not a simple sum of retry counts. For example, `openai-python 2.46.0` defaults to an initial send plus two retries, and an outer layer allowing three attempts yields at most `3 × 3 = 9` sends. Its default ten-minute timeout can itself be retried, so an interactive request deadline can be exceeded dramatically without an explicit budget.

Once a streaming response delivers a partial, an automatic retry cannot pretend to “continue from the break”: a new POST can generate different content and a new call ID. Recover only when the API family provides a verifiable recovery cursor and protocol. Otherwise close the old stream, mark its partial failed, and regenerate with a new attempt. Circuit breaking and fallback should be based on repeated failure and business risk, rather than swallowing errors into an empty result or representing one provider's failure as the same response from another model.

## Exercise and self-check

Write handling policies for 401, 429, 500, connection reset, schema failure, and a tool-write timeout. Self-check: an outer layer retries three times, an SDK twice, and a queue four times. How many requests can they send at most, and how will you cap the total at an acceptable level?

## Mastery checklist

- [ ] I classify by structured error type/code rather than guessing from message strings or one status code.
- [ ] Connection, read/stream-idle, single-call, and business deadlines have independent bounds.
- [ ] Retries are constrained by attempts, retry deadline, `Retry-After`, exponential backoff, and jitter.
- [ ] The SDK, gateway, queue, and application have one explicit retry owner, and I have calculated the worst-case request count.
- [ ] Model generation is separate from email, billing, database writes, and other side effects; side effects have stable business idempotency keys.
- [ ] A new error type fails conservatively and retains the request ID; it is neither treated as success nor retried forever.
- [ ] I can parse both wire forms of `Retry-After`, reject invalid/unbounded waits, and make decisions with a monotonic deadline.
- [ ] After a stream has delivered a partial, I do not silently concatenate ordinary POST retries; recovery relies only on an explicit provider protocol.

## Next step

Continue to [[llm-api-integration/06-usage-observability-and-provider-adapters|Usage, Observability, and Provider Adapters]].

## References

- [RFC 9110: HTTP Semantics—Idempotent methods and Retry-After](https://www.rfc-editor.org/rfc/rfc9110) (accessed 2026-07-21)
- [OpenAI: API errors](https://developers.openai.com/api/docs/guides/error-codes) (accessed 2026-07-21)
- [OpenAI: Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) (accessed 2026-07-21)
- [OpenAI: official Python SDK—Retries and timeouts](https://github.com/openai/openai-python#retries) (accessed 2026-07-21)
- [Anthropic: API errors](https://platform.claude.com/docs/en/api/errors) (accessed 2026-07-21)
- [Anthropic: Rate limits](https://platform.claude.com/docs/en/api/rate-limits) (accessed 2026-07-21)
- [Google: Troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting) (accessed 2026-07-21)
- [Google: Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (accessed 2026-07-21)
