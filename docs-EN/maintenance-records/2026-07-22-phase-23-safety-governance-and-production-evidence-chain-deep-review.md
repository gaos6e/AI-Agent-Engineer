---
title: "2026-07-22 Phase 23 Deep Review Record: Safety, Governance, and
  Production Evidence Chain"
aliases:
  - Phase 23 optimization record
tags:
  - maintenance
  - ai-safety
  - ai-governance
  - evaluation
  - llmops
  - observability
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第二十三阶段安全治理与生产证据链深审记录.md
translation_source_hash: e4ad6695757da96632279c75c7be35206d662ef2400f34f1fb6cb32445615a5f
translation_route: zh-CN/维护记录/2026-07-22-第二十三阶段安全治理与生产证据链深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第二十三阶段安全治理与生产证据链深审记录
---

# 2026-07-22 Phase 23 Deep Review Record: Safety, Governance, and Production Evidence Chain

## Phase conclusion

This phase unifies safety, governance, evaluation, release gates, and runtime monitoring into a reviewable production evidence chain. Risk/control requirements cannot be replaced by a model output, hash, Trace ID, or passing boolean. Offline evaluation, release approval, Canary window, and regression candidate each have their own version, complete digest, owner, and independent source/authorization boundary.

It covers [[ai-safety/00-index|AI Safety]], AI Governance, Evaluation Systems, LLMOps, and Runtime Monitoring.

> [!important] What this phase does not prove
>
> Offline JSON, fixed fixtures, SHA-256, single-machine tests, and a static-site build cannot prove real model/tool execution, artifact provenance, Provider compliance, identity authorization, signed approval, production-telemetry completeness, user ground truth, causal business effect, or legal compliance. They prove only that the current teaching contracts, negative paths, handoff fields, and public-release boundary can be checked repeatedly.

## Multi-Agent division of work and primary-Agent review

1. The Safety/Governance specialist checked AI Act timelines, NIST/MCP security boundaries, identity/least privilege/supply chain, red teaming/incident response, traceability, and production change page by page. The Governance project adds data/Provider owners and version fields.
2. The Evaluation specialist checked MLflow automatic evaluation, OpenTelemetry GenAI semantic conventions, RFC 8785 boundaries, and the offline evaluation evidence chain. The primary Agent made invalid UTF-8 and oversized numeric values fail as CLI contract errors.
3. The LLMOps/Monitoring specialist narrowed conservative responses to Provider drift, observation-window/business-event age, integer numerators/denominators, and regression-candidate boundaries.
4. Two independent read-only reviews checked Safety/Governance and the cross-course digest protocol. The latter identified and drove fixes for online-observation bundle schema/profile not entering the decision digest, escaped surrogate rejection being too late in evaluation, and format labels not being fixed by golden vectors.

The worktree already contained uncommitted work in this phase's scope. This phase did not revert or reattribute it; it supplemented, narrowed, and verified issues discovered through contextual checks.

## Key changes

### Safety and governance: controls, approvals, and evidence no longer impersonate one another

- The AI Safety course connects identity, least privilege, supply chain, red teaming, monitoring, and incident response into an auditable control chain. A hash can find a mismatch only when actually compared in a controlled release gate; it cannot prove authorization or provenance. An MCP token likewise is not user intent, object authorization, or approval.
- The AI Governance course corrects boundaries between the EU AI Act's in-force and future-applicability dates and says AI Omnibus must still be checked by its independent procedural status. NIST AI RMF 1.0 revision status, transparency/documentation, release approval, and change management are no longer presented as static interchangeable facts.
- The Governance project adds data/Provider owner, version, and approval evidence. Both Safety and Governance projects expand negative contract tests so field presence cannot be mistaken for an implemented control.

### Evaluation, release, and monitoring: a versioned local profile, not fictitious universal canonical JSON

- The Offline Layered Evaluation project rejects raw invalid UTF-8 and isolated surrogate escapes at input time, and treats oversized values that cannot be represented as finite <code>float</code> as contract errors. Complete digests, format labels, and fixed golden vectors have regressions.
- Three projects explicitly share <code>python-json-sorted-utf8-v1</code>, a **local Python-teaching byte profile only**. It places positional arguments in an outer array, serializes JSON with sorted keys, compact separators, and <code>allow_nan=False</code>, then UTF-8 encodes and calculates SHA-256. It is not RFC 8785 JCS, cross-language canonical JSON, a signature, or proof of provenance.
- The LLMOps eval artifact uses <code>artifact_digest_format</code>; the online-observation bundle uses <code>evidence_digest_format</code>. The bundle's <code>schema_version</code> and format field now both enter every online <code>Decision.evidence_sha256</code>, so an upgrade cannot leave unbound interpretive semantics. Tests cover unknown format, format-label drift, and schema/profile changes.
- Runtime Monitoring accepts <code>candidate_gate_evidence_digest_format</code> and separately records the runtime-summary format in <code>Decision</code> and human-triage handoff. Fixtures remain independent teaching samples and must not pretend to interoperate end to end with real LLMOps artifacts.
- The Offline-to-Online Evidence Handoff and Regression Loop lesson was added/rewritten with a field-mapping table and Mermaid evidence chain. It makes explicit that a monitoring finding can create only a candidate awaiting human triage; it cannot automatically write back to the frozen evaluation set.

