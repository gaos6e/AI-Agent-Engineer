---
title: "Disconnect Recovery, Timeouts, and Terminal States"
tags:
  - ai-agent-engineer
  - realtime
  - recovery
  - idempotency
aliases:
  - Real-time session recovery
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/06-断线恢复超时与终态.md
translation_source_hash: 4dbaccc67c95c418169522ac75915c5fbd89ad1d58860c9e263e47e288d2c021
translation_route: zh-CN/实时多模态交互/06-断线恢复超时与终态
translation_default_route: zh-CN/实时多模态交互/06-断线恢复超时与终态
---

# Disconnect Recovery, Timeouts, and Terminal States

## Why it matters

Mobile-network changes, browser sleep, call transfer, provider connection limits, and process restarts all interrupt a session. “The socket reopened” cannot prove that old output stopped, context recovered, or a tool did not execute twice. A session without explicit terminal states can also keep microphones, resources, and approvals alive indefinitely.

## How to implement it

Split recovery into three steps and retain evidence for each:

1. **Transport recovery**: re-establish the WebRTC/WebSocket/telephony media path;
2. **Session recovery**: use a short-lived resume handle bound to a user/tenant and negotiate the last acknowledged event/sequence;
3. **Business reconciliation**: rebuild turns, responses, and outstanding calls from a durable event log/checkpoint, then query side-effect receipts.

Success at step 2 does not mean “resume listening.” It enters a **side-effect reconciliation gate**. That gate processes only queries and receipts for old calls, or an explicit timeout/human handoff; it does not accept new turns, responses, or write tools:

| Reconciliation conclusion | What the runtime may do | What it must not do |
| --- | --- | --- |
| No outstanding calls | Open the gate and accept new work | Treat the old response as still playable |
| A receipt shows committed/failed | Persist the result, explain the known state to the user, then continue under policy | Assume rollback because of model text |
| Confirmed not started | Record the conclusion; if business need remains, start a **new** authorized action | Automatically replay the old write request |
| \`unknown\`, conflicting receipt, or expired permission | Keep the gate, move to \`needs_human\` or controlled reconciliation | Accept a new write action or claim that the outcome is certain |

A checkpoint must at least save the session/version, last acknowledged event, active turn/response, playback generation, outstanding tools and intent digests, approvals, deadlines, and acceptable terminal states. Raw audio should not be retained for a long period by default just because recovery is convenient; retain controlled pointers, summaries, or a necessary window and expire them under the privacy policy.

On disconnect, first freeze new side effects, cancel/isolate the old response, and make the client clear its buffer. After reconnecting, even a late chunk from an old generation is dropped because its response ID/version does not match. A resume token is not a permanent identity credential: it needs a short lifetime, scope, rotation, and server-side verification.

At minimum, distinguish these terminal states:

- \`completed\`: a verifier has proven the goal is complete;
- \`canceled\`: the user/runtime explicitly canceled and side effects have been reconciled;
- \`timed_out\`: the deadline expired and outstanding actions enter reconciliation;
- \`failed\`: an unrecoverable error was recorded with its failure stage;
- \`needs_human\`: state is unknown or risk does not allow automatic continuation.

A timeout is not an exception string. It is a deterministic state transition: stop further generation/calls, clear playback, persist outstanding items, release media resources, and tell the user the boundary between what is known and unknown.

## Common failures

- Relying only on a provider session, so approvals, receipts, and business progress disappear when it expires.
- Automatically replaying the last tool request after reconnection, causing duplicate charges or bookings.
- Letting a server keep generating and performing high-risk actions after the client disconnects.
- Writing a resume token to public logs or long-term storage without binding it to a user/tenant.
- Marking a timeout as \`failed\` and then discarding unknown side effects.

## How to validate

Inject faults at key crash windows: before/after committing a turn, before/after sending a tool request, before/after an external commit, before/after saving a receipt, and while response audio is buffered. On every recovery, verify side-effect count, old-audio leaks, outstanding state, terminal state, and resource release. Also test invalid, expired, and cross-user tokens plus late events during disconnect.

## Practice task

Draw the checkpoint structure for a ten-minute real-time session. Then write a recovery protocol for “payment status is unknown when the network disconnects”: which fields persist, who to query first, when retry is allowed, when to hand off to a human, and what the user hears.

## Dynamic implementation examples and next step

On 2026-07-18, [Google Live session management](https://ai.google.dev/gemini-api/docs/live-api/session-management) showed connection-termination notices, session-resumption handles, and context compression. Those are product mechanisms, not substitutes for an application checkpoint. Lifetimes and compatibility can differ completely across services. Next: [[real-time-multimodal-interaction/07-privacy-security-and-trust-boundaries|Privacy, security, and trust boundaries]].
