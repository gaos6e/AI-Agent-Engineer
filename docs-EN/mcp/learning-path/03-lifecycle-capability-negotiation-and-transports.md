---
title: "MCP Lifecycle, Capability Negotiation, and Transports"
aliases:
  - MCP lifecycle transports
  - MCP JSON-RPC
tags:
  - MCP
  - JSON-RPC
source_checked: 2026-07-21
lang: en
translation_key: "MCP/学习路线/03-生命周期能力协商与传输.md"
translation_source_hash: 4f104b67462b8a58460ad445cf384ac9986b8d4bbe1aa1acc913f795644e77d7
translation_route: zh-CN/MCP/学习路线/03-生命周期能力协商与传输
translation_default_route: zh-CN/MCP/学习路线/03-生命周期能力协商与传输
---

# MCP Lifecycle, Capability Negotiation, and Transports

## Learning objectives

After this lesson, you should be able to:

- Distinguish JSON-RPC requests, responses, and notifications, and manage IDs correctly.
- Explain a session through its initialization, operation, and shutdown phases.
- Check capabilities according to message direction rather than by looking only at the top-level version.
- Compare stdio and Streamable HTTP, and locate framing, session, version, and timeout failures.

## JSON-RPC is the message envelope

MCP represents data-layer messages with JSON-RPC 2.0:

| Type | Key fields | Expects a reply? | Core constraint |
| --- | --- | --- | --- |
| request | `jsonrpc`, `id`, `method`, optional `params` | Yes | The same sender must not reuse an ID before its request completes |
| response | `jsonrpc`, `id`, either `result` or `error` | No | Its ID matches the original request; exactly one of result/error is present |
| notification | `jsonrpc`, `method`, optional `params` | No | It must not contain an ID |

```json
{"jsonrpc":"2.0","id":7,"method":"tools/list"}
{"jsonrpc":"2.0","id":7,"result":{"tools":[]}}
{"jsonrpc":"2.0","method":"notifications/tools/list_changed"}
```

An ID belongs to the correlation space of the request sender. Both sides can send requests at the same time, so an implementation should correlate by “sending direction + ID,” rather than assuming one global ID sequence across a bidirectional connection. In Python, booleans are subclasses of integers, but an MCP RequestId must not treat `true` as an integer ID.

> [!note] Boundary of the teaching validator
> This course's offline validator uses a stricter profile than general JSON-RPC: it rejects unknown top-level fields, duplicate JSON keys, and NaN/Infinity, and supports only the parameter objects used in the course. This helps reveal errors early; it is not complete official conformance.

## Lifecycle stage 1: initialization

```mermaid
sequenceDiagram
    participant H as Host / Client
    participant S as Server
    H->>S: initialize(version, client capabilities, clientInfo)
    S-->>H: result(selected version, server capabilities, serverInfo)
    H->>H: Validate version and required capabilities
    alt Incompatible
        H--xS: Close connection; do not enter operation
    else Accepted
        H-)S: notifications/initialized
        H->>S: Negotiated requests such as tools/list
        S-->>H: Response or supported notification
        opt Timeout or user cancellation
            H-)S: notifications/cancelled(requestId)
        end
    end
```

*Figure 1. Initialization and constrained operation for a stable MCP session. Text alternative: the client first sends `initialize`; the server returns its selected version and capabilities; the client validates locally, closes if incompatible, and otherwise sends `initialized` before normal requests begin. Cancellation refers to an already sent request and does not itself disconnect the session. The diagram is based on MCP `2025-11-25` lifecycle and JSON-RPC 2.0; the Mermaid source is the regeneration method.*

Initialization must be the first interaction between client and server:

1. client → server: an `initialize` request containing the supported `protocolVersion`, client capabilities, and `clientInfo`.
2. server → client: a response with the same ID, returning the selected protocol version, server capabilities, and `serverInfo`.
3. The client checks whether it supports the version selected by the server. If it does not, it should disconnect.
4. client → server: `notifications/initialized`.
5. Normal operation begins.

Before the server responds to `initialize`, the client should not send another request except ping. Before the server receives the initialized notification, the server should not send another request except ping and logging. To make its state machine clearer, the course project applies the stricter rule that all three handshake steps must finish consecutively.

