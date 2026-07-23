---
title: "Project: Offline MCP Message Validation"
aliases:
  - MCP offline validation project
  - MCP teaching protocol validator
tags:
  - MCP
  - project
source_checked: 2026-07-21
execution_verified: 2026-07-21
lang: en
translation_key: "MCP/学习路线/06-项目-离线MCP消息验证.md"
translation_source_hash: 8af9076083470bd43e475c67c684eda69880b9a39977323f078ffb5c419cf206
translation_route: zh-CN/MCP/学习路线/06-项目-离线MCP消息验证
translation_default_route: zh-CN/MCP/学习路线/06-项目-离线MCP消息验证
---

# Project: Offline MCP Message Validation

## Project goal

Complete a repeatable MCP teaching-validation project without a network, real server, SDK, or API key. It turns the learning path's key rules into data-driven checks:

- Strict JSON and the JSON-RPC envelope.
- The initialize state machine and bidirectional request IDs.
- Client/server capability direction and sub-capabilities.
- Tool inputs, structured outputs, and two kinds of error.
- The five stable Resources methods, pagination, content, and subscription state.
- HTTP token audience/resource, tenant, scope, and authorization-revision binding.
- Key boundaries for roots, sampling, elicitation, and experimental Tasks.
- Positive, negative, and regression tests.

> [!warning] Capability boundary
> This is the course-defined `offline-mcp-teaching-profile-v2`, not the official MCP conformance suite. It implements only the methods and schema subset used by the course from the stable `2025-11-25` specification, and deliberately tightens rules for unknown fields, URI, Base64, and a 64 KiB content budget. It does not implement the Draft candidate protocol. A real implementation should prefer an official SDK and test transport, interoperability, and security against the versions on both sides.

> [!important] Separate wire and control plane
> Fixture `transport_context_defaults`, per-step `transport_context`, `authorization_revision`, and `control_event` are **course control-plane metadata**, not MCP JSON-RPC fields. They model the trusted identity snapshot obtained after HTTP-layer signature validation, token introspection, and access policy; never copy them into a real MCP message.

> [!tip] Next layer of executable evidence
> After this project, run [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|the Loopback Streamable HTTP and OAuth Resource Boundaries project]]. It does not modify or reuse this validator's `transport_context` fixtures. Instead, it independently validates HTTP headers/statuses, JSON/SSE, sessions, PRM document/challenge shape, and an offline token policy on a real endpoint. Its HTTP resource does not claim RFC 9728 conformance. The projects cover the message contract and transport/resource boundary separately.

## Project files

| File | Purpose |
| --- | --- |
| [validate_mcp_messages.py](mcp/examples/validate_mcp_messages.py) | State machine, capability gates, schema subset, and command-line entry point |
| [mcp-cases.json](mcp/examples/mcp-cases.json) | 54 data-driven positive/negative cases |
| [test_validate_mcp_messages.py](mcp/examples/test_validate_mcp_messages.py) | 108 automated regression tests |

The project uses only the Python 3 standard library. Fixtures contain no network addresses other than the documentation-reserved `example.com` domain, no real user data, and no credentials.

## Runtime environment

This course was verified with Windows 11, PowerShell 7, and Python 3.11. From the repository root, enter the English MCP course:

```powershell
Set-Location ".\docs-EN\mcp" # Enter the MCP teaching project so that relative example and fixture paths resolve correctly.
```

Run the 54 data cases:

```powershell
python -B .\examples\validate_mcp_messages.py # Run strict JSON fixture validation; -B prevents local cache files.
```

Run the tests:

```powershell
python -B .\examples\test_validate_mcp_messages.py # Run unit and data-driven regression tests in normal mode.
python -B -O .\examples\test_validate_mcp_messages.py # Check that safety logic does not incorrectly depend on bare assert statements removable by optimization.
python -B -W error .\examples\test_validate_mcp_messages.py # Turn any Python warning into a failure.
python -B -O -W error .\examples\test_validate_mcp_messages.py # Cover optimized and strict-warning conditions together.
```

`-B` prevents `__pycache__` creation; `-W error` treats warnings as failures; `-O` reruns the validator to prove that it did not incorrectly implement security checks as `assert` statements that optimization can remove.

The expected summary includes:

