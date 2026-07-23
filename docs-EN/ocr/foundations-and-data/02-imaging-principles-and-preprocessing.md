---
title: "Imaging Principles and Preprocessing"
tags:
  - ai-agent-engineer
  - ocr
  - image-processing
aliases:
  - OCR image preprocessing
source_checked: 2026-07-22
lang: en
translation_key: OCR/01-基础与数据/02-成像原理与预处理.md
translation_source_hash: 0bc9f211335a46c598fbdfc310456c8a2e54268350866bf0854a045dc846e8a3
translation_route: zh-CN/OCR/01-基础与数据/02-成像原理与预处理
translation_default_route: zh-CN/OCR/01-基础与数据/02-成像原理与预处理
---

# Imaging Principles and Preprocessing

## Objective

Understand resolution, contrast, skew, and noise in a testable way, and avoid applying one filter recipe to every document.

## Why pixels determine whether characters are distinguishable

A digital image is a grid of pixels. If character strokes occupy only a few pixels, compression, defocus, or scaling can erase the local differences between an **8** and a **3**. DPI (dots per inch) describes acquisition density, but an existing image's DPI metadata is not the same as real sharpness. Changing a 72-DPI label to 300 DPI does not create detail.

Common problems and processing hypotheses:

| Problem | Observable symptom | Candidate treatment | Risk |
| --- | --- | --- | --- |
| Skew | Text baselines are not horizontal | Deskew rotation correction | Excess rotation creates interpolation blur |
| Perspective | The page is trapezoidal | Four-point perspective correction | An inaccurate boundary can crop body text |
| Uneven illumination | One side is gray and the other white | Local thresholding or background estimation | Faint strokes can be removed |
| Salt-and-pepper noise | Scattered black and white dots | Median filtering or connected-component filtering | Punctuation can be discarded as noise |
| Ink bridging | Character strokes are too thick | Mild erosion | Thin strokes can break |

Binarization divides pixels into foreground and background. A global threshold fits evenly lit pages. A local threshold estimates each small region and fits shadows, but may create texture noise. Tesseract's official quality guide explicitly lists rotation, binarization, noise, and borders as factors, but it does not require enabling all of them.

## Reversible experiments

Every preprocessing step should record **name + parameters + input_hash + output_hash**. Compare the same validation set:

~~~text
Original image -> OCR -> baseline metrics
Original image -> deskew -> OCR -> new metrics
Original image -> deskew + local threshold -> OCR -> new metrics
~~~

Promote a step only after it improves the target document slices consistently. An image that looks cleaner to a person is not necessarily more accurate for OCR; some engines already preprocess internally, and external binarization can discard information.

## Troubleshooting order

1. Draw detection boxes back onto the original image first. Establish whether text was missed or misrecognized.
2. Check orientation, cropping, alpha channels, and color inversion.
3. Ablate one setting at a time on a small, representative sample rather than changing five parameters at once.
4. Report effects by document type, such as mobile photographs, scans, and low-resolution faxes.

## Exercises and self-check

- Design three mutually exclusive comparison experiments for a receipt photographed at an angle on a phone.
- Explain why scaling an image by four can make the file larger without adding information.
- Decide whether every small connected component should be removed. It should not: punctuation, superscripts, and small type can be equally small.

## Next step and references

Continue with [[ocr/foundations-and-data/03-text-detection-recognition-and-data-annotation|Text detection, recognition, and data annotation]]. See [Tesseract's official quality-improvement guide (5.x documentation line)](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), checked on 2026-07-22. Test the guide's concrete thresholds and modes against the version you actually use.
