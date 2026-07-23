---
title: "Requests Client, Session, and Contract Reading"
tags:
  - ai-agent-engineer
  - api
  - http
  - requests
aliases:
  - Requests client fundamentals
  - API contract reading
source_checked: 2026-07-22
lang: en
translation_key: API/02-Requests客户端与契约阅读.md
translation_source_hash: 37cf647557578894551f29a6e922be736c9ed4206fcacba55afe34e335bc8dec
translation_route: zh-CN/API/02-Requests客户端与契约阅读
translation_default_route: zh-CN/API/02-Requests客户端与契约阅读
---

# Requests Client, Session, and Contract Reading

## Objective

The previous lesson decomposed HTTP into requests and responses. This lesson applies those concepts with Python Requests and adds engineering boundaries beginners commonly skip: isolated dependencies, reused `Session` objects, TLS validation, redirect control, OpenAPI contract reading, and test doubles that prove client behavior.

By the end, you should be able to explain *why* a call is made this way rather than merely copy one `requests.get()` line.

## Establish the learning environment first

From your own practice directory in Windows 11 and PowerShell 7, create a virtual environment:

```powershell
python -m venv .venv  # Create an isolated dependency environment in your own practice directory.
.\.venv\Scripts\Activate.ps1  # Activate it so subsequent python and pip commands point to this environment.
python -m pip install --upgrade pip  # Update the installer in the current environment, not an uncertain global pip.
python -m pip install "requests>=2.33,<3"  # Install the Requests major-version range verified by this course.
python -c "import sys, requests; print(sys.executable); print(requests.__version__)"  # Check both the interpreter location and installed Requests version.
```

`venv` keeps project dependencies separate from system Python, and `pip` installs into the active environment. This course constrains its examples in `examples/requirements.txt`; do not commit `.venv`, wheel caches, or interpreter-generated `__pycache__`.

As of **2026-07-22**, the Requests stable documentation showed 2.34.2, while this offline project ran with 2.33.0. `requests>=2.33,<3` allows compatible 2.x updates; it does not mean every future 2.x release is test-free. Team projects commonly record exact resolution with a lock file or reproducible build tool.

## Understand the call lifecycle from one request

A minimal GET:

```python
import requests  # Import the Requests client library.

response = requests.get(  # Send a minimum GET; production code must still validate endpoint schema and business semantics.
    "https://example.com/api/items",  # Use the resource address specified by the API documentation.
    params={"limit": 20},  # Let the library encode the page size as a query parameter.
    headers={"Accept": "application/json"},  # State that the client expects a JSON representation.
    timeout=(3.05, 15),  # Limit both connection and read waits.
)
response.raise_for_status()  # Handle HTTP-layer failures before treating an error body as success data.
data = response.json()  # Parse JSON; the next step is still to check data type and required fields.
```

This code does five things:

1. Encodes `params` into the query string.
2. Declares that JSON is expected.
3. Sets connection and read timeouts.
4. Converts 4xx/5xx into `HTTPError`.
5. Attempts to parse the body as a Python value.

It is still incomplete: redirect policy, response media type, schema, retries, and resource reuse have no explicit contract. `response.json()` succeeding proves only syntactic parseability, not a correct status or fields.

## Why use Session?

`requests.Session` reuses a connection pool within one session and can retain shared headers, authentication, and cookies. It is more suitable than opening a new connection for every page when an Agent repeatedly calls the same service:

```python
from collections.abc import Iterator  # Import the iterator type to state that the function yields pages one at a time.

import requests  # Import the client library that provides a reusable connection pool and HTTP methods.


def iter_pages(base_url: str) -> Iterator[dict]:  # Request fixed page numbers and yield one JSON object per page.
    with requests.Session() as session:  # This function creates the Session, and the context manager closes its pool when finished.
        session.headers.update(  # Set headers needed on every page as session defaults.
            {  # Update several stable headers with one mapping.
                "Accept": "application/json",  # Explicitly request JSON responses.
                "User-Agent": "agent-course-client/0.1",  # Let server logs identify the teaching-client version.
            }
        )
        for page_number in range(1, 4):  # Request only the first three pages here; production pagination should use a server cursor or next link.
            response = session.get(  # Send the current-page request with the Session connection pool.
                f"{base_url.rstrip('/')}/items",  # Remove a trailing slash to avoid a double-slash path.
                params={"page": page_number},  # Supply the current page number as a query parameter.
                timeout=(3.05, 15),  # Every request has explicit connection and read bounds.
            )
            response.raise_for_status()  # Stop early for 4xx/5xx instead of parsing an error response.
            value = response.json()  # Parse the successful response body into a Python value.
            if not isinstance(value, dict):  # This example contract requires a top-level JSON object for each page.
                raise ValueError("expected a JSON object")  # Do not let an array or string silently enter downstream logic.
            yield value  # Yield one page so the caller can process while fetching rather than accumulate every page first.
```

Ownership must be explicit: whoever creates a Session closes it. If a client accepts a caller-injected Session, it should usually not close it unilaterally. The course project closes only Sessions it creates and tests that contract.

### Environment configuration affects Session

Requests can read proxy environment variables and `.netrc` by default. That helps corporate networks and user configuration, but it can make an offline test that should access only `127.0.0.1` depend on machine state. The teaching client therefore sets `trust_env=False` for **self-created Sessions used only by this local project**.

Do not mechanically copy this setting to a real project. Whether a production service needs a proxy, enterprise CA, `.netrc`, or platform authentication is determined by its deployment environment and security policy.

## TLS, proxies, and redirect boundaries

### Keep certificate verification enabled