```json
{
  "status": "ok",
  "profile": "offline-mcp-teaching-profile-v2",
  "protocol_version": "2025-11-25",
  "case_count": 54,
  "passed": 16,
  "expected_failures": 38
}
```

“expected_failures” means that negative samples were rejected correctly; it does not mean the tests failed.

## Read the fixture first

`mcp-cases.json` has eight parts:

1. `schema_version`: the fixture structure version, not an MCP version.
2. `protocol_version`: the stable specification date currently validated by the course.
3. `transport_context_defaults`: secret-free defaults for HTTP transport type, active token, token audience, and RFC 8707 `resource`.
4. `authorization`: protected resource, authorization revision, principal/tenant/scope, resource graph, and template policy.
5. `client`: clientInfo and roots/sampling/elicitation/tasks capabilities.
6. `server`: serverInfo and tools/resources/prompts/logging/tasks capabilities.
7. `tool`: one offline weather tool with input/output schemas and optional task support.
8. `cases`: setup, bidirectional steps, control events, expected pass/fail status, and error fragments for every case.

Every step explicitly states its direction:

```jsonc
{ // The fixture uses an outer direction field to remove ambiguity in bidirectional JSON-RPC.
  "direction": "server_to_client", // This request goes from server to client, which determines capability and method-direction checks.
  "message": { // Only this inner object is the strict JSON-RPC message.
    "jsonrpc": "2.0", // Fixed protocol-version field.
    "id": 10, // Request ID; the client should later return a response or error with this same ID.
    "method": "roots/list" // The server asks the client to list currently available roots.
  } // End inner JSON-RPC request.
}
```

> [!note] JSONC used for teaching
> The outer fixture and inner JSON-RPC message have different responsibilities. Remove the `//` comments before using it as strict JSON test data.

Direction is not decoration. `roots/list` must be a server-to-client request; changing it to `client_to_server` must be rejected.

## How the validator works

### 1. Strict JSON

Python's default `json.loads` accepts duplicate keys by overwriting the earlier value and accepts NaN/Infinity. The project explicitly rejects both, limits fixtures to 2 MB and JSON container nesting to 64 before recursive decoding, reads only “limit + 1 byte,” and does not echo a local path in an I/O error. This prevents a signature, audit trail, or different parser from seeing different values and avoids the false budget of “read all input, then check its size.”

### 2. JSON-RPC envelope

The validator distinguishes:

- Request: method + ID.
- Notification: method with no ID.
- Response: ID plus exactly one of result/error.

It correlates requests by “sending direction + ID type + ID value.” Integer `5` and string `"5"` are different; both sides can use ID `5` concurrently; the same sender cannot reuse an ID while an earlier request is unanswered.

A message cannot carry both `method` and `result`/`error`. A successful response is first validated against its pending method, then atomically consumes the pending request. A malformed `InitializeResult`, `tools/list`, or other successful result cannot pop correlation state first and leave a later valid response permanently unmatched. A valid JSON-RPC error response does terminate its corresponding request, but does not fabricate a business-success state such as a subscription.

### 3. Initialize state machine

The states are:

```text
new
→ waiting_for_initialize_response
→ waiting_for_initialized_notification
→ ready
```

Ordinary requests cannot skip the handshake. Response IDs, version, info, and capabilities must match the course profile.

### 4. Bidirectional capability gates

The validator rejects:

- A client sending `tools/list` when the server did not declare tools.
- A server sending `roots/list` when the client did not declare roots.
- A server sending tool-enabled sampling when the client declares sampling but not `sampling.tools`.
- A server sending URL mode when the client did not declare `elicitation.url`.
- A client task-augmenting `tools/call` when the server did not declare `tasks.requests.tools.call`.

It also checks Boolean sub-capabilities such as `tools.listChanged`, `resources.listChanged`, `resources.subscribe`, and `roots.listChanged`.

### 5. Resources contract and subscription state

The stable profile accepts exactly these five client-to-server methods:

- `resources/list` and `resources/templates/list`: may take an opaque string cursor; cursor, descriptor, URI template, MIME, annotations, and size in results are checked.
- `resources/read`: its requested URI must appear in the current tenant's explicit resource policy; a result may contain only the requested URI or a child URI explicitly allowed by the policy graph.
- `resources/subscribe` and `resources/unsubscribe`: both require the server to declare `resources.subscribe: true`.

