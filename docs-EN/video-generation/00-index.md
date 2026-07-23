---
title: "Video Generation Learning Path"
tags:
  - ai-agent-engineer
  - video-generation
  - multimodal
aliases:
  - AI video-generation learning path
  - Text-to-Video
ai_learning_stage: 8. Extended applications and complex collaboration
ai_learning_order: 53
ai_learning_schema: 2
ai_learning_id: video-generation
ai_learning_domain: multimodal
ai_learning_catalog_order: 5300
ai_learning_hard_prerequisites: []
ai_learning_track_multimodal_realtime_order: 1200
ai_learning_track_multimodal_realtime_kind: optional
content_origin: original
content_status: dynamic
source_checked: 2026-07-22
lang: en
translation_key: 视频生成/00-目录.md
translation_source_hash: c4034aa08951c9d194897268c3ac1384367e6417b5437db7ce305446e9fe3ed0
translation_route: zh-CN/视频生成/00-目录
translation_default_route: zh-CN/视频生成/00-目录
---

# Video Generation

## About this knowledge base

Video generation produces audiovisual content that changes over time from text, images, or existing clips. It is not simply “many images generated in sequence”: shots, frame rate, motion, identity continuity, audio, subtitles, post-production, and failure recovery all determine delivery quality. This course uses a short-shot workflow: storyboard first, generate one shot at a time, validate a task package offline, then finish the work through human editing and review. Inputs, shot transformations, and release candidates must also be tracked separately with versions, object-level access control, and revocation/deletion propagation.

## Where this course fits in the overall route

It sits near the end of the Extended Applications and Complex Collaboration stage and combines prompting, multimodal input, asynchronous jobs, evaluation, safety, and production engineering. After completing it, you should be able to have an Agent orchestrate video work without delegating creative or release decisions to the Agent entirely.

## Learning objectives

- Understand the relationship among frames, frame rate, duration, resolution, shots, and a timeline.
- Explain intuitively both spatial quality and temporal consistency in video generation.
- Break a creative brief into a storyboard, shot list, generation jobs, post-production, audio, and subtitle interfaces.
- Design layered acceptance for motion, identity, continuity, audio/video synchronization, and safety.
- Use an offline validator to check timelines, rights information, recovery rules, human-review gates, and the provenance chain of `source_revision`, `transform_id`, and `release_id`.

## Prerequisites

Before starting, it is helpful to understand composition, conditioning, and quality boundaries in [[image-generation/00-index|Image Generation]]; describe shot constraints with [[prompt-engineering/00-index|Prompt Engineering]]; understand asynchronous jobs and failure recovery through [[workflow-automation/00-index|Workflow Automation]]; and express task packages with [[json/00-index|JSON]]. These are task-oriented capabilities, not a requirement to complete four entire courses first. No editing-software experience is required; this course focuses on transferable workflows and interfaces.

## Recommended order

1. [[video-generation/01-foundations-and-generation-principles/01-video-fundamentals-and-timing|Video fundamentals and timing]] — read frame rate, duration, shots, and timelines correctly.
2. [[video-generation/01-foundations-and-generation-principles/02-generation-principles-and-temporal-consistency|Generation principles and temporal consistency]] — understand why video adds a temporal challenge beyond image generation.
3. [[video-generation/01-foundations-and-generation-principles/03-text-and-image-conditioning|Text and image conditioning]] — choose text, first-frame, reference-asset, or existing-video conditioning.
4. [[video-generation/02-engineering-and-quality/04-storyboarding-and-shot-lists|Storyboarding and shot lists]] — break a story into generatable short shots.
5. [[video-generation/02-engineering-and-quality/05-generation-and-post-production-assembly-workflow|Generation and post-production assembly workflow]] — manage asynchronous jobs, versions, and the handoff to post-production.
6. [[video-generation/02-engineering-and-quality/06-audio-captions-and-accessibility-interfaces|Audio, captions, and accessibility interfaces]] — treat synchronized audio and captions as formal deliverables.
7. [[video-generation/02-engineering-and-quality/07-quality-motion-and-identity-consistency-evaluation|Quality, motion, and identity-consistency evaluation]] — establish frame-, shot-, and finished-piece reviews.
8. [[video-generation/02-engineering-and-quality/08-cost-failure-recovery-and-provenance-governance|Cost, failure recovery, and provenance governance]] — limit retries, preserve provenance, and release safely.
9. [[video-generation/03-project-and-self-assessment/09-project-video-generation-job-package-validation|Project: Video Generation Job Package Validation]] — complete a fully offline storyboard-job-package check.

