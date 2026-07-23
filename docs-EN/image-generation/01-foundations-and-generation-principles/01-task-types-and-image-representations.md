---
title: "Image-Generation Task Types and Image Representations"
tags:
  - image-generation
  - foundations
aliases:
  - Text-to-image and image-editing tasks
source_checked: 2026-07-22
lang: en
translation_key: 图像生成/01-基础与生成原理/01-任务类型与图像表示.md
translation_source_hash: 3109d8ff378849c8deda7fbf1977d50c25c2c2c94b81a8c4fcb89180177b5b50
translation_route: zh-CN/图像生成/01-基础与生成原理/01-任务类型与图像表示
translation_default_route: zh-CN/图像生成/01-基础与生成原理/01-任务类型与图像表示
---

# Task Types and Image Representations

## Goal of this lesson

Answer two questions first: which task should the model perform, and what exactly makes up the deliverable? If the task is wrong, even a beautifully worded prompt is difficult to accept.

## Start with pixels

A digital image is a regular grid. Each cell is a **pixel**, usually storing values for red, green, and blue channels; an image with transparency also has an alpha channel. `1024 × 1024` describes the pixel grid, not print dimensions, and does not guarantee clarity. Aspect ratio is `width ÷ height`, which determines the compositional space of landscape, portrait, or square images.

Models usually do not iterate over every final high-resolution pixel directly. Many first compress an image into a **latent space**: a smaller numeric representation that retains the main visual structure, then use a decoder to reconstruct pixels. A latent space is like a design sketch, not an image a person can inspect directly.

## Six common tasks

| Task | Input | Output | Key acceptance |
| --- | --- | --- |
| Text-to-image | Text | New image | Prompt adherence, composition, quality |
| Image-to-image | Image + text | New image retaining some input structure | Similarity to input, extent of change |
| Inpainting | Image + mask + text | Replacement only in the selected area | Edge blending, preservation outside the mask |
| Outpainting | Image + new canvas extent | Completion outward from the image | Perspective, light, and texture continuity |
| Variations | Image | Multiple versions of the same theme | Diversity and identity preservation |
| Super-resolution/restoration | Low-resolution or damaged image | Clearer version | Improved detail without inventing material facts |

A mask is a black-and-white or alpha image aligned to the input that indicates “where change is allowed.” Different APIs can reverse the meaning of black and white or impose different size and format conventions. Read current documentation and test a small sample before integration.

## Requirement-clarification template

Do not collect only “draw a future city.” Ask at least about purpose and audience, canvas ratio, subject and action, must-have and prohibited elements, whether text needs to be accurate, rights to reference material, acceptable editing range, delivery format, number of attempts, and human approver. Every reference also needs an `asset_id`, `source_revision`, permitted use, and object-level authorization/ACL; authorize it before a reviewer, model, or Agent reads it. For uses such as news, medicine, identity documents, or scientific evidence, also ask “is synthesis allowed?” A generated image cannot stand in for a factual record.

## Common errors and diagnosis

- **Treating format as quality**: PNG is not automatically clearer than JPEG; they are encoding choices.
- **Ignoring downstream crop**: decide the publishing ratio before composition or a platform can crop away the subject.
- **Using generation as lossless restoration**: generative restoration can fill in plausible-looking detail and must not claim to restore real information.
- **Unclear edit scope**: record the mask version and a “must not change” list, then spot-check unedited areas.
- **Treating output as evidence**: generated imagery can be illustrative or creative material. Only independently supported external facts may be labeled `evidence_supported`.

## Exercise and self-check

1. “Replace the background of a product image with a beach while leaving the product unchanged” is which task type, and which inputs are needed?
2. What is the aspect ratio of portrait `1080 × 1350`, and why is it not enough to write `4:5` and ignore pixel dimensions?
3. Write one risk statement for “restore a blurred license plate.”

When you can clearly distinguish task, input, and acceptance object, continue with [[image-generation/01-foundations-and-generation-principles/02-diffusion-and-autoregressive-intuition|Diffusion and Autoregressive Intuition]].

## References

- [OpenAI Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) (generation and editing interface example; checked 2026-07-22)
- [High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
