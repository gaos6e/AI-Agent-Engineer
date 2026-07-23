---
title: "2026-07-22 Phase 21 Deep Review Record: Deep Learning, Speech, Data
  Annotation, and Provider API Contracts"
aliases:
  - Phase 21 optimization record
tags:
  - maintenance
  - api
  - data-annotation
  - deep-learning
  - speech
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第二十一阶段深度学习语音数据标注与厂商API合同深审记录.md
translation_source_hash: c9583593b1bcb978f06d4a4a4e97824457a42dd924d6b0a0fdd2b7a6fad68ec2
translation_route: zh-CN/维护记录/2026-07-22-第二十一阶段深度学习语音数据标注与厂商API合同深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第二十一阶段深度学习语音数据标注与厂商API合同深审记录
---

# 2026-07-22 Phase 21 Deep Review Record: Deep Learning, Speech, Data Annotation, and Provider API Contracts

## Phase conclusion

This phase brings dynamic Provider interfaces, human annotation, training candidates, and speech I/O into one traceable evidence chain: documentation snapshots are separate from live execution; input snapshots, annotation/training candidates, and release artifacts are separate; local operation, Provider diagnostics, and object authorization are separate; and planning, generation, playback, and release are separate. A learner can no longer mistake one model name, one <code>request_id</code>, one authorization reference, one kappa calculation, or one passing offline script for proof that something is production-executable, ACL-approved, release-approved, or real media quality.

It covers the Provider AI API reference, Data Annotation, [[deep-learning/00-index|Deep Learning engineering practice and modernization route]], [[speech-recognition/00-index|Speech Recognition]], and [[text-to-speech/00-index|Text-to-Speech]].

> [!important] What this phase does not prove
>
> Offline JSON/SSML/transcript/training fixtures, static syntax, page links, and a Quartz build prove consistency of the current teaching contracts. They do not prove any real Provider account, model availability or price, actual audio decoding/recognition/naturalness, person identity, voice permission, object-level ACL backend, production approval, model quality, data representativeness, labor/privacy/legal conclusion, or external-system receipt.

## Multi-Agent division of work and primary-Agent review

1. The primary Agent checked official entry points, model/SDK/structured-output boundaries for the Provider API reference page by page, and standardized terminology for <code>provider_request_id</code>, local <code>operation_id</code>, authorization, and outcome.
2. The Data Annotation specialist changed only the Data Annotation directory, project, and new governance/release pages; the primary Agent preserved other chapter changes that existed beforehand.
3. The Deep Learning specialist changed only high-risk Deep Learning entry points, the original engineering route, a zero-dependency auditor, and precise publication policy; the frozen D2L reference body remains fail-closed.
4. The speech specialist separately reviewed ASR and TTS media formats, revision, evaluation, streaming state, voice risk, and offline projects.
5. An independent read-only integration review checked learning order, links, source dates, IDs, approvals, ACL, and public boundaries. Every finding received a narrow repair and a recheck from the primary Agent or original specialist.

Pre-existing changes outside this phase were Data Annotation pages 02–04, ASR pages 04–05, and the TTS SSML page. During a Deep Learning publication-policy repair, an independent existing LangChain image-whitelist change in <code>.website</code> was also found and retained; it is not counted as this phase's work.

## Key changes

### Provider APIs: dynamic reference material is not an executable contract

- The index adds a minimum Provider contract: “OpenAI-compatible” reuses only part of the request/response shape. Models, streaming events, tools, structured output, data retention, retries, and permissions remain Provider-specific and must be checked per Provider.
- Each page records its own <code>source_checked</code> and source baseline. The index no longer conflates an independent OpenAI-page check on 2026-07-20 with a whole-set check on 2026-07-22.
- Call-affecting facts were corrected: Cohere v2's <code>json_schema</code> / <code>response_format</code> combination restrictions; Kimi K2.6's explicit way to turn off thinking and its <code>web_search</code> not currently recommended as a new dependency; GLM's current <code>glm-5.2</code>/<code>glm-5v-turbo</code> teaching baseline; and DeepSeek's announced deprecation window for old models.
- Anthropic's canonical pinned model ID, Gemini API family, Mistral SDK main entry point, and xAI cache key are not cross-Provider semantics. Cache keys, Provider request IDs, business idempotency, and identity authorization cannot substitute for one another.

### Data Annotation: govern first, then turn observations into publishable evidence

- The learning order now requires the minimum governance gate after completing a task card and before touching real data or people; only then does it move to guidelines, workflow, quality control, and active learning.
- Two pages on governance/privacy/license/labor safety and version/release/production feedback separate <code>sample_id</code>, <code>source_revision</code>, <code>annotation_id</code>, <code>final_label</code>, and <code>release_id</code>, and place withdrawal, tombstones, frozen sets, and production feedback in a controlled chain.
- The offline auditor strictly rejects duplicate JSON keys, nonstandard constants, mixed versions, unpaired dual annotation, inconsistent input snapshots, and records without evidence. It measures only agreement/kappa/conflicts for a teaching batch; it does not replace adjudication, representativeness, licensing, or privacy conclusions.

### Deep Learning: a training candidate must not masquerade as a release artifact early

