---
title: "2026-07-21 Phase 16 Tool Protocol and RAG Lifecycle Deep Review Record"
aliases:
  - Phase 16 optimization record
tags:
  - maintenance
  - tool-calling
  - mcp
  - rag
  - knowledge-base
  - multi-agent
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-21-第十六阶段工具协议与RAG生命周期深审记录.md
translation_source_hash: 543386a12e31f52fa4d2830227e54487d72a2e303d01e983ddcdf0e6bdaab514
translation_route: zh-CN/维护记录/2026-07-21-第十六阶段工具协议与RAG生命周期深审记录
translation_default_route: zh-CN/维护记录/2026-07-21-第十六阶段工具协议与RAG生命周期深审记录
---

# 2026-07-21 Phase 16 Tool Protocol and RAG Lifecycle Deep Review Record

This phase deep-reviewed Tool Calling, MCP, RAG, and Knowledge Base without changing their order/domain. It repaired four high-risk chains: Tool Result v2 binding did not cover downstream request/receipt/status reference; SQLite persistence did not fully inherit approver identity/right-open expiry/business-state/status-query purpose; Knowledge Base query could treat search projection ACL/body as online fact; MCP validator/Streamable HTTP had pending-consumption and cursorless duplicate-SSE semantics defects.

Tool audit now binds tenant/subject/Provider/API family/response-call-operation, idempotency key/adapter/full tool contract, request/result digests, and downstream request/receipt/opaque status reference. SQLite persists <code>approver_id</code>, recomputes approval digest, checks business state at intent acceptance and worker submission, gives status query a separate host-owned call identity/purpose, checks portable UTC/approval TTL/lease before reservation, and explicitly rejects old v1 database rather than silently treating it as v2.

MCP separates JSON-RPC request/notification/success/error; bounds file/JSON depth/string/array/object/schema recursion/pending count; validates declared teaching Schema subset and rejects unimplemented keywords; provides finite <code>tools/list</code>, sampling text, and <code>tasks/list</code>; fails unimplemented prompts/logging/completion/tasks operations instead of accepting unverified success; and consumes pending only after method-specific success (or legal JSON-RPC error), never a fake business success.

RAG/Knowledge Base published pointer binds canonical revision and search projection. Canonical ACL runs before keyword matching/window; unauthorized documents do not return or consume public candidate window. Authorized candidates recompute canonical content/source/build and search-body hashes then compare canonical/search ACL; one-sided projection expansion has no visibility, reconciliation reports inconsistency, and body/ACL mismatch fails query closed.

Evidence: Tool Result 112, SQLite 81, MCP validator 101, MCP loopback 80, cited QA 71, provenance 71, adapter 36, external provenance 42, Knowledge Store 38 all pass normal and <code>-O -B -W error</code> with required CLI equivalence; 632 tests/mode; 46/46 site tests; build 907 source Markdown, 561 full, 346 stubs, 910 staged, 2,432 HTML; all gates 0. Sources include official Provider Function Calling, JSON Schema, MCP 2025-11-25, RAG research/OWASP, and SQLite docs.

Next: explicit persistent-runtime v1→v2 migration; locked SDK capture/replay/isolated live tests; mature Draft 2020-12 validator; durable MCP event store/ack/retention/session migration; transactional RAG store/projection; signed attestation; real retrieval/evaluation; and Obsidian visual checks.
