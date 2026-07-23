---
title: "2026-07-22 Phase 20 Deep Review Record: Protocol, Media, Machine
  Learning, and Workflow Contracts"
aliases:
  - Phase 20 optimization record
tags:
  - maintenance
  - api
  - agentic-patterns
  - workflow
  - machine-learning
  - multimodal
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第二十阶段协议媒体机器学习与工作流合同深审记录.md
translation_source_hash: 35bdb629c9f83288e1e3b6552e8629c516d328ede046efc61fbe434cb7d00f6e
translation_route: zh-CN/维护记录/2026-07-22-第二十阶段协议媒体机器学习与工作流合同深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第二十阶段协议媒体机器学习与工作流合同深审记录
---

# 2026-07-22 Phase 20 Deep Review Record: Protocol, Media, Machine Learning, and Workflow Contracts

## Phase conclusion

This phase turns boundaries in seven adjacent courses—often misread as “correct format, connected protocol, or successful model generation means it can be executed or released”—into testable contracts. HTTP/JSON, Agent delegation, conventional machine learning, generative media, and deterministic workflows now all distinguish: parseable input; a valid structural/business contract; authorization by a trusted principal; a receipt for a side effect; and a reconciled final outcome. The learning route therefore no longer treats an SDK, protocol capability, model output, digest, or content credential as business success, proof of fact, or permission.

It covers API, JSON, [[agentic-design-patterns/00-index|Agentic Design Patterns]], Machine Learning, Image Generation, Video Generation, and Workflow Automation.

> [!important] What this phase does not prove
>
> Offline standard-library fixtures, a single-process state machine, loopback HTTP, static-page checks, and a Quartz build prove consistency between teaching contracts and current content. They do not prove production validation of real OAuth/mTLS, external webhooks or message systems, production concurrency/leases, real Provider APIs, model quality/cost, object-level ACL backends, C2PA validators, physical content purge, human-approval signatures, or legal compliance.

## Multi-Agent division of work and primary-Agent review

The primary Agent first established cross-course standards that “structured input is not an executable action,” “a protocol ID is not a trusted identity,” “a receipt is not an outcome,” and “media provenance is not fact or authorization.” It then assigned non-overlapping work:

1. Primary Agent: protocol, retries, structured output, and entry-page work for API and JSON.
2. Agentic patterns: review only the original beginner route and offline project; do not rewrite the frozen reference layer with an unknown license.
3. Machine learning: core path, offline classification project, and deep-learning bridge reference.
4. Image/video: media-asset governance, release evidence, and two offline projects.
5. Workflow Automation: triggers, contracts, scheduling, approvals, observability, and the offline DAG project.

The primary Agent independently checked Agentic MCP/A2A normative wording, dynamic media announcements, cross-version machine-learning behavior, workflow event identity, and every project test count. No Agent staged, committed, pushed, or rewrote another course. A pre-existing user change to <code>05-persistent-state-recovery-and-idempotency.md</code> in Workflow Automation was explicitly isolated; this phase neither rewrote it nor included it in its specialist conclusions.

## Key changes

### API and JSON: separate transport, representation, and execution gates

- Although Requests <code>SSLError</code> is a subclass of <code>ConnectionError</code>, certificate-chain or hostname-identity failure no longer enters the retry branch. The reliable client adds regressions, and the course uses a decision diagram to distinguish TLS, unknown side effects, idempotent queries, and <code>Retry-After</code> handling.
- API examples now accept <code>application/json</code> and <code>+json</code> based on parsed media type. Pagination teaching checks successful status, JSON object shape, element shape, cursor, <code>max_pages</code>, and <code>max_items</code>, rather than sending a “successful response that is not JSON” or one-page growth downstream.
- The JSON course adds the Mermaid gate: complete bounded decoding → strict parsing → domain schema/profile → factual/version/business invariants → authorization/allowlist → approval/idempotency → outcome. JSON from a model, MCP, or external source passes only some of these gates.

### Agentic patterns: protocol capability does not take over authorization, and approval follows evidence

