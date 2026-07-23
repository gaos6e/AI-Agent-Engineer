---
title: "Project: Reliable API Client"
tags:
  - ai-agent-engineer
  - api
  - project
aliases:
  - Reliable API client project
source_checked: 2026-07-22
lang: en
translation_key: API/07-实战-可靠API客户端.md
translation_source_hash: fb3d49b6cb2225d95fae5e58fcf050dbb20eec69e23bd54cc694b898db2319f7
translation_route: zh-CN/API/07-实战-可靠API客户端
translation_default_route: zh-CN/API/07-实战-可靠API客户端
---

# Project: Reliable API Client

## Project objective

In Windows 11 and PowerShell 7, start a teaching API that listens only on `127.0.0.1`, then use a Python client to:

1. read three records with cursor pagination;
2. recover after the first two 503 responses with finite retries;
3. recover without duplicate creation using the same idempotency key when the server created an item but the first response failed;
4. classify 3xx, 404, 409, invalid JSON, wrong content type, and schema errors;
5. stop decisively at repeated cursors, maximum-page limits, retry exhaustion, and `Retry-After` boundaries; and
6. run 29 reliable-client unit and loopback-integration tests that need neither the internet nor real keys, plus 6 offline Markdown contract tests for the OpenAI reference page.

Project code is in `docs-EN/api/examples/`. It is a teaching implementation, not a generic SDK ready for production. A production client still needs the target API contract, logs and metrics, deadline, authentication, and schema tools.

## Files and responsibilities

```text
examples/
├── requirements.txt                    # Requests is the only third-party dependency
├── mock_api_server.py                  # Local teaching API
├── reliable_client.py                  # Endpoint methods, internal retry loop, and error classification
├── demo.py                             # Manual demonstration entry point
├── test_reliable_client_unit.py        # Deterministic unit tests with a scripted Session
├── test_reliable_client_integration.py # Real loopback HTTP integration tests
└── test_openai_api_markdown.py         # Static tests for reference-page Python snippets and safety contracts
```

### Server fault scenarios

| Endpoint | Behavior | Capability to verify |
| --- | --- | --- |
| `GET /items` | Two cursor pages | Complete pagination and termination. |
| `GET /looping-items`, `/endless-items` | Repeated or never-ending cursor | Repeated-cursor detection and maximum pages. |
| `GET /bad-items`, `/bad-cursor` | Invalid pagination schema | Representation-error classification. |
| `GET /flaky` | First two calls return 503; third succeeds | Finite retries and `Retry-After`. |
| `GET /retry-later` | 503 + `Retry-After: 120` | Stop when it exceeds budget; do not retry early. |
| `GET /bad-json` | Declares JSON but body is corrupt | Representation-error classification. |
| `GET /text-json`, `/no-content`, `/redirect` | Media type, 204, and 302 | 2xx/3xx and response-parsing boundaries. |
| `POST /jobs` | Requires `Idempotency-Key` | Replay deduplication and conflict when one key has different bodies. |
| Any other path | 404 problem JSON | Retain machine error code and request ID. |

## Step 1: create an isolated environment

From the project root:

```powershell
python -m venv .venv  # Create a local isolated environment beside the project root.
.\.venv\Scripts\Activate.ps1  # Activate it in the current PowerShell session.
python -m pip install --upgrade pip  # Update the installer for the current environment.
python -m pip install -r '.\docs-EN\api\examples\requirements.txt'  # Install Requests from the project's minimal dependency list.
```

`.venv` is local-only and must not enter the vault or Git. An existing isolated environment can instead install the requirements directly.

## Step 2: start the local service

Terminal A:

```powershell
python -B '.\docs-EN\api\examples\mock_api_server.py'  # Start the teaching service in terminal A; it binds only to 127.0.0.1.
```

Expected output:

```text
Teaching API started at http://127.0.0.1:8765
Press Ctrl+C to stop.
```

