---
title: "2026-07-20 Phase 9 Dynamic Material, Publication Gates, and Runtime
  Audit Record"
aliases:
  - AI Agent Engineer Phase 9 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - documentation-audit
  - provenance
  - mermaid
  - runtime-validation
  - publishing
content_origin: original
content_status: validated
source_checked: 2026-07-20
lang: en
translation_key: 维护记录/2026-07-20-第九阶段动态资料发布门禁与运行时审计记录.md
translation_source_hash: e5b457ad142aba1b8b2f054fc56df9c8a42df783e3e5c0acde47b8ff1700cf0c
translation_route: zh-CN/维护记录/2026-07-20-第九阶段动态资料发布门禁与运行时审计记录
translation_default_route: zh-CN/维护记录/2026-07-20-第九阶段动态资料发布门禁与运行时审计记录
---

# 2026-07-20 Phase 9 Dynamic Material, Publication Gates, and Runtime Audit Record

This phase continues Phase 8 work on dynamic SDK/protocol pages, optional-dependency examples, third-party reference-layer publication boundary, and Mermaid runtime risk. The primary Agent owned scope, terminology, sources, conflict review, and final gate. Three specialists installed/verified LangGraph, CrewAI, Matplotlib, and scikit-learn environments outside the vault; another reviewed Mermaid localization/accessibility. Specialists did not change project files; all changes were landed centrally.

> [!important] Evidence boundary
>
> This phase proves behavior for fixed versions, dates, and current test/build paths. It does not prove dynamic APIs never change, nor present offline fixtures, keyless runtimes, or browser rendering as live Provider, production concurrency, packet-capture-level zero connection, a complete license inventory, or Obsidian-desktop acceptance. Third-party reference pages without page-level source/license metadata remain fail-closed; no licenses were inferred in bulk to increase public page counts.

## 1. Dynamic material and factual boundaries

- Gemini introductory material makes the Interactions API, GA in June 2026, the main path for new projects. <code>generateContent</code>/Chats remain supported legacy compatibility layers. API state, Steps, streaming event, continuation, and tool result are no longer mixed; Gemini 3.5 examples use <code>thinking_level</code> rather than copy explicit <code>temperature</code>, <code>top_p</code>, or <code>top_k</code> into 3.x.
- LangChain fixes Python import <code>langchain-voyageai</code> to importable <code>langchain_voyageai</code>, while distribution install name remains <code>langchain-voyageai</code>. Fictional model names are removed and “all Provider advanced capabilities are equal” becomes a unified entry point plus capability gates.
- Old Bedrock Claude 3.5 identifiers become an AWS-model-card-checkable Sonnet 4.6 example. Model ID, region availability, and <code>bedrock_converse</code> support still require checking in the target account.
- MCP stable baseline remains <code>2025-11-25</code>; candidate extensions and implementation-specific ability are not presented as stable fact.
- API/SDK/model-catalog/transitive-dependency versions retain check dates for reproduction/drift detection, not permanent install advice.

## 2. Optional-dependency examples and course contracts

Specialists used Python 3.11.9, temporary virtual environments outside the vault, and <code>-B</code>/<code>PYTHONDONTWRITEBYTECODE</code>; temp directories were verified and deleted after work.

| Project | Pinned direct dependency | One-run tests | Four-mode result | Boundary tightened |
| --- | --- | ---: | --- | --- |
| LangGraph recoverable approval | <code>langgraph==1.2.9</code>, <code>langgraph-checkpoint-sqlite==3.1.0</code> | 8 | 32/32 | Normalize <code>thread_id</code>; recovery across processes shares SQLite after start/inspect/resume. |
| CrewAI persistent Flow | <code>crewai==1.15.4</code> | 9 | 36/36 | Normalize <code>flow_id</code>; same operation ID/different payload conflict cannot produce a second effect. |
| Agent evaluation dashboard | <code>matplotlib==3.11.0</code> | 12 | 48/48 | p50/p95 exist only after at least one completed run; dry run cannot overwrite course artifact. |
| Ticket-intent router | <code>scikit-learn==1.9.0</code> | 9 | 36/36 | <code>random_state</code> restricted to nonnegative 32-bit range; virtual environment stays outside vault. |

Four modes are normal, <code>-O</code>, <code>-W error</code>, and <code>-O -W error</code>. Two known CrewAI transitive-dependency warnings remain narrowly allowlisted by complete message; all other warnings fail.

CrewAI installation is not a lightweight contract. With pip 24.0 bundled in a fresh Python 3.11 venv, <code>jsonschema → rpds-py</code> resolves as <code>ResolutionImpossible</code>. Upgrading pip only in that temp venv to 26.1.2 succeeds and <code>pip check</code> finds no broken dependency. One direct dependency resolves 138 distributions and about 800 MB, transitively adding ChromaDB, LanceDB, MCP, OpenAI SDK, and OpenTelemetry. Course commands now include reproducible pip upgrade and state: a one-line requirement is not a lockfile; tests disable CrewAI telemetry/AMP tracing/isolated-process OpenTelemetry without doing packet capture; no API/LLM/HTTP log proves only the current path, not arbitrary deployment zero egress; production needs capability trimming, full dependency lock, SBOM, and license/vulnerability/egress audit.

