---
title: "Fusion Architecture Intuition"
tags:
  - multimodal-ai
  - fusion
  - architecture
aliases:
  - Multimodal fusion
  - Cross-modal architectures
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/01-基础与架构/03-融合架构直觉.md
translation_source_hash: 14eb3b3697d99055063dd87a8c6cfd2e36ac93945a5816f52d601e1e354cec17
translation_route: zh-CN/多模态AI/01-基础与架构/03-融合架构直觉
translation_default_route: zh-CN/多模态AI/01-基础与架构/03-融合架构直觉
---

# Fusion Architecture Intuition

## Goal of this lesson

Understand when and at what granularity different modalities interact, and choose a fusion strategy based on task, data, and latency.

## What fusion solves

After encoding modalities independently, a system must answer:

- Which text passage corresponds to which image region?
- Which audio event is synchronized with which video moment?
- How should it reason when a modality is missing or conflicts with another?
- How can joint evidence become structured output?

Fusion is not simply concatenating files. It determines the timing, granularity, and compute cost of information exchange.

## Early fusion

Place tokens or features from different modalities into a common model early, allowing attention to learn fine-grained interactions.

Strengths: it can represent complex relationships such as region-to-word and frame-to-speech. Weaknesses: long sequences, high compute and memory cost, and demanding requirements for data alignment and positional encoding. Use it for tasks that require joint reasoning over detail.

## Late fusion

Each modality independently produces a prediction or score, and a rule or model combines them at the end.

~~~text
final_score = w_text * text_score + w_image * image_score
~~~

Strengths: modules can be replaced independently, missing modalities and caching are easier, and debugging is clear. Weakness: relationships lost during independent encoding cannot be recovered at the end. It suits multi-channel classification, risk scoring, or systems with mature unimodal models.

## Intermediate fusion and cross-attention

Each encoder first extracts a representation, then cross-attention lets one modality query another. This balances fine-grained interaction with computational cost. Visual question answering often needs the text question to attend to a specific image patch; video question answering also needs temporal position.

## Shared embeddings and retrieval-based fusion

Map different modalities to a shared space, retrieve candidates first, then let a generative model analyze a small amount of evidence. This suits large media collections:

~~~text
text question -> shared vector -> retrieve images/segments -> generator answers from evidence
~~~

It reduces generative context, but retrieval can miss key evidence, so evaluate recall separately.

## Cascaded systems

Production systems commonly route work as follows:

1. A lightweight metadata or text model decides which modalities are needed.
2. OCR, ASR, or vision models extract candidates.
3. A multimodal model processes only high-value segments.
4. Rules validate the structure and evidence.

This is more controllable than “send every medium to the largest model at once,” and makes privacy minimization easier.

## Missing and conflicting modalities

Use modality dropout—randomly omitting a modality—during training and evaluation to see whether a system recognizes what it lacks. A fusion component should distinguish “there is no audio,” “audio parsing failed,” and “the audio contains no target event.”

When captions say “red light” but the image shows green, output both the conflict and its sources rather than averaging them into a vague conclusion. High-risk tasks should use rules or human arbitration.

## Selection table

| Requirement | Preferred approach |
| --- | --- |
| Cross-media search | Shared embeddings |
| Fine-grained image-text Q&A | Early fusion or cross-attention |
| Independent multi-sensor scoring | Late fusion |
| Very long video | Segmented retrieval plus segment fusion |
| Privacy-sensitive work | Local extraction plus minimal evidence sent |
| Frequently missing modalities | Modular late or intermediate fusion |

## Exercise and self-check

Choose a fusion approach for “determine whether a customer-service call recording and ticket text show that the issue was resolved,” and explain the fallback when the recording is missing. Self-check: why cannot late fusion restore tone or overlapping speech lost by ASR?

## Next step

Continue with [[multimodal-ai/02-engineering-and-quality/04-preprocessing-and-spatiotemporal-evidence|Preprocessing and Spatiotemporal Evidence]].

## References

- Radford et al., [CLIP](https://arxiv.org/abs/2103.00020)
- Girdhar et al., [ImageBind](https://arxiv.org/abs/2305.05665)
