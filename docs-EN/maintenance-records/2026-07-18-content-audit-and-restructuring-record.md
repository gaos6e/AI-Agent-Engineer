---
title: "2026-07-18 Content Audit and Restructuring Record"
aliases:
  - AI Agent Engineer full-repository content audit 2026-07-18
  - Course restructuring decision record 2026-07-18
tags:
  - AI-Agent-Engineer
  - content-audit
  - maintenance
  - decision-record
audit_date: 2026-07-18
audit_scope: documentation and public-site publication layer
content_status: validated
lang: en
translation_key: 维护记录/2026-07-18-内容审计与重构记录.md
translation_source_hash: 56d172ab0747bc40d68e5f2f0e5027029779a4c8a6113750bdcca75326882fe1
translation_route: zh-CN/维护记录/2026-07-18-内容审计与重构记录
translation_default_route: zh-CN/维护记录/2026-07-18-内容审计与重构记录
---

# 2026-07-18 Content Audit and Restructuring Record

## Conclusion summary

This audit does **not** conclude that all original 53 courses should be rewritten. Baseline checks found modern main-path entry pages, source boundaries, hands-on projects, and mastery criteria broadly mature. The main problems were a route that presented every course as one linear sequence, three explicit core-capability gaps, diagrams/real run results concentrated in reference layers rather than the main path, and a website that hard-coded 53 courses, 8 stages, and continuous integer order.

The resulting strategy is:

1. Keep all 53 original course entry points; do not delete or mass-rewrite without evidence.
2. Add Modern LLM Capabilities and Model Selection, Environment Agents, and Realtime Multimodal Interaction to close explicit gaps.
3. Replace the universal linear route with a course map, role paths, and content tiers.
4. Add precise diagrams to high-value Agent/RAG/evaluation/safety/multi-Agent/LLMOps paths and generate/embed actual Data Visualization results.
5. Clarify stable, extension, experimental, and observed boundaries for MCP, Agent Skills, A2A, and AG-UI.
6. Downgrade unverified Machine Learning quick-reference pages rather than rewriting every historical mirror under the banner of optimization.
7. Generate site course discovery, stage statistics, and navigation from metadata to remove hard-coded barriers to future course changes.

> [!important] Decision boundary
>
> “Keep” does not prove every historical paragraph is correct, and “downgrade to reference” does not mean content has no value. This audit directly changes only evidence-backed, main-path-impacting material. Unreviewed mirrors, legal conclusions, third-party image permission, and rapidly changing protocols are not written as stable facts.

## Baseline and evidence hierarchy

The baseline predated this audit's new courses and covered the then-current source tree and site-generation manifest. Counts describe what existed, not quality: 53 top-level course entries with stage/order/objective/prerequisite/mastery metadata; 844 Markdown; 172 Python files; 61 Python names containing <code>test</code>; 49 main-path <code>examples/</code> directories after excluding two frozen/imported reference subtrees; 534 image assets; 15 Mermaid pages; zero unresolved top-index wikilinks; and no common <code>content_tier</code>/<code>difficulty</code> convention. All 534 images were concentrated in Python Fundamentals, Agentic Design Patterns, and LangChain, leaving runtime/data-flow/trust-boundary/release-state explanations underrepresented on the main path.

The existing site manifest aligned 844 source Markdown with 687 full pages, 157 stubs, 3 generated pages, 187 public resources, 650 excluded resources, and no route collision. It was an audit starting point, not post-change proof.

Evidence priority was: current repository facts; standards/first-party documentation; original papers/official projects; dynamic vendor documentation for date-specific API/model facts; then existing curation/engineering inference, labeled observed/experimental/needs-review if stronger support was absent. Dynamic content uses four states: <code>stable</code>, <code>dynamic</code>, <code>frontier/observed</code>, and <code>needs-review</code>.

The audit completed inventory-level directory/index/metadata/file/test/image/Mermaid/publication checks, not sentence-level review of 844 Markdown. It deeply sampled Agent Core, Tool Calling, MCP, Agent Skills, RAG, evaluation, LLMOps, monitoring, safety, governance, multi-Agent, Data Visualization, and Machine Learning entries. It records limits: reference titles are structural evidence only; benchmark/vendor documentation cannot prove local business constraints; test count cannot prove coverage; offline simulators cannot prove browser/desktop/audio/cloud/model behavior; law/license/cross-border/recording require responsible review; and frozen Python reference paths still had about 103 historical broken links plus 3 stub-transition issues.

