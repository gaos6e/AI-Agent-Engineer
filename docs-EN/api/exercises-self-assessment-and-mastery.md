---
title: "API Exercises, Self-Assessment, and Mastery Criteria"
tags:
  - ai-agent-engineer
  - api
  - exercise
aliases:
  - API self-assessment
  - API mastery check
source_checked: 2026-07-22
lang: en
translation_key: API/08-练习自测与掌握标准.md
translation_source_hash: 298c1c990e3c09a459eaa088febeb4054f3a67d5c63f2f0ce515c2bde24b9990
translation_route: zh-CN/API/08-练习自测与掌握标准
translation_default_route: zh-CN/API/08-练习自测与掌握标准
---

# API Exercises, Self-Assessment, and Mastery Criteria

## How to use this page

Answer the conceptual questions before looking at the answers, then independently rewrite the core loop from the project. The goal is not to memorize every status code. It is to find a contract for an unfamiliar API, write a bounded call, explain a failure, and protect credentials.

## Group 1: documentation reading and request construction

Choose public API documentation that needs no real key, or use the local teaching service. Complete a one-page call card:

```text
Service and documentation:
Base URL:
Method + path:
Authentication:
Query/path/header/body parameters:
Success status and response schema:
Error status and machine-readable error code:
Pagination:
Rate limit:
Timeout/retry/idempotency conventions:
Version or retrieval date:
```

Acceptance criterion: another learner can construct the request from this card without guessing a header name, pagination stop condition, or retry rule.

## Group 2: small coding exercises

### Exercise 1: fetch JSON safely

Write `fetch_json(url)` that:

- allows only `https://`, plus `http://127.0.0.1` for local testing;
- uses `(connect, read)` timeout;
- sends `Accept: application/json`;
- checks status and content type first;
- raises a distinct exception for invalid JSON; and
- does not catch an error and return an empty dictionary.

### Exercise 2: bounded pagination

Implement cursor pagination from a blank file:

- configure `max_pages` and `max_items`;
- treat cursors as opaque;
- detect repeated cursors;
- validate that `items` is an array on every page; and
- use a generator rather than load all data at once.

### Exercise 3: parse `Retry-After`

Handle each of: `"15"`, a valid HTTP date, a past date, a negative number, an empty string, the non-ASCII digit `"²"`, and arbitrary text. Specify whether an invalid value falls back to local backoff or fails immediately. If a valid value exceeds the wait budget, stop or defer instead of truncating it and retrying early. Use a sleep spy and fixed clock in tests to make the choice deterministic.

### Exercise 4: classify errors

Construct inputs and assert exception type for: refused connection, 404 problem JSON, 503, 200 HTML, 200 invalid JSON, and 200 with a required field missing.

### Exercise 5: safe logging

Given request information containing Authorization, Cookie, signed query, user email, and request ID, emit one allowed structured log. Use an allowlist of fields, not “print everything then string-replace.”

## Group 3: integrated task

Build a recoverable importer on [[api/project-reliable-api-client|the reliable API client project]]:

1. Read items through pagination.
2. Write each item with stable `id` to local JSONL.
3. Save the next cursor after every successfully processed page.
4. Resume after interruption.
5. Do not duplicate IDs already written.
6. Retry 429/503 within a finite budget; put other 4xx into a failure report.
7. Keep complete body text and sensitive headers out of logs.
8. Test an interruption after page two, then rerun to produce complete non-duplicate data.

The project is not done merely because it “ran without errors.” Supply a test command, successful output, one intentionally failing case, design notes, and risks not covered.

## Concept self-check

1. Does `response.json()` succeeding prove that a request succeeded? Why?
2. How do the investigation directions for 401 and 403 differ?
3. Does `timeout=10` mean an entire download takes at most 10 seconds?
4. Why can a POST result be unknown after a read timeout?
5. GET is idempotent. Does that permit infinite retry?
6. Why can several workers each handling 429 create a retry storm?
7. What can offset pagination do while data keeps being inserted?
8. When is one idempotency key reused, and when must a new key be created?
9. Why is a natural-language error `message` unsuitable as a stable program branch?
10. Which diagnostic fields are most valuable in a log without leaking credentials?

> [!question]- Reference answers
> 1. No. It proves only that the body parses; still check status, content type, schema, and business state.
> 2. For 401, first check missing or expired credentials and target service; for 403, first check scope, role, resource ownership, and policy.
> 3. Not necessarily. Requests timeout mainly constrains connection and periods with no socket data, not the complete operation deadline.
> 4. The server can already have executed while the response was lost on its return path.
> 5. No. You still need a maximum count, deadline, backoff, rate limits, and failure classification.
> 6. Workers can wait together and retry together, further exceeding server capacity. Coordinate global rate/concurrency and add jitter.
> 7. Earlier insertions or deletions move positions, causing duplicates or omissions.
> 8. Reuse it for retries of one logical operation; create a new one for a new logical operation, provided the server explicitly supports the feature.
> 9. Wording can change or be translated and has no guaranteed structure. Use status and documented machine-readable codes.
> 10. Service, method, route template, status, duration, attempt count, error class, and request ID—not token, Cookie, signed URL, or sensitive body.

## Common-misconception check

Decide whether each statement is true and explain why:

- “Once HTTPS is used, placing a token in the URL is safe.”
- “Every 5xx should be retried until success.”
- “An idempotency key starts working automatically when the client adds a random header.”
- “An empty pagination array necessarily ends every API.”
- “An SDK has encapsulated HTTP, so timeout and status codes no longer matter.”
- “Catching an exception and returning `None` makes an Agent more stable.”

All are false. HTTPS does not stop URLs entering logs; retries need conditions and budgets; an idempotency key needs server contract support; pagination termination varies; an SDK still has reliability defaults; and `None` erases failure semantics and causes poorer later decisions.

## Final mastery criteria

### Foundational understanding

- [ ] I can decompose a request/response and explain method, URL, headers, body, and status.
- [ ] I can distinguish authentication from authorization, API key from OAuth, and access token from refresh token.
- [ ] I can explain 2xx, 4xx, and 5xx categories and handle common status codes correctly.

### Independent implementation

- [ ] I can create an environment from scratch with `venv + pip` and use Requests.
- [ ] Every request has a sensible connection/read timeout, and the outer task has deadline awareness.
- [ ] I can implement bounded cursor pagination and checkpoint recovery.
- [ ] I decide retry from operation semantics and error type.
- [ ] I implement capped, jittered backoff that respects `Retry-After`.
- [ ] If `Retry-After` exceeds the wait budget, I stop or defer rather than request early.
- [ ] For supported APIs, I reuse idempotency keys correctly and handle conflict.

### Diagnosis and security

- [ ] I can distinguish configuration, construction, transport, HTTP, representation, schema, and business errors.
- [ ] Logs keep request ID, duration, status, and attempts without exposing credentials or sensitive body.
- [ ] For uncertain outcomes, I record “unknown and query/compensate,” not a fabricated definite failure.
- [ ] I can test success and failure paths and accurately state which network calls were not run.
- [ ] The 35 tests in `api/examples` pass, and I can distinguish 29 scripted-Session/loopback-HTTP evidence tests from 6 offline reference-page static contracts.

When all criteria are met, return to [[api/00-index|the API learning path]] and follow the overall route into later knowledge bases such as [[llm-api-integration/00-index|LLM API Integration]].

## References and continued learning

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [Requests User Guide](https://docs.python-requests.org/en/stable/user/)
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)

Retrieved on 2026-07-22.

