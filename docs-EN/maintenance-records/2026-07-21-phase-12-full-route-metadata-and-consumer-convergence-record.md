---
title: "2026-07-21 Phase 12 Full Route Metadata and Consumer Convergence Record"
aliases:
  - Phase 12 optimization record
tags:
  - maintenance
  - learning-roadmap
  - metadata
  - multi-agent
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-21-第十二阶段全量路线元数据与消费者收敛记录.md
translation_source_hash: 8bf857455483b91ab9f8227536447bd74371aeb2f2e0c3e3719d2a426d883942
translation_route: zh-CN/维护记录/2026-07-21-第十二阶段全量路线元数据与消费者收敛记录
translation_default_route: zh-CN/维护记录/2026-07-21-第十二阶段全量路线元数据与消费者收敛记录
---

# 2026-07-21 Phase 12 Full Route Metadata and Consumer Convergence Record

This phase completed page-level route review for the remaining 33 top-level courses, putting all 56/56 courses into learning-route metadata v2. Obsidian's overall route, public Homepage, CourseNavigator, and site validator now read or check the same <code>domain/catalog_order/hard_prerequisites/track</code> relationships. Legacy <code>ai_learning_stage/order</code> remains for historical compatibility but no longer drives the three primary consumers.

The migration covers engineering/mathematical foundations; data/runtime/framework work; and production/multimodal courses. Only two new nonempty hard-prerequisite groups have page-level support: <code>synthetic-data</code> depends on Data Cleaning, Data Annotation, and Evaluation; <code>multi-agent-collaboration</code> depends on Agent Core. The other 31 newly migrated courses explicitly use <code>[]</code>. Recommended learning, local capability, and integration order were not promoted to hard prerequisites.

Role counts are: Agent Application Development 31 (9 core/13 recommended/9 optional), RAG and Knowledge Bases 35 (17/12/6), Agent Platform and Reliability 37 (14/16/7), Multimodal and Realtime 29 (10/13/6). There are ten controlled domains, nine currently populated; <code>frontier-reference</code> remains empty rather than receiving a placeholder course. Corrections include placing AI Fundamentals at the actual common start; making Markdown/regex navigation valid; making Machine/Deep Learning recommended background rather than hidden hard gates; distinguishing framework capability/order/full-course prerequisite; retaining verified CrewAI 1.15.4 while recording 1.15.5 only as observation; and separating MLOps release objects from LLMOps composite-application release objects.

The old overall-route note called an absent Dataview helper. It now stores a static domain table and four role lists directly. <code>prepare-content.mjs</code> regenerates the same snapshot from strict YAML AST and compares it exactly; metadata/route drift fails the build. Every course must be schema 2, Homepage calculates role counts from tracks, CourseNavigator offers role order and domain tree, and site validation checks nine populated domains/four roles/56 entries/real folders.

Verification: all 56 v2, unique ID/catalog/track order, existing acyclic visible earlier hard prerequisites; website tests 46/46; build 894 source Markdown, 548 full, 346 stubs, 897 staged pages; 2,396 HTML, nine domains, four roles, 56 course entries, 72 folders; every publication gate 0. Dynamic facts were checked against official Python/Git/Coreutils/PyTorch, MCP/Agent Skills/LangChain, CrewAI, NIST, and W3C material on the stated date.

This proves current route metadata consistency, not page-level fact/license/example review for all 893 source Markdown. Next: Obsidian visual review; page-by-page treatment of stubs; dynamic-framework/history review; frontier-entry rules; external-query audit before deleting compatibility fields; and controlled live Provider/media/deployment evidence.