State changes only after a successful response, not when the request is sent. A failed subscribe does not create a subscription; a failed unsubscribe keeps the old subscription. `notifications/resources/updated` must correspond to an active subscription for the same principal and tenant. A child relationship comes from an explicit policy graph, not a shared string prefix. `notifications/resources/list_changed` depends only on `resources.listChanged`, not on a per-item subscription.

The project locally checks URIs, URI templates, MIME, descriptors, canonical padded Base64, and UTF-8 byte count. One item and the full `resources/read.contents` share a 64 KiB teaching budget, with at most 64 content items; each list page has at most 256 items. This prevents gates from being bypassed with many empty objects or small chunks. A structurally valid resource is still untrusted data, not a system instruction.

### 6. Out-of-wire authorization snapshot and revocation

Before every teaching Resources operation, the validator checks the complete `transport_context` before handling the MCP message:

1. The transport is the `streamable_http` transport modeled by this project.
2. The access token remains active.
3. The token audience and the RFC 8707 `resource` used in both authorization and token exchange bind exactly to the current MCP protected resource.
4. The subject exists and is not revoked; tenant and principal remain consistently bound.
5. The claims in this request do not exceed policy-granted scopes and include the scope required by the current method.
6. `authorization_revision` is the currently effective revision.

Changing the revision clears active subscriptions first; requests, notification delivery context, and pending success results with an old revision all fail closed. Fixtures neither retain nor validate a real bearer token and do not simulate signatures, issuers, expiration, introspection, 401/403, or `WWW-Authenticate`. Those belong to real HTTP/OAuth integration tests. stdio does not use this HTTP authorization flow and should obtain credentials from a controlled environment.

### 7. Tool contract

Input validation checks required fields, types, enums, `minLength`, and unknown fields. The schema accepts only explicit keywords that the course actually executes and bounds recursion depth, properties, enums, arrays, and string size, avoiding a silent “declared but not executed” schema. If an `outputSchema` exists, output must contain conforming `structuredContent`. A successful `tools/list` result also checks pagination cursor, descriptor, unique tool names, and at most 256 items. An execution error with `isError: true` may provide only actionable content; a JSON-RPC error represents a protocol-layer failure.

### 8. Client features and Tasks

- A root response must use a `file://` URI. Roots express only a coordination scope and never replace a resource ACL, token scope, or file-system sandbox.
- Sampling checks messages, `maxTokens`, tool descriptors, and tools/context sub-capabilities. This profile accepts only bounded text content for a successful result; it does not claim to implement a complete multimodal or tool-use schema.
- Form elicitation rejects common secret field names; URL mode requires an absolute HTTPS URL in this teaching profile.
- Task augmentation checks capability and tool-level `taskSupport`, distinguishes `CreateTaskResult` from a normal tool result, and checks basic bounded structure for every `tasks/list` Task snapshot: ID, status, timestamp, required TTL, and an optional polling interval.

These checks are a teaching subset. For example, the validator does not implement the full restricted elicitation schema, every content type, SSE framing, task-ownership storage, real OAuth, or the official conformance corpus. `tasks/list` validates only bounded structural snapshots; it does not prove the current requestor may see the task, check state transitions, or retain task state. Successful schemas for `prompts/*`, `logging/setLevel`, `completion/complete`, and `tasks/get/result/cancel` are not implemented, so the validator rejects those requests explicitly before creating pending state instead of accepting a success result it cannot validate.

## Step-by-step experiments

Change only one fixture case at a time, predict the result, and then run it:

1. Reverse the direction of a valid roots request.
2. Remove the client's `sampling.tools` while preserving a tool-enabled sampling request.
3. Add an `id` to a notification.
4. Send two unanswered requests with the same ID in the same direction.
5. Change tool `unit` to `kelvin`.
6. Remove `structuredContent` from a successful tool result.
7. Request `api_key` through form elicitation.
8. Remove the server's `tasks.requests.tools.call` and still send a task-augmented tool call.
9. Change URL elicitation to `http://` and observe this profile's hardening rule.
10. Change `token_audience` or the RFC 8707 `resource` to another server.
11. First subscribe successfully, then switch to `authz-v2` and observe subscription invalidation and rejection of old-revision reads.
12. Change a child URI so that it merely shares a similar prefix with `handbookish`.

