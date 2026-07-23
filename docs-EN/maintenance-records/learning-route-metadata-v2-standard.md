---
title: "Learning-Route Metadata v2 Standard"
tags:
  - maintenance
  - learning-roadmap
  - metadata
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/学习路线元数据v2规范.md
translation_source_hash: 7d75f5a3ee7b63185461f5c0162bc3871da2845387141aff27a60d7fb6ea3846
translation_route: zh-CN/维护记录/学习路线元数据v2规范
translation_default_route: zh-CN/维护记录/学习路线元数据v2规范
---

# Learning-Route Metadata v2 Standard

## Objective

The former <code>ai_learning_stage</code> and <code>ai_learning_order</code> fields can produce only one global course catalog. They cannot express a stable course ID, actual hard prerequisites, or ordering for different roles. This standard separates knowledge domain, catalog order, dependency graph, and role tracks into distinct fields. All 57 courses must be reviewed page by page before declaring relationships; relationships must not be inferred in bulk from legacy numbers or titles.

## Field contract

~~~yaml
# Keep legacy stage / order during the compatibility period; v2 consumers no longer sort or group by them.
ai_learning_schema: 2
ai_learning_id: agent-core
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3200
ai_learning_hard_prerequisites:
  - tool-calling

ai_learning_track_agent_app_order: 600
ai_learning_track_agent_app_kind: core
~~~

| Field | Semantics |
| --- | --- |
| <code>ai_learning_schema</code> | Every v2 page uses the integer <code>2</code>; once declared, it may not fall back to legacy metadata. |
| <code>ai_learning_stage</code> / <code>ai_learning_order</code> | Retained temporarily for historical queries. The build still checks validity and global uniqueness, but v2 consumers no longer sort or group by them. |
| <code>ai_learning_id</code> | A unique kebab-case ID that does not change when a Chinese title changes. |
| <code>ai_learning_domain</code> | A controlled knowledge domain, not a display title. |
| <code>ai_learning_catalog_order</code> | A positive JavaScript-safe integer for global catalog order, with gaps left for insertion. |
| <code>ai_learning_hard_prerequisites</code> | Role-independent hard dependencies. <code>[]</code> means a page-level review confirmed that no universal hard prerequisite exists. |
| <code>ai_learning_track_&lt;role&gt;_order</code> | A positive JavaScript-safe integer giving the course order in one role track. |
| <code>ai_learning_track_&lt;role&gt;_kind</code> | One of <code>core</code>, <code>recommended</code>, or <code>optional</code>. |

The first-version domains are fixed as <code>foundations</code>, <code>model-and-context</code>, <code>retrieval-and-data</code>, <code>multimodal</code>, <code>agent-runtime</code>, <code>framework-practice</code>, <code>evaluation-reliability</code>, <code>safety-governance</code>, <code>production-ops</code>, and <code>frontier-reference</code>.

The first-version role IDs are fixed as <code>agent_app</code>, <code>rag</code>, <code>agent_platform</code>, and <code>multimodal_realtime</code>. The role set is derived from track fields; it is not stored as a second roles list that could drift.

## Validation rules

- The public build requires all 57 top-level courses to declare <code>schema: 2</code>. A fallback to legacy metadata fails closed, and missing v2 fields must not be silently derived from legacy fields.
- Legacy <code>stage/order</code> remains only for short-term compatibility. Before removing it, external vault queries and historical notes must be checked separately; this phase does not clean it up mechanically.
- The website reads metadata using a YAML AST and validates controlled field names; ID, domain, and order types; hard-prerequisite existence, duplicates, self-cycles, and whole-graph cycles; and the pairing and unique order of each role's order/kind fields. Misspelled fields or noncanonical scalars such as tags and anchors fail closed.
- Whenever a course belongs to a role track, every hard prerequisite must belong to the same track and appear earlier. If the course is <code>core</code>, each hard prerequisite must also be <code>core</code> for that role. This prevents a track from showing a course while hiding its required prerequisite.
- Global catalog order and the dependency DAG are separate concerns; the validator does not infer dependencies from catalog position.
- Personal completion-status fields remain local only. The public build strips them, and they are not evidence of content quality.
- A top-level course index must not degrade into a public-build stub that loses route fields. That condition fails the build closed.

## Full-review result

All 57 courses have now migrated. Only the following courses declare nonempty hard prerequisites; the other 49 explicitly use <code>[]</code> because page-level review found no universal, whole-course hard prerequisite.

