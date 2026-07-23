---
title: "Authentication, Status Codes, and Credential Security"
tags:
  - ai-agent-engineer
  - api
  - authentication
aliases:
  - API authentication
  - HTTP status codes
source_checked: 2026-07-22
lang: en
translation_key: API/03-认证状态码与凭据安全.md
translation_source_hash: 5c7d68542ed18b7e5fabf97650c3170acd5332f82f074e5943d83692c7e134d3
translation_route: zh-CN/API/03-认证状态码与凭据安全
translation_default_route: zh-CN/API/03-认证状态码与凭据安全
---

# Authentication, Status Codes, and Credential Security

## Objective

Understand that “who are you?” and “what are you allowed to do?” are distinct questions. Use API keys, Basic Auth, and Bearer tokens as documentation specifies; choose an appropriate action for common status codes; and avoid putting credentials in code, URLs, logs, or repositories.

## Authentication and authorization

- **Authentication** proves who a caller is, for example by validating an API key or access token.
- **Authorization** decides whether that identity can read a resource or take an action, often based on roles, scopes, organization, and resource ownership.

An otherwise valid token with insufficient scope is normally an authorization problem. Logging in again does not necessarily solve it.

## Four common mechanisms

### API key

An API key commonly identifies a project, application, or account. The exact header name is vendor-defined; a common form is:

```python
headers = {"X-API-Key": api_key}  # Put the API key in the header required by this hypothetical service's contract, never in the URL.
```

Some services require `Authorization: Bearer <api-key>`. Even if the value is called an API key, pass it exactly as that service documents; do not invent a header name. API keys suit server-to-server calls, but usually do not represent the full authorization flow in which a user delegates access to an application.

### HTTP Basic Auth

Basic Auth combines and encodes a username and password. Encoding is not encryption, so HTTPS is mandatory. Use Requests `auth=` rather than composing Base64 manually:

```python
import requests  # Import Requests so it constructs the HTTP Basic Auth header according to the specification.

response = requests.get(  # Request a protected resource with GET.
    "https://example.com/protected",  # Example HTTPS address; use the host declared by real project documentation.
    auth=("username", "password"),  # Let Requests generate Basic Auth instead of hand-building Base64.
    timeout=(3.05, 15),  # Bound connection and read waits so a network failure cannot block forever.
)
```

### Bearer token

Bearer means that possession is sufficient for use. RFC 6750 defines the common header form:

```python
headers = {"Authorization": f"Bearer {access_token}"}  # Carry the access token under the Bearer convention; never print it or place it in a query string.
```

Anyone who obtains a token can often impersonate its holder, so use HTTPS, minimal scope, short lifetimes, secure storage, and rotation. Do not put a Bearer token in a query string; URLs more readily enter access logs, histories, and monitoring data.

### OAuth 2.0

OAuth 2.0 is an authorization framework, not one token format. Typical parties are the resource owner, client, authorization server, and resource server. The client obtains an access token through an authorization flow and uses it to access a resource. A refresh token, if issued, is used only with the authorization server to obtain a new access token; it must not be sent to an ordinary resource API.

At this stage, master these boundaries:

- An access token has scope, lifetime, and target-resource limits.
- User-delegation and machine-identity scenarios use different authorization flows.
- Do not hand-write OAuth redirects, security checks, or token-refresh details. Prefer the service's official SDK or a mature OAuth library.
- OAuth security guidance evolves; when implementing, consult both service documentation and current BCP material such as RFC 9700.

## Managing local development credentials in Windows

Code reads credentials only from environment variables:

```python
import os  # Import os to read credentials from the current process environment rather than hard-coding them in source.

api_key = os.environ.get("EXAMPLE_API_KEY")  # Read the variable value only; do not echo it in logs.
if not api_key:  # A missing or empty value must not proceed to a potentially unauthenticated request.
    raise RuntimeError("EXAMPLE_API_KEY is not configured")  # Name the variable only; do not disclose sensitive content.
```

Set a placeholder in the current PowerShell process:

```powershell
$env:EXAMPLE_API_KEY = "replace-with-local-secret"  # Set a placeholder only for this PowerShell process; never place a real value in history or documentation.
python .\app.py  # Run a local script that reads credentials from its environment.
```

The process variable disappears when the terminal closes. If a project uses `.env`, commit only `.env.example`, add `.env` to `.gitignore`, and verify that Git history has not already tracked it. In production, use the deployment platform's secret manager rather than baking tokens into an image or config file.

> [!danger] If a credential leaks
> Removing a string from a file does not remove the risk. Stop spreading it, revoke or rotate it through the provider's process, and handle Git history only with explicit authorization. Do not paste the original value again into chats, logs, or screenshots.

## Status codes are decision inputs

