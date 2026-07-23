---
title: "Architecture and End-to-End Contract"
tags:
  - ai-agent-engineer
  - realtime
  - architecture
  - speech-to-speech
aliases:
  - Cascaded and Speech-to-Speech
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/01-架构与端到端合同.md
translation_source_hash: 88d1a8e1d4eee179c5e593077a31d4eeeea16c6dc956639e8bf0269428b312f5
translation_route: zh-CN/实时多模态交互/01-架构与端到端合同
translation_default_route: zh-CN/实时多模态交互/01-架构与端到端合同
---

# Architecture and End-to-End Contract

## Why it matters

“Speech in, speech out” does not describe how to debug a system, replace a component, or prove that a tool call was correct. A real-time agent has at least two routes: an explicit cascaded \`ASR → LLM/runtime → TTS\` pipeline and direct or joint speech-to-speech (S2S). Both can be streaming, half duplex, or full duplex; **full duplex is an interaction capability, not a synonym for one model architecture**.

## How to implement it

| Dimension | Cascaded ASR→LLM→TTS | Speech-to-speech |
| --- | --- | --- |
| Intermediate representation | Explicit transcript, tool calls, and synthesis text | May primarily use continuous audio or audio tokens |
| Replaceability | ASR, reasoning, and TTS can be replaced and regressed separately | Components are more tightly coupled and need end-to-end adaptation |
| Prosody and nonverbal information | Prosody/time information must be retained explicitly | May be used directly, but must not be assumed correct |
| Latency | Multi-hop latency adds up and can be optimized by segment | May reduce explicit hops; actual latency still needs measurement |
| Auditability | Text and boundaries are relatively clear | Requires separately generated auditable transcripts/events |
| Fault isolation | Can be isolated by segment | Relies more on end-to-end traces and ablation baselines |

Whichever route you choose, the application runtime should own the following contract:

\`\`\`jsonc
{ // Minimum envelope for a correlatable, sortable real-time session event
  "session_id": "s-1", // The session that owns the event; do not mix it with a bearer token or user credential
  "event_id": "e-18", // Stable ID for event deduplication and audit
  "turn_id": "t-3", // Correlates the current user turn so its entire output can be interrupted or canceled
  "response_id": "r-3", // Correlates this assistant response, which may contain events from multiple modalities
  "type": "response.audio", // Declares the payload category so the consumer selects the audio-processing branch
  "sequence": 4, // Monotonic number within one stream; replay/out-of-order handling cannot rely only on arrival time
  "at_ms": 8120 // Session-relative timestamp for latency and VAD/interruption diagnosis
}
\`\`\`

> [!note] JSONC is for instruction
> The trailing \`//\` annotations explain the example. Remove comments before transmitting a strict JSON event.

The model may decide content, but it must not exclusively own permissions, tool side effects, approvals, event logs, or terminal states. Direct S2S must also turn tool parameters into a verifiable structure rather than infer them from audio that is currently playing.

An architecture ADR should at least record the target task, interaction mode, privacy/deployment constraints, failure budget, explainability, fallback path, baseline, end-to-end evaluation, and a revalidation date. Do not select a model first and reverse-engineer the requirements afterward.

## Common failures

- Hiding VAD, reasoning, tools, first packet, and playback buffers behind one “voice latency” number.
- Treating a revisable partial transcript in a cascade as final user intent.
- Having no independent event log in S2S, so the system cannot explain which audio caused a write action.
- Assuming that changing to a “native real-time model” automatically solves echo, network jitter, authorization, and recovery.
- Providing no text/button fallback, so a microphone-permission failure makes the entire task unusable.

## How to validate

Run a deterministic text baseline, a cascaded baseline, and the candidate S2S system over the same task set. Compare task success, interruption, latency, cost, and safety with the same initial state, tool sandbox, and terminal-state grader; ablate ASR, turn detection, tools, and TTS separately. Additional architectural complexity is warranted only when end-to-end performance improves and risk remains controlled.

## Practice task

Write a one-page ADR for “rescheduling a call by phone” or “in-browser voice search.” State the inputs/outputs, evidence that must be retained, three fallback modes, one major failure for each of cascade and S2S, and an evaluation result that would overturn the current choice.

## Evidence and next step

Real-time turns and interruptions need independent evaluation; see [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721). Product implementations are only candidate evidence. For example, the [OpenAI Realtime overview](https://developers.openai.com/api/docs/guides/realtime) described speech-to-speech, transcription, and different connection methods on the date checked; verify concrete capabilities against the target version. Next: [[real-time-multimodal-interaction/02-session-events-and-transport-boundaries|Sessions, events, and transport boundaries]].
