---
title: "Batch, Streaming, and Post-processing"
tags:
  - ai-agent-engineer
  - asr
  - streaming
aliases:
  - ASR service engineering
source_checked: 2026-07-14
lang: en
translation_key: 语音识别/02-工程与质量/05-批处理流式与后处理.md
translation_source_hash: 4e62aa6fe91ec1a7ad9ca4a8cb78651fa03b5f659a5a33110a50688ffacb55d1
translation_route: zh-CN/语音识别/02-工程与质量/05-批处理流式与后处理
translation_default_route: zh-CN/语音识别/02-工程与质量/05-批处理流式与后处理
---

# Batch, Streaming, and Post-processing

## Objective

Compare offline batch recognition with real-time streaming recognition, and design partial/final states, text normalization, and reliable failure handling.

## Batch and streaming

**Batch processing** recognizes audio after the full asset is available. It supports global context, retries, and high-throughput scheduling, making it suitable for meeting archives. **Streaming** emits results while receiving audio, prioritizing time to first token and continuous updates for live captions or voice assistants.

A streaming contract cannot rely on one ambiguous **final** state. It must distinguish at least:

- **partial**: a temporary hypothesis that later audio can revise; suitable only for UI preview or explicitly low-risk prediction.
- **provisional_final**: the current segment is closed, but the provider may issue a revision after global rescoring, cross-segment merging, or human correction.
- **committed**: the version this system confirms as a persistent record. Downstream retrieval, summarization, tools, and audit can consume only this state; a later correction is a new provenance-bearing revision event, not a silent overwrite.

If a target interface exposes only **final**, the adapter must document which semantic it implements at integration time. Do not infer “no more partials in this turn” means “never revisable.” The client updates idempotently by **segment_id + revision** rather than appending every partial and duplicating text. Each revision also associates the model/rule version that produced it and the upstream audio time range.

When ASR drives a real-time Agent, a **partial** must not trigger a write-capable tool directly. An independent **turn.commit** event or user confirmation promotes a revisable observation to actionable input. See [[real-time-multimodal-interaction/00-index|Real-Time Multimodal Interaction]] for full event boundaries around VAD, turns, interruption, tools, and conversation state.

## Latency decomposition

User-perceived latency includes capture buffering, VAD waiting, transport, queueing, inference, post-processing, and rendering. Reporting only “model real-time factor” cannot explain end-to-end experience. A streaming service also needs backpressure: when consumption is slower than audio arrival, does it degrade, drop data, add capacity, or disconnect? Make that policy explicit.

## Text post-processing

Retain **raw_text**, then generate versioned layers for:

- capitalization and punctuation restoration;
- numbers, dates, and unit normalization;
- proper-noun candidates;
- a redacted copy for sensitive information.

Rules must not invent content without evidence. In streaming, punctuation may depend on later context and should update with final-state handling.

## Retries and idempotency

Use bounded retries and backoff only for operations that are safe to retry. Uploading an entire audio segment needs a request ID, segment sequence number, and checksum summary so retry does not create a duplicate transcript. If a timeout leaves terminal state unknown, query the state before blindly creating another task.

## Exercises and self-check

- Design a JSON event sequence for **partial → partial revision → final**.
- Draw a batch queue and failure-recovery points for a 30-minute meeting.
- Why does “model inference took 200 ms” not prove end-to-end latency is 200 ms? Buffering and system overhead remain.

## Next step and references

Continue with [[speech-recognition/engineering-and-quality/06-wer-cer-and-slice-evaluation|WER, CER, and slice evaluation]]. Whether a product supports true streaming, word-level timestamps, or context prompts must follow the target SDK's current official documentation. The [Whisper repository](https://github.com/openai/whisper), checked on 2026-07-14, illustrates one implementation and cannot be generalized to all ASR interfaces.
