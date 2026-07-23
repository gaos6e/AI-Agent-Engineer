---
title: "Multimodal AI Learning Path"
tags:
  - ai-agent-engineer
  - multimodal-ai
  - learning-path
aliases:
  - Multimodal AI index
  - Multimodal learning
source_checked: 2026-07-22
ai_learning_stage: 8. Extended applications and complex collaboration
ai_learning_order: 48
ai_learning_schema: 2
ai_learning_id: multimodal-ai
ai_learning_domain: multimodal
ai_learning_catalog_order: 4800
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 410
ai_learning_track_rag_kind: optional
ai_learning_track_multimodal_realtime_order: 200
ai_learning_track_multimodal_realtime_kind: core
content_origin: original
content_status: dynamic
lang: en
translation_key: 多模态AI/00-目录.md
translation_source_hash: 5dd715d512a9273498a1b0a7febddf92130c5e9c3ee95d92439368bfc9c3a155
translation_route: zh-CN/多模态AI/00-目录
translation_default_route: zh-CN/多模态AI/00-目录
---

# Multimodal AI

> Sources were accessed on 2026-07-22. The media types, sizes, durations, sampling, and billing rules supported by models change quickly. Before integration, recheck the model page and API documentation for the chosen provider. This course does not treat a current limit as a permanent rule.

## About this knowledge base

A modality is a form in which information is represented: text, images, audio, video, depth, or sensor data. Multimodal AI is not fundamentally about uploading different files together. It preserves the structure, time, space, and provenance of each input so a model can align evidence and produce verifiable results. This course starts with representation and alignment, then covers input contracts, fusion architectures, preprocessing, prompting and structured output, evaluation, cost, and safety.

## Where this course fits in the overall route

Enter this course after understanding the basic capabilities of modern LLMs; it is the general entry point for applications with complex inputs. Fill in embeddings, prompting and context, Agent runtime, and production knowledge as each task requires—none needs to be finished in full first. [[ocr/00-index|OCR]], [[speech-recognition/00-index|Speech Recognition]], [[text-to-speech/00-index|Text to Speech]], [[image-generation/00-index|Image Generation]], and [[video-generation/00-index|Video Generation]] each go deeper into a particular perception or generation capability. [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]] then combines audio, turns, user interruption, tools, and session state into end-to-end systems.

## Learning objectives

- Distinguish raw media, feature representations, shared embeddings, alignment, and genuine cross-modal reasoning.
- Define explicit input contracts and provenance records for images, audio, video, and documents.
- Understand the trade-offs among early fusion, late fusion, cross-attention, and shared spaces.
- Preserve spatial and temporal evidence such as image regions, page numbers, timestamps, and audio-video synchronization.
- Design prompts with structured output, evidence references, missing-modality rules, and uncertainty rules.
- Evaluate perception, alignment, reasoning, task success, latency and cost, privacy, and safety as separate layers.
- Complete an offline evidence-routing project that uses synthetic metadata only.

## Prerequisites

- Understand vectors, cosine similarity, and retrieval from [[vector-fundamentals/00-index|Vector Fundamentals]] and [[embeddings/00-index|Embeddings]].
- Be able to read and write Python and JSON, and understand MIME types, file sizes, and hashes.
- Understand [[prompt-engineering/00-index|Prompt Engineering]], [[context-engineering/00-index|Context Engineering]], and structured output.

## Recommended order

