---
title: "Frontier Topic: MCP Extensions, Apps, and Version Compatibility"
aliases:
  - MCP extensions and Apps
  - MCP frontier observations
tags:
  - MCP
  - frontier
  - compatibility
source_checked: 2026-07-19
content_tier: frontier
content_origin: original
content_status: dynamic
lang: en
translation_key: "MCP/学习路线/07-前沿专题-扩展Apps与版本兼容.md"
translation_source_hash: 2476e7b3f15a86b5a166396f615567b82f9169ec4df4b66568c2af151359e842
translation_route: zh-CN/MCP/学习路线/07-前沿专题-扩展Apps与版本兼容
translation_default_route: zh-CN/MCP/学习路线/07-前沿专题-扩展Apps与版本兼容
---

# Frontier Topic: MCP Extensions, Apps, and Version Compatibility

## Learning objectives

After this lesson, you should be able to:

- Record the current stable specification, independent extensions, experimental extensions, and a next-version draft separately.
- Explain which layer owns dynamic tool discovery and which layer owns the host policy of exposing only a small set of tools to the model.
- Write a compatibility matrix for extension negotiation, missing support, fallback, authorization, and breaking changes.
- Explain the value of MCP Apps and Tasks without incorrectly presenting either as a core capability that every implementation supports.

> [!warning] Observation status, not a stable prerequisite
> This page records first-party MCP materials as of 2026-07-19. `2025-11-25` remained the official latest stable specification; `2026-07-28` was a locked but not formally released release candidate under `/specification/draft`. Extensions evolve independently, and support varies across hosts, SDKs, and servers. Before implementation, recheck the specification version, extension version, support matrix, and actual negotiation outcome.

## Build a four-layer version ledger first

| Layer | Status on 2026-07-19 | Conclusion you may draw |
| --- | --- | --- |
| core stable | `2025-11-25`; marked latest by the official version page | You may write protocol tests against its MUST/SHOULD requirements; still validate the real implementation on both sides |
| official extension | In `ext-*` repositories in the MCP organization; evolves independently from core | Use only when both sides explicitly negotiate support; an SDK can conform to core without implementing it |
| experimental extension | In `experimental-ext-*` repositories for incubation | Use only as an experimental dependency, with a pinned version, isolation, and exit plan |
| draft core/SEP | Official Draft or a proposal still in progress | Suitable for migration exploration; cannot replace the current stable interoperability contract |

Recording “we support MCP” is not actionable. At a minimum, record the core specification version, version actually negotiated during initialize, extension identifier and version, host/client/server/SDK version, validation date, and fallback behavior.

## Dynamic discovery does not mean putting every tool into context

The stable specification already has `tools/list`, pagination, and optional `notifications/tools/list_changed`. That solves “how can the client obtain the current tool catalog?” It does not decide which schemas a host should expose to the model for a particular turn.

A controlled on-demand tool layer normally has three steps:

1. **Synchronize the catalog.** Read the name, description, input/output schema, and version fingerprint from an authorized server. Invalidate the cache after a list change.
2. **Deterministic prefilter.** Remove unavailable tools according to tenant, identity, task type, data domain, risk, and environment. Security policy must not be delegated to model ranking.
3. **Task-level selection.** Retrieve or classify a small set of candidate schemas and let the model choose among them. Before the call, runtime still revalidates arguments, permissions, approval, and budget.

Typical failures are treating tool descriptions as trusted authorization claims, caching a list without handling change, approving by name rather than schema fingerprint, and hiding side effects or error semantics to save tokens. Validation should cover tool addition/removal, a schema change under the same name, unauthorized candidates, pagination, cache invalidation, and model-selection error.

The current Draft adds server discovery and describes the base protocol as stateless, self-contained requests with per-request capability negotiation. That is a next-version candidate design and must not be applied backwards to `2025-11-25`'s stateful connection and initialization negotiation.

## Extension negotiation and fallback

Official extension rules require extensions to be off by default and explicitly opted into by both client and server. Extension support is exchanged through `extensions` in capabilities. When one side lacks support, the application must:

- Fall back to a meaningful core result; or
- If the extension is a security or business hard requirement, reject explicitly instead of silently changing semantics.

