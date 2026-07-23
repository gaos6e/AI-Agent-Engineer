---
title: "HTTP Requests and Responses"
tags:
  - ai-agent-engineer
  - api
  - http
aliases:
  - HTTP API fundamentals
source_checked: 2026-07-22
lang: en
translation_key: API/01-HTTP请求与响应.md
translation_source_hash: d099370bb590fd0f3ba4af4569e3f43e5180556f083a49af0df11849ccec6a99
translation_route: zh-CN/API/01-HTTP请求与响应
translation_default_route: zh-CN/API/01-HTTP请求与响应
---

# HTTP Requests and Responses

## Objective

Learn to break an HTTP API call into its method, URL, headers, body, status code, and response body, understand each responsibility, and send a minimum request with Python.

## First intuition: a formatted question and answer

Think of an API as a service counter: the URL is the counter's address, the HTTP method expresses intent, headers are the instructions on the outside of an envelope, and the body is the submitted material. A response status code first tells you the result category; response headers carry metadata; the response body carries data or error detail.

HTTP is a stateless request/response protocol. “Stateless” here does not mean that a service never stores data. It means the semantics of each request should be understandable independently; the application can separately manage state such as login sessions and database records.

```text
client -- request --> server
client <-- response -- server
```

## The five parts of a request

Suppose you need the second page of tasks:

```http
GET /v1/tasks?cursor=page-2&limit=20 HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer <token>
```

### 1. Method

| Method | Common intent | Safe method | Idempotent in RFC semantics |
| --- | --- | --- | --- |
| `GET` | Read a resource | Yes | Yes |
| `HEAD` | Read response metadata only | Yes | Yes |
| `POST` | Create a resource or trigger an action | No | No |
| `PUT` | Create or replace a resource as a whole with the supplied representation | No | Yes |
| `PATCH` | Apply a partial modification | No | Not necessarily |
| `DELETE` | Delete a resource | No | Yes |

“Safe” means the client did not request a server-state change; it does not imply no logging or billing. “Idempotent” means the **intended effect** of repeating the same request is equivalent to one execution; it does not guarantee an identical response every time. Do not infer business behavior from a method name alone—read the API documentation.

### 2. URL

```text
https://api.example.com/v1/tasks?cursor=page-2&limit=20
\___/   \_____________/\_______/ \____________________/
scheme       host         path            query
```

- `scheme`: production APIs should normally use `https`.
- `host`: the machine hosting the service.
- `path`: the resource or operation path.
- `query`: parameters such as filters, ordering, cursors, and page size.

Pass query parameters with `params=` in Python rather than hand-building `?` and `&`:

```python
import requests  # Import Requests so it encodes query parameters safely and sends the HTTP request.

response = requests.get(  # Issue a GET request; this address only demonstrates parameter encoding and is not a production endpoint.
    "https://example.com/v1/tasks",  # Keep the base URL separate instead of hand-building a query string.
    params={"cursor": "page-2", "limit": 20},  # Let the library URL-encode the cursor and page size correctly.
    timeout=(3.05, 15),  # Set separate limits for connection and read waits to avoid indefinite blocking.
)
print(response.request.url)  # Print the actual URL sent to see how params become query parameters.
```

### 3. Headers

Headers are metadata that is not the business payload itself. Field names are case-insensitive. Common fields are:

| Header | Purpose |
| --- | --- |
| `Accept: application/json` | The client wants JSON in the response. |
| `Content-Type: application/json` | The body currently being sent is JSON. |
| `Authorization: Bearer ...` | Carries access credentials. |
| `User-Agent` | Identifies the client program and version. |
| `Idempotency-Key` | Some APIs use it to identify repeated create requests; support is determined by the API documentation. |
| `Retry-After` | The server's suggested wait before trying again. |
| `X-Request-ID` or vendor equivalent | Diagnostic identifier for one call; the name is not a universal standard. |

`Accept` says what you want to receive; `Content-Type` says what you are sending. Do not confuse them.

### 4. Body

GET usually uses query parameters. Creating a resource or invoking an operation often uses a JSON body:

```python
payload = {"title": "Study APIs", "priority": 2}  # Represent the create-request body as a Python dictionary that will be JSON serialized.

response = requests.post(  # Issue a create operation; production code must still decide from the contract whether to use an idempotency key.
    "https://example.com/v1/tasks",  # Example address for the resource being written.
    json=payload,  # Requests handles JSON encoding and an appropriate Content-Type.
    timeout=(3.05, 30),  # A write can need a longer read budget, but still needs an upper bound.
)
```

