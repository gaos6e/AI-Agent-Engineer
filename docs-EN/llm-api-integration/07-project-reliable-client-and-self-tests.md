---
title: "Reliable Client Project and Self-Tests"
tags:
  - llm-api
  - project
  - testing
aliases:
  - LLM API Integration Project
source_checked: 2026-07-21
source_baseline:
  - Python 3.11 standard-library documentation
  - RFC 9110 HTTP Semantics
  - OpenAI, Anthropic, and Google official error and streaming documentation
content_origin: original
content_status: validated
execution_verified: 2026-07-21
lang: en
translation_key: LLM API集成/07-可靠客户端项目与自测.md
translation_source_hash: 886f7f464991609b09c377bc778ac47fabaaa372fe19e0b8a9585b5b9fd5d4fa
translation_route: zh-CN/LLM-API集成/07-可靠客户端项目与自测
translation_default_route: zh-CN/LLM-API集成/07-可靠客户端项目与自测
---

# Reliable Client Project and Self-Tests

## Project goal and boundary

Implement a provider-neutral reliable-client core in a fully offline environment: strict request/response contracts, temporary and permanent errors, `Retry-After`, exponential backoff, jitter, dual limits for attempts and retry deadline, and a canonical streaming-event state machine. A mock transport makes failure sequences repeatable without an SDK, network, or key.

This is not a real HTTP client. It does not replace an SDK's connection/read/stream-idle timeouts, and does not claim that canonical event names belong to any provider. A real adapter maps official SDK exceptions, raw events, usage, and request IDs into the local contract, and is integration-tested separately.

## Project files

| File | Responsibility |
| --- | --- |
| [[llm-api-integration/examples/reliable_client.py\|reliable_client.py]] | request/response contracts, error classification, retry policy, attempt record, mock transport, and canonical streaming state machine |
| [[llm-api-integration/examples/test_reliable_client.py\|test_reliable_client.py]] | 22 unit tests covering input, backoff, deadline, unknown failure, stream order, partials, terminal states, and resource limits |

## Runtime environment

