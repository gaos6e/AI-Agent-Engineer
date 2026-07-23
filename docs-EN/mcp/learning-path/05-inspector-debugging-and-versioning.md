---
title: "MCP Inspector, Debugging, and Version Management"
aliases:
  - MCP debugging
  - MCP Inspector
tags:
  - MCP
  - debugging
source_checked: 2026-07-19
lang: en
translation_key: "MCP/学习路线/05-Inspector调试与版本管理.md"
translation_source_hash: 6f6ba83db319ee909288a57820bfb1e1957e085d3f739ed2deb63d49ec5f7a12
translation_route: zh-CN/MCP/学习路线/05-Inspector调试与版本管理
translation_default_route: zh-CN/MCP/学习路线/05-Inspector调试与版本管理
---

# MCP Inspector, Debugging, and Version Management

## Learning objectives

After this lesson, you should be able to:

- Use Inspector to verify a connection, capabilities, resources/prompts/tools, and notifications.
- Collect the smallest useful evidence by layer instead of attributing every failure to “version incompatibility.”
- Design structured logs and issue reports that do not expose secrets.
- Distinguish specification, negotiated, SDK, and application versions, and create an upgrade gate.

## What Inspector is good at answering

The official MCP Inspector is an interactive development tool. It can connect to a stdio or Streamable HTTP server and show:

- The connection command, arguments, environment, and transport.
- Resources, prompts, and tools exposed after initialization.
- Resource contents and subscriptions.
- Prompt arguments and generated messages.
- Tool schemas, manually entered arguments, and execution results.
- Server logs and notifications.

It is particularly useful for answering “what did the server actually declare, and what did it actually return?” rather than guessing from configuration. By itself, it cannot prove that:

- Production identity and permission are correct.
- Concurrency, timeout, retry, and recovery are reliable.
- Every negative parameter is rejected.
- A version upgrade has no regression.
- The server or returned content is safe and trustworthy.

Inspector is therefore an entry point for development evidence; it does not replace automated contract tests, integration tests, load tests, or security review.

## Start it on Windows 11 / PowerShell 7

The generic form in official documentation checked on 2026-07-14 is:

```powershell
npx @modelcontextprotocol/inspector "<server-command>" "<arg1>" "<arg2>" # npx starts Inspector; replace angle-bracket placeholders with a verified real server command and arguments.
```

To inspect a local Python server, replace the final portion with the real, verified start command from that project's README. Do not copy an unknown package name or example path unchanged. `npx` may download dependencies from the network and execute code; in an enterprise or sensitive environment, review package, version, and source first, pin a version when necessary, and run it in isolation.

Safe startup procedure:

1. First verify the server command by itself in a terminal, and record its absolute path and working directory.
2. Pass only required environment variables; do not put real tokens in a tutorial, command history, or screenshot.
3. Start Inspector and select the correct transport.
4. Save the initialized protocol version and capabilities from both sides.
5. Begin with read-only list/read operations, then test writes using a test account and recoverable data.

## A seven-layer troubleshooting method

### 1. Configuration and process

Check whether the command exists, its absolute path, cwd, file permissions, and runtime version. A GUI host may have a different environment from the current PowerShell session; “it runs in my terminal” does not prove that the host can start it.

### 2. Transport

- stdio: stdin/stdout framing, UTF-8, newline handling, and stderr.
- HTTP: URL, DNS, TLS, proxy, Origin, status code, Content-Type, and GET/SSE.

First prove that bytes can make a correct round trip; only then examine the protocol.

### 3. JSON-RPC

Check `jsonrpc`, method, ID pairing, the result/error exclusive choice, that notifications have no ID, and whether any outstanding ID is duplicated. Save the first failing message after redaction rather than relying only on a UI phrase such as “connection failed.”

### 4. Lifecycle and version

Check whether initialize was first, which version the server selected, whether the client accepted it, and whether the initialized notification arrived. For HTTP, check whether subsequent requests carry the negotiated `MCP-Protocol-Version`.

### 5. Capability and direction

Confirm from the raw initialize exchange:

- Whether the server declares tools/resources/prompts.
- Whether the client declares roots/sampling/elicitation.
- Whether required sub-capabilities are present: `listChanged`, `sampling.tools`, elicitation mode, or a Tasks request path.
- Whether the method direction is correct.

`-32602 Invalid params` has many causes. One is a server sending sampling/elicitation to a client that did not declare the feature. Do not infer the root cause from the error code alone.

### 6. Contract

Check the tool name, input schema, required fields, enums, unknown fields, output schema, `structuredContent`, and correct distinction between protocol and execution errors.

### 7. Business and downstream systems

Finally, check identity, scope, resource ownership, rate limiting, database state, third-party APIs, idempotency, and recovery. A business failure does not require blindly restarting the MCP session.

## Logging strategy

For a stdio server:

