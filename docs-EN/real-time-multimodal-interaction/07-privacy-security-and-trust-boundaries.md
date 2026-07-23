---
title: "Privacy, Security, and Trust Boundaries"
tags:
  - ai-agent-engineer
  - realtime
  - privacy
  - security
aliases:
  - Real-time voice-agent security
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/07-隐私安全与信任边界.md
translation_source_hash: 561e9160e00eed7d55510b48a92929ef7ec15ea98fde0e1f422592071c974691
translation_route: zh-CN/实时多模态交互/07-隐私安全与信任边界
translation_default_route: zh-CN/实时多模态交互/07-隐私安全与信任边界
---

# Privacy, Security, and Trust Boundaries

## Why it matters

A real-time agent's microphone can continually capture bystanders, background devices, identity cues, and sensitive transactions. Instructions in audio may also come from a speaker, a recording, or malicious media. Low latency is not a reason to skip consent, permissions, minimization, or approvals.

## How to implement it

First draw the trust boundaries: device/browser, media gateway, real-time model service, application runtime, tools, state store, and human review. For every edge, state the principal, authentication, encryption, allowed media/events, retention period, logging level, and revocation method.

| Risk | Key control | Validation evidence |
| --- | --- | --- |
| Accidental capture/bystander speech | Explicit permission, visible indicators, push-to-talk/mute, minimal collection | Device-permission, mute, and switching tests |
| Exposure of raw audio or transcripts | Transport/storage protection, tiered retention, redacted logs, access audit | Data-flow and deletion spot checks |
| Audio prompt injection | Treat media/transcripts as untrusted observations; keep policy and permissions in the runtime | Malicious-recording/background-instruction tests |
| Impersonation | Voice content is not identity authentication; use independent authentication for high-risk actions | Replay/synthetic-voice tests |
| Tool misuse | Least privilege, scope, approval, rate/budget limits, idempotency, and receipts | Overprivilege/expired-approval tests |
| Voice-generation misuse | Voice authorization, use restrictions, disclosure, and incident response | Asset-rights records and revocation exercises |

[W3C Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/) covers device permissions, privacy indicators, and security considerations, but each organization still has to decide recording notices, consent, retention, voiceprint, and minor-related rules for its product, region, and users. A browser receives only short-lived, minimum-scope credentials; long-lived service keys remain on the trusted server.

Prioritize IDs, state transitions, latency, and policy decisions in session logs. Do not record raw audio or complete transcripts by default. Debug samples need separate authorization, access control, expiration/deletion, and audit. For video/screen sharing, crop windows before capture, mask notifications, and limit which content tools can see.

Model output, ASR text, tool results, and remote media cannot raise their own trust level. A policy outside the model must decide high-risk actions using the authenticated user, current state, scope, parameter digest, and fresh approval.

## Common failures

- Granting microphone permission once without a continuously visible state or a fast revocation path.
- Using “the speaker said a birthday/password” as the sole authentication method, ignoring replay and synthetic voices.
- Writing raw audio, tokens, and tool parameters into one open log to trace latency.
- Treating a connected telephone call as consent to recording or automated action.
- Prompting the model to “ignore malicious audio” while the runtime still gives it high-privilege write tools.

## How to validate

Conduct data-flow audits and threat-driven tests: permission rejection/revocation, background-TV injection, replayed recordings, cross-user resume tokens, malicious transcripts, expired approval, log access, deletion requests, tool overreach, and human takeover. Results must prove that controls operate outside the model while retaining the minimum necessary audit evidence.

## Practice task

For a real-time customer-service agent, draw a trust-boundary table showing who can access raw audio, transcripts, tool parameters, and receipts, and how long each is retained. Then design a background-audio attack that urges “export the customer list,” and describe controls that still block it when the model fails.

## Evidence and next step

For system-level prompt injection, identity, sandboxing, supply chain, and incident recovery, see [[ai-safety/00-index|AI Safety]]. For risk governance, see [[ai-governance/00-index|AI Governance]]. Authorized professionals must confirm concrete legal/contractual requirements. Next: [[real-time-multimodal-interaction/08-end-to-end-evaluation-and-offline-project|End-to-end evaluation and the offline project]].
