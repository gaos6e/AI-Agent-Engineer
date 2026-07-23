---
title: "2026-07-22 Phase 24 Deep Review Record: Retrieval, Tools, and Agent Runtime"
aliases:
  - Phase 24 optimization record
tags:
  - maintenance
  - rag
  - retrieval
  - mcp
  - tool-calling
  - agent-runtime
  - langchain
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第二十四阶段检索工具与Agent运行时深审记录.md
translation_source_hash: 4107f84eeb7eaf968d6c57ec235dab87716fd20e1d96dbcf9fa9f397d419067a
translation_route: zh-CN/维护记录/2026-07-22-第二十四阶段检索工具与Agent运行时深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第二十四阶段检索工具与Agent运行时深审记录
---

# 2026-07-22 Phase 24 Deep Review Record: Retrieval, Tools, and Agent Runtime

## Phase conclusion

This phase turns the learning route “retrieval evidence → context/Skill → MCP capability transfer → authorized Tool Calling execution → Agent-state recovery → framework implementation” into a chain of verifiable boundaries. The point is not to add an API catalog for a framework; it is to let learners distinguish who proposes an action, who holds identity and authorization, what can safely replay, what must only be reconciled, and what offline contract tests cannot prove.

It covers RAG, [[embeddings/00-index|Embedding]], [[reranking/00-index|Reranking]], [[agent-skills/00-index|Agent Skills]], [[mcp/00-index|MCP]], Tool Calling, Agent Core, and [[langchain/00-index|LangChain / LangGraph]].

> [!important] What this phase does not prove
>
> Fixed fixtures, an in-memory host, single-machine SQLite contention, a keyless shim, static Provider profiles, and a website build do not prove real model routing, production identity, human approval, a real MCP host, Provider SDKs, external side effects, cross-region failure recovery, or exactly-once semantics. They prove only that the declared negative paths fail closed and repeat in a constrained environment.

## Multi-Agent division of work and primary-Agent review

1. The retrieval specialist tightened provenance, ACL, budget, numerical, and evaluation boundaries page by page across the RAG core path, Embedding, Reranking, and Semantic Search. The primary Agent reran project tests and fixed findings from review.
2. The protocol/capability specialist checked the stable MCP specification, Streamable HTTP cursor/session semantics, task-structure boundary, Agent Skills client differences, resource paths, and input-size limits.
3. The Tool Calling specialist completed runtime review of both dispatcher and SQLite outbox layers. An independent read-only review reproduced deeply nested output, approval-time upper-bound, and cross-Provider-profile replay defects; the primary Agent added tests and fixed them.
4. The Agent Core specialist reviewed state machine, approval, budget, receipt, checkpoint, and recovery semantics. The LangChain specialist checked <code>create_agent</code>, structured output, interrupt/replay, version snapshot, and four-mode commands against official documentation and an isolated resolution environment.
5. The final read-only Agent compared terminology, learning order, wikilinks, and rendered local-resource links across all eight course directories and found no P0, P1, or P2 issue.

The worktree already contained extensive uncommitted changes in this scope. This phase did not revert or reattribute them; it added only findings from page-by-page reading, contextual checking, and regression.

## Key changes

### Retrieval: return “hits” to evidence with identity and access boundaries

- RAG 01–11 further clarify the relationship among source/provenance artifacts, offline citations, ACL-before-score, projections, versions, budgets, cross-layer evaluation, and external-source artifacts. Retrieval score, citation, or summary cannot cross current access control or replace source evidence.
- Embedding, Reranking, and Semantic Search examples tighten oversized-number, deterministic-ordering, degradation, and evaluation boundaries, preventing Python numerical behavior or all-green results from being mistaken for reliable vector space or online recall.
- Learning order remains corpus/chunking → representation/retrieval → reranking/generation → evaluation/safety/production evidence, linking retrieval artifacts to the untrusted-input boundary of Agent/Tool execution.

### Skills, MCP, and Tool Calling: responsibilities are no longer conflated

- The Agent Skills entry distinguishes a Skill (progressive work instructions for a client), Tool Calling (an application executing a controlled action), and MCP (a client–server capability protocol). Supported directories, automatic activation, and preauthorization can vary by client; a Skill file is not identity, authorization, or a sandbox.
- The Skill validator rejects noncanonical resource references, and the text-statistics example consistently limits UTF-8 input to 1 MiB. Its 56 tests fix path traversal, frontmatter, script, and resource boundaries.
- The MCP course uses stable specification <code>2025-11-25</code> as baseline and says candidate drafts are not settled facts. HTTP loopback tightens JSON depth, cursorless polling, POST SSE, and GET cursor boundaries. Offline message validation limits task objects to structural validation rather than inventing scheduling/persistence capability.
- The Tool Result v2 dispatcher now performs bounded JSON-domain validation before recursively scanning sensitive keys. An overly deep handler output becomes <code>OUTPUT_CONTRACT_VIOLATION</code> instead of a recursion exception. Approval expiry requires <code>now &lt; expires_at &lt;= MAX_PORTABLE_UNIX_SECONDS</code>. In-memory idempotency records, unknown outcome, and status reconciliation all bind the first Provider/API family/adapter revision; another profile can only conflict, never replay around approval or reconciliation.
- SQLite and in-memory layers align the time/profile semantics and recheck them in persistent audit. The teaching material still claims only at-least-once-compatible primitives, not distributed exactly-once.