- The beginner route adds a responsibility table for Tool Calling, MCP, and A2A: local capability invocation, standardized tool/resource connection, and independent-Agent delegation can be combined, but none replaces identity outside the model, object-level authorization, approval, idempotency, or receipt/outcome verification.
- Current MCP Authorization and A2A specifications supply the boundaries for resource/audience, no token passthrough, per-request/object-scope authorization, and the fact that <code>TASK_STATE_AUTH_REQUIRED</code> asks for additional authorization rather than confirming human approval.
- The recoverable-workflow state rises to v3. High-risk paths complete read-only checks before persisting an approval wait. The approval fingerprint binds action, check evidence, risk, and policy version. Passing an approval decision on the first call fails closed, as do duplicate JSON keys and duplicate receipt keys.

### Machine learning: correct a real version regression and narrow deep-learning reference material to verifiable interface boundaries

- <code>ticket_router.py</code> removes explicit <code>l1_ratio=0.0</code>, which triggered a warning when scikit-learn 1.7.1 runs with warnings as errors. The course's locked direct dependency remains 1.9.0, but it accurately says the local work verified only compatibility with 1.7.1; that does not replace rebuilding the locked environment.
- Boundaries for data splitting, nested selection, calibration/thresholds, drift, group slices, fairness, and privacy minimization return to the core path.
- The loss/optimizer reference is rewritten to make logits/labels/shapes, CrossEntropy versus BCE-with-logits, loss versus business metrics, and framework differences among Adam, AdamW, and weight decay explicit. The Transformer page distinguishes the original paper's post-norm from the teaching diagram's pre-norm. The Mamba page adds upstream Linux/Python/PyTorch/CUDA runtime requirements and the boundary that complexity is not measured throughput.
- The site metadata gate also caught and repaired invalid <code>content_origin</code>/<code>content_status</code> enumerations on four pages; they are now truthfully labeled original and validated.

### Image and video: media assets have a provenance chain, but a credential or generation result is not automatically fact

- Both courses and projects consistently use <code>asset_id</code>, <code>source_revision</code>, <code>transform_id</code>, <code>release_id</code>, <code>acl_reference</code>, and a revocation/deletion-propagation plan. Assets must pass object-level ACL before preview, scoring, or model invocation.
- C2PA/Content Credentials are limited to verifiable provenance/integrity assertions. They do not prove factual truth, a person's identity, rights, or business authorization. <code>evidence_bound</code> and <code>evidence_supported</code> remain separate.
- The Video index accurately states that the closure of Sora 2/API was a **future plan** announced on an official page checked on 2026-07-22 (target 2026-09-24), not an already completed event.
- The image-task auditor and video-task-package validator add hard gates and regressions for asset revision, ACL, deletion propagation, factual evidence, budget, and release chain.

### Workflow Automation: event identity may deduplicate, but it is neither caller identity nor authorization

- The offline engine no longer concatenates CloudEvents identity as <code>source + "::" + id</code>. It encodes a canonical JSON pair to avoid delimiter collisions. Optional <code>time</code> is narrowed to the RFC 3339 subset that the standard library can reliably parse with an explicit UTC offset; it is not claimed to be a general CloudEvents gateway.
- The entry teaching sequence becomes bounded raw input, signature/mTLS/authentication, freshness/nonce, contract, structured deduplication, persistent creation, and asynchronous execution. Each execution is still authorized through a trusted actor, policy, and resource ACL.
- The course consistently distinguishes the scopes of <code>event identity</code>, <code>instance_id</code>, <code>operation_id</code>, <code>attempt_id</code>, <code>trace_id</code>, receipt, and outcome. It strengthens boundaries for conditional joins, unknown results, compensation, atomic approval consumption, versioning, and observability.

## Cross-course terminology and responsibility boundaries

| Term | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| Parseable JSON | Text can be decoded under constrained resources and pass syntax. | Domain schema, factual verification, authorization, or permission to execute. |
| Protocol/capability ID | Correlation information for a protocol request, tool/resource capability, or remote task. | A trusted actor, tenant, object permission, or local action ID. |
| <code>event identity</code> | An authenticated structured <code>(source, id)</code> used to determine duplicate events. | Webhook signature, caller identity, authorization result, or retention policy for deduplication. |
| <code>operation_id</code> / <code>attempt_id</code> | The former represents a stable business intention; the latter a claim, delivery, or retry. | Each other, a receipt, trace ID, or business outcome. |
| Receipt / outcome | The former is evidence of an external action; the latter is a reconciled final business state. | “Accepted,” an HTTP success code, remote <code>completed</code>, or a model self-report. |
| <code>source_revision</code> / <code>transform_id</code> / <code>release_id</code> | Respectively, a frozen input, one processing/transform, and an auditable release candidate. | Content truth, current authorization, dataset version, or model alias. |
| Content Credentials | A provenance/integrity signal for a particular assertion/history. | A person's consent, copyright/access authorization, factual truth, or release approval. |
| Approval fingerprint | A substitution-resistant digest binding action, evidence, policy, and state. | Approver authentication, signature, one-time-consumption transaction, or downstream authorization. |

