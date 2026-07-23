---
title: "2026-07-19 Phase 2 Content Deep Review Record"
aliases:
  - AI Agent Engineer Phase 2 content optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - content-audit
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第二阶段内容深审记录.md
translation_source_hash: 749f08678c735e8fa5ba7205cabfe9ba599a980619ab2d0241bd1e73e222e074
translation_route: zh-CN/维护记录/2026-07-19-第二阶段内容深审记录
translation_default_route: zh-CN/维护记录/2026-07-19-第二阶段内容深审记录
---

# 2026-07-19 Phase 2 Content Deep Review Record

This phase followed the principle “repair factual errors, obsolete practice, inverted route order, and publication risk before expanding courses.” The primary Agent unified standards, cross-dependencies, and final changes. Several read-only sub-Agents audited the learning route, core domains, examples/links, historical-code risk, and third-party publication boundary; sub-Agents did not merge content directly.

> [!important] Conclusion boundary
>
> This phase completed a verifiable set of high-priority repairs. It does not mean all 875 source documents were deeply reviewed page by page. Historical pages without <code>content_origin</code>/<code>content_status</code> remain **unclassified**, and cannot be inferred to be original or validated. The follow-up queue appears at the end.

## Main improvements

### 1. Unify the learning route and dependencies

- Corrected the order of JSON and API to remove their circular prerequisite wording: JSON is order 4 and API is order 5.
- Changed the Agent Platform route to “model, prompt, context, API, and safety/evaluation foundations → Tool Calling → Agent Core.” MCP becomes a capability branch to learn when standardized external capabilities or context protocols are needed, not every Agent's hard prerequisite.
- Added Tool Calling and Agent Core to the realtime multimodal route; added model/prompt/context/API, safety/evaluation, and ACL boundaries to RAG; and made LLMOps explicitly depend on evaluation foundations.
- Defined <code>ai_learning_order</code> as stable display order rather than a purported DAG capable of expressing every role path, optional branch, and hard dependency at once.
- Repaired an incorrect course link in the Linux directory and restored navigable links where real wikilinks in Chunking, Embedding, and Vector Database pages had been enclosed in inline-code marks.

### 2. Deep-review Tool Calling reliability boundaries

- Updated OpenAI function-calling strict-default differences, schema subset, and current parallel-call limitations using first-party material checked on 2026-07-19. Anthropic/Google Provider differences remain explicit rather than treating one API's semantics as a general standard.
- Defined tool results as untrusted input. Schema validation proves structure only, not ownership, authorization, business correctness, or side-effect safety.
- Rewrote timeout classification: return retryable <code>TIMEOUT_BEFORE_EXECUTE</code> only when handler/downstream submission is proven not to have started. When submission may have occurred, return <code>OUTCOME_UNKNOWN</code>, query receipt/operation or seek human review first, and prohibit blind retry.
- Added tenant, subject, tool, and key to the idempotency namespace; added tenant, subject, operation, and call ID to call correlation to prevent cross-tenant collisions. A model proposal carries only name/arguments; Provider call ID and application operation/idempotency context are bound separately by a trusted adapter.
- Writing approval binds request intent, schema version, and explicit policy revision, so a version change invalidates older approval. Cache/receipt data is defensively deep-copied on store/return so callers cannot mutate a response and contaminate a later hit.
- Extended the offline dispatcher, fixture, and tests to 57 unit tests, 18 data-driven cases, and 23 steps. Coverage includes parameters, authorization, approval expiry/mismatch/version change, cross-tenant and same-tenant/cross-subject isolation, idempotency conflicts, call-ID conflicts, explicit retry classification, throttling, pre-execution timeout, lost post-submit response, receipt reconciliation, and uncertain branches where receipt is unavailable.

> [!note] Example boundary
>
> The dispatcher uses in-process maps for idempotency records, downstream receipts, and uncertain intents. It verifies only sequential-retry contracts and failure semantics. Production still needs persistence, atomic <code>in_progress</code>/unique constraints, real downstream idempotency keys, status query, concurrency tests, transactions/compensation, and observability; this phase does not present the in-memory simulator as a production storage design.

