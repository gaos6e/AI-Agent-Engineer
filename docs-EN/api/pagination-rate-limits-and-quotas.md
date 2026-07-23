---
title: "Pagination, Rate Limits, and Quotas"
tags:
  - ai-agent-engineer
  - api
  - pagination
  - rate-limit
aliases:
  - API pagination
  - API rate limits
source_checked: 2026-07-22
lang: en
translation_key: API/04-分页限流与配额.md
translation_source_hash: af5d891ac2f31c0456067d0b06925328b2531e8a83c4586403b209f554aeebee
translation_route: zh-CN/API/04-分页限流与配额
translation_default_route: zh-CN/API/04-分页限流与配额
---

# Pagination, Rate Limits, and Quotas

## Objective

Learn to read a list API completely and within defined bounds; understand offset/page, cursor, and link pagination; distinguish rate limits from quotas; and respect server guidance for 429 rather than creating a thundering herd with concurrent retries.

## Why an API does not return every result at once

Suppose a knowledge base has one million documents. Returning them all at once consumes server memory, network bandwidth, and client memory, and makes recovery from an intermediate failure difficult. Pagination splits results into finite responses. The cost is that you must save the correct next-page position, account for data changes, and put a termination boundary around the loop.

## Three common pagination styles

### Page or offset pagination

```http
GET /items?page=3&page_size=50
GET /items?offset=100&limit=50
```

It is easy to jump to a particular position and suits relatively stable, small data sets. If earlier data is inserted or deleted while you read, an offset can cause duplicates or omissions. Deep offset queries can also be expensive for the server.

### Cursor pagination

```json
{
  "items": [{"id": "a1"}, {"id": "a2"}],
  "next_cursor": "opaque-value"
}
```

JSON does not allow valid end-of-line comments: `items` is the current page's resource array and `next_cursor` is the opaque continuation position issued by the server. The client returns it unchanged; it must not infer a page number from the string or modify it.

Return the opaque cursor unchanged in the next request:

```http
GET /items?cursor=opaque-value&limit=50
```

The client should not parse or alter a cursor. It is often better suited than an offset for data that changes continuously, but snapshot consistency and cursor expiry are entirely contract-dependent.

### Link or next-URL pagination

The server supplies the next-page URL directly, perhaps in a JSON `next` field or a variably standardized `Link` header. Verify that the next URL still belongs to the expected host before sending credentials, so Authorization is not accidentally forwarded to an untrusted host.

> [!note] There is no universal field name
> APIs can use `next_cursor`, `has_more`, `page_token`, `next`, or `Link`. Pagination parameters and termination conditions come from the target API's official documentation.

## A cursor loop that fails closed