| Course ID | Hard prerequisites | Evidence boundary |
| --- | --- | --- |
| <code>context-engineering</code> | <code>prompt-engineering</code> | Its entry page explicitly requires completion of Prompt Engineering first. |
| <code>document-parsing</code> | <code>data-cleaning</code>, <code>json</code> | Its entry page explicitly requires both full courses first. |
| <code>knowledge-base</code> | <code>document-parsing</code> | Its entry page explicitly requires Document Parsing first. |
| <code>agent-core</code> | <code>tool-calling</code> | The Agent loop depends on verified Tool Calling boundaries. |
| <code>llmops</code> | <code>evaluation</code> | A release gate must already have a regression-capable evaluation contract. |
| <code>benchmark-design</code> | <code>evaluation</code> | The Benchmark Design entry page explicitly requires case and grader mastery first. |
| <code>synthetic-data</code> | <code>data-cleaning</code>, <code>data-annotation</code>, <code>evaluation</code> | The Synthetic Data entry page uses the strong wording “learn first.” |
| <code>multi-agent-collaboration</code> | <code>agent-core</code> | The Multi-Agent Collaboration entry page explicitly requires completion of Agent Core. |

Only relationships supported by strong wording in the body, such as “complete first” or “learn first,” and capable of closing within a role track were recorded. “Recommended to understand first,” “may be learned in parallel,” and “as the project needs” are represented only through track order or explanatory prose, not upgraded to hard prerequisites. MCP, Environment Agents, Agent Skills, specific frameworks, and the system-integration order from Chunking to Reranking remain within that boundary.

| Role track | Total courses | Core | Recommended | Optional |
| --- | ---: | ---: | ---: | ---: |
| <code>agent_app</code> | 32 | 9 | 13 | 10 |
| <code>rag</code> | 35 | 17 | 12 | 6 |
| <code>agent_platform</code> | 38 | 14 | 16 | 8 |
| <code>multimodal_realtime</code> | 29 | 10 | 13 | 6 |

The RAG track uses fine-grained within-catalog order to express recommended progress from ingestion through retrieval and generation to evaluation. The multimodal track labels OCR as recommended and ASR/TTS as core; it does not claim that an end-to-end speech-to-speech runtime must deploy separate ASR/TTS services. The full Privacy Computing course comes after security, while data minimization, purpose limitation, and retention limits should still be handled in the early security milestone.

“Security and evaluation foundations” still means selected sections within courses, not stable course-level nodes. It remains an explicit human milestone and must not cause the entire AI Safety or Evaluation Systems course to be set as an early hard prerequisite for every project. The complete AI Safety course sits near the production-release gate by role, and the complete AI Governance course enters the Agent Platform track; their course-level track positions do not replace required early chapters.

## Rules for entering frontier and reference material

<code>frontier-reference</code> is not a catch-all news bucket. A topic can become a course only when all of the following are true:

1. It has a versioned primary specification, original paper, or public governance mechanism, rather than vendor claims alone.
2. It can deliver a testable engineering artifact or adoption-decision evidence.
3. Its boundary with existing courses is clear, and it records an observation date, adoption conditions, and migration and exit conditions.
4. It is optional by default in every role track unless there is separate, strong evidence of a universal hard dependency.
5. It presents durable principles in a separate layer from rapidly changing SDKs, extensions, and vendor adapters.

The first course in this domain is [[a2a/00-index|A2A]]. Its adoption basis is that A2A <code>1.0.0</code> provides a formal protocol model, version negotiation, standard bindings, security requirements, and interoperability testing, and can yield stable learning artifacts such as an Agent Card, a Task contract, negative cases, and a migration decision. It belongs only to the optional <code>agent_app</code> and <code>agent_platform</code> tracks; it is not a hard prerequisite for MCP, Multi-Agent work, or ordinary Agent applications.

## Consumers and synchronization

The overall learning route calls one checkable Dataview course map in Obsidian and directly stores the four role lists. That view reads compatible <code>stage/order</code> fields for grouping and writes local completion status into course entry pages. The public build does not depend on Dataview. Instead, it replaces that call with a static knowledge-domain table produced from the same YAML AST result and verifies the role lists character by character. The build fails closed when metadata changes but the route is not synchronized.

The website Homepage and CourseNavigator read only v2 <code>domain/catalog_order/track</code> fields. The Homepage presents the ten knowledge domains that currently contain courses and statistics for the four role tracks; CourseNavigator offers both role-sorted entry points and the full course tree organized by domain. The controlled domain count remains ten; <code>frontier-reference</code> stays sparse through the entry rules above rather than creating courses merely to fill it. Legacy <code>stage/order</code> continues to drive only the overall route's local interactive map, not the public homepage or course navigation.
