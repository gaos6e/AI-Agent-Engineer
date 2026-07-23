---
title: "Video Quality, Motion, and Identity-Consistency Evaluation"
tags:
  - video-generation
  - evaluation
  - consistency
aliases:
  - Video generation acceptance
source_checked: 2026-07-22
lang: en
translation_key: 视频生成/02-工程与质量/07-质量运动与身份一致性评测.md
translation_source_hash: 3f7dff995ac410dfe4906dde6c1171ff744bbe9691e9b10151cb0cc2b3a62ade
translation_route: zh-CN/视频生成/02-工程与质量/07-质量运动与身份一致性评测
translation_default_route: zh-CN/视频生成/02-工程与质量/07-质量运动与身份一致性评测
---

# Video Quality, Motion, and Identity-Consistency Evaluation

## Learning objective

Use frame-level, shot-level, and finished-piece review to detect problems at different scales, while understanding the limits of automated metrics.

## Three levels of review

### Sampled frame inspection

Extract frames at the start, middle, end, and points of fast motion or occlusion. Check shapes, limbs, text, logos, backgrounds, and sensitive content. A valid frame does not prove the video is valid, but it can quickly locate visual breakdowns.

### Playback within a shot

Play at normal speed, slow speed, and in a loop. Check whether motion is continuous, speed is plausible, contact relationships hold, texture flickers, identity drifts, the camera moves as requested, and audio/video are synchronized. Record the time of an issue instead of merely writing “it looks a little strange.”

### Finished piece and cross-shot review

Check narrative, direction, prop state, color, volume, captions, transitions, pacing, and rights disclosures. Cross-shot consistency comes from project state and editing choices, not only from one generation model.

## Scoring dimensions and hard gates

You can score prompt adherence, individual-frame quality, motion naturalness, subject identity, background stability, physics/causality, shot language, continuity, audio/video, accessibility, safety, and rights separately. Safety and rights review should also check input `source_revision`, object-level authorization/ACL, revocation/deletion propagation status, and whether factual external claims have independent evidence sufficient for `evidence_supported`. Lack of consent for a person, prohibited content, an ACL that denies reading, factual deception or insufficient evidence, or an incorrect critical caption number should be hard failures that an average score cannot erase.

## The role of automated metrics

FVD compares distributions of video features at a set level; its original paper tested correlation through human studies. It still depends on the feature network, sample set, and data domain, and is not an acceptance tool for one business clip. Per-frame perceptual distance can help detect flicker or editing preservation, but camera motion affects it. Optical-flow or tracking signals can flag motion anomalies but cannot decide whether an action meets the creative brief or physical common sense.

Automated signals are appropriate for screening and regression monitoring; final review needs people. Any automatic frame extraction, OCR, identity similarity, or evaluation model may read material only after object-level authorization/ACL allows it. When comparing candidates or model versions, randomize order, hide system names, and record `source_revision`, `transform_id`, failure labels, and attempt count. Associate a `release_id` only after human approval. Showing only successful examples severely overstates stability.

## Identity and continuity checklist

Choose observable anchors for each subject: face/appearance, clothing, color, props, left/right relationships, and size. Recheck after every return from occlusion, turn, and cut. For real people, also check whether consent exists for generation and release; “it does not look exactly like them” does not eliminate privacy or reputational risk.

## Common mistakes and troubleshooting

- **Watching only once at normal speed:** slow playback, loops, and key-frame inspection expose different defects.
- **Reporting only an average score:** retain timestamps, shot IDs, and failure categories.
- **Declaring the product better because FVD decreases:** verify data, implementation, sample size, and human preference.
- **Letting reviewers see model names:** use blinded paired comparisons to reduce bias.
- **Publishing after a passing score:** scoring is not authorization; revocation or deletion should stop access to linked candidates and review artifacts.
- **Making a factual claim because synthetic video looks plausible:** separate factual evidence from the video itself and declare `evidence_supported` only when independent evidence is sufficient.

## Exercise and self-check

Design 12 failure labels for three shots, assigning each to frame-level, within-shot, or cross-shot review. Why can simple frame differences falsely report “flicker” when the camera is intentionally panning?

Next: [[video-generation/02-engineering-and-quality/08-cost-failure-recovery-and-provenance-governance|Cost, Failure Recovery, and Provenance Governance]].

## References

- [Towards Accurate Generative Models of Video: A New Metric & Challenges](https://arxiv.org/abs/1812.01717)
- [Video Diffusion Models](https://arxiv.org/abs/2204.03458)