### Version negotiation is not “both sides say latest”

The client sends the version it supports. The server may return that version or select another version it supports; the client ultimately decides whether to accept it. Protocol version, SDK version, host product version, and server package version are four separate fields.

On 2026-07-21, the first-party version page still marked `2025-11-25` as latest. `2026-07-28` was still an explicitly marked Draft release candidate, dated after this review, and removes initialization. Its message shape must not be applied to the stable state machine in this page. A `2025-11-25` session must still follow the value negotiated in the initialize response; over HTTP, the client must also send the `MCP-Protocol-Version` header on subsequent requests.

## Lifecycle stage 2: capability-constrained operation

Capabilities are bidirectional and declared by their owner:

```jsonc
{ // Illustration of the capability subset actually negotiated by both sides after initialization
  "clientCapabilities": { // Reverse capabilities that the client/host offers the server, not permissions the server may automatically exercise
    "roots": {"listChanged": true}, // The client supports roots/list_changed notifications, used to report changes in available roots
    "sampling": {"tools": {}}, // The client supports the tools shape within sampling, but each request still requires control and authorization
    "elicitation": {"form": {}, "url": {}} // The client supports form and URL elicitation; user consent is a separate decision
  }, // End client capabilities
  "serverCapabilities": { // Capabilities exposed by the server to the client; they do not mean a user or tenant has resource authorization
    "tools": {"listChanged": true}, // The server offers tools and can notify a tool-list change
    "resources": {"subscribe": true, "listChanged": true}, // The server supports resource subscriptions and resource-list changes
    "prompts": {} // The server supports the base prompts feature; an empty object means no additional sub-capability is declared
  } // End server capabilities
}
```

> [!note] JSONC used for teaching
> This object explains negotiation semantics line by line. Remove the `//` comments for an actual `initialize` JSON-RPC payload.

Check in this order:

1. Is the method direction correct? For example, `tools/call` is normally client → server, while `roots/list` is server → client.
2. Did the receiver declare the top-level capability?
3. Is a sub-capability also required? Tool-enabled sampling requires `sampling.tools`; URL elicitation requires `elicitation.url`.
4. In the stable `2025-11-25` specification, if a request carries experimental `task` data, did the receiver declare the corresponding `tasks.requests...` capability? Does the tool's `execution.taskSupport` also allow it? The newer Tasks extension is a separate contract under observation and must not be mixed in.
5. Are business identity, scope, and user consent satisfied? Capability negotiation cannot replace this step.

Lists, subscriptions, and notifications also require the right sub-capability. A server should send `notifications/tools/list_changed` only when it declares `tools.listChanged: true`. In Resources, `listChanged` and `subscribe` are independent: the former permits list-change notifications, and the latter permits subscribe/unsubscribe and per-item updated notifications after a successful subscription. The same principle applies to the client's Roots-change notification. A capability is still not data authorization: business identity, scope, URI ACL, and revocation state must be checked for every relevant operation.

## Lifecycle stage 3: shutdown

MCP has no dedicated shutdown message:

- With stdio, the client normally closes the server's stdin, waits for exit, and terminates through the operating system only after a timeout.
- With HTTP, closing the relevant connections represents the end.

“Closing an SSE stream” is not the same as “cancelling a request.” A Streamable HTTP connection can break at any time; cancellation still requires an MCP cancellation notification. A production implementation must also release subprocesses, sessions, tasks, temporary files, and downstream connections.

## Standard transport 1: stdio

stdio is suitable for a local server:

- The client starts the server subprocess.
- stdin/stdout exchange UTF-8 JSON-RPC. Each message is separated by a newline, and a message must not contain an embedded newline.
- The server's stdout may contain only valid MCP messages.
- Diagnostic logs go to stderr; stderr output does not necessarily mean the protocol failed.

Common Windows issues:

- The host's working directory differs from the directory used for manual execution; use absolute paths in configuration.
- A GUI host inherits a different `PATH` than the PowerShell session.
- The server writes `print("started")` to stdout and contaminates the first JSON message.
- A file uses the wrong encoding, or formatted JSON is written across multiple stdio lines.
- Real secrets are stored in shared configuration; use host secret management and minimal environment variables instead.

## Standard transport 2: Streamable HTTP

