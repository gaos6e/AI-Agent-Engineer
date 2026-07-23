---
title: "2026-07-19 Phase 3 Framework Recovery and Learning-Route Metadata Record"
aliases:
  - AI Agent Engineer Phase 3 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - framework-practice
  - learning-roadmap
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第三阶段框架恢复与路线元数据记录.md
translation_source_hash: 27100d86c4e6871ca19aa4e9979303c88bb9ddb7e27ac53429561d212be67fe0
translation_route: zh-CN/维护记录/2026-07-19-第三阶段框架恢复与路线元数据记录
translation_default_route: zh-CN/维护记录/2026-07-19-第三阶段框架恢复与路线元数据记录
---

# 2026-07-19 Phase 3 Framework Recovery and Learning-Route Metadata Record

This phase turns two high-priority items from the Phase 2 queue into runnable evidence: real-runtime Layer B recovery projects for LangGraph and CrewAI, and the first learning-route relationships moved from handwritten prose into strictly validated metadata. The primary Agent unified state, idempotency, recovery, source, and route semantics. Specialist Agents performed read-only audits of version APIs, course linkage, and verification boundaries; final changes and conflict resolution remained with the primary Agent.

> [!important] Conclusion boundary
>
> This is the first migration of framework-recovery practice and learning-route metadata. It does not mean all 56 courses, every framework-reference page, or every source document was deeply reviewed page by page. Real model calls, multi-worker concurrency, production databases, desktop visual checks, and migration of the remaining courses remain in the follow-up queue.

## 1. LangGraph: from conceptual explanation to a real recoverable approval flow

- Added the LangGraph Recoverable Approval Flow project; its former testing/upgrades checklist moved to section 09, with index and previous/next navigation updated.
- Added <code>examples/langgraph_layer_b/</code>, directly running <code>langgraph==1.2.9</code> and <code>langgraph-checkpoint-sqlite==3.1.0</code>. The isolated environment resolves <code>langgraph-checkpoint==4.1.1</code> and <code>langchain-core==1.4.9</code>.
- The example uses real <code>StateGraph</code>, <code>SqliteSaver</code>, <code>interrupt()</code>, <code>Command(resume=...)</code>, and <code>durability="sync"</code> to verify recovery across database connections and Python processes.
- Before resuming, the application wrapper checks thread existence, trusted <code>owner_id</code> binding, target node, and pending interrupt. This prevents treating runtime defaults for unknown/completed threads as authorization denial. The example owner parameter simulates an authentication boundary only; it does not replace real AuthN/AuthZ.
- Approval binds both request ID and action fingerprint. No business write occurs before interrupt. The final action produces only a deterministic dry-run receipt and explicitly does not claim exactly-once external effects.
- The main path adds timing boundaries for <code>sync</code>, <code>async</code>, and <code>exit</code> writes, and consistently records that LCEL actually ran in the isolated <code>langchain-core==1.4.9</code> environment.

## 2. CrewAI: layer persistent state and business receipts

- Added the Real CrewAI Persistent Flow project and <code>examples/crewai_layer_b/</code>, directly running <code>crewai==1.15.4</code> without a model call or API key.
- The example verifies <code>Flow</code>, structured <code>FlowState</code>, <code>@start()</code>, <code>@router()</code>, <code>@listen()</code>, explicit <code>@persist(...)</code>, and <code>SQLiteFlowPersistence</code>. Route labels are distinct from listener method names, avoiding the locked-version self-listening problem.
- A Flow-state UUID identifies execution lineage only. Business <code>operation_id</code> and <code>payload_hash</code> handle idempotency and conflict detection. A previously confusing deterministic name in Layer A was also changed to <code>operation_id</code>.
- A separate SQLite receipt ledger is layered with Flow persistence. Tests inject failure after a receipt commits but before Flow state saves; a new process hydrates the same UUID and reuses the receipt, keeping serial <code>effect_count</code> at 1.
- Same-UUID recovery, fork from snapshot, and unknown-UUID fail-closed behavior are each tested. The text states that <code>@persist</code> hydration is neither node-level checkpoint skipping nor distributed exactly-once.
- Anonymous telemetry, AMP tracing, Flow lifecycle events, and local logs are documented separately. AMP tracing is explicitly disabled by <code>tracing=False</code> for every Flow; an environment value <code>false</code> is not misrepresented as a reliable opt-out. Windows tests enable UTF-8 before import and allowlist only two full transitive-dependency warnings for the locked version.

## 3. Learning-route metadata v2: decouple display order from dependency

- Added [[maintenance-records/learning-route-metadata-v2-standard|Learning-Route Metadata v2 Standard]], defining stable course ID, knowledge domain, global catalog order, role-independent hard prerequisites, and order/type for each of four role tracks.
- <code>.website/scripts/prepare-content.mjs</code> now reads course metadata through a pinned <code>yaml@2.9.0</code> AST. Legacy pages remain strictly validated; after declaring schema 2, a page cannot omit fields or silently fall back.
- The validator checks ID/domain/JavaScript-safe-positive-integer types; unique catalog order; hard-prerequisite existence, duplicate, self-cycle, and full-graph cycle; paired track order/kind; role/type enums; unique order per role; and noncanonical YAML tags/anchors.
- If a top-level course index degrades into a publication-policy stub without route information, the build fails closed. The manifest reports legacy and v2 counts separately.
- The first batch migrates only Tool Calling, Agent Core, Evaluation Systems, and LLMOps, with only two reviewed hard edges: <code>tool-calling → agent-core</code> and <code>evaluation → llmops</code>. MCP, Environment Agents, and the full Safety course were not guessed to be universal hard prerequisites.
- The overall route adds where frameworks enter on demand and explains that legacy display order, role-recommended path, and true hard dependency are distinct concepts.

