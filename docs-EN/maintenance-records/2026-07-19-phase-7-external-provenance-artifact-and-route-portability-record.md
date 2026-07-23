---
title: "2026-07-19 Phase 7 External Provenance Artifact and Route Portability Record"
aliases:
  - AI Agent Engineer Phase 7 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - rag
  - provenance
  - trust-boundary
  - learning-path
  - portability
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第七阶段外部来源工件与路线可移植性记录.md
translation_source_hash: 27937c0351933763e5f377bdb696867df22fe3df5e5dd5fe40260a9ff89ea4a3
translation_route: zh-CN/维护记录/2026-07-19-第七阶段外部来源工件与路线可移植性记录
translation_default_route: zh-CN/维护记录/2026-07-19-第七阶段外部来源工件与路线可移植性记录
---

# 2026-07-19 Phase 7 External Provenance Artifact and Route Portability Record

This phase implements the Phase 6 <code>provenance external artifact v2</code> queue item and addresses course-route dependency semantics plus machine-portable project commands. The primary Agent unified wire contract, trust boundary, terminology, course placement, and final verification. Specialists audited v1/v2 contracts, course dependencies, absolute paths, Provider-contract gaps, and read-only red team. Every high-risk red-team finding was reproduced, repaired, and given a regression; final review left no P0/P1.

> [!important] Conclusion boundary
>
> <code>external-provenance-bundle-v2</code> proves that, with an out-of-band-approved canonical JSON value, versioned algorithms, and consumer-owned live state, a protected artifact can preserve reconstructable relationships across a JSON boundary and fail closed. It does not prove source truth, signature, AuthN, SLSA/in-toto conformance, distributed-publication consistency, or physical deletion. The Lesson 9 reference engine still does not automatically import the Lesson 10 artifact.

## 1. From producer digest to independently verifiable external artifact

The new External Provenance Artifact v2 project extends Lesson 10's <code>CrossLayerEngine.export_external_provenance_bundle()</code>. A complete protected bundle contains:

- versioned contracts for parser, normalizer, mapping, knowledge state, chunk, index, IDs, and coordinates;
- source event, inline raw/canonical forms, ACL snapshot, full Parser record, KB revision, adapter elements, and crosswalk;
- full chunks/index entries with explicit tenant/document/source/revision route;
- generation, capture/tombstone/authorization/pipeline, and document/entry closure;
- payload self-hash plus honest <code>attestation.mode: none</code> and <code>trust_scope: self-consistency-only</code>.

The consumer accepts bounded strict-UTF-8 JSON text/bytes only, never producer in-memory objects. <code>TrustedImportPolicy</code> independently pins canonical bundle-value digest, generation, pipeline, and authorization revision. Pretty/compact JSON with the same parsed value receives the same digest, so this is not exact wire-byte pinning. Wire-byte identity, signer identity, and cross-organization trust still require transport digest, signed envelope, trusted control plane, or transparency log.

Using current trusted Parser/Chunking implementations, consumer fresh-rebuild verifies raw/canonical/Parser record, parser config and complete element order; versioned knowledge state, KB revision identity, producer document snapshot; crosswalk/adapter element/chunk/entry/ACL/access snapshot/route/coverage/generation closure; native line locator, lexical span, <code>exact/prefix/suffix</code>; and the continuing limits <code>canonical_mapping.status: unavailable</code> and <code>document-revision-bridge</code>. If the full producer release manifest is absent, its hash is only a diagnostic reference labeled <code>opaque-producer-reference-only</code>; consumer never presents unrebuildable digest as verified closure. Producer identity inputs such as <code>capture_artifact_sha256</code> still depend on out-of-band policy/generation pin, not consumer reconstruction of producer database.

## 2. Red-team closure: move from structurally valid to boundary-usable

The independent red team reproduced then closed:

| Issue | Repair and regression |
| --- | --- |
| 1,200 JSON nesting levels escaped as bare <code>RecursionError</code> | Scan container depth before decoding and normalize defensive recursion failures into structured failure. |
| <code>StagedExternalBundle</code>/<code>PublishedExternalBundle</code> could be constructed manually | Public constructors reject; import/publish use private provenance marker; forged objects cannot publish. |
| Query body could self-report tenant/on-call group | Tenant/groups/auth are issued from host-owned <code>ConsumerLiveState</code> principal grant; query body only accepts <code>query_id/query/top_k</code>. |
| Context could replay across live-state snapshot | <code>TrustedRequestContext</code> binds issuing live-state marker exactly. |
| Two subjects with same public result competed for one trace | Host issues a fresh 128-bit request nonce; trace binds nonce/bundle/generation/public trace, while audit keeps separate attribution. |
| Public/protected audit returned together | Public query returns public schema only; audit writes to host-owned sink and sink failure fails whole query closed. |
| Public citation exposed sensitive <code>source_uri</code> | Public projection retains typed logical source/KB identity only; URI/version go only to protected audit. |
| Schema URI limit 300 versus implementation 1000 | Independent <code>sourceUri</code> contract is 1000; normal/long real exporter bundles both pass Draft 2020-12. |
| <code>D:/...</code> escaped temporary Parser root | Portable path grammar rejects drive/stream/backslash/traversal/device names/dangerous endings/overlong segments; resolve descendant check and exclusive create follow. |
| Materialization emitted bare <code>OSError</code> | Path materialization and Parser rebuild map separately to stable structured errors. |
| Element/crosswalk sets allowed reordering | Parser → crosswalk → adapter-element order is bound item-by-item, so reassembled downstream chunk/entry/hash still rejects. |
| KB source/build/producers snapshot treated as opaque hash | One versioned knowledge-state algorithm binds/recomputes the full producer document snapshot. |

Files include external-v2 implementation/schema/test plus Lesson 9/10/11 and Parser/Knowledge Store/Chunking capability/cross-link updates. Forty-two specialist tests cover strict JSON, trusted policy, identity/route/path/order/coordinate/coverage, live authorization, trace, publication state machine, protected-audit delivery, and non-disclosure. Final red-team review found no P0/P1.

## 3. Learning route: display order must not impersonate dependency topology

Course audit found a nonexistent “safety and evaluation foundations” course in the overall route and legacy sidebar order that looked like strict prerequisites. Repairs:

- An Early Safety and Evaluation milestone links actual threat modeling, prompt injection, tool overreach, identity/least privilege, evaluation objectives, case layering, and deterministic assertions, with minimum completion evidence.
- Tool Calling is an Agent Core universal hard prerequisite.
- MCP is an on-demand interoperability branch, not a hard prerequisite for every Agent runtime.
- Framework practice is selected based on state/recovery/collaboration/control needs.
- Course Navigator <code>LEARNING ROADMAP</code> becomes <code>COURSE CATALOG</code>, declaring legacy order to be display order only.
- Website regressions cover the navigation semantics.

Only relationships already checked page by page migrated. Missing v2-prerequisite metadata means “not migrated yet,” not “confirmed without dependencies.”

## 4. Machine-portable project commands and publication paths

A path audit found 23 current-machine absolute project roots in 22 main-path project pages. Each was changed to run from the project root containing <code>docs/</code> and <code>.website/</code>, using project-relative paths; frozen third-party body was not mechanically changed. Scope included Agent Skills/Core, Benchmark, CrewAI, JSON, LangChain, LLM API, MLOps, OCR, Context/Prompt, image/video/speech, workflow, synthetic data, regex, evaluation, and monitoring.

Smoke testing repaired three previously non-runnable <code>unittest</code> commands: LLM API Integration 20 tests, Context Engineering 15, Prompt Engineering 15. <code>.website/scripts/prepare-content.mjs</code> adds a pre-publication gate: full-published course Markdown containing a Windows absolute path to the project directory fails before redaction; maintenance records may retain historical evidence. Website tests cover failing examples and valid project-relative paths.

