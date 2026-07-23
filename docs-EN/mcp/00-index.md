---
title: "MCP"
aliases:
  - Model Context Protocol
  - MCP learning path
tags:
  - ai-agent-engineer
  - MCP
  - learning-path
source_url: https://modelcontextprotocol.io/llms.txt
source_path: /llms.txt
created_at: 2026-05-07T20:53:16+08:00
source_checked: 2026-07-21
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: page-specific
ai_learning_stage: 5. Single Agent and Tools
ai_learning_order: 31
ai_learning_schema: 2
ai_learning_id: mcp
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3100
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 625
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 625
ai_learning_track_agent_platform_kind: optional
lang: en
translation_key: "MCP/00-目录.md"
translation_source_hash: a6e2da07010e616020c28afba511ec8da1121bf47b2c30dd2ac50a3002616481
translation_route: zh-CN/MCP/00-目录
translation_default_route: zh-CN/MCP/00-目录
---

# MCP

## Knowledge-base overview

Model Context Protocol (MCP) is an open protocol for connecting AI applications to external capabilities and context in a consistent way. This knowledge base does not stop at “copy a server configuration.” It is designed to help a beginner:

- Explain the host, client, server, and bidirectional capabilities.
- Read the JSON-RPC lifecycle and capability negotiation.
- Choose correct boundaries for tools/resources/prompts and roots/sampling/elicitation.
- Compare stdio and Streamable HTTP.
- Review authorization, security, debugging, and versions.
- Validate key rules for messages, schemas, errors, and experimental Tasks with an offline project.
- Validate Streamable HTTP, sessions, and OAuth resource boundaries with real loopback HTTP round trips.

The knowledge base has two layers:

1. **Learning path:** seven stable core lessons and runnable projects. Start here. One frontier-observation topic is also available, but is not a stable prerequisite.
2. **Official-document reference layer:** 18 local Chinese summaries that existed before this task. Each uses a compressed “key conclusion — main content — cautions — related pages” template; none is an upstream-body mirror or full translation. They remain frozen in principle and are consulted only as needed; confirmed problems receive only narrow corrections.

Source boundary: the learning path is original teaching material for this project. The 18 historical summaries are now marked page by page as `curated` / `needs-review`, accurately indicating “locally curated; current facts and provenance have not yet been restored.” Because they remain in the frozen reference tree, the publication gate continues to generate a stub for every one. Changing frontmatter alone does not release the body. A genuinely independent, verified rewrite must move into the learning-path layer; a local summary must not be mislabeled `third-party` / `frozen-reference` to bypass the gate.

> [!warning] MCP documentation cannot be uniformly labeled MIT
> The former `modelcontextprotocol/docs` repository was archived under MIT. After the project moved into `modelcontextprotocol/modelcontextprotocol`, the [license transition on 2026-01-05](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/edeb0b74f537) set CC BY 4.0 for ordinary new documentation contributions while unrelicensed older contributions retained their original license. A page that evolved across the transition may contain contributions under different licenses. The current reference layer therefore uses `page-specific`: until page-level commit history, attribution, and modification notice have been checked, the public site continues to show only a source-link stub.

> [!info] Reference-layer audit boundary, 2026-07-20
> The most recent official-repository commit before the acquisition time was [`76ceb47f`](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/76ceb47f2d7671c864dfc1db2fa7d7c9f8a46331), and all 18 source paths existed then. This workspace did not retain HTTP response hashes or a deployment revision, so it cannot claim that the captured body byte-for-byte matches that tree. Commit history supports treating “Protocol Versioning” and “Example Servers” as MIT-recovery candidates, and “Build with Agent Skills” and “Client Best Practices” as CC BY 4.0-recovery candidates; the other 14 pages cross the license transition and remain fail-closed. Candidates also need fixed sources, license notice, attribution/modification notice, and fact revalidation before publication; finding a license alone cannot automatically publish them.

> [!info] Dynamic-fact boundary
> This learning path was checked against first-party material obtained on 2026-07-21. The official version page still marked `2025-11-25` as latest; `2026-07-28` remained a release candidate under `/specification/draft` and is dated after this review, so it cannot be the current stable interoperability contract. Both projects implement only a teaching subset of `2025-11-25`. They do not mix in the candidate's no-initialize model, `server/discover`, or per-request capability shapes. A real implementation must check host, client, server, SDK, and extension support and follow actual negotiation.

## Where this course fits in the overall roadmap

MCP is an on-demand interoperability branch in the “Single Agent and Tools” stage. Course-directory numbering expresses display order only. Enter this course when a project needs standardized cross-process, cross-product, or cross-organization exchange of tools, resources, prompts, or client features. Before starting, you should have:

- [[api/00-index|API]]: HTTP, authentication, timeouts, and errors.
- [[json/00-index|JSON]]: JSON and JSON Schema.
- If the main goal is to expose or invoke tools, [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]] first, to understand how a model chooses a tool and how a host validates and dispatches it.
- Before connecting to an untrusted resource or remote server, or turning protocol checks into regression cases, complete the overall roadmap's [[all-of-ai#early-safety-and-evaluation-milestone|early safety and evaluation milestone]]. It is not a prerequisite for the entire AI-safety and evaluation discipline.

MCP further standardizes tools, context, and client features as an integration boundary across implementations. It is not an Agent planning loop, nor is it a universal prerequisite for [[agent-core/00-index|Agent Core]]. Study it before or after Agent Core according to interoperability needs. If you use only in-process functions, a direct SDK, or an existing private interface with no protocol-interoperability requirement, you can defer MCP.

## Learning objectives

- Distinguish host, client, server, data layer, and transport layer.
- Use a direction matrix to explain server features and client features.
- Correctly distinguish requests, responses, notifications, and bidirectional request IDs.
- Explain initialization, protocol-version selection, capability/sub-capability, operation, and shutdown.
- Write tool input/output schemas and distinguish protocol errors from tool-execution errors.
- Understand control and security boundaries for roots, sampling, elicitation, and Tasks.
- Compare stdio, Streamable HTTP, and older HTTP+SSE material.
- Use Inspector and layered logs to locate failures and record four kinds of version fact.
- Complete an offline data-driven validation project and explain why it is not an official conformance suite.
- Run real loopback Streamable HTTP and distinguish transport, session, OAuth resource policy, and message schema.

## Prerequisites

- Read JSON objects, arrays, and a minimal JSON Schema.
- Understand HTTP request/response, status codes, bearer tokens, and timeouts.
- Run `python -B script.py` on Windows 11 / PowerShell 7.
- Know the difference between stdout and stderr.
- You do not need to know a particular MCP SDK first: learn the protocol, then choose an implementation.

## Core mental model

| Capability owner | Main capabilities | Typical request direction |
| --- | --- | --- |
| server | tools, resources, prompts, logging, completions | client → server |
| client | roots, sampling, elicitation | server → client |
| both/utility | ping, progress, cancellation, experimental Tasks | Depends on the particular method and capability |

A capability declares “the protocol function available in this session.” It does not mean that the user has consented, a resource is authorized, or server content is trustworthy.

## Recommended sequence

| Order | Lesson | Question it answers | Completion evidence |
| --- | --- | --- | --- |
| 1 | [[mcp/learning-path/01-architecture-and-roles\|Architecture and Roles]] | Who connects to whom, and where are bidirectional capability and control located? | Can draw a multi-server host and trust boundaries |
| 2 | [[mcp/learning-path/02-primitives-and-tool-contracts\|Primitives and Tool Contracts]] | When should I choose a tool/resource/prompt/root/sampling/elicitation? | Can choose features for the running scenario and write schemas |
| 3 | [[mcp/learning-path/03-lifecycle-capability-negotiation-and-transports\|Lifecycle, Capability Negotiation, and Transports]] | In what order, direction, and transport do messages run? | Can write a handshake and locate failure by layer |
| 4 | [[mcp/learning-path/04-authorization-and-security-boundaries\|Authorization and Security Boundaries]] | Once a capability is available, how do I prevent overreach and leakage? | Completes a threat model with prevention/detection/recovery |
| 5 | [[mcp/learning-path/05-inspector-debugging-and-versioning\|Inspector, Debugging, and Version Management]] | How do I troubleshoot and upgrade with actual evidence? | Completes a seven-layer issue report and four-version table |
| 6 | [[mcp/learning-path/06-project-offline-mcp-message-validation\|Project: Offline MCP Message Validation]] | How do I turn key protocol rules into regression checks? | All 54 cases and 108 tests pass |
| 7 | [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries\|Project: Loopback Streamable HTTP and OAuth Resource Boundaries]] | How do I use real HTTP to validate headers/statuses, JSON/SSE, session, PRM shape, and authorization failure? | CLI `PASS`/`BLOCK` and all 80 tests pass in four modes |
| 8 (optional) | [[mcp/learning-path/07-frontier-extensions-apps-and-version-compatibility\|Frontier Topic: Extensions, Apps, and Version Compatibility]] | How do I separate stable core, extensions, experiments, and Drafts, and fall back safely? | Version ledger + compatibility matrix + negative interoperability tests |

Allow 11–16 hours for the stable core: 60–90 minutes for each of the first five lessons and 2–4 hours for each project. Study the frontier topic only for extensions or migration exploration. Do not read all 18 reference-layer pages in order at the start; consult them when you have a specific question.

## Hands-on entry points

