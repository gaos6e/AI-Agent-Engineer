---
title: "Speech Recognition"
tags:
  - ai-agent-engineer
  - speech
  - asr
aliases:
  - ASR learning path
  - Automatic speech recognition
ai_learning_stage: 8. Extended applications and complex collaboration
ai_learning_order: 50
ai_learning_schema: 2
ai_learning_id: speech-recognition
ai_learning_domain: multimodal
ai_learning_catalog_order: 5000
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 475
ai_learning_track_rag_kind: optional
ai_learning_track_multimodal_realtime_order: 300
ai_learning_track_multimodal_realtime_kind: core
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音识别/00-目录.md
translation_source_hash: b8155559c48c74f687d3bd2474183628735ee52bb9364e105cd6a76160b49173
translation_route: zh-CN/语音识别/00-目录
translation_default_route: zh-CN/语音识别/00-目录
---

# Speech Recognition

## Course overview

Speech recognition, or Automatic Speech Recognition (ASR), converts linguistic content in audio into text. In Agent engineering, a usable result is normally more than a full transcript: it includes segments, timestamps, language, anonymous speaker labels, failure reasons, and audio provenance. Each processing run should join **asset_id**, **source_revision**, acquisition and analysis formats, timestamp reference, model/decoder/normalization versions, and **segment_id + revision** into one evidence chain. Without it, “the same transcript segment” cannot be reproduced, corrected, or deleted.

This course is for learners without audio or deep-learning background. Dynamic material was checked on **2026-07-22**. Model commands, supported languages, upload limits, and hardware requirements can change; the course does not treat a repository's or vendor's current options as a permanent interface.

## Where this fits in the overall path

Speech recognition is in the Extended applications and complex collaboration stage and provides the input channel for a voice Agent. Recognized text can flow into [[context-engineering/00-index|Context Engineering]], [[rag/00-index|RAG]], and [[workflow-automation/00-index|Workflow Automation]]. Together with [[text-to-speech/00-index|Text to Speech]], it forms the input/output modules; [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]] then handles turns, interruptions, tools, and session recovery.

~~~mermaid
flowchart LR
    A[Audio asset\nasset_id + source_revision] --> B[Decode and format contract\ntime reference, sample rate, channels]
    B --> C[Segmentation and recognition\nsegment_id + revision]
    C --> D[Committed transcript\nmodel, decode, normalization versions]
    D --> E[Retrieval, summarization, or Agent runtime]
    E --> F[Tools or high-risk actions]
    G[Independent identity, policy, and approval] -. gate .-> F
~~~

The transcript in this diagram is always **untrusted user input**. It can support understanding and retrieval, but cannot independently authorize tools, side effects, or identity decisions. Real-time turns, interruption, and action gates are developed separately in [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]].

## Learning objectives

- Explain the minimal intuition for waveforms, sample rate, channels, frames, and spectra.
- Distinguish the responsibilities and boundaries of conventional acoustic/language modules and end-to-end ASR.
- Design a data contract for VAD, segmentation, timestamps, speakers, and post-processing.
- Distinguish acquisition format, model-analysis format, and subtitle/transcript output format, including time coordinates and revision semantics.
- Calculate WER/CER correctly and inspect quality differences by environment, language, or group slices.
- Compare batch and streaming architectures, and design backpressure, unknown terminal state, privacy, and human review.
- Complete a fully offline synthetic transcript-evaluation project.

## Prerequisites

- [[python-fundamentals/00-index|Python Fundamentals]], [[json/00-index|JSON]], and [[probability-and-statistics/00-index|Probability and Statistics]] are recommended.
- No signal-processing background is required; formulas serve sampling and evaluation intuition only.

## Recommended order