- A new original engineering-route page reorganizes the tensors, generalization, numerical stability, Transformer, optimization, and training-system material needed by Agent/RAG/Embedding/multimodal work into a goal-oriented route, adding a lifecycle Mermaid and cross-course links.
- A new zero-dependency training-run auditor checks split leakage, test-set model selection, missing lineage, NaN/Inf, and mutable candidate aliases. Generic metrics are required only to be finite, so loss or perplexity is no longer incorrectly rejected.
- Training records now use <code>candidate_id</code>. <code>release_id</code> is produced only in an external release record after quality, governance, and human gates pass. Training candidates, Data Annotation releases, and TTS planned/playable/released states therefore cannot be confused.
- The Deep Learning frozen tree publishes precisely two existing entry points, the original route page, and two offline examples. The remaining 140 D2L reference pages remain traceable local references/stubs and are not loosened by changing frontmatter or a directory prefix.

### Speech: media result, authorization, and release have independent states

- ASR now covers asset format/time base, <code>source_revision</code>, committed transcript revision, empty-reference WER/CER, anonymous speakers, streaming/batch boundaries, and privacy deletion. The offline project rises to schema 1.1 but still does not read real audio or run a model.
- TTS now covers voice-catalog version, language–voice–purpose matching, SSML safety, unknown terminal state, revocation boundaries, quality/disclosure, and voice-cloning risk. Its offline project creates only a plan that does not echo original text/full SSML; it never generates audio.
- TTS uses <code>operation_id</code> consistently for local deduplication and plan correlation. Only a real Provider response may produce and separately record <code>provider_request_id</code>. <code>acl_reference</code> is a structural association only; an external identity/authorization system must decide the real object-level ACL before generation, reading, or release.

## Cross-course terminology and state boundaries

| Term | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| <code>provider_request_id</code> | Diagnostic correlation evidence for one Provider request/response | Local idempotency, business intention, user identity, or an authorization decision |
| <code>operation_id</code> | Local deduplication/correlation key for one stable business operation or planned item | Provider receipt, object ACL, or final outcome |
| <code>source_revision</code> | A controlled input snapshot actually seen by a person or model | Source license, content truth, or current access authorization |
| <code>candidate_id</code> | A training candidate awaiting quality/governance/human gates | An approved <code>release_id</code> or production release |
| <code>release_id</code> | A traceable release artifact with manifest, purpose, and gate | Permanent online representativeness, model forgetting, or business success |
| <code>acl_reference</code> | A reference to an object/scope that an authorization system must decide | An authenticated subject, object-level allow/deny decision, or consent evidence |
| <code>annotation_id</code> / <code>final_label</code> | One initial annotation observation / an adjudicated label after a defined process | Each other, input snapshot, or downstream projection rule |

## Sources, original material, and third-party boundary

All new Chinese-language explanations, flow diagrams, teaching code, fixtures, and tests in this phase are original. Provider documentation, specifications, and papers are used only to check dynamic facts and terminology; text without explicit redistribution terms is not copied. Representative primary sources include:

- [OpenAI Tools](https://developers.openai.com/api/docs/guides/tools), [Anthropic Model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions), [Gemini Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview), [DeepSeek Docs](https://api-docs.deepseek.com/), [Cohere v2 Chat](https://docs.cohere.com/v2/reference/chat), and official links on each Provider page.
- [Google PAIR People + AI Guidebook](https://pair.withgoogle.com/guidebook/), [Cohen 1960](https://doi.org/10.1177/001316446002000104), [Artstein & Poesio 2008](https://aclanthology.org/J08-4004/), [W3C PROV-O](https://www.w3.org/TR/prov-o/), and [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework).
- [PyTorch AMP](https://docs.pytorch.org/docs/stable/amp.html), [PyTorch Reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html), [Transformer](https://arxiv.org/abs/1706.03762), [BERT](https://arxiv.org/abs/1810.04805), and [AdamW](https://arxiv.org/abs/1711.05101).
- [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/), [OpenAI Speech to text](https://developers.openai.com/api/docs/guides/speech-to-text), [OpenAI Text to speech](https://developers.openai.com/api/docs/guides/text-to-speech), [NIST OpenASR](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf), and [ITU-T P.800](https://www.itu.int/rec/T-REC-P.800).

## Verification evidence

| Check | Result |
| --- | --- |
| Deep Learning training auditor | 8 tests: normal, <code>-O</code>, warnings-as-errors, and <code>-O + warnings-as-errors</code> all passed. |
| Data Annotation auditor | 12 tests; all four modes passed. |
| ASR offline evaluation | 69 tests; all four modes passed. |
| TTS offline synthesis plan | 73 tests; all four modes passed. |
| Consolidated project regressions | 162 tests per mode; 648 test executions across four modes all passed. |
| Static checks | AST checks for 8 Python files, 96 Provider-API Python fenced blocks, related JSON/Markdown semantics, and scoped <code>git diff --check</code> passed. |
| Cross-course read-only review | Body wikilinks/embeds in all five scopes parsed; no P1/P2 terminology, learning-order, or public-boundary issue remained. |

## Follow-up queue

1. Run low-risk, non-sensitive Provider integration tests for the target account, region, and exact SDK/model versions. Static verification of dynamic API notes does not replace live-call, cost, rate-limit, or data-retention validation.
2. After connecting the offline ASR/TTS/annotation/training contracts to controlled real systems, validate audio/model quality, identity, object ACL, voice/data authorization, approvals, receipts, and deletion/withdrawal propagation.
3. Review the current framework/device/dependency runnability of the remaining D2L historical notebooks chapter by chapter. They are presently frozen reference snapshots, not validated modern training practice.
4. Inspect new Mermaid diagrams, long tables, and callouts in Obsidian desktop. A Quartz build cannot replace local interaction/rendering checks.

This record covers only Phase 21. It does not mean the long-running <code>/goal</code> is complete.