Requests verifies HTTPS certificates by default. Do not “fix” a certificate error with `verify=False`: that abandons server identity verification and makes the connection vulnerable to a man-in-the-middle attack. Instead, check hostname, system time, enterprise proxy, and trusted CA configuration.

A certificate-chain or hostname-validation failure is not transient network jitter. Treat it as a configuration or security event and investigate; do not place `SSLError` into a retryable `ConnectionError` branch. The integrated project has a regression test for this inheritance relationship.

### An API client should not blindly follow redirects

Requests' general `request()` allows redirects by default. That is convenient in a browser, but an API request can carry Authorization, an idempotency key, or a sensitive body. A reliable client can start with:

```python
response = session.request(  # Send through an existing Session and inherit its controlled headers and connection configuration.
    "GET",  # State the HTTP method explicitly rather than relying on a default.
    url,  # Use an already validated target URL; do not place untrusted user input here directly.
    timeout=(3.05, 15),  # Bound connection and read phases to avoid an indefinitely stuck call.
    allow_redirects=False,  # Do not automatically follow API redirects; inspect Location and credential boundaries first.
)
```

If the target API says redirects should be followed, validate the `Location` scheme, host, method changes, and credential-forwarding rules. Do not assume safety because the current client library happens to strip some headers; do not rest security on an untested default.

### Do not log full URLs

A query string can contain signatures, cursors, or user data. Prefer the service name and route template, such as `/v1/items/{id}`, instead of printing a final URL with its query string.

## How to read OpenAPI instead of guessing a contract from an SDK

OpenAPI describes an HTTP API in YAML or JSON. On first reading, locate these items in order:

| Location | What to find |
| --- | --- |
| `servers` | Base URL and environment |
| `paths` + method | Endpoint and operation semantics |
| `parameters` | Path, query, and header parameters and requiredness |
| `requestBody` | Request media type and schema |
| `responses` | Success/error statuses, headers, and response schemas |
| `components.schemas` | Reusable object structures |
| `securitySchemes` + `security` | Authentication mechanisms and where they apply |

OpenAPI describes a contract; it does not guarantee that the service implementation is correct. An SDK is only one wrapping of the contract. Critical clients should retain a small number of contract tests that verify actual responses still provide the needed fields and statuses.

### Minimum call card

After reading documentation, write a card before writing code:

```text
Documentation and retrieval date:
Base URL / API version:
Method + path:
Authentication and scope:
Path/query/header/body parameters:
Success statuses and schema:
Error statuses and machine-readable codes:
Pagination, rate limits, timeouts, retries, idempotency:
Deprecation or migration notes:
```

When documentation does not state an item, write “not documented.” Do not invent a default from another API.

## Versions, deprecations, and compatibility

An API can express a version in its URL (such as `/v1`), headers, dates, or model names. Before an upgrade, check at least:

- whether endpoints, fields, status codes, or defaults change;
- whether an old field is deleted immediately or marked deprecated first;
- whether the SDK version and server API version are separate concepts;
- whether a migration guide, deprecation date, or compatibility window exists; and
- whether an old client can still read new responses during rollback.

For response fields, generally “read required fields, tolerate harmless additions, reject missing or type-changed critical fields.” Do not mistake “ignore unknown content” for skipping schema validation.

## Test doubles and local contract tests

Client reliability needs two layers of evidence:

1. **Scripted Session**: start no network, return 503 or raise `ReadTimeout` precisely, and record the client's timeout, headers, and `allow_redirects`; this is suitable for retry decisions.
2. **Loopback integration test**: start a local service on a random `127.0.0.1` port and verify actual serialization, status codes, headers, pagination, and resource cleanup.

A double proves only client behavior for its arranged inputs. It does not prove that a real vendor service, proxy, TLS chain, or billable endpoint is available. When external calls have not been run, state that limitation clearly.

## Common mistakes

- Create a never-closed Session during global module import.
- Assume an SDK automatically picks sensible timeout, retry, and redirect policies.
- Use `verify=False` to bypass certificate errors.
- Mistake behavior from proxies, `.netrc`, and environment variables for deterministic program behavior.
- Read only a successful-response example and skip errors, rate limits, pagination, and changelog.
- Treat an OpenAPI schema as runtime verification and omit failure-path tests.

## Exercises and self-check

1. Write a complete call card for the local teaching `/items` endpoint.
2. Use a scripted Session to assert that the client actually passes its `(connect, read)` timeout and `allow_redirects=False`.
3. Compare function-level `requests.get()` with a long-lived Session in ownership and connection reuse.
4. Find an official OpenAPI document and record the method, authentication, parameters, response, and errors for one endpoint without calling the real service.

- [ ] I can create a venv and verify the interpreter and Requests version in use.
- [ ] I can explain a Session's connection pool, configuration inheritance, and close responsibility.
- [ ] I do not disable TLS verification to conceal a configuration error.
- [ ] I explicitly decide whether an API redirect should be followed.
- [ ] I can derive a call card from OpenAPI and distinguish a documentation claim from an actual verification.

## References

- [Requests 2.34.2 documentation](https://docs.python-requests.org/en/stable/)
- [Requests Advanced Usage: Session, TLS, proxies, and timeouts](https://docs.python-requests.org/en/stable/user/advanced/)
- [Requests API: `allow_redirects` and request arguments](https://docs.python-requests.org/en/stable/api/)
- [OpenAPI Specification 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)

Retrieved on 2026-07-22. Extended reference: [[api/upstream-references/requests-quickstart|Requests Quickstart]]. Next: [[api/authentication-status-codes-and-credential-security|Authentication, status codes, and credential security]].