```python
from collections.abc import Iterator  # State that the function yields items on demand instead of loading every page into memory first.
from typing import Any  # Represent JSON-object fields that can contain several valid JSON value types.

import requests  # Use Requests to make paginated calls and distinguish its JSON decoding exception.


def parse_json_object(response: requests.Response) -> dict[str, Any]:  # Verify the minimum pagination contract: an HTTP response with a top-level JSON object.
    response.raise_for_status()  # Reject 4xx/5xx before parsing an error page as successful pagination data.
    media_type = (  # Extract the primary media type without charset parameters.
        response.headers.get("Content-Type", "")  # Let a missing header participate as an empty string in uniform rejection.
        .split(";", 1)[0]  # Turn `application/json; charset=utf-8` into the primary type.
        .strip()  # Remove server-provided surrounding whitespace.
        .lower()  # Normalize case before comparison.
    )
    if media_type != "application/json" and not media_type.endswith("+json"):  # Accept vendor JSON types such as problem+json as well.
        raise ValueError("expected a JSON response")  # Keep HTML or text error pages out of JSON decoding.
    try:  # JSON decoding can still fail, for example when a gateway truncates a response body.
        value = response.json()  # Use Requests' JSON decoder to produce a Python value.
    except requests.exceptions.JSONDecodeError as exc:  # Catch the library-defined JSON parsing failure.
        raise ValueError("response declared JSON but could not be parsed") from exc  # Preserve causality while exposing a stable course-level error.
    if not isinstance(value, dict):  # The pagination protocol requires a top-level object, not an array or string.
        raise ValueError("pagination response must be a JSON object")  # Reject a shape error before safely reading fields.
    return value  # Return an object that passed the minimum protocol check; the caller validates its fields.


def iter_items(  # Define a pagination generator with three protections: page count, item count, and repeated cursors.
    base_url: str,  # API base URL from trusted configuration.
    *,  # Require later limiting parameters by keyword to reduce positional mistakes.
    max_pages: int = 100,  # Cap the number of requests to stop a server that never terminates.
    max_items: int = 1_000,  # Cap total emitted items to stop an unexpectedly huge page or unbounded downstream work.
) -> Iterator[dict[str, Any]]:  # Yield one item object at a time after its minimum shape check.
    if type(max_pages) is not int or max_pages < 1:  # bool is an int subclass, so use type for strict validation.
        raise ValueError("max_pages must be a positive integer")  # Reject zero, negative, float, and Boolean page budgets.
    if type(max_items) is not int or max_items < 1:  # Validate the item budget just as strictly.
        raise ValueError("max_items must be a positive integer")  # Do not silently replace an invalid budget with a default.

    cursor: str | None = None  # The first page usually has no cursor; later pages use the server-returned value unchanged.
    seen_cursors: set[str] = set()  # Keep received next-page cursors to detect loops.
    yielded = 0  # Count items already handed to the caller.

    with requests.Session() as session:  # This function owns the Session and the context manager closes it on completion or failure.
        for _ in range(max_pages):  # Issue at most max_pages requests; if no termination appears, fail after the budget.
            params = {"limit": 50}  # Request a page size explicitly chosen by this example.
            if cursor is not None:  # Do not send a cursor for the first page.
                params["cursor"] = cursor  # Return the server-issued cursor unchanged; do not parse, increment, or rewrite it.

            response = session.get(  # Request the current page with the connection pool.
                f"{base_url.rstrip('/')}/items",  # Remove a trailing slash before adding the fixed resource path.
                params=params,  # Let Requests encode the query string.
                headers={"Accept": "application/json"},  # This client explicitly accepts JSON only.
                timeout=(3.05, 15),  # Every page has connection and read timeouts.
            )
            page = parse_json_object(response)  # Validate HTTP, media type, and top-level JSON shape before reading items.

            items = page.get("items")  # Read the contract's current-page resource array.
            if not isinstance(items, list):  # A missing or type-drifted field is not an empty page.
                raise ValueError("response is missing the items array")  # Stop instead of silently losing data under a broken contract.
            for item in items:  # Process the current page one item at a time to keep memory use streaming.
                if not isinstance(item, dict):  # This example requires each item to be a JSON object.
                    raise ValueError("items must contain only JSON objects")  # Scalar and array items need a different business parser.
                if yielded >= max_items:  # Check the total budget before yielding an item beyond caller capacity.
                    raise RuntimeError(f"maximum item count {max_items} exceeded")  # Budget exhaustion is a controlled failure, not a reason to keep consuming memory.
                yielded += 1  # Increment only when a valid item is about to be delivered.
                yield item  # Let the caller consume while fetching rather than collect every page.

            next_cursor = page.get("next_cursor")  # Read the continuation position supplied by the server.
            if next_cursor is None:  # This example uses null as normal termination.
                return  # End the generator and close the Session automatically when there is no next page.
            if not isinstance(next_cursor, str) or not next_cursor:  # Empty or non-string cursors are not trustworthy.
                raise ValueError("next_cursor has an invalid format")  # Do not continue with a guessed default position.
            if next_cursor in seen_cursors:  # A repeated cursor would create an infinite loop and duplicate import.
                raise RuntimeError("server returned a repeated next_cursor; stopping")  # Stop immediately and investigate the server contract.

            seen_cursors.add(next_cursor)  # Record the new cursor for next-round loop detection.
            cursor = next_cursor  # Use it as the sole continuation token for the following page.

    raise RuntimeError(f"maximum page count {max_pages} exceeded")  # Fail closed if the page budget is exhausted without a terminating cursor.
```

Key protections:

