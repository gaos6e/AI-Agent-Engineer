---
title: "2026-07-21 Phase 15 Prompt, API, and Retrieval State Contract Deep
  Review Record"
aliases:
  - Phase 15 optimization record
tags:
  - maintenance
  - prompt-engineering
  - llm-api
  - retrieval
  - vector-database
  - multi-agent
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-21-第十五阶段提示词API与检索状态合同深审记录.md
translation_source_hash: d94910bbee2ef8d5f87d43b6af803c1aa17d5152ad626cc88c9036e2e003baf0
translation_route: zh-CN/维护记录/2026-07-21-第十五阶段提示词API与检索状态合同深审记录
translation_default_route: zh-CN/维护记录/2026-07-21-第十五阶段提示词API与检索状态合同深审记录
---

# 2026-07-21 Phase 15 Prompt, API, and Retrieval State Contract Deep Review Record

This phase deeply reviewed Prompt Engineering and LLM API Integration chapter by chapter, and reviewed evaluation/safety/lifecycle pages for Embedding, Semantic Search, and Vector Database. Twenty-six course pages, five offline projects, fixtures, and tests changed without changing course names or role routes. It proves current offline contracts/negative tests/public build, not real Provider endpoints/model quality/IAM/distributed database/permanent audit ledger/all historical review.

Prompt Lab now treats prompt, dataset, schema, and report as independent but bound versioned assets. Dataset v2 has 12 typical/boundary/multilingual/insufficient/adversarial cases plus annotation reason; versions/digests enter the report; a declared teaching-schema subset rejects unknown fields/keywords/dialects/IDs/drift; reports recompute every CaseResult so altered label/risk/errors/chars/pass cannot pass; CLI errors exit nonzero with normal/<code>-O</code> equivalence. It does not claim full Draft 2020-12 support. Officially checked facts say reusable OpenAI prompts/old Evals were deprecated on 2026-06-03; structured output limits structure only, not refusal/incomplete/fact/business/AuthZ; untrusted web/user/tool content never becomes system/developer instruction.

Nine LLM API pages distinguish application canonical contract, Provider wire/API contract, and SDK convenience. Offline fixtures preserve OpenAI Responses, Anthropic Messages, and Gemini Interactions differences in storage/history/continuation/stream/tool result. Stateless continuation requires complete source-bound history; unknown terminal/block, truncation, stream error, incomplete tools fail closed. Source URL policy strictly confines official host/GitHub approved repo after exact decoding. It also records OpenAI workload identity, Anthropic API key/WIF, Gemini Standard-key migration, fallback restrictions, and a bounded reliable client (one retry owner/monotonic deadline/4096 events/100000 characters/no provisional release).

Retrieval fixes reject duplicate ranked IDs/invalid qrels and constrain nDCG 0..1; Semantic Search audits full channel candidate window, not final top-k. Vector store v2 adds expected source revision, delete-before-create fence, resurrection semantics, disk-revision freshness, 100000 point/tombstone cap, 20 MiB serialized-state cap, and fails before replace/memory update. Source revision is opaque; ABA/permanent history/space-signature query envelope remain unsolved limits.

Verification: Prompt 19, client 22, Provider 99, Embedding 31, Semantic Search 34, Vector Database 41 in normal/<code>-O</code>/<code>-W error</code>; 46/46 site tests; build 905 source Markdown, 559 full, 346 stubs, 908 staged, 2,425 HTML; all public gates 0. Follow-up adds query contract signature/encoding role, durable lifecycle/audit, locked SDK capture/replay/live tests, real Prompt evaluation, consistent text/dtype/Embedding metadata, and Obsidian visual review.