- stdout contains only MCP JSON-RPC.
- Diagnostics go to stderr.
- A log on stderr does not automatically mean failure.

For Streamable HTTP:

- A client will usually not capture the remote server's stderr.
- Use server-side log aggregation, HTTP tools, and MCP logging notifications.
- Trace `Mcp-Session-Id` and SSE, but do not treat a session ID as identity.

Suggested fields:

```text
timestamp, server_name, server_version, transport,
negotiated_protocol, request_direction, request_id, method,
capability_decision, duration_ms, outcome, retry_or_cancel
```

Redact tokens, cookies, prompt/resource bodies, personal data, and sensitive local paths by default. For reproduction, record a schema version, parameter field names, and irreversible digests; plaintext is not necessary.

## Inspector's minimal test matrix

| Area | Positive | Negative | Evidence to save |
| --- | --- | --- | --- |
| initialize | Supported version and capabilities | Unsupported version/missing capability | Version/capability from both sides |
| tools | Valid arguments | Missing argument, wrong type, unknown field | Schema, result/error |
| resources | list/read/templates; successful subscribe → updated → reread → unsubscribe | Invalid URI/template/cursor/Base64, out-of-scope access, total-size limit, missing sub-capability, failed subscription, old notification after revocation | URI/MIME/size, capability, subscription state, redacted authorization decision |
| prompts | Valid arguments | Missing argument | Returned messages and provenance |
| notifications | Received after declaration | Undeclared sub-capability | Direction and method |
| security | Allowed test account | Wrong audience/resource/tenant/scope, expired token, old authorization revision, Roots pretending to be an ACL | Authorization decision and redacted audit |

For sampling, elicitation, roots, or Tasks, whether Inspector/the host implements the relevant client feature varies with tool version. When no matching UI or message is observed, record “not verified by the current tool”; do not infer that the protocol feature does not exist.

## Version record: four facts

| Field | Example meaning | Where to obtain it |
| --- | --- | --- |
| spec version | Which protocol document is currently being followed | Official version page, for example `2025-11-25` |
| negotiated version | What this session actually uses | Initialize response |
| SDK version | What the implementation library supports | Lockfile, package metadata, or SDK release |
| app/server version | Which product and build | App About page, package version, or Git commit |

Also record the document retrieval date. Do not write only “latest,” and do not infer that a larger SDK package number supports every optional feature in the newest specification.

## Upgrade gate

Before upgrading a protocol or SDK:

1. Read the target specification's key changes and the SDK release notes.
2. List added, removed, and soft-deprecated fields and capabilities.
3. Add regression examples for existing initialize, tools/resources/prompts, and client features.
4. Run offline message/contract tests.
5. Use Inspector to validate the real server.
6. Run integration tests in the target host, especially for authorization, user consent, and error presentation.
7. Test an old peer or deliberately stop compatibility, then record a rollback plan.

In `2025-11-25`, boundaries such as URL elicitation, sampling tool use, and Tasks may not all be implemented by every SDK/host at once; Tasks are still experimental. Release decisions must use “both sides declare it + measured behavior,” not merely the feature's presence in a specification page.

## Reusable issue report

```text
host/client name and version:
server package/commit:
SDK and runtime:
document retrieval date:
requested protocol version / server-selected version:
capabilities on both sides:
transport and endpoint/command (redacted):
minimal reproduction:
expected / actual:
first failing layer:
first failing request ID and method:
Inspector observation / redacted log:
does it involve a real write, credential, or production data:
```

## Hands-on exercise

1. For “Inspector can list tools, but `tools/call` returns invalid params,” use the seven-layer method to write the next smallest piece of evidence.
2. For “stdio JSON parse error,” independently test stdout contamination, encoding, and newline framing.
3. Simulate a missing capability: compare initialization and explain why restarting the server cannot implement missing client sampling.
4. Fill in the four-version table and regression matrix for one SDK upgrade.
5. Rewrite a log containing a token and full body into a structure that remains correlatable without disclosing secrets.

## Self-check

1. Why does one successful Inspector tool call not prove production readiness?
2. Does stderr output mean a stdio server failed?
3. Why can `-32602` not be attributed directly to schema?
4. Where do specification version and negotiated version come from, respectively?
5. Tasks appear in the current specification. Why must SDK/host capability and actual behavior still be checked?

You have mastered the lesson when you can independently perform “seven-layer diagnosis + four-version record + minimal test matrix.”

## Next step

Continue to [[mcp/learning-path/06-project-offline-mcp-message-validation|Project: Offline MCP Message Validation]] to turn these checks into repeatable automated evidence.

## References

The following are first-party MCP materials, retrieved or checked on 2026-07-14.

- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- [Debugging MCP](https://modelcontextprotocol.io/docs/tools/debugging)
- [Protocol Versioning](https://modelcontextprotocol.io/docs/learn/versioning)
- [Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
