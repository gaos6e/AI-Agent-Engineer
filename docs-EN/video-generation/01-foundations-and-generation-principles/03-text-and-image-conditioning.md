---
title: "Text and Image Conditioning for Video Generation"
tags:
  - video-generation
  - conditional-generation
  - prompting
aliases:
  - Video conditioning inputs
source_checked: 2026-07-22
lang: en
translation_key: 视频生成/01-基础与生成原理/03-文本与图像条件.md
translation_source_hash: 43c1753bbe160ca8301f5b1e5cf53af3f57e798f6764d4a987ad6b72a59e097e
translation_route: zh-CN/视频生成/01-基础与生成原理/03-文本与图像条件
translation_default_route: zh-CN/视频生成/01-基础与生成原理/03-文本与图像条件
---

# Text and Image Conditioning for Video Generation

## Learning objective

Choose text, a first frame, a last frame, reference assets, or an existing clip according to the control goal, rather than submitting every input to a model indiscriminately.

## A shot template for text prompts

Use one main sentence to cover “shot/camera — subject — action — environment — lighting — pacing”:

> Locked-off medium shot; a small orange robot places a blue cup in the center of a wooden table; a morning kitchen with soft side-window light; one slow placement only, ending with the hand away from the cup.

This is more testable than “cinematic, epic, 8K.” If spoken content or exact text is required, put it in post-production audio and caption layers first; do not assume every video model can spell reliably or synchronize long dialogue.

## When to use visual conditioning

- **First frame / image-to-video:** when the initial composition must be fixed or a static design must start moving.
- **First and last frame:** when the endpoint must be explicit, while the intermediate motion still needs review. Not every provider supports it.
- **Character or object reference:** when identity features matter; verify consent and asset rights.
- **Video extension:** when an existing clip needs to continue; check boundary frames, movement direction, and audio continuity.
- **Video editing:** when original motion or structure is preserved while a local area changes; state protected regions and allowed changes.

Provider input types, file sizes, durations, person-related restrictions, and retention policies may change. A business job records only the intent (for example, `conditioning.kind = first_frame`); the adapter queries capability at run time. If capability is not available, it must return a structured “not executable” result rather than silently falling back to text-only generation.

## Prioritizing conflicting conditions

Write a priority for each condition: rights and safety gates come first; then identity or product attributes that must be preserved; then action and composition; finally style preferences. For example, if a first frame is a night scene and the text requests noon, a human must decide which overrides the other. Do not wait for the model to “compromise” and discover the result is unusable.

## A reproducible input inventory

For each reference file, record `asset_id`, `source_revision`, `acl_reference`, a relative identifier, SHA-256, rights status, intended-use restriction, crop/color processing, upload time, and deletion policy. Object-level authorization/ACL must come before preview, scoring, model access, and post-production export. On revocation or deletion, propagate through input, shot `transform_id`, and release `release_id`. Never put real faces, unauthorized materials, or customer secrets in an example repository. Current OpenAI and Google documentation both show text/image conditioning, but their concrete capabilities differ and keep changing, so they are evidence only as of the integration date.

## Common mistakes and troubleshooting

- **The person in the reference image conflicts with the text in age or clothing:** fix the requirement first rather than repeatedly gambling on a prompt.
- **Writing the action but not the end state:** add a visible state that must hold when the shot ends.
- **Assuming a reference image locks identity:** still perform human review across frames and across shots.
- **Turning a restricted person input into a description:** follow service rules and applicable law; do not bypass safety mechanisms.

## Exercise and self-check

For “turn a product poster into a 6-second opening animation,” design two conditioning plans: text-only and first-frame-conditioned. For each, list strengths, failure risks, input rights, and acceptance criteria.

Next, move into production planning: [[video-generation/02-engineering-and-quality/04-storyboarding-and-shot-lists|Storyboarding and Shot Lists]].

## References

- [OpenAI Video generation guide](https://developers.openai.com/api/docs/guides/video-generation) (checked/accessed 2026-07-22; includes the planned future shutdown)
- [Google Cloud: generate videos using first and last frames](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-first-and-last-frames) (checked 2026-07-22)