Restore the fixture afterward and rerun all 108 tests.

## Extension tasks

### Foundation extension

- Add an integer parameter with `minimum`/`maximum` to the tool, plus positive and negative fixtures.
- Add multipage state to `tools/list`, cross-page uniqueness, and dynamic `listChanged` cache-invalidation checks.
- Validate accepted form responses against the originally requested schema.

### Advanced extension

- Implement an explicit policy for whether JSON-RPC batch is allowed.
- Create request-token correlation for progress/cancellation.
- Add state machines for task status, `tasks/get`, `tasks/result`, and related-task metadata.
- Extend the existing [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|independent transport project]] with an official SDK adapter, long-connection backpressure, proxy faults, and persistent SSE resume; do not put this logic into message fixtures.
- Write one minimal client and server with official SDKs and integration-test them against this fixture; never rename the teaching validator as official conformance.

For every extension, add a failing test first, then implement the smallest rule.

## Troubleshooting guide

| Symptom | Cause | Action |
| --- | --- | --- |
| Fixture root/key error | JSON structure or unknown field | Check the strict schema and duplicate keys |
| “wrong direction” | Method is sent by the wrong side | Compare server/client capability |
| “did not declare capability” | Top-level or sub-capability is missing | Fix the capability or do not send the request |
| Token audience/resource error | Token or RFC 8707 resource was sent to another server | Stop the request and repeat the correct authorization flow |
| Stale authorization revision | Policy was revoked or refreshed while an old identity snapshot was reused | Discard old requests/subscriptions and reauthorize with fresh identity |
| Resource update has no active subscription | Subscribe failed, was unsubscribed, was revoked, or URI is outside the explicit child graph | Resubscribe and inspect the resource graph; do not infer relationship from a string prefix |
| Response has no matching request | ID/direction is wrong or a response is duplicated | Inspect outstanding requests |
| `structuredContent` fails | Output does not match its schema | Fix the server result; do not change only its text |
| Tests fail only with `-O` | Production logic incorrectly uses `assert` | Separate explicit exceptions from test assertions |

## Project acceptance

- [ ] The CLI reports 54 cases: 16 positive passes and 38 expected negative rejections.
- [ ] All 108 tests pass in normal mode.
- [ ] All 108 tests pass with `-O`.
- [ ] All 108 tests produce no warning with `-W error`.
- [ ] All 108 tests pass under combined `-O -W error`.
- [ ] I can explain why direction + ID jointly determine request/response correlation.
- [ ] I can give a server-capability, client-capability, and sub-capability gate.
- [ ] I can distinguish a tool protocol error from an execution error.
- [ ] I can explain the current dynamic/experimental boundary of URL elicitation and Tasks.
- [ ] I can explain why capability, Roots, token scope, tenant ACL, and subscription state cannot replace one another.
- [ ] I can state that `transport_context`, authorization revision, and control events are not MCP wire fields.
- [ ] No cache, secret, real data, or network side effect was generated.

## Self-check

1. Why does a rejected negative case count as “passed” in the summary?
2. Why can one global set not record request IDs?
3. Why must `structuredContent` be checked when an output schema exists?
4. Why does the validator reject `api_key` in a form while still not proving that elicitation is secure overall?
5. Which missing evidence prevents this project from being called a protocol conformance test?
6. Why may an updated notification not be accepted immediately after a subscribe request has been sent?
7. Why cannot a URI prefix prove a sub-resource relationship?
8. Why does a token with the correct scope still need audience, resource, tenant, and revocation-revision checks?

At minimum, the answer should mention the full specification schema, real transport, official SDKs, version interoperability, authorization, concurrency/disconnection, performance, and security testing.

## Next step

After completing this project, first continue to [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|Loopback Streamable HTTP and OAuth Resource Boundaries]] for real header/status/session evidence. Then return to [[mcp/00-index|the MCP index]], choose a server/client tutorial from the official reference layer, and reproduce it with a real SDK. After that, continue to [[agent-core/00-index|Agent Core]] and treat MCP as a controlled integration boundary rather than a planner.

## References

The following are first-party or original protocol sources, retrieved or checked on 2026-07-21.

- [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP Schema Reference](https://modelcontextprotocol.io/specification/2025-11-25/schema)
- [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Server Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
