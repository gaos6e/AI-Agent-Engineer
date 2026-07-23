---
title: "Audio Digitization and the ASR Pipeline"
tags:
  - ai-agent-engineer
  - asr
  - audio
aliases:
  - ASR pipeline
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音识别/01-基础与数据/01-声音数字化与ASR全流程.md
translation_source_hash: 40f1b7716fac41e10760ed51a6484da7a4643c11f4c69b724590d861b7e53f6a
translation_route: zh-CN/语音识别/01-基础与数据/01-声音数字化与ASR全流程
translation_default_route: zh-CN/语音识别/01-基础与数据/01-声音数字化与ASR全流程
---

# Audio Digitization and the ASR Pipeline

## Objective

Understand how sound becomes digital samples, and define ASR input, output, and provenance fields.

## From air vibration to a digital waveform

A microphone converts changes in air pressure into electrical signals, then an analog-to-digital converter samples them at fixed intervals. **Sample rate** is the number of samples per second; for example, 16 kHz means 16,000 samples per second. **Bit depth** determines the amplitude precision of each PCM sample. **Channel** states whether audio is mono or multichannel.

The minimum intuition behind the sampling theorem is that representing the highest frequency $f_{max}$ requires a sample rate greater than $2f_{max}$. This does not mean a higher sample rate automatically improves recognition: a model may require one format, and poor resampling, clipping, and noise can matter more.

Short-time processing divides a waveform into overlapping **frames**. Speech is approximately stable over tens of milliseconds, so a spectrum can be extracted for each frame. Modern end-to-end models can also learn representations directly from waveform or internal features.

Do not collapse these concepts into “audio format”:

| Layer | Example | Facts to record | Common mistake |
| --- | --- | --- | --- |
| Container | WAV, MP4, WebM | Detected container and duration | Treating filename extension as encoding |
| Codec/sample representation | PCM, AAC, Opus | Codec and sample width/layout where applicable | Assuming every WAV is uncompressed PCM |
| Sampling layout | 48 kHz stereo, 16 kHz mono | **sample_rate_hz**, **channels**, and mixdown rule | Assuming higher sample rate is necessarily more accurate |
| Model-analysis input | A model-required mono waveform or feature | Resampling/mixdown **transform_revision** and model requirement | Treating original-file parameters as actual model input |

For each asset, retain at least **asset_id**, **source_revision**, original format, analysis format, **timestamp_reference**, and conversion version. If timestamps begin at zero at the asset start, represent a segment as a half-open interval **[start_seconds, end_seconds)**. A player's wall clock, upload time, and audio-sample coordinates must not be mixed. Resampling, mixdown, cropping, and silence removal create new traceable transformation records rather than overwriting the source.

## ASR pipeline

~~~mermaid
flowchart LR
    A[Acquire asset] --> B[Bounded decode and inspection]
    B --> C[Resample and channel handling]
    C --> D[VAD and segmentation]
    D --> E[Model decoding]
    E --> F[Timestamps and anonymous speakers]
    F --> G[Raw and normalized text]
    G --> H[Evaluation and human review]
    H --> I[Policy-constrained downstream use]
~~~

Minimum input metadata: **asset_id**, **source_revision**, format, sample rate, channels, duration, language prompt, collection/access permission, and time reference. Minimum output metadata: **segment_id**, **revision**, segment start/end, raw text, normalized text, **partial/provisional_final/committed** semantics, model/configuration version, and error information. If a model does not provide a field, state **unknown** or omit it; do not fill the contract with guesses.

## Common errors

- Treating a filename extension as the real codec; decode and inspect parameters instead.
- Adding stereo channels directly and causing phase cancellation; select a channel or use safe mixdown explicitly.
- Allowing audio amplitude to exceed representation range and clip; lost information cannot be recovered by the model.
- Reading unbounded long files and causing memory or timeout problems.
- Passing untrusted uploads directly to a complex decoder. Limit size, duration, codec/container, nested media, and resource consumption, and isolate parsing failures.

## Exercises and self-check

1. About how many bytes per second are 16 kHz, 16-bit, mono raw PCM? $16000\times2=32000$ bytes, excluding container overhead.
2. Is 44.1 kHz always more suitable for an ASR model than 16 kHz? No; inspect the model input contract and test it.
3. List traceable output fields for a two-person meeting recording.

## Next step and references

Continue with [[speech-recognition/foundations-and-data/02-acoustic-language-and-end-to-end-intuition|Acoustic, language, and end-to-end intuition]]. For file-reading concepts, see [Python wave](https://docs.python.org/3/library/wave.html), checked on 2026-07-22. It targets WAVE and is not a general audio decoder or security auditor. Actual container, codec, and sampling support must follow the current contract of the target model or service.
