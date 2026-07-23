---
title: "API Learning Path"
tags:
  - ai-agent-engineer
  - api
  - http
aliases:
  - API
  - API learning path
source_checked: 2026-07-22
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 5
ai_learning_schema: 2
ai_learning_id: api
ai_learning_domain: foundations
ai_learning_catalog_order: 500
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 40
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 40
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 40
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 40
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: API/00-目录.md
translation_source_hash: 92dc1a06c5ea370b762d33add82819a3abd7256b14ce95128caa35b1c78a74cd
translation_route: zh-CN/API/00-目录
translation_default_route: zh-CN/API/00-目录
---

# API Learning Path

## Course overview

An API (Application Programming Interface) is a defined interaction boundary between programs. This course follows the most common kind, the HTTP API: first read requests and responses, then learn the Requests client, authentication, pagination, rate limits, and reliability, and finally complete a Python client that paginates automatically, retries within a finite budget, and classifies failures. The vendor API notes and the longer Requests Quickstart belong to the reference layer; do not begin your first API lesson by memorizing one vendor SDK's parameters.

> [!info] Currency of material
> The general HTTP and Requests material in this course was last checked on **2026-07-22**. RFC protocol semantics are comparatively stable. Vendor SDKs, model names, and endpoints follow the `source_checked` date on each vendor page; this course-wide date is not a pre-run verification for them. Check the relevant official documentation before use.

## Where this course fits

API belongs to the Engineering foundations knowledge domain. Start once you can work with Python functions and exceptions and JSON objects and arrays; it connects later LLM APIs, tool calling, MCP, and RAG services. Those are capabilities, not a requirement to finish an entire Python or JSON course first. Agents commonly call remote models, search services, database gateways, or self-hosted tools. Sending one successful request is not enough for a recoverable Agent system.

## Learning objectives

After completing the course, you should be able to:

- describe a request as “method + URL + headers + body” and a response as “status code + headers + body”;
- call a JSON API with Requests and always set timeouts;
- distinguish the proper use of API keys, Basic Auth, Bearer tokens, and OAuth 2.0;
- handle pagination, 429 rate limiting, connection and read timeouts, retries, and exponential backoff correctly;
- decide whether an operation is appropriate to retry and use an idempotency key to protect supported create operations;
- keep transport, HTTP, data-format, and business errors separate; and
- retain enough request identifiers, timing, and error evidence without logging credentials.

## Prerequisites

- Be able to run a Python file and understand functions, exceptions, dictionaries, and lists.
- Understand JSON objects and arrays in [[json/00-index|JSON]].
- Be able to create a virtual environment in PowerShell 7:

```powershell
python -m venv .venv  # Create an isolated environment in the current practice directory so project dependencies do not pollute system Python.
.\.venv\Scripts\Activate.ps1  # Activate only the environment just created in this PowerShell session.
python -m pip install --upgrade pip  # Update the installer paired with the current interpreter.
python -m pip install requests  # Install the HTTP client library used by later examples in this course.
```

If PowerShell blocks the activation script the first time, you can temporarily use `Set-ExecutionPolicy -Scope Process Bypass` in the current process. Do not change the machine-wide policy for one project.

## Recommended sequence

1. [[api/http-requests-and-responses|HTTP requests and responses]]: build a protocol mental model for methods, URLs, headers, bodies, and status codes.
2. [[api/requests-client-session-and-contract-reading|Requests client, Session, and contract reading]]: create an isolated environment and understand Session, TLS, redirects, OpenAPI, and test doubles.
3. [[api/authentication-status-codes-and-credential-security|Authentication, status codes, and credential security]]: make credentialed requests and choose the next action from the response.
4. [[api/pagination-rate-limits-and-quotas|Pagination, rate limits, and quotas]]: retrieve a list completely while respecting the server's pace.
5. [[api/timeouts-retries-backoff-and-idempotency|Timeouts, retries, backoff, and idempotency]]: recover transient failures only when it is safe to do so.
6. [[api/error-classification-logging-and-troubleshooting|Error classification, logging, and troubleshooting]]: make failures diagnosable instead of swallowing them with one `except Exception`.
7. [[api/project-reliable-api-client|Project: reliable API client]]: complete pagination, retry, and idempotent creation against a local mock API.
8. [[api/exercises-self-assessment-and-mastery|Exercises, self-assessment, and mastery criteria]]: work independently and verify that you genuinely understand the material.

## Vendor API reference layer