In Basic Python, Matplotlib/NumPy imports in Day31–35 <code>example01.py</code> move into plotting entry, leaving algorithm module and two tests runnable in standard-library environment while plotting still requires explicit course dependencies. One transient internal subprocess <code>returncode=1</code> appeared once each in Embedding/Reranking CLI-equivalence tests; identical stress/full-mode reruns passed. <code>check=True</code> formerly hid useful context behind <code>CalledProcessError</code>; tests now assert return code and preserve decoded stderr. There is insufficient evidence to attribute the two exits to code, concurrent installation, antivirus, or Windows noise, so the record preserves uncertainty rather than pretending they never happened.

## 3. Third-party reference-layer publication gate

<code>.website/scripts/prepare-content.mjs</code> adds explicit fail-closed prefixes for known upstream-reference trees: full Deep Learning reproduction, fixed-date LangChain reference layer, old MCP translation, and old Agent Skills reference layer. When a page has <code>source</code>/<code>source_url</code> but lacks page-level <code>content_origin</code>, public layer emits only a source-jump page; adjacent old LangChain attachments cannot stay public merely because Markdown became a stub.

The gate safely demotes 186 known-upstream Markdown pages to <code>third-party-metadata-missing</code> stubs and blocks 12 LangChain image attachments without corresponding publication evidence. This is a page-review queue, not a count to mass-fill. Full publication returns only after source, version, content origin, redistribution license, and local changes are checked.

## 4. Mermaid security, localization, and accessibility

- The Quartz plugin had fixed Mermaid 11.4.0 from cdnjs. Runtime patch now copies the entry and all ESM chunks from lockfile <code>mermaid==11.16.0</code> and loads same-origin in build and fresh dev.
- Restore of original diagram source changes from <code>innerHTML</code> to <code>textContent</code>; Mermaid <code>securityLevel</code> is <code>strict</code>. Patch validates source and compiled bundle and remains repeatable for warm runtime without reintroducing CDN.
- Build checks SHA-256 of published Mermaid entry plus 103 chunks against installed package and rejects cdnjs loader, rather than checking filenames or one entry.
- Zoom control is about 44×44px, has visible keyboard focus, remains visible on touch/narrow screens. Build preview/fresh dev verify diagram render, dark-theme switch, full-screen clone, and no console errors/warnings.
- <code>.website/legal/Mermaid-MIT.txt</code> preserves top-level MIT license; generated third-party declaration records 11.16.0/same-origin. This is not complete transitive-dependency attribution; SBOM/license report remains needed.
- After 11.4.0→11.16.0, <code>npm audit --omit=dev</code> reports 0 known vulnerabilities, a current registry-advisory snapshot rather than future guarantee.

## 5. Verification actually performed

- Provider contract: 96 tests pass in all four modes.
- Base Python: 64 files with no course optional dependency, 2,485 tests per mode, full four-mode rerun.
- Optional dependencies: four table files, 38 tests per mode in isolated environments.
- Aggregated Python: 68 test files, 2,523 tests per mode, 10,092 test-method executions in four modes; base and isolated environments counted separately.
- Embedding/Reranking diagnostic changes: 59 tests per mode pass in targeted four-mode rerun; each CLI performs 30 one-process stress runs and Embedding normal/optimized subprocesses complete 100 stress rounds.
- Site: <code>npm test</code> 38/38; <code>npm audit --omit=dev</code> zero known vulnerabilities. Final build sees 891 source Markdown, 548 full, 343 stubs, and 3 generated pages (894 staged Markdown), publishing 213 assets, 2,386 HTML, 2,723 public files. Broken links, forbidden files, progress/sensitive/self-redirect/table-wikilink/checkbox/KaTeX gates are all 0; navigation is 8 stages, 56 courses, 73 folders.

## Key sources and follow-up

Key official material: [Gemini Getting started](https://ai.google.dev/gemini-api/docs/get-started), [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview), [Gemini 3.5 migration notes](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.5), [LangChain VoyageAI embeddings](https://docs.langchain.com/oss/python/integrations/embeddings/voyageai), [AWS Bedrock model catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html), [Claude Sonnet 4.6 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html), [MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25), [Mermaid npm](https://www.npmjs.com/package/mermaid), and [Mermaid releases](https://github.com/mermaid-js/mermaid/releases). Provider-source detail continues in the [[maintenance-records/2026-07-19-phase-8-three-provider-contract-and-streaming-state-machine-record|Phase 8 record]].

Next: review the 186 stubs page by page; separately determine redistribution permission for LangChain Academy/raw, Agent Skills, and other full external material; produce SBOM/NOTICE; establish isolated lockfile/CI matrices for optional dependencies; build credential-gated no-side-effect live Provider contracts; inspect Mermaid/tables/Callouts/wikilinks/mobile layout in Obsidian; preserve the expanded stderr diagnostic if the unexplained CLI exit recurs; and continue v2 metadata/dynamic-SDK/cross-knowledge-base review.

See the preceding [[maintenance-records/2026-07-19-phase-8-three-provider-contract-and-streaming-state-machine-record|Phase 8 record]]. Source/license/original-curated-third-party policy continues through the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