1. [[speech-recognition/foundations-and-data/01-audio-digitization-and-asr-pipeline|Audio digitization and the ASR pipeline]]: learn waveforms, sampling, and the output contract.
2. [[speech-recognition/foundations-and-data/02-acoustic-language-and-end-to-end-intuition|Acoustic, language, and end-to-end intuition]]: understand what different model routes do.
3. [[speech-recognition/foundations-and-data/03-data-annotation-and-splitting|Data annotation and splitting]]: establish transcription rules and a leakage-free dataset.
4. [[speech-recognition/engineering-and-quality/04-vad-segmentation-timestamps-and-speakers|VAD, segmentation, timestamps, and speakers]]: turn a continuous meeting into usable segments.
5. [[speech-recognition/engineering-and-quality/05-batch-streaming-and-postprocessing|Batch, streaming, and post-processing]]: design real-time/offline services and a stable text layer.
6. [[speech-recognition/engineering-and-quality/06-wer-cer-and-slice-evaluation|WER, CER, and slice evaluation]]: measure error under consistent rules.
7. [[speech-recognition/engineering-and-quality/07-fairness-privacy-deployment-and-troubleshooting|Fairness, privacy, deployment, and troubleshooting]]: cover data boundaries and group differences.
8. [[speech-recognition/project-and-self-check/08-project-offline-transcript-evaluation|Project: offline transcript evaluation]]: run fixture evaluation and interpret the report.

## Hands-on entry point

- Main project: [[speech-recognition/project-and-self-check/08-project-offline-transcript-evaluation|Offline transcript evaluation]].
- Project assets: [[speech-recognition/project-and-self-check/examples/evaluate_transcript.py|evaluation script]], [[speech-recognition/project-and-self-check/examples/asr_fixture.json|synthetic transcript fixture]], and [[speech-recognition/project-and-self-check/examples/test_contract_and_cli.py|contract and CLI regression tests]].
- The project does not read or generate audio, download a model, or require a key. It validates synthetic format/time-reference metadata and committed transcripts only, so it cannot prove real-media encoding, audio quality, or recognition quality.

## Mastery criteria

- [ ] I can explain sample rate, channels, frames, VAD, and speaker diarization.
- [ ] I can distinguish recognizing content, identifying who is speaking, and verifying a speaker's identity.
- [ ] I can define partial/final result semantics and revision rules for streaming recognition.
- [ ] I can calculate WER/CER by hand and explain how normalization, tokenization, and slicing affect the metric.
- [ ] I can design runtime metrics and a controlled diagnostic process that do not record raw audio body content.
- [ ] I can run the project, locate timestamp/text problems, and add an anonymous slice.

## Connections to other knowledge bases

- Combined audio and image inputs are covered in [[multimodal-ai/00-index|Multimodal AI]].
- For how streaming ASR enters an interruptible dialog state machine and associates with TTS and tool calls, see [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]].
- ASR text cleaning, chunking, and retrieval connect to [[data-cleaning/00-index|Data Cleaning]], [[chunking-strategies/00-index|Chunking Strategies]], and [[semantic-search/00-index|Semantic Search]].
- Metric gates and online alerts connect to [[evaluation-framework/00-index|Evaluation Framework]] and [[runtime-monitoring/00-index|Runtime Monitoring]].

## Primary references

The following sources were checked on **2026-07-22**:

- [OpenAI Whisper repository](https://github.com/openai/whisper) (one implementation for understanding offline models, dependencies, and format conversion; recheck its current README and model table before installing)
- [Robust Speech Recognition via Large-Scale Weak Supervision (the Whisper paper)](https://arxiv.org/abs/2212.04356)
- [OpenAI Speech to text guide](https://developers.openai.com/api/docs/guides/speech-to-text) (a current product snapshot: bounded file transcription and real-time transcription use different paths; it does not define this course's general interface contract)
- [NIST OpenASR 2020 Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf)
- [NIST SCTK repository](https://github.com/usnistgov/SCTK) (its README identifies SCTK 2.4.12)
- [Python wave standard-library documentation](https://docs.python.org/3/library/wave.html) (supports uncompressed PCM WAVE only)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

> [!note] Boundary between facts and recommendations
> Whisper, cloud transcription APIs, and real-time sessions are concrete implementations. The asset chain, slicing, logging, and review practices in this course are engineering recommendations that must be validated against your languages, devices, setting, budget, and compliance needs. No model or transcript alone can prove a speaker's real-world identity or consent.