### Main project: Offline MCP teaching validator

From the repository root:

```powershell
Set-Location ".\docs-EN\mcp" # Enter the MCP teaching-project directory so that subsequent relative paths resolve correctly.
python -B .\examples\validate_mcp_messages.py # Run 54 offline JSON-RPC cases; -B does not create __pycache__.
python -B .\examples\test_validate_mcp_messages.py # Run all regression tests in normal interpreter mode.
python -B -O .\examples\test_validate_mcp_messages.py # Verify that critical protocol gates do not rely on bare assert removable by -O.
python -B -W error .\examples\test_validate_mcp_messages.py # Promote every warning to failure to expose compatibility problems early.
python -B -O -W error .\examples\test_validate_mcp_messages.py # Cover optimized and strict-warning modes together.
```

Current acceptance baseline:

- Strict JSON fixture: 54 cases.
- 16 positive passes and 38 expected negative rejections.
- 108 unit/data-driven tests.
- Normal and `-O` modes, plus warnings-as-errors, all pass.
- No network, secret, third-party dependency, or cache requirement.

### Advanced project: Loopback Streamable HTTP and OAuth resource boundaries

Complete the offline message state machine first, then run the independent real HTTP boundary:

```powershell
python -B .\examples\streamable_http\loopback_mcp_http.py demo # Run real loopback HTTP through the normal handshake, JSON/SSE, and session path.
python -B .\examples\streamable_http\loopback_mcp_http.py attack # Run attack paths; BLOCK means attacks were successfully rejected.
python -B .\examples\streamable_http\test_loopback_mcp_http.py # Run 80 HTTP-boundary regression tests in normal mode.
python -B -O .\examples\streamable_http\test_loopback_mcp_http.py # Verify that production gates do not rely on bare assert in optimized mode.
python -B -W error .\examples\streamable_http\test_loopback_mcp_http.py # Promote resource, thread, and HTTP warnings to failures.
python -B -O -W error .\examples\streamable_http\test_loopback_mcp_http.py # Combine the strictest interpreter and warning checks.
```

Current acceptance baseline: real loopback POST/GET/DELETE and JSON/SSE round trips; CLI outputs `PASS`/`BLOCK`; 80 tests cover initialize alternative versions, Origin, headers/statuses, Unicode identity/session, PRM document/challenge shape, RFC 8707 resource, scope/tenant/revision, concurrency, JSON-depth budgets, explicit recovery, no cursorless replay, expiry, and revocation. See [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|the project lesson]].

> [!warning] Authorization capability boundary
> The project's HTTP is real; its token policy is an offline fixture. It has no authorization server, PKCE, signature/JWKS, introspection, or TLS and must not be described as “OAuth implemented.” Its `http://127.0.0.1` resource validates only PRM shape and does not meet RFC 9728's HTTPS requirement.

### Third project: minimal real-SDK interoperability

After both teaching projects, choose one official SDK:

1. Follow [[mcp/upstream-references/mcp/mcp-5a5f093c|Build an MCP Server]] to make a read-only, offline minimal server.
2. Use [[mcp/upstream-references/section-06/mcp-inspector-168aa4da|MCP Inspector]] to validate initialize and tool/resource behavior.
3. Follow [[mcp/upstream-references/mcp/mcp-162d781b|Build an MCP Client]] to make a minimal client.
4. Record the protocol specification, negotiated version, SDK, and client/server versions.
5. Add one negative schema test, one missing-capability test, and one security test.

Dynamic SDK commands, package names, and arguments must come from official documentation at development time; do not guess them from this learning path.

## Mastery checklist

- [ ] I can explain why a host normally establishes an independent client for each server.
- [ ] I can list three server features and three client features without notes.
- [ ] I can state a message's direction, ID, capability, and lifecycle state.
- [ ] I can explain why `sampling.tools`, elicitation mode, and Tasks need sub-capabilities.
- [ ] I can write an input schema with required fields, enums, and an unknown-field policy, plus a verifiable output schema.
- [ ] I can distinguish a JSON-RPC protocol error from a tool-execution error.
- [ ] I can explain stdio stdout restrictions and the Origin/session/authorization risks of Streamable HTTP.
- [ ] I can explain why token passthrough is prohibited and where form/url elicitation place their secret boundary.
- [ ] I can use Inspector/logs with the seven-layer method and record four kinds of version fact.
- [ ] I can run and explain the offline project's 54 cases and 108 tests.
- [ ] I can run the loopback project's CLI `PASS`/`BLOCK` and 80 tests, and explain initialize version negotiation, JSON/SSE, Unicode identity/session, and 401/403.
- [ ] I can state that the offline message validator does not cover real transport, and the loopback project still does not cover real OAuth, the full specification, or SDK interoperability.

