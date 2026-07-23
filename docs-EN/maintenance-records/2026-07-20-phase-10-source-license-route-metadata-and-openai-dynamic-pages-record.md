---
title: "2026-07-20 Phase 10 Source, License, Route Metadata, and OpenAI Dynamic
  Pages Record"
aliases:
  - Phase 10 optimization record
tags:
  - maintenance
  - provenance
  - licensing
  - learning-roadmap
  - openai
source_checked: 2026-07-20
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-20-第十阶段来源许可路线元数据与OpenAI动态页记录.md
translation_source_hash: eaa95fbd06e9e6e735922a4a1f6c3997feffafc6540813e93f668f4c6657526f
translation_route: zh-CN/维护记录/2026-07-20-第十阶段来源许可路线元数据与OpenAI动态页记录
translation_default_route: zh-CN/维护记录/2026-07-20-第十阶段来源许可路线元数据与OpenAI动态页记录
---

# 2026-07-20 Phase 10 Source, License, Route Metadata, and OpenAI Dynamic Pages Record

## Objective and evidence boundary

This phase did not use a count of unreviewed third-party pages as a completion metric. It prioritized high-risk work that changes public boundary, main route, or current API practice: audit frozen reference pages from real inbound links/source evidence; correct Agent Skills/MCP license facts and publication gates; migrate a second reviewed batch to learning-route metadata v2; revise dynamic OpenAI API pages from official documentation and SDK source checked on 2026-07-20; and validate with counterexample tests, full Quartz build, and multimode Python checks instead of Markdown appearance alone.

A public build proves current export policy, links, and static gates—not extra authorization for third-party material, remote API execution, account permission, or live SDK behavior.

## 1. Frozen reference-page audit and narrow restoration

Phase 9 had 186 <code>third-party-metadata-missing</code> stubs: D2L 141, LangChain 25, MCP 12, Agent Skills 8. Page-level inbound-link analysis found 71 referenced by at least one full page, but inbound links are not redistribution permission. The final layer has 189 fail-closed stubs:

| Reference layer | Current stubs | Conclusion |
| --- | ---: | --- |
| D2L Chinese reference body | 140 | Apache-2.0 repository source is known, but page images, code exceptions, and precise snapshot require sampling; only local <code>00-source-and-index.md</code> returns as curated navigation. |
| LangChain official reference layer | 23 | Two high-inbound MIT pages with no attachment block return; Semantic Search is withdrawn after fact/terminology/code findings; Memory/RAG remain blocked by image governance/snapshot evidence. |
| MCP official reference layer | 18 | Current/cross-migration page licenses cannot all be called MIT; all remain stubs. |
| Agent Skills official reference layer | 8 | Documentation is CC BY 4.0 but no fixed page-content snapshot exists; all remain stubs. |

The count rises by three because D2L local index/two LangChain pages return while a stricter path audit finds one MCP page missing source fields and a bad frozen prefix that missed five actual <code>MCP/03-develop-with-MCP/</code> official reference pages. All six join the fail-closed queue.

The restored LangChain Conceptual Overviews comparison and Graph API pages declare <code>third-party</code>, <code>frozen-reference</code>, source URL, MIT, upstream attribution, local-change explanation, and a visible frozen-source callout. They have no attachment block and match the MIT LangChain docs repository. Unknown precise local Git commit means they are fixed-date references, not current SDK tutorials. Quartz HTML confirmed visible callouts/upstream links. Semantic Search instead became <code>needs-review</code> after ISAACUS indentation error, five outputs mislabeled as Python, reversed <code>InMemoryVectorStore</code> score direction, and machine-translation problems in Cohere/Voyage/IBM watsonx/Milvus/Retriever terminology. Confirmed issues were repaired, but 39 remaining Python fences passing AST does not prove external integrations run.

## 2. Agent Skills and MCP license boundary

Agent Skills repository code is Apache-2.0, while <code>docs/</code> and site documentation are CC BY 4.0. The old registry's blanket Apache claim could cause a future incorrect release even though pages were stubs. The repair registers exactly 8 local reference pages and exact <code>agentskills.io</code> paths; requires <code>third-party</code>, <code>frozen-reference</code>, <code>CC-BY-4.0</code>, fixed attribution/local-translation notice; rejects false/zero/negative/placeholder/control-character values; injects visible attribution/source/license/change callout; checks a local fixed copy of upstream <code>docs/LICENSE</code> by SHA-256 <code>9E5F...CD94</code>; limits <code>Agent Skills/examples/</code> to five reviewed files; and restores a Specification example Skill's own <code>license: Apache-2.0</code> rather than mistaking page license for Skill metadata. Security review replayed origin/status/path/binding/license/attribution/control-character/fenced-heading/stub-title/unreviewed-asset attacks with no P0. All eight official pages remain stubs pending fixed content blobs and final-HTML attribution assertion.

MCP's archived <code>modelcontextprotocol/docs</code> repository is MIT, but after migration to <code>modelcontextprotocol/modelcontextprotocol</code>, a 2026-01-05 license change makes ordinary new documentation CC BY 4.0 while unrelicensed old contributions keep prior license; cross-change pages can contain both. Registry therefore keeps only known archived-MIT paths, sets current MCP <code>reference_layer_license: page-specific</code>, and leaves 18 frozen pages fail-closed. An architecture correction clarifies Roots/Sampling/Elicitation are client capabilities while logging is server-to-client log-message capability. The local-summary Client Concepts page loses an unprovable MIT claim and becomes <code>needs-review</code>. Declarations distinguish archived MIT from new/cross-migration pages needing page-level review.

