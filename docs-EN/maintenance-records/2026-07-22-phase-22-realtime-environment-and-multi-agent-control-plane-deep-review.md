---
title: "2026-07-22 Phase 22 Deep Review Record: Realtime, Environment, and
  Multi-Agent Control Plane"
aliases:
  - Phase 22 optimization record
tags:
  - maintenance
  - realtime
  - environment-agent
  - multi-agent
  - security
  - evaluation
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第二十二阶段实时环境与多Agent控制面深审记录.md
translation_source_hash: c7d8f5fe2280c2a06be10c93406c3cb57c40084468c6adf4eec9b8e77ddbbbf4
translation_route: zh-CN/维护记录/2026-07-22-第二十二阶段实时环境与多Agent控制面深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第二十二阶段实时环境与多Agent控制面深审记录
---

# 2026-07-22 Phase 22 Deep Review Record: Realtime, Environment, and Multi-Agent Control Plane

## Phase conclusion

This phase separates things that merely “look as though they happened” in realtime sessions, environment execution, and multi-Agent collaboration into independently verifiable facts. Media/text observation, model proposal, runtime state, authorization decision, execution receipt, and human reconciliation cannot replace each other. The courses now distinguish the correlation/state contracts an offline simulator can prove from the parts a production system must still prove through adapters, IAM, durable state, external facts, and human controls.

It covers Realtime Multimodal Interaction, Environment Agents, and Multi-Agent Collaboration.

> [!important] What this phase does not prove
>
> Offline events, synthetic JSON, single-process scheduling, and a Quartz build do not prove real audio capture/playback; network/device quality; Provider-session recovery; real tool/business receipts; user identity; object ACL; approval signatures; cross-process leases; atomic transactions; human reconciliation; compensation execution; or organizational compliance. They prove only that the current teaching contracts, failure paths, and public-release boundary are repeatably checkable.

## Multi-Agent division of work and primary-Agent review

1. The Realtime Multimodal specialist reviewed product examples, media/control/state planes, backpressure, disconnect recovery, and the offline session project. The primary Agent made follow-up repairs to JSON strictness, the tool-receipt boundary, state diagrams, and test counts.
2. The Environment Agent specialist stayed within browser, desktop, coding, sandbox, recovery, and evaluation pages; it added boundaries for identity, delegation, credentials, approval, audit, and concurrent recovery without changing the runtime project's established teaching scope.
3. The Multi-Agent specialist addressed delegation, messaging, conflict, stopping, evaluation, and the offline scheduler. The primary Agent standardized learning order for the new identity chapter, <code>grant_ref</code> terminology, and cross-course citations.
4. Two independent read-only reviews checked, respectively, the three courses' facts/links/contract closure and the scheduler's state machine, dependency propagation, result conflict, and CLI. All P1/P2 issues received narrow implementation, documentation, and negative-test repairs from the primary Agent and then a recheck.

The worktree already contained some uncommitted realtime/environment/multi-Agent edits at the start. This phase neither reverted nor attributed that pre-existing work; it supplemented or narrowed only breakpoints found through page-level review.

## Key changes

### Realtime multimodal: layer strict input, waiting gates, and the execution ledger

- <code>realtime_session.py</code> now rejects duplicate JSON keys and nonstandard constants such as <code>NaN</code>/<code>Infinity</code>, and uses <code>allow_nan=False</code> when computing event digests and output JSON. Nested tool parameters cannot bypass the finite-JSON boundary.
- <code>WaitingTool</code> is now a testable output gate: it may declare additional calls, receive matching results, handle a user interruption, disconnect, or timeout. Until every pending call ends, it rejects new input frames, output audio, and response completion. State diagram, textual alternative, and regression tests state that this is a blocking teaching model, not a full-duplex production product.
- Model <code>tool.call</code>, an application-internal execution receipt, and offline <code>tool.result</code> are explicitly distinct. The simulator's simplified events prove only <code>call_id + response_id</code> correlation and derive a turn from the response ledger. A production write must still recheck authorization/approval at the execution boundary, persist intent/idempotency/receipt, and reconcile against external facts.
- Project tests rise from 29 to 33, covering duplicate JSON keys, nonstandard numeric values, non-finite nested parameters, multiple tool results, and input/output rejection while waiting for a tool.

### Environment Agents: plans, identity, and environment capability are no longer conflated

- The unified interaction contract adds five evidence tables: user goal, model plan, delegation/policy, specific approval, and adapter receipt. Page wording, screen avatars, model self-reports, and an already signed-in state are observations only; they cannot become authorization.
- Browser pages add the boundary for dynamic locators and <code>locator.all()</code>. Desktop pages state that window/accessibility information is not proof of business subject or object ownership. Coding pages state that a Git linked worktree protects a worktree but is not a security sandbox for processes, networks, credentials, or files outside the repository.
- Sandbox, approval, and recovery pages add the subject–delegation–credential–approval chain, minimum audit retention, and worker lease/state-version requirements beyond a generation high-water mark. Evaluation pages separate functional, security, privacy/audit, recovery, and release-reproducibility evidence.