The scripts use only the Python standard library. In Windows 11 PowerShell 7, run this from the project root that contains both `docs-EN/` and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\llm-api-integration'  # Enter the course directory so unittest resolves example paths predictably.
py -3.11 --version  # Verify that the actual interpreter matches the course verification baseline.
py -3.11 -B -W error -m unittest discover -s .\examples -p 'test_reliable_client.py' -v  # Run the reliable-client regression tests normally and treat warnings as failures.
py -3.11 -O -B -W error -m unittest discover -s .\examples -p 'test_reliable_client.py' -v  # Repeat in optimized mode to prove production gates do not rely on bare assert.
Pop-Location  # Return to the working directory from before entering the course directory.
```

`-B` prevents `.pyc` output. Because the project has zero dependencies, validation does not create a `.venv` inside the vault. A real adapter project should use `venv + pip` outside the vault and pin SDK versions as described in [[llm-api-integration/01-environment-dependencies-and-secret-management|Environment, Dependencies, and Secret Management]].

## Step-by-step reading and experiments

### 1. Inspect the canonical contract

`LLMRequest` retains stable `operation_id`, prompt version, logical model configuration, and input. All attempts for one business operation reuse the same request object. `LLMResponse` distinguishes `completed`, `refused`, and `truncated`, while retaining server request ID, provider, actual model, and raw usage units.

These classes validate only local field shapes. They do not automatically redact `user_text`; production logging must use an allowlist rather than serialize the entire object.

### 2. Verify that retries handle only classified temporary errors

`call_with_retry()` catches only `TransientError`. Authentication, permission, invalid request, exhausted quota, and unsupported capability are `PermanentError`; unknown exceptions such as adapter bugs also surface directly rather than being retried blindly because they “might recover.”

Backoff waits consider all of:

- the local exponential cap and bounded jitter;
- the minimum `retry_after_seconds` parsed by the adapter;
- `max_attempts`;
- `retry_deadline_seconds`.

Tests inject a fake clock, fake sleeper, and deterministic randomness, so they never wait in real time. `retry_deadline_seconds` bounds this layer's retry scheduling; a real SDK still needs per-attempt connection, read/stream-idle, and single-call timeouts.

### 3. Observe attempt evidence

A successful result retains the outcome, structured error category, provider request ID, and planned wait for every attempt. `operation_id` remains stable while request ID can differ on each attempt. On exhaustion, `RetryExhaustedError` distinguishes `attempts_exhausted` from `retry_deadline_exhausted` and retains the last temporary error.

This still does not automatically guarantee idempotent external side effects. Sending email, charging, writing a database, or executing a tool should occur after complete generation and validation, committed by a trusted business layer with its own unique key.

### 4. Verify the streaming state machine

The local canonical protocol has only four types: `response.started`, `response.text.delta`, `response.finished`, and `response.failed`. Only one valid `finished` returns `StreamResult`; refusal and truncation return explicit terminal states and are not completion.

An in-stream failure, or a normally closed connection missing a terminal event, raises an exception retaining request ID and partial text and marks the partial as failed. Unknown canonical events, field drift, sequence errors, invalid usage, and events arriving after a terminal all fail. The state machine limits canonical events to 4,096 and constrains complete text to 100,000 characters through one cumulative `text_chars` limit. It has no separate per-delta threshold, but the cumulative check before every append blocks both one enormous delta and many small deltas. A limit violation raises a non-retriable `StreamLimitError` retaining resource name, limit, observed value, request ID, and bounded partial. This prevents unbounded memory growth while retaining auditable termination evidence. A real adapter may ignore explicitly understood provider telemetry events, but must first make that decision against the current official protocol and close a real stream on failure or cancellation.

## Local verification record

Completed on Python 3.11.9 on 2026-07-21:

- `py -3.11 -m py_compile`: script and tests passed.
- Normal mode: all 22 tests passed with warnings treated as errors.
- `python -O` mode: the same 22 tests passed; critical gates do not rely on bare `assert` that optimization removes.
- Tests make no network calls, read no environment variables, create no real wait, and need no API key.

No provider live API, SDK-compatibility, real-timeout, rate-limit-header, or streaming-event test was performed. Obsidian Reading View was not verified either.

## Steps for integrating a real provider

1. Pin the official SDK version and check current authentication, timeouts, default retries, errors, rate limits, streaming, usage, and schema documentation.
2. Create an adapter that maps raw exceptions through structured code/type; do not depend on error-message strings.
3. State whether the SDK or this layer owns retries, disable or budget other layers, and prevent multiplied request counts.
4. Read a key from a secret manager or environment variable without printing it; use a minimal non-sensitive request for a smoke test.
5. Map real typed events to canonical states, fault-injecting stream interruption, unknown events, refusal, truncation, and incomplete tool arguments.
6. Record operation/trace ID, every request ID, versions, usage, latency, and result state; do not record raw bodies by default.
7. Run task evaluation, controlled integration tests, and low-volume validation before production.

## Extension tasks

1. First complete [[llm-api-integration/08-project-provider-contract-tests|Provider Contract Tests]] to understand the boundary among the canonical core, Reference/SDK event projections, and real wire/live contracts.
2. Then add an adapter for one pinned real SDK while keeping offline tests fully network-free.
3. Inject fake transport latency and add per-attempt timeout and end-to-end business-deadline tests.
4. Parse RFC 9110 `Retry-After` delta-seconds/HTTP-date and map it to canonical seconds.
5. Add local concurrency/token-bucket scheduling and compare failure rate for “queue first” versus “retry after a 429.”
6. Add business idempotency keys and state storage for tool calling, simulating “the server acted but the response was lost.”

## Self-check questions

1. Why can the same 429 be either a temporary rate limit or a permanent quota problem?
2. With two SDK retries, three outer retries, and four queue retries, how many attempts are possible in the worst case?
3. What do a retry deadline and one SDK read timeout constrain respectively?
4. Why can neither HTTP 200 nor the first text delta prove a stream is complete? Why limit event count and cumulative `text_chars` separately, and how does the same cumulative limit block one enormous delta?
5. Why cannot an old partial and a new generation be concatenated after an interruption?
6. What problem does each of operation ID, trace ID, and provider request ID solve?

## Mastery checklist

- [ ] I can run the normal and `-O` groups of 22 tests and explain each category of failure.
- [ ] Only classified temporary errors enter one retry budget with attempts, deadline, backoff, and jitter.
- [ ] Permanent and unknown errors are not retried; an exhausted quota is not treated as an ordinary 429 loop.
- [ ] Completion, refusal, truncation, in-stream error, missing terminal, and unknown event all have explicit states.
- [ ] An event-count or cumulative-text violation (including a single delta that immediately breaches the cumulative value) produces an auditable failure and never releases a provisional result.
- [ ] A partial is not treated as complete output; external side effects follow complete validation and possess business idempotency.
- [ ] A real adapter's SDK version, default retry, timeout, events, and usage are proven by official sources and integration tests.

## Primary references

- [Python 3.11: `unittest`](https://docs.python.org/3.11/library/unittest.html) (accessed 2026-07-21)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) (accessed 2026-07-21)
- [OpenAI: Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) (accessed 2026-07-21)
- [OpenAI: Migrate to Responses—Update streaming consumers](https://developers.openai.com/api/docs/guides/migrate-to-responses#7-update-streaming-consumers) (accessed 2026-07-21)
- [Anthropic: API errors](https://platform.claude.com/docs/en/api/errors) (accessed 2026-07-21)
- [Google: Troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting) (accessed 2026-07-21)

## Back to the index

Continue to [[llm-api-integration/08-project-provider-contract-tests|Provider Contract Tests]], or return to [[llm-api-integration/00-index|LLM API Integration Learning Path]].
