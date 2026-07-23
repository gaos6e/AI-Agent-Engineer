---
title: "VAD, Turns, and User Interruption"
tags:
  - ai-agent-engineer
  - realtime
  - vad
  - barge-in
aliases:
  - Turn Detection and Barge-in
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/03-VAD轮次与用户打断.md
translation_source_hash: 7f33ddae6f4ae45ba4f12df5f211ba47d93ead6fbe45ed5c8d01c24e14f5a0dc
translation_route: zh-CN/实时多模态交互/03-VAD轮次与用户打断
translation_default_route: zh-CN/实时多模态交互/03-VAD轮次与用户打断
---

# VAD, Turns, and User Interruption

## Why it matters

VAD (voice activity detection) answers “does someone seem to be speaking now?”, not “is the user's meaning complete?” Treating a short pause as an ending causes the agent to talk over the user; waiting too long makes it feel sluggish. User interruption also races with generated audio, the client playback queue, and tool calls that have already started.

## How to implement it

Split a turn into four signal layers:

1. Audio activity: speech start/end, noise, and echo;
2. Endpointing: silence thresholds, maximum turn length, and manual submission;
3. Semantic turn: whether syntax/intent is sufficient to act;
4. Control events: \`turn.commit\`, \`user.interrupt\`, and \`response.cancel\`.

\`\`\`mermaid
sequenceDiagram
    participant U as User / microphone
    participant C as Client playout and VAD
    participant R as Session runtime
    participant T as Tool executor
    U->>C: New speech frame (barge-in)
    C->>R: user.interrupt(turn-2, response-1)
    par Stop old output
        R-->>C: cancel response-1
        C->>C: Stop immediately and clear the old buffer
    and Reconcile side effects
        R->>T: query(call-id / idempotency-key)
        T-->>R: not-started / committed / unknown
    end
    C->>R: audio.frame*(turn-2)
    C->>R: turn.commit(turn-2)
    R-->>C: New response-2 or clarification
\`\`\`

> **Figure 2: Dual-track processing of a user interruption.** Text alternative: after the client detects new speech, it immediately cancels and clears playback of the old response. At the same time, the runtime independently queries whether the old tool call never started, committed, or is unknown, and only then processes the new turn. Basis: current behavior notes for VAD/interruption and pending function calls in [Google Live capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities), turn/interruption evaluation questions in [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721), and agent idempotency principles. License status: this diagram is original to this knowledge base and does not copy third-party graphics. The repository currently does not declare a separate license that applies to all original body text, so no additional license is asserted here; the project owner must confirm the scope of public use. Regeneration: render the Mermaid source on this page directly.

The completion condition for barge-in is not “a cancel was sent.” The old response must enter an irreversible canceled state, the client must no longer play old chunks, late old chunks must be dropped by response ID, and the tool state must be reconciled or explicitly marked \`unknown\`. Treat microphone echo, background speech, and brief backchannel words as separate test slices.

## Common failures

- Committing a turn whenever VAD fires, so a cough or keyboard noise makes the model act.
- Canceling generation on the server while the client still plays hundreds of milliseconds of buffered old audio.
- Reusing an old \`response_id\`, so late audio “revives” in a new turn.
- Treating an interrupt as a transaction rollback when a write tool may already have committed.
- Testing only quiet single-speaker recordings, not echo, crosstalk, overlap, or self-correction.

## How to validate

Record monotonic times for speech start/end, commit, first output, interruption, the last actual old-audio playback, and tool receipts. Evaluate interruption-detection precision/recall, false-interruption rate, latency from user speech to old-playback stop, post-interruption task recovery, and late-chunk leaks. Slice thresholds by device, language, and noise; do not use one global average.

## Practice task

Write expected event sequences for these four audio cases: a natural pause, mid-sentence hesitation, proactive user correction, and speaker echo. State which cases update only VAD, which commit, which cancel, and how to respond when a tool has already committed.

## Evidence and next step

[Full-Duplex-Bench](https://arxiv.org/abs/2503.04721) treats pauses, backchannels, turn taking, and interruption as separate real-time behaviors. It is a research-evaluation framework, not a complete production-acceptance suite. Product behavior depends on the target version. Next: [[real-time-multimodal-interaction/04-low-latency-backpressure-and-jitter|Low latency, backpressure, and jitter]].
