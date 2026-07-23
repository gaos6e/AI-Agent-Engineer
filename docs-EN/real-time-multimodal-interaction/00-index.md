---
title: "Real-Time Multimodal Interaction"
tags:
  - ai-agent-engineer
  - realtime
  - multimodal
  - voice-agent
  - learning-path
aliases:
  - Real-time voice agent
  - Real-time multimodal agent learning path
source_checked: 2026-07-22
source_baseline:
  - "W3C WebRTC Recommendation (2025-03-13)"
  - "W3C Media Capture and Streams Candidate Recommendation Draft (2025-10-09;
    checked 2026-07-22)"
  - "IETF RFC 6455 (WebSocket) and RFC 3261 (SIP)"
  - "Full-Duplex-Bench (arXiv:2503.04721, ASRU 2025)"
  - "OpenAI Realtime and audio; Google Live API reference and session management
    (dynamic examples; checked 2026-07-22)"
ai_learning_stage: 8. Extended applications and complex collaboration
ai_learning_order: 51.5
ai_learning_schema: 2
ai_learning_id: realtime-multimodal-interaction
ai_learning_domain: multimodal
ai_learning_catalog_order: 5150
ai_learning_hard_prerequisites: []
ai_learning_track_multimodal_realtime_order: 700
ai_learning_track_multimodal_realtime_kind: core
content_tier: advanced
difficulty: intermediate-advanced
estimated_hours: 12-16
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/00-目录.md
translation_source_hash: 82b8169f966c8a4660171b47aad25e2dd8c00db2f4f5faec3d23b2d627191478
translation_route: zh-CN/实时多模态交互/00-目录
translation_default_route: zh-CN/实时多模态交互/00-目录
---

# Real-Time Multimodal Interaction

## Course overview

A real-time voice agent is not finished once [[speech-recognition/00-index|ASR]], an LLM, and [[text-to-speech/00-index|TTS]] are connected in sequence. It is an event system that continuously receives media, interprets turns, lets the user interrupt, calls tools, and recovers after network instability. Its real engineering boundary is:

\`\`\`text
Media frames and playback buffers
  ↕
Session events: turn / response / interruption / tool / timeout
  ↕
Authoritative state and a side-effect ledger
\`\`\`

This course compares a cascaded \`ASR → LLM/runtime → TTS\` design with direct speech-to-speech, then establishes vendor-neutral contracts for the media, control, and state planes. The focus is not a particular product's parameters, but how to prove that old output really stopped, a tool result belongs to the right call, a disconnect did not duplicate a side effect, and an end-to-end task genuinely completed.

> [!info] Boundary for dynamic facts
> W3C/IETF specifications, papers, and product documentation were reviewed on **2026-07-22**. The W3C WebRTC Recommendation includes a marked candidate amendment, while Media Capture and Streams remains a Candidate Recommendation Draft. Current OpenAI documentation distinguishes voice-agent, real-time translation, and real-time transcription session purposes; Google Live transcripts and server content can also arrive independently with no ordering guarantee between them. These are observations about product interfaces, not this course's stable event semantics: map them through an adapter to your own event contract, recheck the target version, and run integration tests. If AG-UI appears in the ecosystem, treat it only as an observation about an agent-to-frontend event protocol, not as a stable dependency of this course.

## Where this fits in the overall path

Complete these first:

- [[multimodal-ai/00-index|Multimodal AI]]: media-input contracts, spatiotemporal evidence, and multi-level evaluation;
- [[speech-recognition/00-index|Speech Recognition]] and [[text-to-speech/00-index|Text to Speech]]: quality boundaries for the input and output channels;
- [[agent-core/00-index|Agent Core]]: model decisions and a deterministic runtime, state, termination, and recovery;
- [[tool-calling-function-calling/00-index|Tool Calling]]: schemas, call IDs, authorization, idempotency, and result validation.

This course combines those capabilities into an interruptible real-time session. You can then explore multilingual real-time translation, shared video/screen input, telephony gateways, embodied interaction, or full-duplex models, but preserve the event contract and application state first.

## Learning objectives

- Compare cascaded and speech-to-speech architectures without mistaking full duplex for a particular model architecture.
- Separate media transport, session control, and authoritative application state, and choose WebRTC, WebSocket, or SIP boundaries for the scenario.
- Design strict event contracts with IDs, sequence numbers, time, correlation, and terminal states.
- Model ASR partial/final/revision, application-level \`turn.commit\`, and actual speaker-playback confirmation separately.
- Distinguish VAD, endpointing, semantic turns, and proactive user interruption.
- Stop old generation and clear old playback on barge-in while reconciling already-started tool side effects independently.
- Break down first-packet and end-to-end latency, and define bounded strategies for buffering, jitter, and backpressure.
- Recover long sessions with checkpoints, resume tokens, idempotency, and reconciliation.
- Evaluate turn behavior, task outcomes, tools, recovery, security, cost, and latency together.

## Prerequisites

- You can read and write Python and JSON, and understand event IDs, sequence numbers, timeouts, deadlines, and hashes.
- You understand audio frames, sampling rates, VAD, partial/final transcripts, and streaming playback.
- You understand tool-call schemas, permissions, approvals, idempotency keys, and receipts.
- You do not need to know WebRTC implementation details or any real-time model SDK in advance.

## Three planes that must remain separate

| Plane | Typical objects | You must not assume when it fails |
| --- | --- | --- |
| Media plane | audio/video frames, codecs, jitter buffers, playout | A live connection means the newest content is playing |
| Control plane | transcript revisions, turns, responses, interrupts, playout, tool calls, timeouts | A cancellation or final transcript means playback stopped or authorization was granted |
| State plane | event logs, checkpoints, approvals, receipts, terminal outcomes | A provider session is the source of business truth |

Transport reconnection, session recovery, and business-side-effect reconciliation are three different actions. A design that collapses them into \`reconnected=true\` cannot prove correct recovery.

## Recommended order

| Order | Course | Key question | Completion evidence |
| --- | --- | --- | --- |
| 1 | [[real-time-multimodal-interaction/01-architecture-and-end-to-end-contract\|Architecture and end-to-end contract]] | Cascaded or speech-to-speech? | An architecture ADR and a minimum contract |
| 2 | [[real-time-multimodal-interaction/02-session-events-and-transport-boundaries\|Sessions, events, and transport boundaries]] | What are WebRTC, WebSocket, and SIP each responsible for? | A three-plane event table |
| 3 | [[real-time-multimodal-interaction/03-vad-turns-and-user-interruption\|VAD, turns, and user interruption]] | How do you stop old output without incorrectly rolling back tools? | A barge-in sequence and race-condition tests |
| 4 | [[real-time-multimodal-interaction/04-low-latency-backpressure-and-jitter\|Low latency, backpressure, and jitter]] | How do speed, stability, and completeness trade off? | A segmented latency budget and network slices |
| 5 | [[real-time-multimodal-interaction/05-tool-calling-and-conversation-state\|Tool calling and conversation state]] | How do partials, turns, responses, and calls correlate? | An authoritative ledger and side-effect protocol |
| 6 | [[real-time-multimodal-interaction/06-disconnect-recovery-timeouts-and-terminal-states\|Disconnect recovery, timeouts, and terminal states]] | Where do you resume after reconnecting? | A checkpoint/reconcile state machine |
| 7 | [[real-time-multimodal-interaction/07-privacy-security-and-trust-boundaries\|Privacy, security, and trust boundaries]] | How do you control a continuous microphone and untrusted speech? | A threat model and approval boundary |
| 8 | [[real-time-multimodal-interaction/08-end-to-end-evaluation-and-offline-project\|End-to-end evaluation and the offline project]] | How do trials prove that the system is usable? | 33 offline contract tests |

## Hands-on entry point

The project uses only the Python 3 standard library. It does not capture or generate audio, access the network, call a model, or execute a real tool:

\`\`\`powershell
Set-Location ".\docs-EN\real-time-multimodal-interaction"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B .\examples\realtime_session.py .\examples\session_fixture.json --pretty
python -B -W error .\examples\test_realtime_session.py
python -B -O -W error .\examples\test_realtime_session.py
\`\`\`

The fixture covers audio frames and turns, an exact duplicate event, interruption of old output, tool correlation, a disconnect checkpoint/resume, and a normal terminal state. The tests also cover incorrect sequence numbers, silence-only commits, unknown/extra fields, incorrect correlations, resume tokens, timeouts, output-queue limits, rejection of old output, and illegal events after termination.

## Mastery criteria

- [ ] I can explain the observability, latency, and replaceability trade-offs between cascaded and speech-to-speech designs for a real scenario.
- [ ] I can explain that SIP is a session-signaling boundary, not audio media itself.
- [ ] I can give \`event_id\`, \`turn_id\`, \`response_id\`, and \`call_id\` one responsibility each.
- [ ] I can explain why VAD detecting sound does not mean the user has finished speaking.
- [ ] I can prove that barge-in clears the old playback buffer and the old response cannot revive.
- [ ] I can handle “tool not executed,” “tool committed,” and “tool result unknown” separately on interruption.
- [ ] I can report segmented p50/p95/p99 latency, interruption quality, and task outcomes rather than only average time to first packet.
- [ ] I can recover application state from a checkpoint and reconcile transport, session, and side-effect layers.
- [ ] I can run and explain the 33 standard-library tests and the real-system properties the simulator does not prove.

## Primary references

| Topic | Primary source and status |
| --- | --- |
| Browser real-time media | [W3C WebRTC Recommendation](https://www.w3.org/TR/webrtc/) (the page includes a marked candidate amendment; checked 2026-07-22) |
| Media capture, tracks, permissions, and indicators | [W3C Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/) (Candidate Recommendation Draft, 2025-10-09; checked 2026-07-22) |
| WebSocket | [IETF RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455) |
| SIP signaling | [IETF RFC 3261](https://datatracker.ietf.org/doc/html/rfc3261) |
| Real-time turn evaluation | Lin et al., [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721) (ASRU 2025, arXiv v3) |
| Tools and disfluent-speech evaluation | Lin et al., [Full-Duplex-Bench v3](https://arxiv.org/abs/2604.04847) (2026 work in progress; frontier observation) |
| Dynamic product examples | [OpenAI Realtime and audio](https://developers.openai.com/api/docs/guides/realtime), [Google Live API reference](https://ai.google.dev/api/live), [session management](https://ai.google.dev/gemini-api/docs/live-api/session-management), and [capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) (all checked 2026-07-22) |

## Course boundaries

This course does not teach acoustic-model training, carrier configuration, specific vendor-SDK parameters, or regional legal conclusions. A real deployment still needs to:

- rerun evaluations on the target devices, networks, languages, accents, and noise conditions;
- confirm the provider's current data use, retention, regions, models, and connection limits;
- have authorized legal and security owners determine requirements for recording notices, consent, minors, voiceprints, and cross-border data;
- validate echo cancellation, codecs, jitter, NAT, and telephony-gateway behavior with the real media stack.