Requests `json=` serializes a Python object and sets the JSON content type; `data=` is commonly for forms or already encoded data. JSON supports only a limited set of data types, so convert objects such as `datetime` and `Path` first.

### 5. API contract

A contract is the agreement both caller and service obey: paths, parameter types, required fields, authentication, response schema, error format, rate limits, and version policy. Being able to send HTTP is not the same as meeting the contract. For example, the service may require `limit` from 1 to 100 or restrict `model` to values the project can access.

## The three parts of a response

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: req_123

{"items": [{"id": "t1", "title": "Study APIs"}], "next_cursor": null}
```

### Status code

Read the hundred-class first, then the precise meaning:

- `1xx`: provisional information.
- `2xx`: the request was successfully handled under its applicable semantics.
- `3xx`: redirection or caching.
- `4xx`: the client request, authentication, authorization, or business condition was not satisfied.
- `5xx`: the server did not complete a valid request.

Status code is an important program branch but does not express every business detail. An error body can carry a machine-readable code, field location, and request ID.

### Headers and body

```python
media_type = (  # Extract the primary media type from Content-Type without charset or other parameters.
    response.headers.get("Content-Type", "")  # Use an empty string instead of raising KeyError when the header is absent.
    .split(";", 1)[0]  # Turn `application/json; charset=utf-8` into `application/json`.
    .strip()  # Remove possible surrounding server whitespace.
    .lower()  # Normalize case for comparison with standard media types.
)
request_id = response.headers.get("X-Request-ID")  # Retain a server diagnostic ID that is safe to log; do not retain credentials.

response.raise_for_status()  # Turn 4xx/5xx into exceptions before treating an error page as successful data.
if media_type != "application/json" and not media_type.endswith("+json"):  # Also accept vendor-defined `application/*+json` types.
    raise ValueError("expected JSON but received a different media type")  # Do not call .json() directly on HTML error pages or other non-JSON content.
data = response.json()  # Parse JSON only after HTTP success and a plausible media type; validate the schema next.
```

`response.json()` succeeding proves only that the body parses as JSON; it does not prove HTTP or business success. Handle the status code first, then validate the schema. Conversely, some 204 responses have no body, so do not call `.json()` unconditionally.

## Reconstructing one call from documentation

For any API document, record this checklist:

1. Base URL and version.
2. Method and path.
3. Authentication method and scope.
4. Path, query, header, and body parameters, including required ones.
5. Success status codes and response schema.
6. Error status codes and error body.
7. Timeout, pagination, rate-limit, retry, and idempotency rules.
8. Whether there is an SDK and whether it hides any of the preceding details.

## Common mistakes

- Put a token in the URL: URLs can enter browser history, proxy logs, and monitoring systems. Use the documented `Authorization` header instead.
- Omit timeouts: Requests does not automatically choose a sensible request timeout for you.
- Check only `status_code == 200`: creation can return 201 and a bodyless success can return 204.
- Call `.json()` immediately on every response: a gateway error can be HTML and 204 can be empty.
- Hand-build query strings: spaces, non-ASCII text, and `&` need encoding; give that job to the client library.
- Guess semantics from a verb in the URL: follow the API documentation and HTTP method.

## Exercises

1. Break a request into method, scheme, host, path, query, headers, and body.
2. Explain the distinction between `Accept` and `Content-Type`.
3. Explain why DELETE's idempotency does not mean “it returns the same status code every time.”
4. Build a Requests `PreparedRequest` and print its URL and headers without sending it:

```python
from requests import Request, Session  # Import Request to construct a request and Session to prepare it without network traffic.

request = Request("GET", "https://example.com/items", params={"q": "AI Agent"})  # Create an unsent GET request.
prepared = Session().prepare_request(request)  # Have Session apply default headers and URL encoding without issuing a network request.
print(prepared.url)  # Inspect the final URL and confirm that spaces and other characters are encoded.
```

## Self-check

- [ ] I can identify the responsibility of each request and response component.
- [ ] I can explain the difference between safe and idempotent methods.
- [ ] I know that parsable JSON does not mean the call succeeded.
- [ ] I can write a call checklist from one page of API documentation.

## References

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), especially the message, method, and status-code sections.
- [Requests Quickstart](https://docs.python-requests.org/en/stable/user/quickstart/).

Retrieved on 2026-07-22. Next: [[api/requests-client-session-and-contract-reading|Requests client, Session, and contract reading]].

