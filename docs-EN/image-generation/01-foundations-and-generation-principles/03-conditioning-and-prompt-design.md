---
title: "Conditioning and Prompt Design for Image Generation"
tags:
  - image-generation
  - prompting
  - conditioning
aliases:
  - Image prompt design
source_checked: 2026-07-22
lang: en
translation_key: 图像生成/01-基础与生成原理/03-条件控制与提示设计.md
translation_source_hash: 1280cee144d49192950275d075a0ffb0b1fcc39f822fb699eb453072186cdf6f
translation_route: zh-CN/图像生成/01-基础与生成原理/03-条件控制与提示设计
translation_default_route: zh-CN/图像生成/01-基础与生成原理/03-条件控制与提示设计
---

# Conditioning and Prompt Design

## Goal of this lesson

Break a creative description into conditions a model can execute, a reviewer can check, and a version system can compare. A prompt is not a magic spell; it is part of a task specification.

## A six-slot prompt structure

Fill the following slots from concrete to abstract:

1. **Purpose and canvas**: e-commerce hero image, teaching illustration, or storyboard; ratio and safe area.
2. **Subject**: who or what, number, appearance, and relative position.
3. **Action and relationships**: what the subject is doing and how subjects interact.
4. **Environment and time**: place, weather, era, and background complexity.
5. **Camera and light**: shot size, viewpoint, focus, and key-light direction.
6. **Visual language**: medium, palette, and texture; use describable features and avoid unnecessary imitation of living artists.

For example: “A 4:5 portrait image for the cover of a Chinese tutorial; a white robotic arm places a blue sample tube into a rack in a bright laboratory; medium shot, slightly top-down, subject centered low; cool-white key light with a little blue rim light; clean vector illustration; reserve the upper 25% as a clear title area; generate no text, logos, or people.”

## Hard constraints, soft preferences, and acceptance

- **Hard constraints**: must be satisfied or the candidate is rejected, such as subject count, prohibited logos, or title safe area.
- **Soft preferences**: desirable but negotiable when in conflict, such as “warm but restrained.”
- **Acceptance criteria**: how a person or program will judge, such as “both sample tubes are visible” and “no readable brand identifier.”

Do not treat a negative prompt as a universal filter. A model may not understand complex negation or may refuse a request before safety filtering. Put critical prohibitions both in pre-request policy checks and in post-generation human review.

## Reference inputs and edit controls

A reference image can supply identity, layout, color, or style, but state which part is referenced and whether use rights exist. For a local edit, also record `asset_id`, `source_revision`, original-image/mask hash, allowed-change region, protected region, target description, and acceptance comparison. Object-level authorization/ACL must apply before any candidate scoring or model read. If a product supports structural-control maps or strength parameters, treat them as provider-specific capabilities: probe capability instead of hard-coding them into generic business logic.

## Iterate instead of piling on words

Change only one major variable at a time: confirm layout, then subject, then style and text. For every round, retain `prompt_version`, reason for change, output ID, score, and the execution chain as `transform_id`. Assign `release_id` only when a candidate enters the publication queue; do not infer versions from filenames. If the same defect does not improve for several rounds, change task decomposition—for example, generate a text-free background first and add typography with a layout tool—instead of endlessly appending adjectives.

## Common errors and diagnosis

- **Contradiction**: “minimal background” while requiring ten props. Establish priority first.
- **Not observable**: “more premium.” Rewrite it as visible palette, material, empty space, camera, and similar features.
- **Changing too much at once**: you cannot know which change worked. Keep a single-variable experiment table.
- **Treating the prompt as a safety policy**: enforce safety rules independently.

## Exercise and self-check

Rewrite “make a beautiful AI poster” as a six-slot specification. Mark three hard constraints, three soft preferences, and four acceptance criteria. Then explain how you would decompose the workflow if text generation is unreliable.

Continue with [[image-generation/02-engineering-and-quality/04-composition-style-text-and-editing|Composition, Style, Text, and Editing]].

## References

- [OpenAI GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) (recheck current product capability on integration day; source checked 2026-07-22)
- [[prompt-engineering/00-index|Prompt Engineering]]
