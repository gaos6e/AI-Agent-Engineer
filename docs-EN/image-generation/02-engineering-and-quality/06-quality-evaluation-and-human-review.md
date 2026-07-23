---
title: "Image-Generation Quality Evaluation and Human Review"
tags:
  - image-generation
  - evaluation
  - human-review
aliases:
  - Image-generation acceptance
source_checked: 2026-07-22
lang: en
translation_key: 图像生成/02-工程与质量/06-质量评测与人工评审.md
translation_source_hash: f3fc4a444625c1f5f3c5512fd6a32f89492d7e2fa31edc30ecd7fcd148e2b934
translation_route: zh-CN/图像生成/02-工程与质量/06-质量评测与人工评审
translation_default_route: zh-CN/图像生成/02-工程与质量/06-质量评测与人工评审
---

# Quality Evaluation and Human Review

## Goal of this lesson

Break “a good image” into task-relevant, reviewable dimensions and understand why automated metrics cannot replace human judgment.

## Define a task-level rubric first

Score each candidate from 1 to 5 on:

- **Prompt adherence**: subject, count, relationships, and prohibited items;
- **Compositional usability**: focal point, safe areas, crop, and downstream layout;
- **Visual integrity**: coherent shapes, limbs, texture, perspective, and lighting;
- **Text and factual correctness**: character-by-character text, numbers, charts, and brand information;
- **Identity and edit preservation**: reference subject, protected area, and unedited area;
- **Safety and rights**: sensitive content, consent for people, trademarks, `source_revision`, object-level authorization/ACL, and revocation/deletion propagation status;
- **Factual-claim boundary**: where imagery is used for an external factual claim, independent evidence must make that claim `evidence_supported`; and
- **Diversity**: whether candidates offer genuinely different options that still meet constraints.

Hard constraints are pass/fail gates, not values to hide in an average. For example, an incorrect brand name cannot be published merely because the image looks good.

## What automated metrics can answer

FID compares the distance between feature distributions for generated and reference image sets. It suits set-level research comparison, not a business acceptance score for one image; it depends on sample size, reference distribution, and feature implementation. LPIPS measures perceptual distance between two images in deep features, useful for edit preservation or reconstruction comparison, but “near” does not mean semantically correct. Image-text similarity can assist prompt adherence but may ignore count, negation, text, and spatial relationships.

Metrics are therefore **diagnostic signals**, not complete judges. After changing encoder, preprocessing, or dataset, do not compare scores directly.

## Designing human review

To compare model or prompt versions, first enforce object-level authorization/ACL before reading images, OCR, scoring, or showing a reviewer. Then use randomized order and blind paired review. Record at least task ID, `source_revision`, `transform_id`, candidates A/B, dimensional selection, failure tag, and note for every sample; record `release_id` only when approving publication. When reviewers disagree, first examine rubric definitions and example anchors rather than only averaging scores.

Build failure tags such as `wrong_count`, `text_error`, `identity_drift`, `unsafe`, and `layout_overflow`. Tags help an Agent choose a next action: rewrite prompt, split task, post-process, or reject outright.

## Minimum regression set

Cover landscape and portrait, single and multiple subjects, Chinese text, reference edits, transparency and format, sensitive boundaries, and typical brand layouts. On a model or provider update, rerun the same tasks with the same blind-review rules. Retain request and sample-selection methods, but do not put restricted media in a public repository.

## Common errors and diagnosis

- **Selecting only the best sample**: also report attempt count and failure rate.
- **Using one aggregate score**: retain every dimension and hard-failure reason.
- **Reviewers know the model**: expectation bias follows; randomize and anonymize.
- **Treating an OCR pass as proof that typography is correct**: OCR does not check font license, hierarchy, or readability.
- **Scoring before permissions**: a high score cannot cure an unauthorized read. After revocation, associated candidates and scoring artifacts should cease to be accessible.
- **Treating generated imagery as factual proof**: Content Credentials, similarity, and review scores do not automatically make an external claim `evidence_supported`.

## Exercise and self-check

For an “e-commerce product hero image,” design six dimensions, three hard gates, and eight failure tags. Explain why FID cannot determine whether one product image is brand compliant.

Next: [[image-generation/02-engineering-and-quality/07-safety-copyright-and-content-credentials|Safety, Copyright, and Content Credentials]].

## References

- [GANs Trained by a Two Time-Scale Update Rule](https://arxiv.org/abs/1706.08500) (introduces FID)
- [The Unreasonable Effectiveness of Deep Features as a Perceptual Metric](https://arxiv.org/abs/1801.03924) (LPIPS)
- [CLIPScore](https://arxiv.org/abs/2104.08718) (interpret applicability boundary in the task context)