## Course-tier and navigation decisions

No courses were deleted and none physically merged. “Grouped in navigation” never means files are merged: RAG/data/multimodal courses own distinct contracts, tests, sources, and failure responsibilities. Core courses retain AI Fundamentals, AI Safety, Agent Skills, Agent Core, JSON, LLM API, LLMOps, MCP, RAG, Tool Calling, Context Engineering, Prompt Engineering, Probability/Statistics, Evaluation, Monitoring, and Privacy Computing. Role-advanced work includes governance, benchmark, retrieval components, MLOps, OCR, multi-Agent, multimodal, workflow, visualization, synthetic data, annotation, cleaning, parsing, knowledge base, semantic search, and speech I/O. Image/video are optional frontier/project material. API, Git, Linux, Markdown, Python, data structures, regex and mathematical foundations remain capability-dependent prerequisites/references; framework/complete historical tutorials are downgraded rather than erased.

Reasons against deletion/physical merge: historical tutorials retain offline/reference value; framework mirrors retain terminology/migration/case clues but require publication limits; rename/delete breaks links/assets/bookmarks; component courses have different input contracts/test/failure domains; and the user explicitly rejected indiscriminate rewrite. Any later deletion needs replacement entry, reverse-link inventory, public redirect, third-party-asset license decision, and user confirmation.

The updated overall route provides four role paths—Agent Application Development, RAG and Knowledge Base, Agent Platform and Reliability, Multimodal and Realtime—and five tiers: core, advanced, frontier, practice, reference. Learning is a closed loop of structure explanation, runnable implementation, expected failure, verification command, and nonapplicability boundary. One course-map Dataview invocation is deliberately replaced only during public export.

## Main implementation decisions

The audit introduced/focused:

- Agent diagrams for proposal/runtime/state/recovery/HITL/untrusted observation; separation of model proposal, deterministic runtime, and authorization.
- RAG three-plane evidence and failure-backtracking model, including ACL, citations, update/deletion, evaluation, and public/protected boundaries.
- Evaluation object relationships across task/trial/trace/grader/outcome/harness and explicit release evidence.
- LLMOps release-gate state machine and monitoring separation from frozen evaluation.
- Security/governance boundaries around identity, least privilege, prompt injection, provenance, policy, and incident response.
- Current classification of MCP stable core/extensions/experimental Tasks/Apps/drafts; Agent Skills client-dependent behavior; A2A/AG-UI stable versus observation status.
- Data Visualization actual reproducible project artifacts with alternatives, not only plotting snippets.
- Dynamic metadata-driven site Homepage/CourseNavigator and publication policy for original, curated, third-party, mixed, dynamic, validated, frozen-reference, and needs-review material.

The audit also established source and publication direction: third-party full material needs source URL/commit/author/license/local-change boundary; unknown permission stays private or becomes public source stub. Original work cites facts; curated work declares dependence; content state is evidence rather than article appearance. Existing high-risk framework/reference layers receive visible warnings rather than unauthorized wholesale rewrites.

## Verification and recorded limits

At the time, all planned focused course/project checks, site unit tests, full site build, local-link/publication scans, and generated-navigation checks reported success under their stated scope. Earlier baseline and historic counts are recorded as historical evidence; they must not be read as present-day build results. Human Obsidian/Desktop visual checks for long tables, Mermaid, Callouts, Dataview, and navigation remained a queue item.

## Follow-up queue

1. Migrate route metadata page by page; do not infer hard dependencies from display order.
2. Unify vault Dataview, Homepage, and CourseNavigator around one verified route model where project boundaries permit.
3. Validate framework deep water: concurrency, migration, encryption, multitenancy, checkpointing, persistence schemas, and real controlled Provider calls.
4. Keep model-quality evidence separate from deterministic runtime tests.
5. Repair frozen-reference source/license/link issues page by page; do not turn dated translations into current API tutorials by mass replacement.
6. Build a cross-course evidence chain linking RAG, evaluation, safety, LLMOps, and monitoring through ACL, trace, regression gate, rollback, and incident rehearsal.
7. Visually inspect site/Obsidian rendering after automated gates pass.

This original project record is grounded in repository facts and primary-source checks available on the audit date. It is not a legal opinion or a blanket license clearance.