| Status code | Common meaning | Client's first action |
| --- | --- | --- |
| `200 OK` | Successful response with a body | Validate content type and data shape. |
| `201 Created` | Resource created | Read the body or `Location`, if supplied. |
| `202 Accepted` | Accepted, possibly for asynchronous processing | Poll a task or wait for a callback as documented. |
| `204 No Content` | Success with no body | Do not call `.json()`. |
| `301/302/307/308` | Redirect | Check whether it is expected; sensitive headers must not be misforwarded to another host. |
| `400 Bad Request` | Invalid request syntax or parameters | Correct the request; do not blindly retry. |
| `401 Unauthorized` | Missing or unacceptable authentication credentials | Check that a token exists, is valid, and is sent to the correct service; refresh through the right flow. |
| `403 Forbidden` | The identity is known but cannot access, or policy denies it | Check scope, role, resource ownership, and policy. |
| `404 Not Found` | Resource does not exist, or its existence is intentionally hidden | Check ID, path, version, and permissions. |
| `409 Conflict` | Conflicts with current resource state | Read the machine code; it can indicate version conflict or duplicate operation. |
| `422 Unprocessable Content` | Syntax is readable but field semantics or validation fail | Correct the payload from field errors. |
| `429 Too Many Requests` | Rate limit reached | Respect `Retry-After`; reduce rate or concurrency. |
| `500 Internal Server Error` | Unexpected server-side failure | Retry conditionally and retain the request ID. |
| `502/503/504` | Gateway failure, unavailable service, or timeout | Often candidates for transient recovery, still constrained by retry budget and idempotency. |

The business detail of one status code varies across APIs. Also read documented machine error codes, such as `invalid_scope` or `rate_limit_exceeded`; do not parse a natural-language `message` that can be translated or rewritten.

### Investigation order for 401 and 403

1. Was the request sent to the correct host and environment (test or production)?
2. Does it use the documented header and scheme?
3. Is the token expired, revoked, or from another project?
4. Do the token's scope, role, organization, and resource ownership match?
5. Did the server return `WWW-Authenticate` or a machine-readable error code?

Do not print a full token to “confirm it was read.” Log a Boolean such as `credential_configured=true`; if necessary, log the local configuration-source name rather than the value.

## A safe request skeleton

```python
import os  # Read an access token injected by the deployment system from the process environment.
from typing import Any  # Describe a JSON object whose fields can contain several value types.

import requests  # Use Requests to send HTTP requests and handle status codes.


def fetch_profile(base_url: str) -> dict[str, Any]:  # Read the current subject's profile from the supplied API base URL.
    token = os.environ.get("EXAMPLE_ACCESS_TOKEN")  # Obtain the token only from the environment, without spreading it as a function argument or log field.
    if not token:  # Do not attempt anonymous or malformed calls without trusted credentials.
        raise RuntimeError("EXAMPLE_ACCESS_TOKEN is not configured")  # Mention only the variable name, never token content.

    response = requests.get(  # Request the profile; a real project must separately choose its retry and redirect policy.
        f"{base_url.rstrip('/')}/v1/profile",  # Normalize a trailing slash before adding the fixed resource path.
        headers={  # Send only the minimum headers required by the endpoint.
            "Accept": "application/json",  # Ask the server for a JSON representation.
            "Authorization": f"Bearer {token}",  # Send the token in the documented Bearer header.
            "User-Agent": "agent-learning-client/0.1",  # Provide a version identifier that contains no sensitive data.
        },
        timeout=(3.05, 15),  # Set independent connection and read timeouts.
    )
    response.raise_for_status()  # Turn HTTP 4xx/5xx into exceptions before an error body reaches a success branch.
    media_type = (  # Parse the primary media type of the successful response.
        response.headers.get("Content-Type", "")  # Use an empty string when the header is absent so it is uniformly rejected.
        .split(";", 1)[0]  # Strip charset and similar parameters.
        .strip()  # Remove surrounding whitespace.
        .lower()  # Normalize case for comparison.
    )
    if media_type != "application/json" and not media_type.endswith("+json"):  # Accept standard JSON and vendor JSON media types.
        raise ValueError("profile endpoint returned an unexpected media type")  # Keep HTML and other content out of the JSON decoder.
    value = response.json()  # Parse a response that has passed HTTP and media-type checks.
    if not isinstance(value, dict):  # The minimum schema contract for this endpoint requires a top-level object.
        raise ValueError("profile endpoint must return a JSON object")  # Arrays and scalars require separate contract handling.
    return value  # Return profile data that passed the minimum shape check.
```

This skeleton does not yet handle retries, field-level schema, or an error body. Its focus is to read credentials from the environment, send them only in the documented header, set timeouts, validate JSON media type and top-level shape after HTTP success, and leak nothing through logging.

## Common mistakes

- Put an API key in an example, Markdown file, notebook output, or exception message.
- Refresh a token indefinitely after 401; refresh failure also needs termination and alerting.
- Retry a 403 as a service failure; permission does not appear after a few seconds.
- Disable TLS certificate verification for “easier debugging.”
- Use a production token for a local demo or test data.
- Catch `HTTPError` and print only `str(exc)`, losing status, request ID, and safely recordable error code.

## Exercises and self-check

1. Write an `.env.example` for a hypothetical API containing only an empty `EXAMPLE_API_KEY=`. Explain why it cannot contain a real value.
2. For every 4xx/5xx status in the table, decide whether to retry automatically, whether manual/configuration repair is required, and what to record.
3. Explain which services should receive an access token and a refresh token.

- [ ] I can distinguish authentication from authorization.
- [ ] I can explain the boundaries among API keys, Basic, Bearer, and OAuth.
- [ ] I choose different actions for 401, 403, 429, and 503.
- [ ] I avoid credential leakage in logs and exceptions.

## References

- [RFC 9110: HTTP Authentication and Status Codes](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 6750: OAuth 2.0 Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750.html)
- [RFC 6749: The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749.html)
- [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700.html)
- [Requests Authentication](https://docs.python-requests.org/en/stable/user/authentication/)

Retrieved on 2026-07-22. Next: [[api/pagination-rate-limits-and-quotas|Pagination, rate limits, and quotas]].