### Multi-Agent systems: delegation does not transfer credentials, and conflict no longer masquerades as success

- A new Identity, Authorization, and Cross-Boundary Trust lesson comes after the delegation contract and before messaging/shared state. It distinguishes role name, runtime principal, Agent Card, <code>grant_ref</code>, approval, and receipt; it says an A2A Card is for discovery rather than business authorization, and MCP HTTP must not pass through a token intended for other resources.
- Delegation contracts consistently use <code>grant_ref</code>, emphasizing that it is a secret-free reference resolved by policy/IAM rather than a bearer credential. The learning route and mastery criteria add cross-trust-domain and execution-boundary rechecks.
- The scheduler now propagates <code>failed</code>, <code>denied</code>, <code>blocked</code>, or <code>needs_review</code> pending-dependency descendants to a fixed point, preventing non-topological declaration order from reporting an upstream failure as deadlock. Task states use a whitelist transition model and still permit only <code>succeeded → needs_review</code> as a conflict escalation.
- When one <code>(task_id, idempotency_key)</code> receives distinct payload digests, its public <code>result</code> is cleared and marked <code>result_trust: conflicted</code>. <code>result_conflicts</code> deep-copies both pieces of evidence, digests, event sequence numbers, and state versions only for synthetic teaching data. A real system should use protected evidence references, isolate already-started downstream side effects, and leave query/compensation/revocation to human decision.
- The documentation no longer calls Python sort-key JSON serialization canonical JSON across implementations. Cross-process implementations must fix and version their own digest scheme. Project tests rise from 61 to 66, adding reverse-order three-layer failure/conflict propagation, invalid transitions, and conflicted-result isolation.

## Cross-course terminology and state boundaries

| Term | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| <code>grant_ref</code> | A secret-free, constrained authorization reference resolved by policy/IAM | Bearer token, visible role name, model plan, or standing execution permission |
| <code>tool.call</code> | A candidate tool intent proposed by a model or orchestration layer | An approved, executed, or committed business fact |
| Execution receipt | Reconciliable evidence from an external adapter/target system about a side effect | Model text, an offline <code>result</code> string, or connection recovery alone |
| <code>payload_digest</code> | A digest that binds a payload under a specified algorithm, version, and value rules | Unspecified “canonical JSON” or automatic cross-language equivalence |
| <code>needs_review</code> | A safe runtime freeze after mutually exclusive evidence is detected | An A2A standard task state, automatic retry, or default failure rollback |
| <code>state_version</code> / lease | Concurrency-control evidence preventing an old worker or late write from overwriting current state | Single-process in-memory state, checkpoint signature, or a simple reconnect marker |

## Sources, original material, and third-party boundary

All new Chinese-language explanations, Mermaid diagrams, teaching code, and tests in this phase are original. External specifications, papers, and official documentation are used only to check facts/boundaries; text without explicit public-redistribution terms is not copied. Primary sources include:

- [W3C WebRTC](https://www.w3.org/TR/webrtc/), [Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/), [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455), [RFC 3261](https://datatracker.ietf.org/doc/html/rfc3261), [OpenAI Realtime](https://developers.openai.com/api/docs/guides/realtime), [Google Live API](https://ai.google.dev/api/live), and [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721).
- [WebArena](https://arxiv.org/abs/2307.13854), [OSWorld](https://arxiv.org/abs/2404.07972), [SWE-bench](https://openreview.net/forum?id=VTF8yNQM66), [Playwright actionability](https://playwright.dev/docs/actionability), [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html), and [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework).
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/), [A2A Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/), [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices), and [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/multi_agent/).

## Verification evidence

| Check | Result |
| --- | --- |
| Realtime session project | 33 tests: normal, <code>-O</code>, warnings-as-errors, and <code>-O + warnings-as-errors</code> all passed. |
| Environment Agent project | 103 tests; all four modes passed. |
| Multi-Agent scheduler project | 66 tests; all four modes passed. |
| Consolidated project regressions | 202 tests per mode; 808 test executions across all four modes passed. |
| Static checks | AST checks for 7 scoped Python files, related Markdown/JSON semantics, and scoped <code>git diff --check</code> passed. |
| Website tests | <code>.website npm test</code>: 48/48 passed; <code>npm run build</code> succeeded. |
| Publication validation | 924 public pages, 231 assets; 0 broken local links, prohibited files, sensitive leaks, or KaTeX errors. |

## Follow-up queue

1. Before mapping the realtime blocking teaching state machine to a true full-duplex media adapter, separately design parallel capture/playout/side-effect states, device/network trials, and fallback paths.
2. Connect reference-style authorization for Environment/Multi-Agent courses to real IAM, short-lived credentials, approval signatures, leases/compare-and-set, protected audit, and business receipts; then test revocation, concurrent recovery, compensation, and cross-tenant attacks.
3. Inspect new Mermaid diagrams, long tables, and callouts in Obsidian desktop. Quartz's static build cannot replace local editing/interaction validation.

This record covers only Phase 22. It does not mean the long-running <code>/goal</code> is complete.
