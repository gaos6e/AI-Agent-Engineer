---
title: "Low Latency, Backpressure, and Jitter"
tags:
  - ai-agent-engineer
  - realtime
  - latency
  - backpressure
  - jitter
aliases:
  - Real-time agent latency engineering
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/04-低延迟背压与抖动.md
translation_source_hash: 797eefd18cc017544a88b761234363c16cceb99ac079f1c456a5350688a7442e
translation_route: zh-CN/实时多模态交互/04-低延迟背压与抖动
translation_default_route: zh-CN/实时多模态交互/04-低延迟背压与抖动
---

# Low Latency, Backpressure, and Jitter

## Why it matters

Reporting only “the model's first packet took 300 ms” misses capture buffering, endpointing, uplink, queuing, tools, downlink, the jitter buffer, and device playback. Worse, an unbounded queue can make throughput look stable while the user hears an answer canceled seconds ago.

## How to implement it

Define a segmented budget on one monotonic clock:

\`\`\`text
User starts speaking
→ first frame captured → speech_start → turn_commit
→ model/tool starts → first playable chunk
→ actual speaker playback → response completes
\`\`\`

Record p50/p95/p99, timeouts, and distributions sliced by network, device, and language for each segment. End-to-end metrics must at least include:

- turn endpoint delay;
- response first-audio time and first actual playback;
- time from the user speaking to old playback stopping (barge-in stop);
- tool-call wait and full task duration;
- audio underruns, dropped frames, late frames, and canceled-chunk leaks.

Backpressure needs a capacity and a policy. As an input queue approaches its limit, reduce noncritical-modal frequency, adjust the codec/frame length, apply flow control, or terminate with an explanation; do not silently accumulate work without bound. An output queue accepts only the current \`response_id\`; after cancellation, clear it and reject late chunks. A jitter buffer trades extra delay for stable playback. Tune it in network slices rather than setting it once on office Wi-Fi.

For video/screen input, state priorities when bandwidth is shared: for example, voice control can take priority over high-resolution video. When dropping frames, retain timestamps and evidence of what was dropped. Use absolute wall-clock time for cross-system correlation, but use a monotonic clock for duration and ordering so clock adjustments do not create negative latency.

## Common failures

- Measuring only averages or server-processing time, not tail latency and actual playback.
- Setting an unbounded buffer to avoid frame loss, yielding increasingly stale rather than real-time output.
- Clearing only the server queue on interruption, not the browser/device playback queue.
- Treating earlier ASR partials as better while ignoring mistaken actions caused by frequent revisions.
- Running load tests without realistic concurrent tools, network impairment, and cold starts.

## How to validate

In controlled trials, inject bandwidth drops, packet loss, reordering, 100–500 ms jitter, long-tail tools, and device switches. Verify that queue limits, flow control, degradation, timeouts, and alerts actually trigger; retain each trial's initial state, trace, terminal state, and network configuration together. Naturalness tests cannot replace task-success and recovery tests.

## Practice task

Write a segmented budget for a target p95 end-to-end latency. Artificially add 400 ms to one segment, then explain whether to sacrifice video frame rate, TTS chunk size, endpointing, or another component—and how to prevent that “optimization” from increasing false interruptions or mistaken actions.

## Evidence and next step

[W3C Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/) notes that real-time remote media may sometimes be briefly out of sync rather than accumulate delay indefinitely; concrete networking and playback algorithms remain implementation decisions. [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721) shows that real-time interaction must also evaluate pauses, backchannels, and interruption, not just text quality. Next: [[real-time-multimodal-interaction/05-tool-calling-and-conversation-state|Tool calling and conversation state]].