### Agent runtime and frameworks: recovery replays an action, not historical decision-making

- The bounded Agent project resumes pending work by executing the frozen action rather than re-running policy to generate a new action. Approval target scope, lookup observation, pending-close contract, and receipt semantics enter checkpoint validation.
- Polling while waiting for human approval does not consume step budget; receipt queries consume tool budget. Transient/permanent write exceptions, malformed receipts, and “may have written but result invalid” all fail closed and retain the action/target/idempotency data required for explicit reconciliation.
- The LangChain course adds commands for normal, <code>-O</code>, <code>-W error</code>, and <code>-O -W error</code> modes, each run independently from repository root. It distinguishes fixed teaching contracts from a dynamic ecosystem snapshot. The checked snapshot is <code>langchain 1.3.14</code>, <code>langgraph 1.2.9</code>, and <code>langchain-core 1.5.0</code>; the LCEL teaching example explicitly pins and actually verifies <code>langchain-core==1.4.9</code>.

## Cross-course terminology and dependency boundaries

| Concept | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| Skill | A client-readable progressive work instruction/resource package | Identity, authorization, tool execution, or sandbox |
| MCP | A protocol between client and server for discovery, invocation, resources/prompts, and transport | User authorization, business-object access control, or approval |
| Tool Calling | A controlled application action proposed by a model and validated/executed by the host | The model possessing service credentials or arbitrary external-side-effect permission |
| Approval | Human confirmation of a specific new intent, subject, parameters, profile, and version | Current AuthZ, resource state, or a permanent pass for safe replay |
| AuthZ | Permission re-evaluated at execution/recovery for current subject and resource | Approval, idempotency key, or hash |
| Idempotency/replay | Duplicate suppression or result reuse in the same scope, semantics, and Provider profile | Cross-Provider migration, automatic success for unknown outcome, or exactly-once |
| Provenance/ACL projection | Source identity/version and current visibility projection for retrieval evidence | Relevance score, generated citation, or model assertion |
| Checkpoint/receipt | Verifiable runtime recovery state and downstream-result evidence | Real distributed commit, signed provenance, or still-valid permission |

## Sources, original material, and third-party boundary

All new Chinese-language explanations, Mermaid diagrams, tables, teaching code, fixtures, and tests in this phase are original project work. The pages only summarize engineering boundaries from primary specifications, official documentation, and papers; they do not reproduce text, diagrams, or code lacking clear redistribution terms. Key checks include:

- [Model Context Protocol specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25), [MCP transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), and [MCP tasks](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks).
- [Agent Skills specification](https://agentskills.io/specification) and [GitHub Copilot agent skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills), with client differences used only to state boundaries.
- [OpenAI function calling guide](https://developers.openai.com/api/docs/guides/function-calling), [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents), [LangChain structured output](https://docs.langchain.com/oss/python/langchain/structured-output), [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), and [langchain-core on PyPI](https://pypi.org/project/langchain-core/).
- The original papers, database/retrieval-system documentation, and RAG official material listed in the respective retrieval courses. This record does not elevate their version snapshots or offline experiment results into proof of online retrieval quality.

## Verification evidence

| Check | Result |
| --- | --- |
| RAG offline projects | 73, 72, 37, and 42 tests; all passed under four Python modes. |
| Embedding / Reranking | 32 / 30 tests; all passed under four Python modes. |
| Agent Skills | 56 tests passed under four modes; validator and text-statistics CLI output satisfied the contract. |
| MCP | 108 offline-message-validation and 80 HTTP-loopback tests passed under four modes; PASS/BLOCK CLI was run. |
| Tool Calling | 120 dispatcher and 94 SQLite-persistence tests passed under four modes; 18-scenario, 23-step fixture CLI passed. |
| Agent Core | 68 tests and demo passed under four modes. |
| LangChain / LangGraph | Offline loop 63, retrieval 17, <code>create_agent</code> 8, and SQLite interrupt 10 tests passed under four modes; the pinned LCEL contract actually ran. |
| Cross-course final review | Wikilinks and rendered local-resource links reachable across eight directories; terminology, counts, and learning dependencies had no P0/P1/P2 issue. |
| Website tests/publication validation | <code>.website npm test</code>: 48/48 passed; <code>npm run build</code> succeeded. Publication validation produced 927 public pages and 231 assets, with 0 broken local links, prohibited files, sensitive leaks, or KaTeX errors. |

## Follow-up queue

1. In an isolated, least-privilege, cost-capped, redacted environment, connect a real MCP host, Provider SDK, identity system, approval flow, and downstream API. Record exact versions, actual exceptions, and rollback paths; do not attach teaching fixtures directly to production.
2. For cross-process/cross-region recovery, add durable quota, fencing/lease, Provider-side idempotency, signature/provenance validation, and auditable approval rather than expanding promises of the in-memory or single-SQLite teaching implementation.
3. Continue evaluating RAG against real corpora, permission changes, long context, and business objectives. Put governance of provenance/ACL/evaluation samples into a controlled artifact repository instead of freezing conclusions from one offline result.
4. As MCP, Agent Skills, LangChain/LangGraph, and Provider APIs evolve, update dynamic content through each course's <code>source_checked</code>, version locks, and integration tests; fixed teaching contracts should retain reproducible environments and migration notes.

This record focuses on Phase 24. The complete delivery is governed by course-level <code>source_checked</code>, version locks, cross-course links, and final publication validation.
