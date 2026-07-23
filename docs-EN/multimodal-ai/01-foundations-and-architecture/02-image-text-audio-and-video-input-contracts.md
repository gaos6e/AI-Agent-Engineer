---
title: "Image, Text, Audio, and Video Input Contracts"
tags:
  - multimodal-ai
  - media-input
  - contracts
aliases:
  - Multimodal input contracts
  - Media input design
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/01-基础与架构/02-图文音视频输入合同.md
translation_source_hash: 59beebc251f0ac1b38ebf0fe776bf3a044905ae5ed858ab2b0864e82b08e6a9d
translation_route: zh-CN/多模态AI/01-基础与架构/02-图文音视频输入合同
translation_default_route: zh-CN/多模态AI/01-基础与架构/02-图文音视频输入合同
---

# Image, Text, Audio, and Video Input Contracts

## Goal of this lesson

Start not with an SDK call, but by defining the media object, the evidence a task needs, permitted processing, and failure conditions.

## General media manifest

Record at least the following for every asset:

~~~json
{
  "asset_id": "A-001",
  "declared_mime": "video/mp4",
  "detected_mime": "video/mp4",
  "bytes": 1250000,
  "sha256": "placeholder-not-a-real-file",
  "source": {
    "kind": "user_upload",
    "locator": "opaque-server-side-id",
    "revision": "record-at-runtime"
  },
  "authorization": {
    "purpose": "answer_this_request",
    "policy_version": "record-at-runtime"
  },
  "classification": "personal",
  "retention_policy": "record-at-runtime",
  "language_hint": "zh-CN",
  "duration_ms": 42000,
  "contains_personal_data": true
}
~~~

In a real system, compute `sha256` over the complete byte stream; never use a placeholder. It binds bytes, not authenticity. The course project operates only on synthetic metadata. `declared_mime` comes from the request, while `detected_mime` should come from a trusted parser. When they conflict, reject or quarantine the asset. After transcoding, cropping, or unpacking, record a new hash, `parent_asset_id`, and transform version for the derivative; do not reuse the original hash.

`classification`, permitted processing locations, and `authorization` must be derived from an authenticated server-side asset record, object-level authorization or ACL, and policy evaluation—not from a filename, EXIF, remote-URL parameters, or caller-supplied JSON. When permission is unknown, deny egress by default and require human confirmation or a restricted local process.

## Image input

Consider dimensions, orientation, color space, transparency, multipage containers, text size, and regions of interest. A task may need:

- whole-image semantics;
- OCR text;
- region boxes and object relationships;
- chart coordinates and legends; or
- a mapping between original and cropped images.

Downscaling reduces cost but can make small text unreadable. Preserve transform parameters after rotation or crop so an evidence box can be mapped back to the original image.

## Audio input

Consider sample rate, channels, bit depth, duration, language, speaker, and timeline. Processing can yield transcription, speaker segments, event labels, or acoustic features. Merging stereo channels, downsampling, and denoising all alter evidence and must be recorded.

Transcription is not a sufficient representation for every task. Judging an alarm, a music segment, emotion, or overlapping speakers requires retaining audio cues.

## Video input

Video contains space, time, and sometimes audio. An input contract should state:

- whether to process the entire video or a specified time window;
- frame-sampling strategy and frame rate;
- whether to extract audio and captions;
- how to align frame timestamps, audio time, and captions;
- whether fast motion or on-screen text requires denser sampling; and
- which time span a conclusion must cite.

As of 2026-07-22, Google's Gemini video-understanding documentation still publishes its File API's default frame-sampling, audio-processing, and media-resolution behavior, and explicitly notes that these rates can change. That is a vendor processing snapshot, not an evidence contract. A critical task must not assume internal sampling is lossless; preprocess, record sampling parameters, and validate against the target task.

## Documents and mixed input

A PDF, presentation, or web page may contain text, tables, images, and reading order together. Retain page numbers, layout boxes, heading hierarchy, and attachment relationships. Extracting plain text alone can lose which column a number belongs to.

## Choosing an input method

Common APIs offer inline bytes, uploaded files, and remote URIs. Choose based on size, reuse, data residency, and retention—not convenience. Vendor limits change, so configure them in an adapter rather than scatter them through business logic.

## Input-failure policy

- Unsupported format: return `supported_types`; do not disguise an extension automatically.
- Asset too large or too long: request segmentation or downsampling, and explain likely loss.
- Required modality missing: refuse conclusions that depend on it.
- Corrupted media: quarantine it and record the parsing error.
- Unauthorized personal data: do not send it to an external model.
- Classification or authorization cannot be confirmed from a trusted record: stop egress, return `authorization_required`, or escalate to a person; do not downgrade based on a caller's self-reported “public” label.
- Modalities conflict: show the evidence side by side and escalate to a person; do not silently choose one.

## Exercise and self-check

Write an input contract for “upload a meeting video and produce a timestamped decision list.” Self-check: with only automatic captions, can you determine a numeric value in a shared-screen table? Does an accessible remote URL mean long-term retention is allowed?

## Next step

Continue with [[multimodal-ai/01-foundations-and-architecture/03-fusion-architecture-intuition|Fusion Architecture Intuition]].

## References

- [Google Gemini API: File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) (accessed 2026-07-22)
- [Google Gemini API: Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) (accessed 2026-07-22)
- [Google Gemini API: Audio understanding](https://ai.google.dev/gemini-api/docs/audio) (accessed 2026-07-22)
