---
title: "Error Classification, Logging, and Troubleshooting"
tags:
  - ai-agent-engineer
  - api
  - observability
aliases:
  - API error handling
  - API troubleshooting
source_checked: 2026-07-22
lang: en
translation_key: API/06-错误分类日志与排查.md
translation_source_hash: 366496817ff4ace0dafcd9341fa70f3bf03eee87fe2b3e7f2749ae5543b26854
translation_route: zh-CN/API/06-错误分类日志与排查
translation_default_route: zh-CN/API/06-错误分类日志与排查
---

# Error Classification, Logging, and Troubleshooting

## Objective

Break “an API call failed” into actionable error layers. Design stable exception boundaries and safe logs. When faced with an HTML error page, invalid JSON, schema changes, business rejection, or network failure, retain enough evidence without exposing credentials.

## Use layers, not one `except Exception`

One call can fail at at least these layers:

| Layer | Example | Retry automatically? |
| --- | --- | --- |
| Local configuration | Wrong base URL, missing environment variable | No; correct configuration. |
| Request construction | Object cannot be JSON serialized, parameter validation fails | No; correct code or input. |
| Transport | DNS, refused connection, connection/read timeout | Depends on stage and idempotency. |
| TLS identity validation | Certificate chain, hostname, or trust configuration failure | No; check CA, hostname, system time, and proxy. Do not hide it with retry or `verify=False`. |
| HTTP | 401, 404, 429, 503 | Follow status and API contract. |
| Representation | Expected JSON but received HTML; malformed JSON | Usually investigate gateway or contract first. |
| Schema/business | Missing field, business error code, task state `failed` | Follow business rule. |

Classification lets upper layers decide correctly: invalid user input can prompt immediately, an authentication error can update configuration, 429 can enter a later queue, a create with unknown outcome needs a status lookup, and only transient server failure enters a finite retry.

## Design your exception boundary

Do not make a business layer depend on every `requests.exceptions` detail. A client module can translate them into a small stable set:

```python
class ApiClientError(Exception):  # Define the stable base exception the business layer needs to recognize.
    """Base class for API-call failures that this client has classified."""  # All subclasses represent a categorized API-call failure.


class ApiTransportError(ApiClientError):  # Represent DNS, connection, or read failure before a usable HTTP response exists.
    """No usable HTTP response was obtained."""  # An upper layer can decide on a finite retry from operation idempotency.


class ApiHttpError(ApiClientError):  # Represent an HTTP status and safely recordable server information.
    def __init__(self, status: int, code: str | None, request_id: str | None):  # Accept status, machine-readable code, and server request ID.
        super().__init__(f"API returned HTTP {status}, code={code!r}")  # Produce a stable message with no response body or credential.
        self.status = status  # Retain HTTP status for retry or user-feedback policy.
        self.code = code  # Retain a documented machine code; do not branch on natural-language detail.
        self.request_id = request_id  # Retain a diagnostic server ID for safe support correlation.


class ApiResponseError(ApiClientError):  # Represent a media type, JSON syntax, or schema that violates client expectations.
    """Response representation or schema does not meet the contract."""  # Investigate gateway, version, and server behavior before blind retry.
```

An upper layer can catch only `ApiClientError` for common presentation, then use the subtype to choose retry, alerting, or user correction. Use `raise ... from exc` to preserve causality. Debug logs can retain a stack trace, but user-facing messages must not expose local paths or response bodies.

## HTTP error bodies

RFC 9457 defines `application/problem+json`, commonly with `type`, `title`, `status`, `detail`, and `instance`; an API can add extension fields. It provides a general representation but is not universal, so the client still follows the target contract.

```json
{
  "type": "https://api.example.com/problems/invalid-cursor",
  "title": "Invalid cursor",
  "status": 400,
  "detail": "Cursor has expired",
  "request_id": "req_123"
}
```

JSON does not allow valid end-of-line comments: `type` is a stable problem-type URI; `title` and `detail` are human-facing and unsuitable for program branching; `status` agrees with the HTTP status; and `request_id` can safely correlate server diagnosis. A real error object can have machine-readable codes defined by its target API.

- Programs should branch first on status, `type`, or a documented machine code.
- `detail` is for people and can change, so do not control logic with substring matching.
- A server must not put stacks, SQL, internal paths, or secrets in `detail`.
- Before displaying `detail`, a client must consider whether it includes sensitive business data.

## Parse a response safely

