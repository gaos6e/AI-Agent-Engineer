---
title: "Sessions, Events, and Transport Boundaries"
tags:
  - ai-agent-engineer
  - realtime
  - webrtc
  - websocket
  - sip
aliases:
  - WebRTC, WebSocket, and SIP boundaries
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/02-会话事件与传输边界.md
translation_source_hash: d36055670bfab3bba0944da436c09e675de2900baf3aa73b8cafe36910b78c0e
translation_route: zh-CN/实时多模态交互/02-会话事件与传输边界
translation_default_route: zh-CN/实时多模态交互/02-会话事件与传输边界
---

# Sessions, Events, and Transport Boundaries

## Why it matters

“Connected” proves only that one channel exists. It does not prove that audio order, the business session, tool results, or the user's playback state agree. Choosing the wrong boundary can leave server keys in a browser, make a WebSocket responsible for media capabilities it does not provide, or mistake SIP signaling for audio transport.

## How to implement it

### Choose a connection by responsibility first

| Boundary | Suitable for | Does not guarantee by itself |
| --- | --- | --- |
| WebRTC | Interactive browser/mobile media that needs media tracks, negotiation, and real-time playback | A business-event schema, tool idempotency, or application checkpoints |
| WebSocket | A server that already has raw media and needs a bidirectional ordered-message channel | Codec negotiation, NAT media traversal, or an adaptive jitter buffer |
| SIP | Establishing, modifying, routing, and terminating telephone sessions | Audio media itself; a media gateway and a media path such as [RTP](https://datatracker.ietf.org/doc/html/rfc3550) are often still needed |

[W3C WebRTC](https://www.w3.org/TR/webrtc/) defines browser APIs for real-time communication; [Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/) defines local-device requests, \`MediaStreamTrack\`, permissions, and lifecycles. [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455) defines the WebSocket protocol. [RFC 3261](https://datatracker.ietf.org/doc/html/rfc3261) makes clear that SIP is an application-layer control/signaling protocol for creating, modifying, and terminating sessions.

### Then define vendor-neutral events

Every event needs at least an \`event_id\`, a \`type\`, monotonic time or ordering information, and a strict \`payload\`. Use distinct correlations for:

- \`turn_id\`: one unit of semantic user input;
- \`response_id\`: one agent output attempt;
- \`call_id\`: one tool intent/result;
- \`session_id\`: the application session, not a socket ID.

\`\`\`mermaid
stateDiagram-v2
    [*] --> Listening
    Listening --> Thinking: turn.commit
    Thinking --> Speaking: response.audio
    Thinking --> WaitingTool: tool.call
    WaitingTool --> WaitingTool: additional tool.call
    WaitingTool --> Thinking: tool.result
    WaitingTool --> Listening: user.interrupt
    Speaking --> Listening: user.interrupt
    Speaking --> Listening: response.completed
    Listening --> Disconnected: transport.disconnected
    Thinking --> Disconnected: transport.disconnected
    WaitingTool --> Disconnected: transport.disconnected
    Speaking --> Disconnected: transport.disconnected
    Disconnected --> Reconciling: transport.resumed
    Reconciling --> Listening: no unresolved call
    Reconciling --> Terminal: timeout / human handoff
    Listening --> Terminal: session.completed / timeout
    Thinking --> Terminal: timeout
    WaitingTool --> Terminal: timeout
    Speaking --> Terminal: timeout
\`\`\`

> **Figure 1: Application-state boundaries for a real-time session.** Text alternative: the session moves from listening to thinking, then may enter tool waiting or playback. While waiting for a tool it may declare additional calls, and returns to thinking only after every call has a result; the user can interrupt a response while it is waiting. Any active phase can disconnect or time out. Reconnection first enters side-effect reconciliation; only when there are no unresolved calls can it return to listening. A timeout or an inability to reconcile safely enters a terminal state or human handoff. Basis: the connection/media lifecycles in W3C WebRTC and Media Capture, the protocol responsibilities in RFC 6455/3261, and this course's application-event contract. License status: this diagram is original to this knowledge base and does not copy third-party graphics. The repository currently does not declare a separate license that applies to all original body text, so no additional license is asserted here; the project owner must confirm the scope of public use. Regeneration: Obsidian or Quartz renders the Mermaid source on this page directly.

Both client and server must treat an unknown event, unknown field, error type, or out-of-range sequence number as a contract error; do not silently ignore it and continue. An exact duplicate of an \`event_id\` may be ignored idempotently, but the same ID with different content must alert. **Re-establishing a recovery channel does not authorize new work**: if a checkpoint has a \`pending\`/\`unknown\` write call, the runtime may accept only its query/receipt, another disconnect, or timeout events. It must not accept a new turn, response, or tool intent until each call has an auditable conclusion.

The offline state machine in this course treats a tool call as **blocking output for the current response**. During \`WaitingTool\`, it accepts only additional \`tool.call\` events, matching \`tool.result\` events, user interruption, disconnect, or timeout, and rejects new audio frames, output audio, and response completion. A real full-duplex product that lets capture or playback continue while a tool runs cannot reuse this single \`phase\`; model capture, playout, and side effects as concurrent states instead, then redefine interruption, backpressure, authorization, and recovery tests.

## Common failures

- Treating a provider connection ID as the business \`session_id\`, then losing approvals and tool receipts after reconnecting.
- Putting audio binary frames, control events, and sensitive credentials into one undifferentiated log.
- Using arrival order in place of sequence numbers, so retries append duplicate audio or transcripts.
- Marking a task successful because a SIP call connected, while ignoring media and business terminal states.
- Keeping long-lived server credentials in a browser or letting an untrusted frontend expand tool permissions itself.

## How to validate

Use contract tests to inject unknown fields, duplicate IDs, out-of-order frames, disconnects, reconnects, and late events. Keep transport tests separate from business tests: the former prove media can arrive; the latter must prove turn/response/call correlations, old-output stopping, checkpoint recovery, and final external state.

## Practice task

For a browser voice agent, draw three tables for the media, control, and state planes: data owner, channel, ID, ordering, retention, retry, and terminal state. Then describe where SIP and a media gateway would sit if the agent added telephone access.

## Dynamic implementation examples and next step

The [OpenAI Realtime overview](https://developers.openai.com/api/docs/guides/realtime) documented WebRTC, WebSocket, and SIP separately for browser/mobile, server media pipelines, and telephone scenarios on 2026-07-18; that is a product interface at that time, not a general specification. [Google Live session management](https://ai.google.dev/gemini-api/docs/live-api/session-management) shows a different design for connection limits, recovery handles, and impending-disconnect events. Recheck both during integration. Next: [[real-time-multimodal-interaction/03-vad-turns-and-user-interruption|VAD, turns, and user interruption]].
