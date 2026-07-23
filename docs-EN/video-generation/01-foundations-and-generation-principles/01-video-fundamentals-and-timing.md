---
title: "Video Fundamentals and Timing"
tags:
  - video-generation
  - foundations
aliases:
  - Frame rate, duration, and shots
source_checked: 2026-07-14
lang: en
translation_key: 视频生成/01-基础与生成原理/01-视频基本量与时序.md
translation_source_hash: 858148da325fe14bbddf0b583d3b85fb5f4d4ac8dad3fa8cb0edcbecdfea1d57
translation_route: zh-CN/视频生成/01-基础与生成原理/01-视频基本量与时序
translation_default_route: zh-CN/视频生成/01-基础与生成原理/01-视频基本量与时序
---

# Video Fundamentals and Timing

## Learning objective

Read the minimum numeric and narrative units in a video job package, without conflating resolution, frame rate, bitrate, and “smoothness.”

## From frames to shots

A **frame** is an image at one moment in time; the **frame rate** (frames per second, FPS) is the number of frames displayed per second. At a constant frame rate, an 8-second, 24-FPS clip has $8\times24=192$ temporal positions. Frame rate controls motion sampling, not image quality; simply duplicating low-frame-rate footage at a higher frame rate does not create real motion information.

**Resolution** is the pixel width and height of each frame. The **aspect ratio** determines the canvas shape, and the **bitrate** roughly describes the amount of encoded data per unit of time. Final file size also depends on the encoder, scene complexity, audio, and container, so resolution alone cannot predict it.

A **shot** is one continuous take or apparently continuous image sequence. A **scene** is a group of shots in the same time and place. A **sequence** can span scenes to fulfill one narrative goal. Generation models are better suited to short jobs with one primary action and one shot intention. Packing “a person enters, sits down, remembers childhood, and flies to the moon” into one request often produces discontinuities.

## Basic timeline constraints

Every shot needs `start_seconds` and `end_seconds`. Establish these engineering rules before production:

- Shots do not overlap unless a dissolve layer is intentionally designed.
- The timeline covers the target duration without unintentional gaps.
- Caption, narration, and sound-effect timestamps fall within the valid range.
- The project uses one time base, with an explicit rounding rule when decimal seconds are converted to frames.

For example, at 24 FPS, `2.5 s` is around frame 60. If an editing system numbers frames from zero, whether a boundary is half-open or closed changes one frame; the job package needs a consistent convention.

## Shot language is a requirement, not decoration

- Shot scale: a wide shot establishes context, a medium shot shows action, and a close-up emphasizes detail.
- Camera angle: eye level, high angle, and low angle affect the perceived relationship.
- Camera movement: locked-off, push-in, pull-back, pan, truck, and follow. A shot should usually have one primary movement.
- Focus: a sharp subject and blurred background are choices, not synonyms for a “cinematic” result.

## Common mistakes and troubleshooting

- **Treating FPS as a generation-quality switch:** first verify native product support, then convert according to the post-production specification.
- **Adding durations without checking the overall duration:** inspect gaps between shots and time occupied by transitions.
- **Confusing 16:9 with pixel dimensions:** the same aspect ratio does not imply the same sharpness or encoding.
- **Putting multiple conflicting camera moves in one shot:** split the shot or specify a primary and secondary movement.

## Exercise and self-check

Break a 12-second “robot serves coffee” clip into three shots. For each, write a start/end time, shot scale, one main action, and one camera movement. Calculate the theoretical frame count at 25 FPS, then explain why the finished file may not contain exactly that number of decodable frames.

Next: [[video-generation/01-foundations-and-generation-principles/02-generation-principles-and-temporal-consistency|Generation Principles and Temporal Consistency]].

## References

- [FFmpeg Documentation](https://ffmpeg.org/ffmpeg.html) (stream, mapping, and processing concepts; checked 2026-07-14)
- [WebVTT specification](https://www.w3.org/TR/webvtt1/)