The service binds only the loopback address, needs no API key, and makes no internet call. If port 8765 is busy, stop the process using it; if you change the port yourself, update the base URL in `demo.py` too.

## Step 3: run the demonstration

Terminal B:

```powershell
python -B '.\docs-EN\api\examples\demo.py'  # Run the manual pagination, transient-failure retry, and idempotent-create demonstration in terminal B.
```

Verify three things:

- the paginated result includes `item-1`, `item-2`, and `item-3`;
- `/flaky` eventually reports `attempt: 3`; and
- the first create and replay with the same key return the same task ID.

## Step 4: run automated tests

Tests start and stop the service themselves on a random free port, so terminal A is not required:

```powershell
python -B -W error::ResourceWarning -m unittest discover -s '.\docs-EN\api\examples' -p 'test_*.py' -v  # Promote ResourceWarning to an error and run every local unit and loopback test with detail.
```

Pass criterion: all 35 tests are `ok` and the process exits with status 0. Twenty-nine verify reliable-client unit and loopback behavior; six only statically check code snippets and safety contracts in the OpenAI reference page. The server, thread, and any client-created Session must be closed after the suite.

## Key design decisions in the client

### 1. Every request has a timeout

`ReliableApiClient.timeout` is `(connect_timeout, read_timeout)`. Scripted-Session tests assert that this tuple reaches the transport and simulate `ReadTimeout` to verify a finite retry. They do not claim to test public-network latency.

### 2. Not every request is retryable

The general `_request_json` is internal; only endpoint methods can declare `retry_authorized=True`. Semantically idempotent HTTP methods can enter retry under a clear contract. POST additionally needs authorization from `create_job()`, the known endpoint that supports an idempotency key. Adding a nonempty header to an arbitrary POST does not grant retry eligibility. The teaching service further narrows its key to printable ASCII without spaces to prevent header-encoding errors; a real API's character set and length remain documentation-defined.

### 3. Transient status codes are allowlisted

The teaching implementation treats only 429, 500, 502, 503, and 504 as retry candidates. 400, 401, 403, 404, 409, and 422 do not repair themselves after the same wait, so they become `ApiHttpError` directly.

### 4. A server wait instruction must not be shortened

When the server returns a valid `Retry-After` within the `max_retry_after` wait budget, the client waits the full duration. If the service asks for 120 seconds and the current budget permits only 30, it immediately returns an `ApiHttpError` with `retry_after=120` for outer-layer deferral; it never requests again after 30 seconds. Only an invalid header falls back to local exponential backoff and jitter. Sleep, clock, and random functions are injectable, so tests never actually wait.

### 5. JSON needs two validation layers

Check `Content-Type` first, then parse JSON. Pagination and job methods also minimally validate `items`, `next_cursor`, and `id`. Representation errors use `ApiResponseError`, not the same category as 404 or 503.

### 6. Pagination has three stop valves

- `next_cursor is None` is normal completion.
- A repeated cursor is a contract error.
- Exceeding `max_pages` is a forced stop.

### 7. Redirects and local environment are controlled explicitly

The teaching client sends `allow_redirects=False`, exposing 3xx to endpoint-specific contract handling. Self-created Sessions use `trust_env=False`, ensuring loopback tests do not read proxies or `.netrc`. A caller-injected Session remains caller-owned: the client neither closes it nor rewrites its environment policy.

## Automated test matrix

| Category | Actually covered |
| --- | --- |
| Pagination | Normal two pages; repeated cursor; maximum pages; invalid items/cursor types. |
| Transport and timeout | Timeout tuple; finite `ReadTimeout` retry; normalization of other `RequestException` failures. |
| TLS | `SSLError` subclasses `ConnectionError` but stops after the first failure, so retry cannot hide certificate identity problems. |
| HTTP | 204; 302 with redirects disabled; 404; 409; 503 recovery and exhaustion. |
| `Retry-After` | Seconds; HTTP date; past date; negative; arbitrary text; non-ASCII digits; overly long ASCII digits; wait-budget overflow. |
| Idempotency | Same key/same payload; same key/different payload; first response failure after write. |
| Representation | `application/json`; `application/problem+json`; incorrect media type; invalid JSON. |
| Configuration and resources | Base URL; timeout/jitter/page boundaries; key ASCII/whitespace/control characters; Session ownership; thread exit. |
| Reference-page static contract | Python fenced blocks on the OpenAI reference page parse; storage, file cleanup, stream terminal state, and tool-loop safeguards are not removed by regression. |