### Production feedback: stop automatic expansion when evidence is insufficient

- Provider drift always enters <code>HUMAN_REVIEW</code> when fallback binding is incomplete or the candidate lacks current-window evidence; an observation boolean cannot automatically trigger <code>FALLBACK</code>.
- The Monitoring project uses explicit <code>window_end</code> to distinguish business-event age from Collector-export age. A fresh Collector does not prove the business stream is current; stale events can escalate to <code>PAGE</code>.
- Online quality/safety ratios derive from verifiable integer numerators/denominators. A zero denominator is unknown, not zero or success. A non-<code>OK</code> window emits only a candidate without original text and awaits human triage.

## Cross-course terminology and evidence boundaries

| Term | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| <code>evidence_sha256</code> | A change-detection reference under a declared algorithm, version, and input bytes | Signature, provenance proof, approval, authorization, or real execution receipt |
| <code>python-json-sorted-utf8-v1</code> | A constrained Python-teaching byte profile shared by three offline projects | RFC 8785 JCS or any cross-language canonical JSON |
| <code>artifact_digest_format</code> | The declared digest-byte profile of an evaluation artifact | The artifact has been loaded, recomputed, or stored trustworthily |
| <code>candidate_gate_evidence_digest_format</code> | The monitoring-side declaration of release-gate digest format | Upstream release-gate fact or real release provenance |
| <code>monitor_evidence_digest_format</code> | The runtime-window digest format declaration in a human-triage candidate | Online result is trustworthy or approved for regression-set writeback |
| <code>HUMAN_REVIEW</code> | A freeze on automated expansion when evidence is insufficient, handed to an accountable reviewer | Automatic fallback, automatic approval, or unattended recovery |

## Sources, original material, and third-party boundary

All new Chinese-language explanations, Mermaid diagrams, field mappings, teaching code, and tests in this phase are original. The pages summarize facts and engineering boundaries from primary specifications/official materials only; they do not copy text lacking explicit redistribution permission. Principal checks:

- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), [NIST AI 600-1 Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf), [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final), and the [European Commission AI Act framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai).
- [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices), and [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html).
- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [MLflow automatic evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/), [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/), [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai), and [Google SRE SLO guidance](https://sre.google/sre-book/service-level-objectives/).

## Verification evidence

| Check | Result |
| --- | --- |
| AI Safety project | 80 tests: normal, <code>-O</code>, warnings-as-errors, and <code>-O + warnings-as-errors</code> all passed. |
| AI Governance project | 73 tests; all four modes passed. |
| Offline Evaluation project | 43 tests; all four modes passed. |
| LLMOps release-gate project | 74 tests; all four modes passed. |
| Offline Monitoring project | 45 tests; all four modes passed. |
| Consolidated project regressions | 315 tests per mode; 1,260 test executions across four modes all passed. |
| Static checks | In-memory <code>compile()</code> of 10 scoped Python files, related JSON/Markdown semantics, and scoped <code>git diff --check</code> passed. |
| Website tests | <code>.website npm test</code>: 48/48 passed; <code>npm run build</code> succeeded. |
| Publication validation | 925 public pages and 231 assets; 0 broken local links, prohibited files, sensitive leaks, or KaTeX errors. |

## Follow-up queue

1. Connect offline eval/artifacts, release gates, Canaries, and runtime windows to one controlled artifact repository or API. Recompute digests in practice, verify provenance/signature/approval, and run clearly specified interoperability tests across language implementations.
2. Before connecting real models, tools, Collectors, and evaluation backends in an isolated environment, design redaction, cost caps, least privilege, sample permission, rollback, and human-escalation paths. Do not connect teaching fixtures directly to production.
3. In the next phase, deeply review the RAG core path, MCP/Tool Calling, Agent Skills, framework practice, and MLOps. Continue Obsidian-desktop reading checks of long tables, Mermaid diagrams, and callouts.

This record covers only Phase 23. It does not mean the long-running <code>/goal</code> is complete.