## 5. Provider-contract read-only audit

This phase did not expand into real Provider integration. Existing LLM API examples are reliable-client skeletons, not complete OpenAI Responses/Anthropic Messages/Gemini Interactions wire/SDK contracts; they do not cover Provider-specific continuation, streaming tool-argument state machine, strict tool schema, or structured-final-output combinations. Official Python SDK release snapshots checked on 2026-07-19 are [openai-python v2.46.0](https://github.com/openai/openai-python/releases/tag/v2.46.0) (2026-07-17), [anthropic-sdk-python v0.117.0](https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.117.0) (2026-07-16), and [python-genai v2.12.1](https://github.com/googleapis/python-genai/releases/tag/v2.12.1) (2026-07-16). They mark the audit point, not a permanent install recommendation; implementation must repin and follow current official docs/events.

## Verification actually performed

- External v2 42/42; RAG provenance 109/109 (Lesson 9: 67, v2: 42); RAG integration 36/36, each passing normal, <code>-O</code>, warnings-as-errors, and <code>-O + warnings-as-errors</code>.
- Repository discovered 67 <code>test_*.py</code>; 62 base-environment files passed 2,387/2,387 in every one of four modes. Five declared optional CrewAI/LangGraph/Matplotlib/scikit-learn files were not run, and were not written as passes.
- Path-project smoke: 20 unique directories, 902 unit tests, plus LangChain's 5 self-checks, all passed; the three repaired commands are also covered by full four-mode regression.
- Six RAG JSON/schema files pass strict UTF-8/duplicate-key/nonfinite checks; normal/long real exporter bundle both validate Draft 2020-12 with 0 errors.
- Current-machine absolute project roots have 0 matches; <code>git diff --check</code> passes; four <code>.pyc</code> and two <code>__pycache__</code> made during verification were removed and generated directories are absent from Git status.
- <code>.website npm test</code> is 35/35; build publishes 891 Markdown, 220 assets, 2,665 public files with all broken local links, forbidden files, progress/sensitive/self-redirect/table-wikilink/checkbox/KaTeX gates at 0.

## Key sources

This project borrows concepts, not conformance claims, from [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md), [SLSA v1.2 provenance](https://slsa.dev/spec/v1.2/provenance), [SLSA build provenance](https://slsa.dev/spec/v1.2/build-provenance), [artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts), [DSSE](https://github.com/secure-systems-lab/dsse/blob/master/protocol.md), [W3C Web Annotation selectors](https://www.w3.org/TR/annotation-model/#selectors), [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), and [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12). Semantic verifier handles sort/hash-preimage/route closure/path containment/live state/publication; the project is neither SLSA-level nor DSSE/JCS conformant.

## Follow-up queue

1. Add Provider contract project with real request/response, streaming tool arguments, continuation, parallel calling, error taxonomy, strict tools, and structured final output.
2. Add Schema CI/cross-language vectors for canonicalization, duplicate keys, Unicode, paths, and ID preimages.
3. Create formal attestation: predicate type, DSSE/equivalent signed envelope, PKI/KMS, key rotation, transparency log, trusted policy distribution.
4. Build trusted runtime control plane with real AuthN/IdP/PDP, live-state freshness, durable protected audit, immutable store, transactional/CAS cutover, concurrent readers, disaster recovery.
5. Migrate RAG Lesson 9 through v1/v2 old-ID crosswalk/downgrade reader; upgrade to <code>canonical-span-verified</code> only after proving canonical slice.
6. Add external-index deletion proof for sparse/dense/vector/graph/cache revocation, deletion propagation, backup erasure, and purge audit. Keep environments out of content trees, run optional-dependency CI matrices, and manually inspect Mermaid/wide tables/Callouts/navigation/mobile layout.

See the preceding [[maintenance-records/2026-07-19-phase-6-cross-module-transport-and-persistence-evidence-chain-record|Phase 6 record]]. Source/license policy continues through the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