## Key sources and material boundary

All new Chinese-language explanations, Mermaid diagrams, teaching code, fixtures, and regression tests from this phase are original. Third-party material is used only through links, specification facts, and minimum necessary terminology; complete materials without explicit redistribution conditions are not propagated into the public layer. Dynamic conclusions prioritize primary sources:

- [Requests documentation](https://docs.python-requests.org/en/stable/), [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), [Python json](https://docs.python.org/3.14/library/json.html), and [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12): HTTP, representation, and strict parsing.
- [MCP 2025-11-25 Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) and [A2A 1.0 specification](https://a2a-protocol.org/latest/specification/): resource/audience, token, and remote-task authorization boundaries.
- [scikit-learn 1.9 release history](https://scikit-learn.org/stable/whats_new.html), [common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html), [PyTorch CrossEntropyLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html), and [AdamW](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html): project compatibility, training/evaluation, and interface boundaries.
- [C2PA 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html), [OpenAI video guide](https://developers.openai.com/api/docs/guides/video-generation), [W3C WebVTT](https://www.w3.org/TR/webvtt1/), and [NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence): generated media, provenance, timelines, and risk boundaries.
- [CloudEvents 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md), [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339), [Temporal Workflow Execution](https://docs.temporal.io/workflow-execution), and [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421): events, time, durable runtime, and inbound-message security.

## Verification evidence

| Check | Phase result |
| --- | --- |
| API / JSON | 35 / 42 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Agentic Design Patterns original beginner route | 57 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Machine Learning | 10 tests; normal and <code>-O</code> passed under <code>-B -W error</code> (actual interpreter: scikit-learn 1.7.1). |
| Image Generation / Video Generation | 90 / 133 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Workflow Automation | 74 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Consolidated specialist regressions | 441 tests per mode across the preceding 7 groups; warnings-as-errors passed. |
| Static/scope checks | Relevant Markdown Python fences, JSON/PowerShell/Mermaid specialist checks, and <code>git diff --check</code> for all seven directories passed. |
| Final website unit tests | <code>.website npm test</code>: 47/47 passed. |
| Final public build | 914 source Markdown pages, 574 full pages, 340 fail-closed stubs, and 229 assets; 917 staged Markdown pages, 2,468 HTML pages, and 2,821 public files. Broken local links, sensitive leaks, table wikilinks, interactive checkboxes, and KaTeX errors were all 0. |

The image/video projects had two ignored, untracked <code>.pyc</code> files accidentally produced by <code>py_compile</code>. The environment rejected an exact deletion command, so no policy was bypassed and they were not placed under version control. All other Python tests in this phase used <code>-B</code>; those local caches were neither course artifacts nor verification evidence.

## Follow-up queue

1. Rebuild the Machine Learning project in an isolated, locked scikit-learn 1.9.0 environment and conduct fuller evaluation with real but de-identified data split by group/time. The current small fixtures and 1.7.1 compatibility are not production proof.
2. Run controlled integration tests against real API/MCP/A2A, media providers, and workflow runtimes. Add OAuth/mTLS, signatures/nonces, durable state, concurrent leases, outbox/inbox, external-receipt reconciliation, object ACL, and deletion-propagation validation.
3. Inspect the new Mermaid diagrams, long tables, and callouts in Obsidian desktop. A Quartz build verifies only the public rendering path and cannot replace local reading experience.
4. Continue deep review of Deep Learning and other courses that retain early <code>source_checked</code> dates but were not covered in this phase. Update with page evidence, not bulk date changes.

This record covers only Phase 20. It does not mean the long-running <code>/goal</code> is complete.