Read these notes after mastering the general path, as a project requires. Model names, SDK methods, and pricing rules are dynamic facts; revisit the official source listed by the relevant note before running code.

- [[api/ai-api-reference/00-index|Vendor AI API reference index]]: read the common verification boundary and credential-security guidance first.
- [[api/ai-api-reference/openai-api|OpenAI API]]
- [[api/ai-api-reference/anthropic-claude-api|Anthropic Claude API]]
- [[api/ai-api-reference/google-gemini-api|Google Gemini API]]
- [[api/ai-api-reference/deepseek-api|DeepSeek API]]
- [[api/ai-api-reference/qwen-api|Qwen API]]
- [[api/ai-api-reference/kimi-api|Kimi API]]
- [[api/ai-api-reference/zhipu-glm-api|Zhipu GLM API]]
- [[api/ai-api-reference/mistral-api|Mistral API]]
- [[api/ai-api-reference/cohere-api|Cohere API]]
- [[api/ai-api-reference/xai-grok-api|xAI Grok API]]

For Requests features such as uploads, cookies, and streaming downloads, see [[api/upstream-references/requests-quickstart|Requests Quickstart]]. It retains its source and full study value but is not counted again as part of the general sequence.

## Hands-on entry points

- Each lesson ends with small exercises.
- The integrated project is [[api/project-reliable-api-client|Project: reliable API client]].
- Complete code is under `docs-EN/api/examples/`; it calls only local `127.0.0.1`, needs no API key, and does not incur external costs.

## Mastery criteria

You are ready to move on to LLM API integration when you can complete these tasks without copying a finished solution:

- Find an API's base URL, endpoint, method, authentication, parameters, response schema, and error conventions from its documentation.
- Write a Requests call with `(connect, read)` timeouts.
- Explain what to check for 401, 403, 404, 409, 422, 429, 500, and 503 instead of retrying everything.
- Write a cursor-pagination loop with a page limit and repeated-cursor protection.
- Retry only transient failures, respect `Retry-After`, and put a cap and jitter on backoff.
- Explain the difference between an HTTP method being idempotent and a business operation never being duplicated.
- Log a request ID, status code, duration, and attempt count while hiding tokens and sensitive request bodies.
- Pass the 35 automated tests in `api/examples`, and distinguish what the 29 reliable-client tests prove from what the 6 offline documentation-contract tests prove.

## Evidence from this verification round

- With Python 3.11.9 and Requests 2.33.0, all 35 tests passed in practice: 29 reliable-client unit and loopback-integration tests that use only random local ports, plus 6 tests that statically parse Python code and protection contracts in the OpenAI reference page without calling a vendor API.
- The project verifies timeout propagation; normalized transport errors, including the rule that TLS identity failures are not retried; 3xx with redirects disabled; 204; content types; pagination runaway; retry exhaustion; `Retry-After` seconds, dates, invalid values, and waiting budgets; and idempotent recovery when the server created a resource but the first response was lost.
- All 138 Python fenced-code blocks in the 21 Markdown files passed syntax parsing, and 76 fully qualified wikilinks resolved to existing files.
- Requests Quickstart was moved only into the reference layer; its SHA-256 was unchanged by the move and its body was not rewritten.
- Vendor examples were checked against official materials and Python syntax only; this round did not install every SDK or use real keys for potentially billable network calls.
- Obsidian Reading View was not automatically verified. The final integration phase will perform the repository-wide static link check.

## Relationship to other courses

- [[python-fundamentals/00-index|Python Fundamentals]] provides syntax, virtual environments, and exception handling; [[json/00-index|JSON]] provides the data format for request and response bodies.
- [[llm-api-integration/00-index|LLM API Integration]] builds on the general HTTP reliability here to cover vendor SDKs, streaming events, token usage, and model errors.
- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]] is about the model deciding which tool to call; API is about the program reliably executing that call.
- [[mcp/00-index|MCP]] standardizes tool and context exposure at the protocol layer, while lower layers can still use HTTP or other transports.
- [[runtime-monitoring/00-index|Runtime Monitoring]], [[llmops/00-index|LLMOps]], and [[ai-safety/00-index|AI Safety]] extend logging, metrics, credential governance, and failure recovery.

## Primary references

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 6585: Additional HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc6585.html)
- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [RFC 6750: OAuth 2.0 Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750.html)
- [Requests documentation](https://docs.python-requests.org/en/stable/)
- [Python `http.server` documentation](https://docs.python.org/3/library/http.server.html)

Retrieved on 2026-07-22.