The current Streamable HTTP transport replaces the old HTTP+SSE transport from `2024-11-05`. The new transport:

- Exposes one MCP endpoint that supports both POST and GET.
- Uses a new HTTP POST for every JSON-RPC message sent by the client.
- May respond with `application/json` or `text/event-stream`; the client must handle both.
- Lets the client open an SSE stream with HTTP GET for server-initiated messages.
- May use `Mcp-Session-Id` for a session, but the session ID is not an identity credential.
- May support recovery after a disconnect using SSE event IDs; duplicate delivery and business idempotency still need higher-layer design.

Minimum security rules:

- Validate `Origin` and reject an invalid value to defend against DNS rebinding.
- Bind a local HTTP server to `127.0.0.1` by default; do not accidentally listen on `0.0.0.0`.
- Use HTTPS and correct authorization remotely.
- Do not treat a disconnect as cancellation or a session ID as authorization.

See [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|the Loopback Streamable HTTP and OAuth Resource Boundaries project]] for executable evidence. It validates POST/GET/DELETE, JSON/SSE, version and session headers, Origin, recovery cursors, and session termination on `127.0.0.1`. Its requirement that a request use `Content-Type: application/json` is a deliberate hardening rule of this teaching profile, not a claim about the stable specification.

## Timeouts, cancellation, progress, and Tasks

The specification recommends a configurable timeout for every sent request. After a timeout:

1. Send a cancellation notification.
2. Stop waiting for the original response.
3. Record the request ID, method, duration, and cancellation outcome.
4. Decide whether to retry based on whether the action is idempotent.

Progress can extend the ordinary timeout judgment, but an absolute limit is still needed so that a malicious or uncontrolled peer cannot occupy resources indefinitely. Tasks provide persistent, pollable execution state; they should not replace every ordinary timeout. They still need TTLs, ownership binding, polling intervals, and final-result handling. For the boundary between experimental Tasks in the stable specification and the newer Tasks extension, see [[mcp/learning-path/07-frontier-extensions-apps-and-version-compatibility|Frontier Topic: Extensions, Apps, and Version Compatibility]].

## Layered troubleshooting table

| Evidence | More likely layer | Next step |
| --- | --- | --- |
| Program absent, connection refused | Startup/transport | Check absolute command, cwd, port, and TLS |
| First stdout line is not JSON | stdio framing | Move logs to stderr |
| Initialize IDs do not match | JSON-RPC/lifecycle | Save raw bidirectional messages and correlate by direction |
| `-32602 Invalid params` | Schema or capability | Check the initialize exchange, method direction, and parameters |
| HTTP POST has no expected response | HTTP/SSE/timeout | Check Content-Type, SSE stream, session, and proxy logs |
| Tool returns `isError: true` | Tool execution/business | Give the actionable error to the model or user; do not rebuild the connection |

## Hands-on exercise

1. Write an initialize request, response, and initialized notification by hand, and label the direction and ID of each.
2. On paper, send a client request with ID `5` and a server request with ID `5` at the same time, then explain why they do not conflict.
3. Design a capability gate: if the server has not declared tools, how should the client report that to its upper layer rather than still sending `tools/list`?
4. Write a stdio server's “started” log to stdout and stderr separately, and predict client behavior.
5. For a remote tool call, write three timeout strategies: a read-only query, a write with an idempotency key, and a write whose outcome cannot be determined.

## Self-check

1. Why must a notification not contain an ID?
2. How do the current protocol version and negotiated version differ?
3. Why does seeing `sampling` not permit a tool-enabled sampling request?
4. Why is an HTTP disconnect not cancellation?
5. In Streamable HTTP, SSE is an optional carrier. Why must it not be treated as the same version as the old HTTP+SSE transport?

You have mastered the lesson when you can draw the three-stage sequence and explain the direction, ID, capability, and transport evidence for any message.

## Next step

Continue to [[mcp/learning-path/04-authorization-and-security-boundaries|Authorization and Security Boundaries]] to separate protocol availability from real permission.

## References

The following are first-party or original protocol sources, retrieved or checked on 2026-07-21.

- [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP Schema Reference](https://modelcontextprotocol.io/specification/2025-11-25/schema)
- [Protocol Versioning](https://modelcontextprotocol.io/docs/learn/versioning)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