- `max_pages` prevents an infinite loop caused by a broken contract.
- `max_items` prevents a finite number of abnormally huge pages or unbounded downstream processing.
- Record seen cursors and stop immediately if one repeats.
- Validate a successful status, JSON media type, and top-level object before validating `items`, elements, and cursor types.
- Use a generator to consume items incrementally instead of loading every page into memory.
- For resumable work, persist the **next-page cursor** and processing progress safely.

Even cursor pagination can return duplicate resources. An import job can deduplicate by a stable resource ID and must define the business rule for “skip duplicate” versus “update existing.”

## Rate limits and quotas are not the same

- **Rate limit**: constrains request rate or concurrency in a short window, for example requests per minute.
- **Quota**: constrains accumulated use over a longer period, for example monthly requests, tokens, or spending budget.
- **Concurrency limit**: constrains the number of in-flight requests at once.

An API can bucket these by account, project, model, user, IP, or endpoint. Header names and counting algorithms are not standardized; do not assume `X-RateLimit-Remaining` exists.

## Handling 429

RFC 6585 defines `429 Too Many Requests`, and a response can include `Retry-After`. The header can be a number of seconds or an HTTP date:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

Client strategy:

1. Read the target API's rate-limit documentation first.
2. If a valid `Retry-After` is present and within the current wait budget, wait the full recommended time. If it exceeds a deadline or wait budget, stop the current retry and defer to an outer layer; do not truncate it and retry early.
3. If the header is absent, use exponential backoff with jitter.
4. Reduce global request rate or concurrency rather than letting every worker retry aggressively on its own.
5. Set a maximum attempt count or total retry budget; after it is exhausted, record a recoverable failure.
6. Record status, route template, attempt count, wait time, and request ID, never a token.

If 429 means “monthly quota exhausted,” retrying in seconds is pointless. A machine error code, reset time, and management-console metrics help distinguish a short-term rate limit from a longer quota.

## Proactive rate limiting

Waiting for 429 before slowing down wastes calls. A batch process can use:

- a fixed worker count to constrain concurrency;
- a token bucket or leaky bucket to control global rate;
- dynamic slowdown from server remaining-capacity data only when the documented header semantics are clear;
- separate queues for interactive requests and background batch work; and
- coalescing duplicate requests for the same resource, caching, or batch endpoints.

Agent loops especially need protection against a model repeatedly choosing the same tool. API-client throttling can reduce the consequence, but the Agent layer should also cap tool-call count and total budget for one task.

## Recovering when pagination and rate limits combine

Save a cursor only after successfully processing its page. If the next page receives 429 or a transient 5xx, retry the current page; after a process restart, continue from the saved cursor. Writing to a downstream system must also be duplicate-safe, for example by upserting on a source resource ID.

```text
fetch a page -> validate -> write/process -> save next_cursor -> fetch next page
                              ^ advance the checkpoint only after success
```

## Common mistakes

- Always stop on an empty `items`: some contracts use `next_cursor` as the actual termination rule. Follow the documentation.
- Continue after a repeated cursor.
- Collect every page before processing, creating a memory peak and requiring full restart after failure.
- Let every thread retry 429 independently, immediately creating more requests.
- Treat every 429 as a short-term rate limit and ignore exhausted quota.
- Log a complete next URL that can contain a sensitive signed query; record safe fields only.

## Exercises and self-check

1. Modify the example to persist the last `next_cursor` in a local state file. Explain when to write it so pages are not skipped.
2. Design a loop that reads at most 500 items or 10 pages, whichever comes first.
3. Draw a flow for three workers sharing one global rate limiter.
4. If a process crashes after processing page four, explain how to avoid duplicate downstream records.

- [ ] I can compare offset and cursor tradeoffs.
- [ ] I set a page limit, repeated-cursor detection, and schema validation for pagination.
- [ ] I can distinguish a rate limit, quota, and concurrency limit.
- [ ] I know 429 does not mean retry forever.

## References

- [RFC 6585: 429 Too Many Requests](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)
- [RFC 9110: Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after)
- [Requests Advanced Usage](https://docs.python-requests.org/en/stable/user/advanced/)

Retrieved on 2026-07-22. Next: [[api/timeouts-retries-backoff-and-idempotency|Timeouts, retries, backoff, and idempotency]].

