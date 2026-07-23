---
title: "Preprocessing and Spatiotemporal Evidence"
tags:
  - multimodal-ai
  - preprocessing
  - grounding
aliases:
  - Multimodal preprocessing
  - Spatiotemporal evidence
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/02-工程与质量/04-预处理与时空证据.md
translation_source_hash: 797481bcb1ba9749503d84a753d8aed91e9237251dbd72953bbb4625f8f64cbd
translation_route: zh-CN/多模态AI/02-工程与质量/04-预处理与时空证据
translation_default_route: zh-CN/多模态AI/02-工程与质量/04-预处理与时空证据
---

# Preprocessing and Spatiotemporal Evidence

## Goal of this lesson

Preserve a path back to the original asset through format validation, transcoding, cropping, frame sampling, and transcription, and understand the loss introduced at each step.

## Immutable originals and derivatives

Store an original asset read-only where authorization permits. Record the following for every derivative:

- `parent_asset_id` and the original hash;
- processor name and version;
- parameters;
- creation time;
- coordinate or time mapping;
- new hash; and
- data classification and retention period.

Do not overwrite the original and retain only the statement “processed.” Without comparable original evidence, reproduction becomes difficult.

## Image preprocessing

A typical order is:

1. Detect the actual format and decode it.
2. Apply EXIF orientation while recording the transformation.
3. Normalize the color space.
4. Scale or tile according to the task.
5. Produce region boxes through OCR or object detection.
6. Map boxes back to original-image coordinates.

Use normalized boxes `(x_min, y_min, x_max, y_max)` in the range 0–1, while also retaining original pixel dimensions. After cropping, reverse-transform evidence boxes through the offset and scale.

## Audio preprocessing

After decoding, record the original sample rate, channels, and duration. Speech tasks may resample, separate channels, use VAD (voice activity detection), and segment audio. Identify every segment with `start_ms` and `end_ms` on the original timeline.

VAD may incorrectly remove quiet speech or pauses; denoising may remove important background events; merging channels may confuse speakers. Retain parameters and references to replayable segments.

## Video preprocessing

Sampling one frame per second can work for slow scenes but misses brief actions. A safer combination is:

- uniform frame sampling for global coverage;
- scene-change detection;
- denser sampling triggered by OCR or motion;
- audio-track and caption extraction; and
- alignment on one millisecond timeline.

Record `timestamp_ms` for a key frame rather than only “frame 42,” because transcoding can change frame numbering. When using a segment, record its original video start and end times.

## Documents and layout

Retain `page`, `bounding_box`, `reading_order`, and element type. Table cells need row and column relationships, and captions need to remain associated with images. For OCR text, retain the text, confidence, language, and region; do not silently treat low-confidence characters as true.

## Evidence ledger

~~~json
{
  "claim_id": "C-3",
  "asset_id": "video-1",
  "source_revision": "sha256:record-at-runtime",
  "evidence": [
    {"kind": "video_interval", "start_ms": 72000, "end_ms": 78000},
    {"kind": "frame_region", "timestamp_ms": 74500,
     "box": [0.10, 0.20, 0.62, 0.55]}
  ],
  "transform_chain": ["extract-audio-v2", "sample-scene-v1"]
}
~~~

A model conclusion must cite verifiable evidence rather than return only free text.

### A valid pointer and a supported conclusion are different things

First perform **binding validation**: do the asset, revision, coordinate system, time range, and `transform_chain` exist and agree? Then perform **evidence-entailment validation**: does the region or segment actually support the claim? Deterministic code can reject invalid IDs, out-of-bounds boxes, and stale references in the first step. The second needs annotation, human spot checks, or controlled evaluation. A clickable timestamp does not automatically prove the conclusion is correct.

## Consistency checks

- `start < end`, and neither exceeds the asset duration.
- Coordinates are within 0–1 or pixel bounds.
- A derivative's `parent_asset_id` exists.
- Transformation-chain parameters are complete.
- Multiple caption and audio tracks use consistent time bases.
- Asset hash matches the processing record.

## Common errors

- **Making a coarse summary first to save tokens**: the summary can omit detail needed by a later question.
- **Confusing coordinate systems**: using old coordinates after rotation or crop. Fix a coordinate convention and test reverse transforms.
- **Time drift**: audio and video lose synchronization after independent transcoding. Verify with the original timeline and calibration points.
- **Retaining only OCR text**: tables, layout, and low-confidence regions disappear.

## Exercise and self-check

Design a video-segment record that lets an answer to “when does the price list appear?” return both a time and region. Self-check: if frames are sampled every five seconds, is a one-second event guaranteed to be visible? How would you design triggered supplementary sampling?

## Next step

Continue with [[multimodal-ai/02-engineering-and-quality/05-multimodal-prompting-and-structured-output|Multimodal Prompting and Structured Output]].

## References

- [Google Gemini API: Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) (accessed 2026-07-22)
- [W3C WebVTT](https://www.w3.org/TR/webvtt1/) (accessed 2026-07-22)
