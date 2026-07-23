---
title: "Offline Multimodal Evidence Routing Project"
tags:
  - multimodal-ai
  - project
  - python
aliases:
  - Multimodal offline project
  - Media evidence router
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/03-项目与自测/08-离线多模态证据路由项目.md
translation_source_hash: be0f5fb02772e8c55abc1cb3f11b3a743aaa45896ee6256c792aa60872e7e6fd
translation_route: zh-CN/多模态AI/03-项目与自测/08-离线多模态证据路由项目
translation_default_route: zh-CN/多模态AI/03-项目与自测/08-离线多模态证据路由项目
---

# Offline Multimodal Evidence Routing Project

## Project goal

Create a processing plan from a synthetic asset manifest without reading, uploading, or generating real media. The project validates MIME consistency, format and size limits, required modalities, a synthetic cost budget, privacy actions, and spatiotemporal evidence types.

## Files

- [multimodal_router.py](multimodal-ai/03-project-and-self-assessment/examples/multimodal_router.py): the Python 3 standard-library router.
- [media_manifest.json](multimodal-ai/03-project-and-self-assessment/examples/media_manifest.json): an input fixture containing synthetic metadata only.
- [test_multimodal_router.py](multimodal-ai/03-project-and-self-assessment/examples/test_multimodal_router.py): validates success, format conflicts, missing modalities, budget, and privacy routing.
- [test_contract_and_cli.py](multimodal-ai/03-project-and-self-assessment/examples/test_contract_and_cli.py): validates strict JSON, closed fields, output-write errors, and CLI exit codes.

The hashes, filenames, and sizes in the manifest are teaching data and do not refer to real people or media.

## Routing semantics

The script maps `detected_mime` to image, audio, video, document, or text, and selects processors and evidence locations:

| Modality | Example processors | Evidence location |
| --- | --- | --- |
| image | `image_decoder`, `ocr` | `image_region` |
| audio | `audio_decoder`, `asr` | `audio_interval` |
| video | `video_probe`, `scene_sampler` | `video_interval`, `frame_region` |
| document | `document_parser`, `layout_extractor` | `page_region` |
| text | `text_parser` | `text_span` |

Synthetic `cost_units` are only for practicing a budget; they are not a provider price or token formula.

## Run it

In PowerShell 7, enter this directory and run:

~~~powershell
python -B .\examples\multimodal_router.py .\examples\media_manifest.json
python -B -m unittest discover -s .\examples -p 'test_*.py' -v
python -B -O -m unittest discover -s .\examples -p 'test_*.py'
python -B -W error -m unittest discover -s .\examples -p 'test_*.py'
~~~

You can write the report to the system temporary directory:

~~~powershell
python -B .\examples\multimodal_router.py .\examples\media_manifest.json --output "$env:TEMP\multimodal-plan.json"
~~~

The script makes no network calls, does not open the fictional `file_name` in the manifest, and does not generate media or reports inside the knowledge base.

`ready` returns exit code 0. A policy block returns 1. A manifest-contract or report-write error returns 2. The 58 tests cover strict JSON, field contracts, format and metadata, modality routing, cost, privacy actions, output files, and the CLI.

## Reading the report

- `status=ready`: format, required modalities, and budget pass.
- `status=blocked`: `errors` lists the reasons; do not continue to a model call.
- `assets`: each asset's modality, processors, `evidence_kinds`, `privacy_action`, and `cost_units`.
- `privacy_action=local_only`: external processing is not permitted.
- `total_cost_units`: must not exceed `policy.budget_units`.

> [!warning] Classification trust boundary
> The fixture's `privacy` is synthetic teaching input already confirmed by a policy layer. The script never reads real media and does not prove that its classification is correct. A production system must resolve classification and permitted processing locations server-side from authenticated asset, tenant, and authorization records; an uploader must not obtain egress permission by placing `privacy: public` in a manifest.

## Adaptation exercises

1. Change the video's privacy to `restricted` and observe `local_only`.
2. Delete the audio asset and confirm `missing_required_modality`.
3. Make `declared_mime` differ from `detected_mime` and confirm rejection.
4. Lower `budget_units` and confirm budget blocking.
5. Add `image/svg+xml`; decide the parsing-safety policy before changing the allowlist. Do not allow it merely because of its extension.
6. Add `transform_chain` and original-coordinate mapping to `evidence_kinds`.

## Mastery check

- [ ] I can distinguish media-manifest validation, preprocessing routing, and model inference.
- [ ] I will not treat `declared_mime` as a trusted format.
- [ ] I can explain the spatial or temporal evidence each modality needs.
- [ ] I can narrow scope when the budget is insufficient rather than silently lower quality.
- [ ] I can explain the different processing policies for `restricted` and `personal`.
- [ ] I know that real integration still needs safe decoding, hashes, authorization, vendor limits, and actual model evaluation.

## Self-test questions

1. Why can this project validate some engineering logic without an actual image?
2. Why cannot a cost estimate be hard-coded as a provider token count?
3. If required video is missing but its transcript exists, should it automatically count as video being present?
4. Does valid MIME mean that file content is safe?

## Limitations

The project does not validate media decoding, OCR/ASR quality, real model capability, time synchronization, or coordinate reverse transforms. It validates only the contract and policy layers before calling a model. `detected_mime` is also synthetic input supplied by an external trusted parser. A real release still needs restricted parsing, trusted classification and authorization evaluation, evidence back-links, and end-to-end evaluation.

## References and next step

Return to [[multimodal-ai/00-index|Multimodal AI]], then choose [[ocr/00-index|OCR]], [[speech-recognition/00-index|Speech Recognition]], or a generation track for deeper study.