## Required experiments

### Experiment A: observe retry exhaustion

Temporarily set client `max_attempts` to 2, then request `/flaky` from a freshly started service. Expect `ApiHttpError(status=503)`, because the teaching service succeeds only on the third call. Restore the code after the experiment; do not change the test expectation merely to “pass.”

### Experiment B: create an idempotency conflict

Use one key to send `{"value": 1}`, then the same key to send `{"value": 2}`. The second request should be 409 with machine code `idempotency_conflict`. A key does not mean “return an old result no matter what body is sent.”

### Experiment C: reason about removed pagination safeguards

Do not alter the finished solution first. On paper, explain what happens if a server always returns `next_cursor="page-2"` and the client lacks repeated-cursor detection and a maximum page count. Then add a dedicated `/looping-items` endpoint and test to the mock server and verify that the client terminates.

### Experiment D: confirm POST's default policy

Read `test_idempotency_header_alone_does_not_authorize_post_retry`: even when an internal request carries a key, an endpoint that does not authorize retry makes only one attempt after 503. Compare it with `create_job()` and explain why all three are necessary: service contract, endpoint-method authorization, and reuse of the same key.

## Troubleshooting common problems

### `ModuleNotFoundError: requests`

Verify the terminal has activated the correct `.venv`, then run:

```powershell
python -c "import sys, requests; print(sys.executable); print(requests.__version__)"  # Show the active interpreter path and library version to confirm that the environment is really active.
```

This prints only interpreter path and library version, not credentials.

### `WinError 10048` or address in use

Port 8765 is usually already occupied. Return to terminal A and press Ctrl+C. Tests use random ports and normally remain unaffected.

### The test process does not exit

Check that `tearDown()` calls `shutdown()`, `server_close()`, and waits for the thread in that order. Do not hide a resource-cleanup bug by force-terminating the process.

### HTML arrives instead of JSON

This project does not normally return HTML. First check the base URL and port. In a real environment, also investigate proxy, login page, gateway, and redirect behavior.

## Project acceptance checklist

- [ ] I can install dependencies from an empty environment and run the tests.
- [ ] I can place the 29 reliable-client tests and 6 reference-page static contracts in the test matrix and choose any 8 to explain which contract a failure would regress.
- [ ] I can change the retry count and predict the `/flaky` result.
- [ ] I can prove that the same key and payload do not create twice, while the same key and different payload return a conflict.
- [ ] I can explain why 404 and invalid JSON use different exceptions.
- [ ] I did not create or commit real credentials, `.venv`, `__pycache__`, or `.pyc`.

## Optional extensions

1. Add a structured event callback recording method, route, status, duration, and attempt, without complete bodies or headers.
2. Add an overall deadline so timeouts, retries, and waits together cannot exceed a call budget.
3. Validate a `Job` schema with a dataclass or Pydantic and add failure tests for missing fields.
4. Add an interruptible pagination checkpoint and simulate a restart after page two is processed.
5. Add a security-log event callback and assert that Authorization, complete URLs, and bodies never enter the event.

## References

- [Python `http.server`](https://docs.python.org/3/library/http.server.html): used here only for local teaching; the Python documentation does not recommend it as a production server.
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)
- [Requests documentation](https://docs.python-requests.org/en/stable/)

Retrieved on 2026-07-22. After the project, continue to [[api/exercises-self-assessment-and-mastery|Exercises, self-assessment, and mastery criteria]].
