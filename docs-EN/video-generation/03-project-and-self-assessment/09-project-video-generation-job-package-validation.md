---
title: "Project: Video Generation Job Package Validation"
tags:
  - video-generation
  - project
  - python
aliases:
  - Video storyboard job-package project
source_checked: 2026-07-22
lang: en
translation_key: 视频生成/03-项目与自测/09-项目：视频生成任务包验证.md
translation_source_hash: 738ddd5ad44cf169a86acceee8f42f7b3ccfc53f3b991aee22bcee760c80c02f
translation_route: zh-CN/视频生成/03-项目与自测/09-项目：视频生成任务包验证
translation_default_route: zh-CN/视频生成/03-项目与自测/09-项目：视频生成任务包验证
---

# Project: Video Generation Job Package Validation

## Project objective

Use the Python standard library to validate a structured job package for an 8-second short video: output specifications, shot coverage, continuity anchors, caption timing, audio rights, human review, a provenance plan, version/release governance, acceptance dimensions, and failure recovery. It runs fully offline: it does not call a generation API or create video, audio, caption, or image files.

## Files

- [[video-generation/03-project-and-self-assessment/examples/video_job_package.json|video_job_package.json]]: a three-shot teaching fixture that declares only an offline adapter and does not impersonate a real provider.
- [[video-generation/03-project-and-self-assessment/examples/validate_video_job.py|validate_video_job.py]]: strictly reads UTF-8 JSON, checks the closed-field contract first, then audits timeline, assets, governance, and budget relationships.
- [[video-generation/03-project-and-self-assessment/examples/test_validate_video_job.py|test_validate_video_job.py]]: retained compatibility smoke tests.
- [[video-generation/03-project-and-self-assessment/examples/test_contract_and_cli.py|test_contract_and_cli.py]]: strict tests for JSON, field types, asset versions, object-level ACL, revocation/deletion propagation, evidence boundaries, cross-field rules, CLI behavior, and read-only operation.

## How to run it

In PowerShell 7, run the following from the project root that contains `docs-CN/`, `docs-EN/`, and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\video-generation\03-project-and-self-assessment\examples'
python -B .\validate_video_job.py .\video_job_package.json
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
```

The suite currently contains **133 tests**. Normal mode, optimized mode, and warnings-as-errors mode should all pass. A valid job returns `0`; a cross-field or governance audit failure returns `1`; file, UTF-8, strict-JSON, or field-contract errors return `2`. The script is read-only, and `-B` avoids `.pyc` caches.

Referenced asset objects contain an `asset_id`, `source_revision`, role, source reference, SHA-256, rights record, and `acl_reference`. Top-level `lineage` distinguishes a frozen requirement version, shot/post-production `transform_id` values, and candidate `release_id` values. `governance` requires object-level authorization/ACL before scoring, a revocation/deletion propagation plan, and limits factual release to `evidence_supported`. This is a teaching business contract, not a mirror of any vendor API.

## Experiments

1. Move the start of the second shot before the end of the first to observe an overlap error.
2. Change the end time of one caption cue to `9.0` to observe an out-of-range error.
3. Delete one shot’s continuity anchor to understand why “keep it consistent” needs checkable fields.
4. Set `human_review_required` to `false` and confirm that the pre-release human gate cannot be omitted.
5. Copy the fixture to design a 12-second version; shot times must continuously cover the entire film rather than merely changing total duration.
6. Add a reference-asset object to one shot, filling `asset_id`, `source_revision`, role, source reference, rights record, `acl_reference`, and a 64-character lowercase SHA-256; then deliberately duplicate the `asset_id` to observe a contract error.
7. Set `object_acl_required` to `false` and explain why the system must reject the job before frame extraction or model scoring.
8. Change `evidence_policy` to another value and explain why Content Credentials or a correct timeline cannot independently support factual release.

## Project acceptance

- [ ] Shot IDs are unique, sorted by time, free of overlaps and gaps, and cover the total duration completely.
- [ ] Every shot has shot scale, camera movement, subject, action, setting, prompt, and continuity anchors.
- [ ] Referenced assets have a valid role, stable source, `source_revision`, content SHA-256, rights record, `acl_reference`, and globally unique ID.
- [ ] Caption cues are within the valid duration, do not overlap, and declare WebVTT format.
- [ ] Audio rights, reference-asset rights, consent, human review, and provenance planning are explicit.
- [ ] `source_revision`, `transform_id`, and `release_id` distinguish requirements, transformations, and release candidates; object-level ACL and revocation/deletion propagation both have a plan.
- [ ] A factual release is marked `evidence_supported` only when independently supported by evidence.
- [ ] Acceptance covers prompt adherence, image quality, motion, identity, continuity, audio/captions, safety, and rights.
- [ ] Retries have per-shot limits and a human-escalation condition.
- [ ] There are no API keys, real-person assets, media files, concrete prices, or model weights.

## Integrated self-check

1. Why does a passing job package prove only that the plan is internally consistent, not that a model will certainly generate it?
2. If a crossfade is required, how should the current “no overlap” rule be extended rather than simply removed?
3. When a vendor endpoint shuts down, which fields can remain and which must be replaced by the adapter?
4. How can validation results be connected to an Agent state machine to prevent endless retries after failure?

## References

- [[video-generation/02-engineering-and-quality/04-storyboarding-and-shot-lists|Storyboarding and Shot Lists]]
- [[video-generation/02-engineering-and-quality/08-cost-failure-recovery-and-provenance-governance|Cost, Failure Recovery, and Provenance Governance]]