## 3. Learning-route metadata v2, second batch

Twelve courses join v2 without changing legacy catalog order: JSON, Data Cleaning, Modern LLM Capabilities and Model Selection, Prompt Engineering, Context Engineering, LLM API Integration, Document Parsing, Knowledge Base Construction, RAG, Workflow Automation, Runtime Monitoring, and Benchmark Design. There are now 16 v2 and 40 legacy courses. Strong body wording only creates:

- <code>json + data-cleaning → document-parsing → knowledge-base</code>;
- <code>prompt-engineering → context-engineering</code>;
- <code>tool-calling → agent-core</code>;
- <code>evaluation → benchmark-design</code>;
- <code>evaluation → llmops</code>.

RAG is role-track integration, not a fabricated hard prerequisite for Chunking/Embedding/Vector Database/Semantic Search/Reranking. Three validator closure rules require every hard prerequisite to appear in each dependent role track, earlier order, and <code>core</code> status when child is core. Overall route adds a Mermaid hard-dependency graph and states it is neither recommended track nor early milestone.

## 4. OpenAI dynamic API page

The OpenAI API page was deeply reviewed against official Docs MCP, current model resolution, and <code>openai-python v2.46.0</code>:

- Chat Completions remains supported, Responses is recommended for new projects, and <code>gpt-5.6</code> is a changing alias requiring release regression.
- All Responses examples explicitly choose <code>store</code>; Responses/<code>previous_response_id</code>/Conversations/Files retention/deletion boundaries are added, with <code>store=False</code> not equal to ZDR.
- File example uses <code>expires_after</code> plus <code>finally</code> deletion.
- Text/structured/image/search/image-generation paths validate lawful terminal state before treating <code>output_text</code>/<code>output_parsed</code> as completion. A unified terminal helper scans <code>output[*].content[*]</code>, rejects <code>refusal</code>, and refuses even mixed partial text/refusal as success.
- Streaming separates provisional delta, refusal, failed, incomplete, top-level error, and EOF without terminal.
- Function calling uses bounded rounds, rejects unknown tool/repeated <code>call_id</code>/nonfinite JSON/out-of-schema arguments/exhaustion, and states in-memory dedup is not durable ledger.
- It explains SDK default two retries, single retry owner, per-attempt timeout versus business deadline, without promising generic HTTP exactly-once.
- A new offline Markdown test parses 16 Python fences and fixes explicit storage, file cleanup, mixed text/refusal, tool-terminal, and streaming-terminal contracts. No credential/network use; <code>execution_verified: false</code> remains.

## 5. Publication gate hardening and verification

Frozen reference trees cannot release mirror body by changing origin to original/curated/mixed; governance fields reject decoded control characters/Unicode line separators; stub title strips controls/Markdown image/link/HTML/remote URL; CC BY attribution inserts directly after frontmatter rather than false fenced heading; Agent Skills assets reject by default in classifier; and the remaining cdnjs preconnect is removed/forbidden.

Checks: <code>npm test</code> 45/45; <code>npm audit --omit=dev</code> zero current known vulnerabilities; build has 892 source Markdown, 546 full, 346 stubs, 895 staged Markdown, 214 assets, 2,392 HTML, 2,730 public files; 56 courses/8 stages/72 folders and 16 v2/40 legacy; all publication gates—including cdnjs references—are 0. OpenAI Markdown has 6 tests in four modes and 16 AST-parseable Python fences. Python matrix has a fixed 69-file list (SHA-256 <code>9B12...31B02</code>), 2,529 tests per mode / 10,116 executions; base 64 files plus OpenAI 6, and cached-offline environments validate LangGraph 8, CrewAI 9, Matplotlib 12, and scikit-learn 9 with <code>pip check</code>. <code>git diff --check</code> passes; no real OpenAI call or external <code>--apply</code> writeback ran.

## Sources and next steps

Key sources: [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart), [Responses migration](https://developers.openai.com/api/docs/guides/migrate-to-responses), [Your data](https://developers.openai.com/api/docs/guides/your-data), [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state), [Function calling](https://developers.openai.com/api/docs/guides/function-calling), [Streaming responses](https://developers.openai.com/api/docs/guides/streaming-responses), [parsed Responses source](https://github.com/openai/openai-python/blob/v2.46.0/src/openai/types/responses/parsed_response.py), [structured-output example](https://github.com/openai/openai-python/blob/v2.46.0/examples/responses/structured_outputs.py), [Agent Skills repository](https://github.com/agentskills/agentskills), its fixed [docs/LICENSE](https://raw.githubusercontent.com/agentskills/agentskills/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs/LICENSE), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), current [MCP license](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/LICENSE), [license switch commit](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/edeb0b74f537), archived [MCP docs](https://github.com/modelcontextprotocol/docs), [LangChain docs](https://github.com/langchain-ai/docs), and [D2L Chinese](https://github.com/d2l-ai/d2l-zh).

Next: review 189 frozen stubs page by page (Semantic Search translation/version, LangChain Memory/RAG images/licenses, MCP page history/composite license, Agent Skills content snapshots); migrate 40 legacy courses; model early safety/evaluation milestones and framework choice groups; add credential-gated low-cost live Provider contract suite; add first CC BY page final-HTML attribution tests and SBOM/NOTICE; then inspect Mermaid/tables/Callouts/code/mobile layout in Obsidian. This record covers Phase 10 only, not the long-running <code>/goal</code>.