1. [[multimodal-ai/01-foundations-and-architecture/01-modalities-representations-and-alignment|Modalities, representations, and alignment]] — build intuition for and identify the limits of shared representations and alignment.
2. [[multimodal-ai/01-foundations-and-architecture/02-image-text-audio-and-video-input-contracts|Image, text, audio, and video input contracts]] — move from file types to verifiable input objects.
3. [[multimodal-ai/01-foundations-and-architecture/03-fusion-architecture-intuition|Fusion architecture intuition]] — choose a shared space, early or late fusion, or cross-modal fusion for the task.
4. [[multimodal-ai/02-engineering-and-quality/04-preprocessing-and-spatiotemporal-evidence|Preprocessing and spatiotemporal evidence]] — retain page, region, and temporal provenance during compression and sampling.
5. [[multimodal-ai/02-engineering-and-quality/05-multimodal-prompting-and-structured-output|Multimodal prompting and structured output]] — state input roles, evidence scope, and output schema.
6. [[multimodal-ai/02-engineering-and-quality/06-multimodal-quality-evaluation|Multimodal quality evaluation]] — separate perception, alignment, reasoning, and end-to-end task metrics.
7. [[multimodal-ai/02-engineering-and-quality/07-latency-cost-privacy-and-safety|Latency, cost, privacy, and safety]] — establish routing, budgets, data minimization, and media-source strategy.
8. [[multimodal-ai/03-project-and-self-assessment/08-offline-multimodal-evidence-routing-project|Offline Multimodal Evidence Routing Project]] — validate inputs, route them, and plan evidence with a synthetic manifest.

## Hands-on project

Start with [[multimodal-ai/03-project-and-self-assessment/08-offline-multimodal-evidence-routing-project|Offline Multimodal Evidence Routing Project]]. The script never reads real images, audio, or video. It checks a synthetic media manifest and outputs the processor, cost units, privacy action, and expected evidence-location method.

## Mastery checklist

- Can explain why “nearby shared vectors” does not mean factual consistency or causal understanding.
- Can write a media, spatial or temporal, provenance, and output contract for an image-text or audio-video task.
- Can explain what frame sampling, cropping, transcription, and compression can each lose.
- Can design an evaluation set that includes missing modalities, modality conflicts, text-only baselines, and adversarial samples.
- Can decide format validation, minimization, authorization, budget, and retention before sending media.
- Can point every important conclusion in output to a page number, region box, or time interval.

## Relationship to other knowledge bases

- [[embeddings/00-index|Embeddings]] provides shared-representation and similarity foundations, but multimodal applications also require alignment and evidence location.
- [[rag/00-index|RAG]] can retrieve image, audio, video, or document segments. Every segment entering the retrieval store must retain its original asset, page/region/time, version, ACL, and deletion status; it must not degrade into a caption detached from provenance.
- [[document-parsing/00-index|Document Parsing]], [[ocr/00-index|OCR]], and [[speech-recognition/00-index|Speech Recognition]] turn media into retrievable structures.
- [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]] owns streaming sessions, VAD and turns, barge-in, backpressure, tool correlation, and disconnect recovery; it does not repeat this course's representation foundation.
- [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]] can coordinate specialists for different modalities, but adds complexity only when one multimodal model or workflow is insufficient.
- [[evaluation-framework/00-index|Evaluation Framework]], [[ai-safety/00-index|AI Safety]], and [[privacy-computing/00-index|Privacy Computing]] carry the system-level quality and governance work.

## Primary references

- Radford et al., [Learning Transferable Visual Models From Natural Language Supervision (CLIP)](https://arxiv.org/abs/2103.00020) (original paper)
- Girdhar et al., [ImageBind: One Embedding Space To Bind Them All](https://arxiv.org/abs/2305.05665) (original paper)
- [Google Gemini API: File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) and [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) (accessed 2026-07-22)
- Yue et al., [MMMU](https://arxiv.org/abs/2311.16502) and [MMMU-Pro](https://arxiv.org/abs/2409.02813) (original evaluation papers)
- [C2PA Specifications 2.4](https://spec.c2pa.org/specifications/specifications/2.4/index.html) (April 2026; accessed 2026-07-22)
- [W3C WebVTT](https://www.w3.org/TR/webvtt1/) (accessed 2026-07-22; the current page is a Candidate Recommendation Draft dated 2026-05-20)