### 3. Update framework-practice version and privacy facts

- Updated the installable CrewAI snapshot to <code>crewai==1.15.4</code> (released 2026-07-17; declares Python <code>&gt;=3.10,&lt;3.14</code>) and separately recorded “current PyPI package version” from the concept documentation deeply read on 2026-07-14.
- Added CrewAI entry/safety coverage for default anonymous telemetry, the broader sharing boundary of <code>share_crew=True</code>, and the deployment warning that <code>OTEL_SDK_DISABLED=true</code> may affect other OpenTelemetry instrumentation in the same process.
- Stopped treating “skip when dependency is missing” as proof that LangChain LCEL is verified. A keyless example actually ran under Python 3.11.9 in an isolated <code>langchain-core==1.4.9</code> environment; the course records exact command, output, and isolation requirements.
- It still does not claim end-to-end real framework APIs for CrewAI or LangGraph ran; both enter the next phase's Layer B practice queue.

### 4. Establish source metadata and publication gates

- Added [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]], unifying <code>content_origin</code>, <code>content_status</code>, source date, execution evidence, and third-party license boundary.
- Migrated 21 legacy status values found in the audit to controlled enums; the build confirmed there were no current out-of-standard <code>content_status</code> values.
- Prioritized labels for 11 high-risk/dynamic top-level entry points: Python, Agentic Design Patterns, MCP, Agent Skills, LangChain, CrewAI, LLM API, Tool Calling, Modern LLM, Realtime Multimodal, and Environment Agent. The other 45 top-level course entries await page-by-page judgment rather than unreviewed bulk classification.
- The public build now uses a fixed <code>yaml@2.9.0</code> AST parser to validate frontmatter and completed source/status fields. Missing fields remain permitted for gradual migration, but parse errors, empty values, duplicate fields, unknown enums, merge keys, aliases, and complex mapping keys fail. Governance fields hidden in flow mappings, indented/sequence mappings, tags/anchors, escaped keys, or folded explicit keys also fail closed, so noncanonical YAML cannot bypass the gate; alias values in unrelated fields are outside this gate.
- A <code>content_origin: third-party</code> page needs an absolute HTTP(S) <code>source_url</code> and must match registered upstream origin/path, a project-permitted license, and a build-copied local license declaration. Merely adding <code>license: MIT</code> cannot pass. Unregistered source; source/license mismatch; missing, empty, unknown, proprietary, misspelled, or unallowlisted license produces a source stub. The whitelist remains <code>MIT</code>, <code>Apache-2.0</code>, and <code>CC0-1.0</code>, as a necessary condition only. If one top-level course still has whitelisted public images, attachments, example code, or data, the build fails, preventing resource leakage after body text is blocked. A <code>mixed</code> entry point is not mistakenly treated as wholly third-party.

### 5. Add safety warnings to the frozen Python reference layer

No third-party body/code with unknown permission was rewritten. Instead, the maintenance entry centralizes four confirmed risks:

- Passing a bare coroutine to <code>asyncio.wait()</code> fails under Python 3.11.9.
- Historical asynchronous-download examples disable TLS verification and lack timeout, status, size, and parsing boundaries.
- A public-course crawler accesses real third-party sites, impersonates a User-Agent, and lacks rate-limit/site-policy checks.
- A 2020 <code>requirements.txt</code> is a historical environment snapshot, not something to install directly in a modern environment.

Main-path exercises use local fixtures/test servers, honest identity, isolated environments, and minimum dependencies. The public site continues to produce source-jump pages only for complete reference layers whose license is unknown.

## Verification actually performed