## Relationships to other knowledge bases

- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]]: how a model/host chooses, approves, and executes tools; MCP describes how capabilities are discovered and exchanged across processes/services.
- [[agent-skills/00-index|Agent Skills]]: packages procedural knowledge about “how to complete a task”; MCP provides “which external capabilities and context can be accessed.” They can be combined and do not replace one another.
- [[agent-core/00-index|Agent Core]]: planning, state, memory, and execution loops; MCP is only one integration boundary.
- [[a2a/00-index|A2A]]: discovery, messages, Tasks, and Artifacts between independent Agent applications; MCP connects an Agent/Host with tools, resources, and context capabilities. They can be combined but are not interchangeable.
- [[api/00-index|API]]: HTTP, OAuth, retry, idempotency, and error handling are the underlying foundation of remote MCP.
- [[ai-safety/00-index|AI Safety]]: expands on prompt injection, permissions, supply chain, and runtime governance.
- [[runtime-monitoring/00-index|Runtime Monitoring]]: brings request IDs, capability decisions, duration, and outcomes into observability.

## Primary references

The following are first-party MCP or original protocol sources, retrieved or checked on 2026-07-21.

| Topic | Source |
| --- | --- |
| Architecture | [MCP Architecture](https://modelcontextprotocol.io/docs/learn/architecture) |
| Current specification | [MCP 2025-11-25 Specification](https://modelcontextprotocol.io/specification/2025-11-25) |
| Lifecycle/capabilities | [Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) |
| Transports | [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) |
| Authorization | [Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html), [RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html) |
| Schema | [Schema Reference](https://modelcontextprotocol.io/specification/2025-11-25/schema) |
| Tools | [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |
| Roots | [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots) |
| Sampling | [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling) |
| Elicitation | [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation) |
| Tasks | [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks) |
| Extensions, Apps, and Tasks migration | [Extensions Overview](https://modelcontextprotocol.io/extensions/overview), [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview), [Tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview) |
| Security | [Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) |
| Debugging | [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector), [Debugging](https://modelcontextprotocol.io/docs/tools/debugging) |
| JSON-RPC | [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification) |

## Official-document reference layer

The following 18 pages are all local Chinese summaries that existed before this task, not upstream-body mirrors. Between 2026-07-19 and 2026-07-20, narrow corrections were made to Roots, logging, the secret boundary of elicitation, optional sessions, vendor-specific Custom Connectors, the scope of Agent Skills, session-hijacking risk classification, and a removed Example Clients source. Every page remains `needs-review` and fails closed on the public site. Folder-qualified wikilinks remove ambiguity among same-named files. They can reflect only the state of material when it was curated; current protocol and product facts must be verified against the stable specification, target SDK/host, and actual capability negotiation.

### 01 — Introduction

- [[mcp/upstream-references/section-01/model-context-protocol-e83708fd|What Is the Model Context Protocol?]]

### 02 — Understanding MCP

- [[mcp/upstream-references/mcp/mcp-12d3c24c|MCP Architecture Overview]]
- [[mcp/upstream-references/mcp/mcp-69534d06|Understanding MCP Servers]]
- [[mcp/upstream-references/mcp/mcp-33873fc3|Understanding MCP Clients]]
- [[mcp/upstream-references/mcp/reference-04-f9b98715|Protocol Versioning]]

### 03 — Developing with MCP

- [[mcp/upstream-references/mcp/mcp-dffc6dbd|Connect to a Local MCP Server]]
- [[mcp/upstream-references/mcp/mcp-e14fd18b|Connect to a Remote MCP Server]]
- [[mcp/upstream-references/mcp/agent-skills-f0c694a5|Build with Agent Skills]]
- [[mcp/upstream-references/mcp/mcp-5a5f093c|Build an MCP Server]]
- [[mcp/upstream-references/mcp/mcp-162d781b|Build an MCP Client]]

### 04 — Clients

- [[mcp/upstream-references/section-04/reference-01-f513fcca|Client Best Practices]]
- [[mcp/upstream-references/section-04/sdks-d79fa5dd|SDKs]]

### 05 — Security

- [[mcp/upstream-references/section-05/mcp-81f62b4a|Understanding MCP Authorization]]
- [[mcp/upstream-references/section-05/reference-02-972d7619|Security Best Practices]]

### 06 — Developer tools

- [[mcp/upstream-references/section-06/mcp-inspector-168aa4da|MCP Inspector]]
- [[mcp/upstream-references/section-06/reference-02-d3fc8859|Debugging]]

### 07 — Examples

- [[mcp/upstream-references/section-07/reference-01-5d630d53|Example Clients]]
- [[mcp/upstream-references/section-07/reference-02-ff330926|Example Servers]]