## Hands-on project

Follow [[video-generation/03-project-and-self-assessment/09-project-video-generation-job-package-validation|the project guide]], inspect the [[video-generation/03-project-and-self-assessment/examples/video_job_package.json|example job package]], and run the [[video-generation/03-project-and-self-assessment/examples/validate_video_job.py|validator]], [[video-generation/03-project-and-self-assessment/examples/test_validate_video_job.py|compatibility smoke test]], and [[video-generation/03-project-and-self-assessment/examples/test_contract_and_cli.py|full contract and CLI tests]]. The scripts do not request an API or create video or audio files.

## Mastery checklist

- [ ] Can turn a creative idea into a shot list with explicit start/end times, shot language, and continuity anchors.
- [ ] Can explain the difference between within-frame quality and across-frame consistency.
- [ ] Can design the interfaces among generation, download, transcoding, editing, captioning, voice-over, and review.
- [ ] Can retry only the failed shot rather than remaking the entire piece each time.
- [ ] Can record asset authorization, consent, generation history, and a Content Credentials plan.
- [ ] Can enforce object-level authorization/ACL before preview, scoring, or model access, and invalidate shot candidates, finished derivatives, caches, and links as planned when access is revoked or data is deleted.
- [ ] Can distinguish synthetic-content disclosure from factual claims; the latter require independent evidence sufficient for `evidence_supported`.
- [ ] The offline job-package validator and its tests pass.

## Relationship to other knowledge bases

- [[image-generation/00-index|Image Generation]] provides foundations in composition, visual conditioning, editing, and image quality.
- [[text-to-speech/00-index|Text-to-Speech]] and [[speech-recognition/00-index|Speech Recognition]] support voice-over, transcription, and caption proofreading.
- [[runtime-monitoring/00-index|Runtime Monitoring]] supports long-job state, retries, and cost observation.
- [[ai-safety/00-index|AI Safety]] and [[ai-governance/00-index|AI Governance]] carry release-risk assessment and accountability records.
- [[knowledge-base-construction/03-versioning-deletion-and-authorization|Versioning, Deletion, and Authorization]] supplies general governance semantics for versions, object-level authorization/ACL, and revocation/deletion propagation.

## Primary references

Sources were checked or accessed on **2026-07-22**. On that date, the official OpenAI video guide announced that Sora 2 video models and the Videos API were deprecated and **scheduled to shut down on 2026-09-24**. That is a future plan, not an event that has already occurred. Accordingly, this course treats vendor fields as adapter configuration rather than permanent knowledge.

- [Video Diffusion Models](https://arxiv.org/abs/2204.03458) (Ho et al., 2022, original paper)
- [Video generation models as world simulators](https://openai.com/index/video-generation-models-as-world-simulators/) (Brooks, Peebles, et al., 2024, technical report)
- [OpenAI Video generation guide](https://developers.openai.com/api/docs/guides/video-generation) (accessed 2026-07-22; current interface and planned shutdown)
- [Google Cloud video generation prompt guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) (current provider prompt-structure examples)
- [WebVTT: The Web Video Text Tracks Format](https://www.w3.org/TR/webvtt1/) (W3C Candidate Recommendation Draft, 2026-05-20)
- [C2PA Content Credentials 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html)