| Check | Result | Evidence boundary |
| --- | --- | --- |
| <code>.website</code> unit tests | 28/28 passed | Source enums; YAML AST/noncanonical-key fail-closed behavior; license/source-URL gates; generic third-party-stub body isolation; attachment fail-closed behavior; existing publication policy and route generation. |
| Full <code>.website</code> build | Passed | 875 source Markdown, 718 full pages, 157 stubs, 198 assets, and 878 generated pages. |
| Site validation | All 0 | Broken local links, prohibited files, progress leaks, sensitive information, self-redirects, table-wikilink leaks, interactive checkboxes, and KaTeX errors. |
| Navigation validation | Passed | 8 stages, 56 course entry points, 106 navigation folders. |
| Tool Calling unit tests | 57/57 passed | One normal and one <code>python -O</code> run. |
| Tool Calling data-driven CLI | 18 cases / 23 steps passed | Repository fixture only; no network or keys. |
| LangChain LCEL minimum run | Passed | Python 3.11.9 with isolated <code>langchain-core==1.4.9</code>; not LangGraph or real-model end-to-end verification. |
| Modern-example audit baseline | 1,917 tests passed before these changes | 56 modern-example test files in normal and <code>-O</code>. New Tool Calling tests were independently rerun, but no new repository-wide aggregate was generated; two optional scientific-computing suites were not run because declared dependencies were absent. |

A site build is not Obsidian-desktop rendering validation. This phase did not automatically click-check visual layouts of every Callout, Dataview block, and Mermaid diagram; the site build covers links, HTML, KaTeX, and other automatable boundaries.

## Key sources

The following dynamic material was checked on 2026-07-19. Course bodies retain only needed facts and direct links:

- [OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling): tool schema, strict behavior, call correlation, and parallel limits.
- [Anthropic Tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) and [Google Gemini Function calling](https://ai.google.dev/gemini-api/docs/function-calling): Provider-tool-contract comparisons.
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12), [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110), and [OWASP LLM01: Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/): schema, HTTP/idempotency, and untrusted-tool-result boundaries.
- [YAML 2.9.0](https://www.npmjs.com/package/yaml/v/2.9.0) and its [Document/CST API](https://eemeli.org/yaml/#documents): pinned parser version, AST, errors, and duplicate-key checks for the publication gate.
- [CrewAI 1.15.4 on PyPI](https://pypi.org/project/crewai/1.15.4/), [CrewAI Telemetry](https://pypi.org/project/crewai/#telemetry), and [langchain-core 1.4.9 on PyPI](https://pypi.org/project/langchain-core/1.4.9/): package/version and telemetry facts.

## Next-phase queue

1. **Real framework Layer B:** add actual <code>StateGraph</code>, checkpointer, and interrupt/resume for LangGraph; add minimal real CrewAI Flow, durable state, and recovery; report framework tests separately from dependency-free skeletons.
2. **Learning-route metadata model:** separate display order from hard dependencies, role paths, and optional relationships; design checkable <code>domain</code>, <code>roles</code>, <code>hard_prerequisites</code>, and <code>track_order</code> fields, then share one source between Obsidian and Quartz.
3. **Unified example runner and CI:** address repository-wide <code>unittest discover</code> yielding 0, pytest module-name collisions, and invisible optional-dependency skips. Report passed/skipped/failed and real dependency environments; do not call a skip framework verification.
4. **Continue source-field migration:** review the remaining 45 top-level entries and third-party sublayers page by page. Python, Agentic, MCP, Agent Skills, LangChain, D2L, and similar layers must each retain source, commit/retrieved, license, and frozen status rather than mechanically inheriting entry fields.
5. **Historical-example modernization:** continue isolating high-risk network, TLS, crawler, and old-dependency examples. Add modern replacement exercises first; do not directly rewrite frozen third-party body text.
6. **Vertical review of RAG, evaluation, safety, and production:** use one cross-cutting project to check retrieval permission, data freshness, offline/online evaluation, cost/latency, security incidents, and rollback evidence, reducing cross-course duplication and terminology drift.
7. **Obsidian visual inspection:** inspect route tables, Callouts, Mermaid diagrams, long tables, and cross-directory links on desktop.

See the previous [[maintenance-records/2026-07-18-content-audit-and-restructuring-record|2026-07-18 content audit and restructuring record]]. The first delivery of real framework Layer B and route-metadata model is in the [[maintenance-records/2026-07-19-phase-3-framework-recovery-and-learning-route-metadata-record|Phase 3 framework recovery and learning-route metadata record]]. Future page review and source labels continue to follow the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