A capability says only that an implementation claims it can speak a protocol feature. It does not mean identity is authenticated, resources are authorized, a user has approved, or returned content is trustworthy. Authorization, approval, and observation sanitization remain host/runtime responsibilities.

Extensions upgrade independently. Adding a required field, changing a field's type or meaning, or removing a field can all be breaking. Prefer a version inside the extension or a capability flag, and retain an explicit sunset condition for the old path.

## MCP Apps: an interactive UI is another trust boundary

MCP Apps allow a tool to reference an interactive UI resource that the host renders in the conversation as a form, chart, or player. First-party documentation describes a sandboxed iframe and `postMessage` communication; the host controls bridge capabilities and security policy, and client support is not universally consistent.

Before adoption, answer four questions:

1. Is plain text or a regular web application already sufficient?
2. Can a client that does not support Apps receive an equivalent text or structured fallback?
3. Who authorizes the iframe's network, scripts, resources, tool proxying, and persistent state?
4. When the UI initiates a write, does it again pass through identity, parameter validation, approval, idempotency, and audit rather than inheriting trust from “being shown in the conversation”?

Sandboxing is an isolation mechanism, not business authorization. Also test CSP/allowed origins, oversized messages, replay, forged tool results, cross-tenant state, and behavior after the host denies a capability.

## Tasks: do not mix two wire contracts

Tasks in `2025-11-25` core are marked experimental. The `2026-07-28` release candidate moves Tasks to an extension and restructures capability/discovery; the related SEP explicitly states that the new extension and the `2025-11-25` experimental Tasks wire are **incompatible**. Until `2026-07-28` becomes a formal release, record it as a Draft candidate rather than as the current stable version.

Migration therefore cannot be a one-line feature-flag change:

- Choose message shape by negotiated core version and extension capability.
- Store legacy task IDs and extension task IDs in separate domains.
- Test creation, polling, input request, cancellation, terminal state, TTL, and reconnection separately.
- When Tasks are unsupported, fall back to a synchronous result, external job handle, or explicit rejection.
- Do not remove the old path until the draft becomes stable and both implementations pass interoperability tests.

## Minimal compatibility matrix

Fill measured results for every target host/server instead of copying a support list:

| Scenario | Expected behavior | Evidence to test |
| --- | --- | --- |
| Same core version, no extension | Use core normally | Initialize/negotiation record and schema contract tests |
| One side lacks an optional extension | Core fallback | Return remains meaningful; no extension method is called |
| One side lacks a required extension | Connection or request rejects explicitly | Stable error code and no partial side effect |
| Tool list changes while running | Invalidate cache and reselect | list-changed, schema fingerprint, approval invalidation |
| Apps host lacks UI support | Text/structured fallback | No blank message or hidden write |
| Legacy Tasks versus new extension | Do not mix wire shapes | Two-version fixtures and negative tests |
| Recover a task after disconnect | Recover from a persistent handle | Reconnect, duplicate polling, irreversible terminal state |

## Practice task

Choose one real host, one client SDK, and one server, then submit a version-compatibility record:

1. Save redacted initialize request/response and the actual negotiated version.
2. List core capabilities, extensions, authorization scope, and user-approval scope; do not combine them into one column.
3. Add and remove a tool once, proving that the cache and candidate schema update.
4. Disable one extension and verify fallback or explicit rejection.
5. When testing Apps/Tasks, pin the extension version and add a negative case for a non-supporting client.

The completion standard is not “the demo displays.” Every negotiated combination must have a deterministic outcome, no unauthorized side effect, and enough logs to reconstruct which contract was used.

## References

The following are first-party MCP materials, checked on 2026-07-19:

- [MCP 2025-11-25 Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Draft Specification](https://modelcontextprotocol.io/specification/draft)
- [2026-07-28 Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)
- [Extensions Overview](https://modelcontextprotocol.io/extensions/overview)
- [MCP Apps Overview](https://modelcontextprotocol.io/extensions/apps/overview)
- [MCP Tasks Extension Overview](https://modelcontextprotocol.io/extensions/tasks/overview)
- [SEP-2663: Tasks Extension](https://modelcontextprotocol.io/seps/2663-tasks-extension)

Next, return to [[mcp/00-index|the MCP index]] and maintain this page's observations separately from stable project tests.
