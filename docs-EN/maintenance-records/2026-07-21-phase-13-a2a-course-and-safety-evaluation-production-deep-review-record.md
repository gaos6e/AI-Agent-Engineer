---
title: "2026-07-21 Phase 13 A2A Course and Safety, Evaluation, Production Deep
  Review Record"
aliases:
  - Phase 13 optimization record
tags:
  - maintenance
  - A2A
  - security
  - evaluation
  - production
  - multi-agent
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-21-第十三阶段A2A协议课程与安全评测生产化深审记录.md
translation_source_hash: 9c62e30a0d2276e35d10d418b34d5cad3f2d4dba4ce66f0db2217f1bcb3025df
translation_route: zh-CN/维护记录/2026-07-21-第十三阶段A2A协议课程与安全评测生产化深审记录
translation_default_route: zh-CN/维护记录/2026-07-21-第十三阶段A2A协议课程与安全评测生产化深审记录
---

# 2026-07-21 Phase 13 A2A Course and Safety, Evaluation, Production Deep Review Record

This phase adds an original optional A2A Protocol <code>1.0.0</code> course, connects it to v2 metadata, two Agent role paths, public navigation, and publication validation, while deeply reviewing Safety/Governance/Privacy, Evaluation/Benchmark/Monitoring, and MLOps/LLMOps/Synthetic Data. It fixes contract gaps that could wrongly allow teaching examples and layers dynamic specifications, real-runtime evidence, and offline validation.

The 346 fail-closed stubs are controlled third-party reference layers—not blank original courses: Deep Learning 140, Python Fundamentals 125, Agentic Design Patterns 32, LangChain 23, MCP 18, Agent Skills 8. No body was copied or policy relaxed to lower the number.

The A2A course has an entry, six topics, and an offline project: A2A boundaries versus API/orchestration/Tool Calling/MCP; Agent Card discovery/version/capability/signature/trust; Message/Task/Status/Part/Artifact; JSON-RPC/gRPC/HTTP+JSON/streaming/webhook/polling/version negotiation; authentication/object authorization/out-of-band credentials/multitenancy/untrusted content; and cross-implementation testing with migration/adoption decision. The validator rejects duplicate JSON fields, nonstandard numbers, invalid Base64, non-HTTPS production endpoint, terminal rollback, and completed task without Artifact. It is a spec subset/local policy, not SDK/Inspector/TCK/TLS/JWS/OAuth/interoperability proof. It is optional for <code>agent_app</code> order 32 and <code>agent_platform</code> order 38, with no hard prerequisite; the route grows to 57 courses/ten populated domains.

Safety/Governance/Privacy changes bind identity, object, data flow, dependency, and side-effect boundaries; clarify NIST iterations, ISO/IEC impact/certification boundaries, EU AI Omnibus status, PET protection limits, and NIST Privacy Framework 1.1 draft status. Evaluation/Benchmark/Monitoring add judge bias/prompt injection/arbitration/version freeze, estimand/task/trial/multiple-comparison/equivalence boundaries, contamination categories, cost/reporting discipline, OpenTelemetry GenAI dynamic status, incident closure, and fail-closed status enumeration. MLOps v2 binds online observation to passed candidate gate/fixed model/artifact digest, distinguishes shadow/Canary, and does not auto-expand on missing evidence; LLMOps uses actual digest-bound fallback evidence.

Verification: A2A 4 CLI fixtures/10 unit tests in three modes; Safety/Governance/Privacy 80/69/76; Evaluation/Benchmark/Monitoring 36/42/34; MLOps/LLMOps/Synthetic Data 52/60/40; 499 cases × three modes all pass; site tests 46/46; build 903 source Markdown, 557 full, 346 stubs, 906 staged pages, 2,421 HTML, and all gates 0. Sources include the [A2A 1.0 specification](https://a2a-protocol.org/latest/specification/), [A2A/MCP boundary](https://a2a-protocol.org/latest/topics/a2a-and-mcp/), [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), and primary privacy/evaluation/EU sources cited in the courses.

Follow-up: visual checks; two-or-more-SDK A2A matrix/Inspector/TCK/bindings/identity tests; real IAM/gateway/artifact/data-lineage/privacy evidence; real registry/control/Canary/rollback; and continued license/version/source review of stubs.
