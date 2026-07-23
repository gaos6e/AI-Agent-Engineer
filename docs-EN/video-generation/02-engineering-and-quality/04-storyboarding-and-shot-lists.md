---
title: "Storyboarding and Shot Lists"
tags:
  - video-generation
  - storyboarding
  - shot-list
aliases:
  - Storyboard and Shot List
source_checked: 2026-07-22
lang: en
translation_key: 视频生成/02-工程与质量/04-分镜与镜头清单.md
translation_source_hash: 594df13e12e5979d59ed91da1ba2d867ab54036e8a56f36cf1da890f32a2a814
translation_route: zh-CN/视频生成/02-工程与质量/04-分镜与镜头清单
translation_default_route: zh-CN/视频生成/02-工程与质量/04-分镜与镜头清单
---

# Storyboarding and Shot Lists

## Learning objective

Break one creative idea into shot jobs that can each be generated, fail, retry, and be accepted independently.

## The difference between a storyboard and a shot list

A **storyboard** uses sketches or reference frames to convey imagery and narrative pacing. A **shot list** is an executable table that records each shot’s identifier, start/end time, shot scale, subject, action, setting, camera, continuity, audio, and acceptance criteria. You can make a storyboard with text boxes and simple diagrams even if you cannot draw.

First write story beats: what the opening must establish, what happens at the turn, and what state remains at the end. Then break each beat into short shots with one primary action. A transition is not an effect for hiding a logical gap; direction, position, and state should connect plausibly before and after a cut.

## Minimum fields for a shot list

| Field | Question |
| --- | --- |
| `shot_id` | Is it stable and unique, suitable for filenames and retries? Do not confuse it with the requirement’s `source_revision`, a shot’s `transform_id`, or a release’s `release_id`. |
| Time | When does it begin and end on the overall timeline? |
| Picture | What are the subject, action, setting, shot scale, camera position, and movement? |
| Conditions | Which authorized first frames, characters, or object references are used? Does each have an `asset_id`, `source_revision`, `acl_reference`, intended-use restriction, and object-level authorization/ACL? |
| Continuity anchors | What are the color, wardrobe, prop position, movement direction, and lighting state? |
| Sound | What is intended for narration, dialogue, ambience, or silence? |
| Acceptance | Which observable conditions must be satisfied? |
| Fallback | On failure, should the shot be shortened, split, made from a still with motion, or captured manually? |

## A continuity bible

Create a small “continuity bible” for recurring subjects: stable names, appearance attributes, color palette, proportions, props, left/right orientation, ambient light, and forbidden changes. Reference only the anchors that a shot needs, so prompts do not become overly long. After a shot is generated, a person updates the state of the actually selected version and records its `source_revision` and `transform_id`. Unselected candidates do not automatically become facts for the next shot, and must never automatically enter the release chain.

## From storyboard to prompt

Do not use the entire script as one prompt. Each shot prompt should state only what is visible in that shot, including the ending state. For example: `S02, medium follow shot; the robot walks in from the left to the table, holding a blue cup throughout; warm overhead light; when the shot ends, the cup is still in its right hand and the tabletop is empty.` Keep narration and captions on separate tracks so a visual prompt and an audio script do not contaminate each other.

## Common mistakes and troubleshooting

- **Gaps or overlaps in the timeline:** validate numbers before submission.
- **Shot IDs changed with sequence edits:** keep IDs stable and use a separate `sequence_order`.
- **Reference assets lack a declared purpose:** attach rights, allowed-use scope, object-level authorization/ACL, and a revocation/deletion propagation target to every input.
- **Continuity described only as “keep it consistent”:** list concrete anchors so they can be checked.
- **Generating the whole piece at once:** a short-shot workflow makes local retries and human control easier.

## Exercise and self-check

Break “on a rainy night, a car arrives at a station, and a passenger enters the hall” into four shots. Write one continuity anchor each for the car, passenger, rainfall, and movement direction. Then identify one element that can be completed in post-production and should not be forced on the model.

Next: [[video-generation/02-engineering-and-quality/05-generation-and-post-production-assembly-workflow|Generation and Post-Production Assembly Workflow]].

## References

- [Google Cloud video generation prompt guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) (examples of prompts for shots, subjects, actions, and styles; checked 2026-07-22)
- [OpenAI Video generation guide](https://developers.openai.com/api/docs/guides/video-generation) (checked/accessed 2026-07-22)