```python
from typing import Any  # Represent fields in a JSON-decoded object that can have multiple value types.

import requests  # Use Requests Response typing and its JSONDecodeError explicitly.


def parse_json_object(response: requests.Response) -> dict[str, Any]:  # Narrow an obtained HTTP response to a trustworthy JSON object.
    media_type = (  # Extract the primary media type from the header.
        response.headers.get("Content-Type", "")  # Use an empty string when missing so it is uniformly rejected below.
        .split(";", 1)[0]  # Remove charset and similar parameters.
        .strip()  # Remove possible boundary whitespace.
        .lower()  # Normalize case for comparison.
    )
    if media_type != "application/json" and not media_type.endswith("+json"):  # Accept standard JSON and vendor `+json` responses.
        raise ApiResponseError(f"expected JSON, received Content-Type={media_type!r}")  # Do not disguise HTML or text as a business object.

    try:  # The body can be truncated or invalid JSON even with a correct header.
        value = response.json()  # Call Requests' response-body decoder.
    except requests.exceptions.JSONDecodeError as exc:  # Catch the JSON decoding failure defined by the library.
        raise ApiResponseError("response declared JSON but could not be parsed") from exc  # Retain causal context while exposing a stable category.

    if not isinstance(value, dict):  # This client contract does not accept an array, string, or null as the top-level response.
        raise ApiResponseError("expected a JSON object")  # Block type errors and semantic drift before field reads.
    return value  # Return an object that passed the representation-layer check; callers validate fields next.
```

A real project also needs field-level schema validation, with a dataclass, TypedDict plus manual checks, or Pydantic/JSON Schema. On validation failure, log a safe field path and contract version; do not log multi-megabyte raw responses in full.

## What to log

Recommended structured fields:

| Field | Example | Note |
| --- | --- | --- |
| `event` | `api_request_finished` | Stable event name. |
| `service` | `vector_store` | Logical service name; it need not include the full host. |
| `method` | `POST` | HTTP method. |
| `route` | `/v1/jobs/{id}` | Route template; avoids high-cardinality values. |
| `status_code` | `503` | Empty when no response exists. |
| `duration_ms` | `842` | State whether it is one attempt or total duration. |
| `attempt` | `2` | Current attempt number. |
| `request_id` | Server-provided ID | Correlates a support case. |
| `error_kind` | `read_timeout` | Stable classification. |
| `retry_wait_ms` | `1200` | When a retry occurs. |

Do not log Authorization, Cookie, API keys, complete signed URLs, user private data, unredacted prompts/documents, or oversized bodies. A header allowlist is safer than “log everything then remove sensitive fields,” because future headers can be sensitive too.

## Division of labor: logs, metrics, and traces

- **Logs** answer “what happened on this call?” and suit request IDs and error context.
- **Metrics** answer “is the system abnormal overall?” for example request count, success rate, status counts, latency quantiles, retry rate, and rate-limit rate.
- **Traces** connect an Agent, model, tools, and multiple API calls into one end-to-end task.

Do not use user ID, full URL, or request ID as a metric label; high cardinality creates cost. Normalize an endpoint to a route such as `/items/{id}`.

## Investigation order

1. **Reproduction boundary**: which environment, endpoint, method, time window, and frequency?
2. **Local evidence**: error category, status, duration, attempts, and server request ID—while hiding credentials.
3. **Request contract**: base URL, API version, authentication header, content type, parameter types, and required fields.
4. **Response evidence**: status, content type, documented machine code, rate-limit headers, and only necessary excerpts.
5. **Dependency state**: an official status page or internal monitoring. Do not infer a global outage from one 503.
6. **Minimum reproduction**: remove Agent and framework layers and call directly with a fixed non-sensitive payload.
7. **Compare changes**: did SDK, configuration, permission, network, or proxy just change?
8. **State a conclusion**: separate proven cause, reasonable inference, and still unknown items.

### Typical symptoms

- `200` but `.json()` fails: you may have an HTML login/proxy page; inspect content type and final URL first.
- Intermittent 401: possible token-refresh race, clock issue, or wrong environment; do not hide it with simple retry.
- Higher latency and retry rate: retries may be amplifying server pressure; inspect first-attempt metrics first.
- 429 only in batch jobs: inspect global concurrency and whether each worker rate-limits independently.
- Duplicate resources after POST timeout: confirm reuse of the idempotency key and server deduplication window.

## Common mistakes

- `except Exception: return None`, merging “not found” and “the service is down” into one result.
- Call only `raise_for_status()` and retain no safely recordable machine code or request ID.
- Print every header and body during diagnosis.
- Decide retry from an error-message string alone.
- Automatically follow an unknown redirect and treat the final response as success from the original endpoint.
- Log only “failed” with no route template, status, duration, or attempts.
- Turn every failure into a user-visible stack trace, leaking local paths and implementation details.

## Exercises and self-check

1. Map 401, 429, invalid JSON, a schema missing a field, and read timeout to exception types.
2. Design one structured failure log that excludes tokens, query signatures, and request body.
3. Rewrite an `except Exception` example into “specific exception → client exception → upper-layer decision.”
4. Explain why `request_id` suits a log field but usually not a metric label.

- [ ] I can distinguish configuration, construction, transport, HTTP, representation, schema, and business errors.
- [ ] I can design a small set of stable client exceptions.
- [ ] I know the separate questions answered by logs, metrics, and traces.
- [ ] I can provide reproducible evidence without exposing credentials.

## References

- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [Requests Errors and Exceptions](https://docs.python-requests.org/en/stable/user/quickstart/#errors-and-exceptions)
- [Requests API: Exceptions](https://docs.python-requests.org/en/stable/api/#exceptions)

Retrieved on 2026-07-22. Next: [[api/project-reliable-api-client|Project: reliable API client]].