## Verification actually performed

| Check | Result | Evidence boundary |
| --- | --- | --- |
| LangChain Layer A | 63/63 passed | Normal, <code>python -O</code>, and warnings-as-errors; framework-independent offline loop plus LCEL dependency branch. |
| LangGraph Layer B | 7/7 passed | Normal, <code>python -O</code>, and warnings-as-errors; real SQLite checkpoint, interrupt/resume, and two independent processes. |
| CrewAI Layer A | 36/36 passed | Normal, <code>python -O</code>, and warnings-as-errors; standard-library offline research-brief contract. |
| CrewAI Layer B | 7/7 passed | Normal, <code>python -O</code>, and warnings-as-errors; real Flow persistence, fork, fault injection, and two independent processes. |
| <code>.website</code> unit tests | 33/33 passed | v2 success path; missing/type/tag/track/prerequisite/cycle/duplicate-position fail-closed checks; full stripping of progress sequence values; existing publication policy. |
| Full <code>.website</code> build | Passed | 879 source Markdown, 722 full pages, 157 stubs, 204 assets; 52 legacy and 4 v2 courses; 882 staged Markdown pages. |
| Site/navigation validation | All passed | 2,398 HTML pages, 56 course entry points; broken local links, prohibited files, learning-progress leaks, sensitive information, self-redirects, and KaTeX errors all 0. |
| Supplemental checks | Passed | <code>git diff --check</code> had no formatting error; neither new Layer B directory had <code>.pyc</code>. |

The first full build was blocked by the public-leak gate because the metadata standard body wrote the literal learner-progress field name. After that explanation was rephrased semantically without exposing the private field name, the second build passed. This failure remains recorded because it shows that the gate applied to new maintenance documentation rather than scanning old courses only.

## Key sources

These dynamic facts, versions, and APIs were checked on 2026-07-19; courses retain only needed explanation and direct links:

- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): interrupt recovery and node replay semantics.
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers): thread, checkpoint, and durability boundaries.
- [langgraph 1.2.9](https://pypi.org/project/langgraph/1.2.9/), [langgraph-checkpoint 4.1.1](https://pypi.org/project/langgraph-checkpoint/4.1.1/), and [SQLite checkpointer 3.1.0](https://pypi.org/project/langgraph-checkpoint-sqlite/3.1.0/): runtime/serialization dependency snapshots for isolation.
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows) and [Checkpointing](https://docs.crewai.com/en/concepts/checkpointing): Flow decorators, state hydration, same-UUID, and fork boundaries.
- [CrewAI Telemetry](https://docs.crewai.com/en/telemetry), [Tracing](https://docs.crewai.com/en/observability/tracing), and [1.15.4 tracing-enablement source](https://github.com/crewAIInc/crewAI/blob/1.15.4/lib/crewai/src/crewai/events/listeners/tracing/utils.py): anonymous telemetry, AMP tracing, and locked-version override priority.
- [crewai 1.15.4 on PyPI](https://pypi.org/project/crewai/1.15.4/) and the [YAML Document API](https://eemeli.org/yaml/#documents) with project-pinned <code>yaml@2.9.0</code>: runtime/Python constraints and AST parsing/fail-closed validation of course frontmatter.

## Follow-up queue

1. **Course-by-course route-v2 migration:** review stable IDs, domains, role orders, and real hard prerequisites for the remaining 52 courses. Missing fields must not be interpreted as “no dependency.”
2. **Unify consumers:** when project boundaries permit, make the vault-level Dataview view, Homepage, and CourseNavigator consume the same validated route model. The outer-vault helper was not changed in this phase because of the existing source/site boundary.
3. **Framework deep water:** validate production-checkpointer concurrency, migration, encryption, and multi-tenant isolation for LangGraph; separately validate CrewAI checkpoint API, multi-worker concurrency, and persistence-schema migration.
4. **Real-model integration:** add a small number of Provider smoke tests after budget, credential isolation, and dataset are available; continue reporting model-quality evidence separately from deterministic-runtime tests.
5. **Frozen-reference governance:** repair old LangChain links and source/license fields page by page; do not bulk-rewrite the 2026-05-07 translated reference layer as a current API tutorial.
6. **Cross-course capstone:** connect RAG, evaluation, safety, LLMOps, and runtime monitoring through one evidence chain with ACL, trace, regression gate, rollback, and incident rehearsal.
7. **Visual/interaction inspection:** manually inspect Mermaid, long tables, Callouts, Dataview, and course navigation in Obsidian and on the public site.

See the preceding [[maintenance-records/2026-07-19-phase-2-content-deep-review-record|Phase 2 content deep review]]. Source classification continues to follow the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
