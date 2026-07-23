---
title: "Modalities, Representations, and Alignment"
tags:
  - multimodal-ai
  - representation
  - alignment
aliases:
  - Multimodal representations
  - Cross-modal alignment
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/01-基础与架构/01-模态、表示与对齐.md
translation_source_hash: d75b0c616e43971417c9778ca3f41148dbb9df799f0575fc73452d83c93370d5
translation_route: zh-CN/多模态AI/01-基础与架构/01-模态、表示与对齐
translation_default_route: zh-CN/多模态AI/01-基础与架构/01-模态、表示与对齐
---

# Modalities, Representations, and Alignment

## Goal of this lesson

Understand how raw signals become vectors or tokens, what cross-modal alignment is, and which capabilities alignment does not guarantee.

## What is a modality?

A modality is an information carrier together with its statistical structure:

- Text is a discrete sequence of tokens, with grammar and order.
- Images are pixels on a spatial grid, where location, scale, and color matter.
- Audio is a waveform changing over time, where sample rate, channels, and spectrum matter.
- Video is a time-indexed image sequence, often with a synchronized audio track.
- Sensors such as depth, thermal imaging, and IMU data have their own units and sampling frequencies.

A filename extension is only a clue about the container, not the modality content. A PDF can contain text, scanned images, tables, and pictures; a video may contain images only or only usable audio.

## From raw signal to representation

Models commonly use encoders to convert input into vector sequences:

~~~text
text tokens          -> text encoder   -> text vectors
image patches        -> vision encoder -> region/global vectors
audio frames         -> audio encoder  -> temporal vectors
video frames + audio -> encoders       -> sequential vectors
~~~

A representation is compression for computation. A global image vector is useful for coarse retrieval but may lose “small text in the upper-left corner.” Per-frame vectors preserve temporal change but cost more.

## Shared spaces and alignment

Alignment brings related content close in a shared vector space. CLIP, for example, uses contrastive learning on image-text pairs so correct pairs receive high similarity and incorrect pairs lower similarity. The minimal intuition is:

~~~text
sim(image, text) = cosine(image_vector, text_vector)
~~~

The training objective increases the gap between matched and unmatched similarity. At inference, it can retrieve images with text or perform zero-shot classification. ImageBind demonstrates a research path that maps images, text, audio, depth, thermal images, and IMU data into a joint space.

## Alignment is not understanding

Nearby vectors only show that the model learned a statistical association. They do not automatically demonstrate:

- the exact count, location, or relationship of objects in an image;
- the causal order of events in a video;
- the real identity of an audio speaker;
- that a text description is unbiased or correct; or
- which modality supplies the true evidence when modalities conflict.

Cross-modal retrieval can also exploit shortcuts: a model may match background, subtitle watermark, or dataset style without recognizing the central object.

## Three alignment granularities

1. **Global alignment**: a whole image and a whole text passage; useful for search and classification.
2. **Local alignment**: an image region and a phrase, or an audio segment and a word; useful for locating evidence.
3. **Temporal alignment**: video segments, audio, and captions correspond on a timeline; useful for event understanding.

The task determines the representation granularity. If output must say “the evidence is at 01:12–01:18,” retaining only one global video vector is insufficient.

## A simple, verifiable example

Suppose an image vector is normalized to (0.8, 0.6), and two text vectors are (1, 0) and (0, 1). Their cosine similarities are 0.8 and 0.6. The model favors the first text, but this is a relative match score, not an 80% factual probability.

## Common errors and diagnosis

- **Treating similarity as a confidence probability**: before calibration, use it only for ranking comparisons, not as a probability.
- **Ignoring modality granularity**: retaining only global vectors for a localization task. Return to the evidence granularity needed for acceptance.
- **Looking only at averages**: slice results by image type, language, noise, and population to check bias.
- **Treating a transcript as the original audio**: transcription loses timbre, pauses, background sound, and speaker information.

## Exercise and self-check

For “find the moment in a training video when the refund policy is discussed,” name at least three representations and their purposes. Self-check: does a transcript match for “refund” prove that the image is showing the refund workflow?

## Next step

Continue with [[multimodal-ai/01-foundations-and-architecture/02-image-text-audio-and-video-input-contracts|Image, Text, Audio, and Video Input Contracts]].

## References

- Radford et al., [CLIP](https://arxiv.org/abs/2103.00020)
- Girdhar et al., [ImageBind](https://arxiv.org/abs/2305.05665)
