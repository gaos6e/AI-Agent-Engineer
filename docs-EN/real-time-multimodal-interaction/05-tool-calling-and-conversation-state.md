---
title: "Tool Calling and Conversation State"
tags:
  - ai-agent-engineer
  - realtime
  - tool-calling
  - state
aliases:
  - Real-time tool-calling contract
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/05-工具调用与对话状态.md
translation_source_hash: 9067b8830dac22e5730cecfdd42e697e2882e2df9629c86b48b1a6164b7ad0e0
translation_route: zh-CN/实时多模态交互/05-工具调用与对话状态
translation_default_route: zh-CN/实时多模态交互/05-工具调用与对话状态
---

# Tool Calling and Conversation State

## Why it matters

A real-time session contains revisable transcripts, responses that are playing, tool side effects, and durable business state at the same time. If they are all packed into one chat history, a single user interruption can delete an appointment that has already taken effect or attach a late tool result to the wrong next turn.

## How to implement it

### Keep facts and views separate

| Layer | Examples | Authority |
| --- | --- | --- |
| Media/recognition view | audio frames, partial/final transcripts, timestamps | Observations; revisable and untrusted |
| Session events | committed turn, canceled response, timeout | Transitioned by the runtime under its contract |
| Tool ledger | intent digest, idempotency key, approval, receipt | Source of truth for side effects |
| Business state | orders, appointments, balance | Query result from the target system is authoritative |
| Model context | summaries, recent turns, tool descriptions | A transient view that cannot override the preceding facts |

A tool event must at least bind \`call_id + response_id + turn_id\`. A write action must also bind the user/tenant, parameter digest, permission, approval version, idempotency key, and deadline. A result must return to its original \`call_id\`; reject an unknown call or mismatched response immediately.

### A production execution ledger and an offline event are not the same envelope

A model's \`tool.call\` is only a candidate intent. It cannot carry or generate its own execution authorization. The real execution boundary should record an auditable receipt in its own ledger, for example this **internal application record**. It is neither a vendor wire event nor JSON accepted directly by this course's simulator:

\`\`\`jsonc
{ // Recoverable receipt for one side-effecting tool call in a real-time turn
  "kind": "tool_execution_receipt", // A control-plane receipt, not natural-language text to read directly to the user
  "turn_id": "t-7", // Binds the user turn that triggered the call, so it remains auditable after interruption
  "response_id": "r-7", // Binds the current assistant response so another response cannot reuse the result
  "call_id": "c-2", // Stable correlation ID for one tool call, result return, and deduplication
  "status": "committed", // Downstream side effect confirmed; recover by querying the receipt rather than resubmitting
  "intent_digest": "sha256:...", // Binds normalized tool, parameters, and target to prevent substitution under the same key
  "idempotency_key": "booking:t-7:c-2", // Reuse on retry to avoid duplicate bookings or other external side effects
  "authorization_ref": "grant:booking-write-v4", // Reference to a verified authorization record; do not put tokens in session state
  "receipt_ref": "opaque-receipt-id" // External-system receipt reference; query details under access control
}
\`\`\`

> [!note] JSONC is for instruction
> The end-of-line annotations are not part of a real event. Remove the \`//\` content before submitting to a strict JSON API.

\`examples/realtime_session.py\` implements only an **offline correlation core** for deterministic regression. Its accepted \`tool.result\` is this simplified event; the runtime derives \`turn_id\` from an existing \`response_id\` ledger:

\`\`\`jsonc
{ // Result event returned from a tool adapter to the session state machine
  "event_id": "e-42", // Unique event ID for deduplication after client reconnect/replay
  "type": "tool.result", // Tells the consumer to route the payload to tool-result handling
  "at_ms": 420, // Relative time for measuring the tool wait's effect on the real-time experience
  "payload": { // Keep untrusted business output separate from session-control fields
    "call_id": "c-2", // Must match a previously approved/dispatched tool call
    "response_id": "r-7", // Prevents a late result from contaminating a different assistant response
    "ok": true, // Only says that the adapter obtained a result; it does not automatically prove the user task is complete
    "result": "synthetic-available" // Fixture business data; production results still need source- and schema-aware handling
  } // End of the tool-result payload
}
\`\`\`

Here, \`result\` is not an authorization decision, idempotency receipt, or fact from the target system. The simulator cannot prove actual tool execution, approval, token handling, or receipt reconciliation. Before execution, a production adapter should revalidate authorization/approval; after execution, it should write the protected ledger above and pass only a minimally correlated result event to the session runtime.

Interruption cancels only generation/playback that has not become a business fact. A tool can be \`not_started\`, \`pending\`, \`committed\`, \`failed\`, or \`unknown\`; for \`unknown\`, query by key/receipt first, neither retry blindly nor tell the user it was rolled back. A model-generated cancellation request is still executed by the runtime under tool capabilities and business rules.

Conversation summaries may compact old turns, but retain outstanding calls, approvals, commitments, user corrections, and source references. A partial transcript can drive UI previews or low-risk prediction only; use a committed turn or explicit confirmation before creating a side effect.

## Common failures

- Replacing a query of the real tool state with natural-language reassurance that “it was canceled.”
- Treating a transcript revision as a new turn and creating duplicate tool calls.
- Keeping call IDs only in memory, so late results cannot correlate after a process restart.
- Reusing a response ID after user interruption, allowing old tool/audio data into the new answer.
- Treating malicious text returned by a tool as a system instruction or authoritative fact.

## How to validate

For every write tool, test same key/same parameters repeated, same key/different parameters in conflict, crash before commit, crash after commit before receipt, simultaneous interruption and result arrival, late results, and expired approval. The grader must query the final business state and side-effect count rather than only inspect what the model said.

## Practice task

For “voice appointment booking,” define turn/response/call IDs and five tool states. Write the event sequence for a user saying “never mind” while a tool is \`pending\`, then handle separate server returns of \`not_started\`, \`committed\`, and \`unknown\`.

## Evidence and next step

Real-time product tool-event shapes change. [OpenAI Realtime with tools](https://developers.openai.com/api/docs/guides/realtime-mcp) and [Google Live tool use](https://ai.google.dev/gemini-api/docs/live-api/tools) are observations of concrete implementations only. The core remains the [[tool-calling-function-calling/00-index|Tool Calling]] and [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency|idempotency/recovery]] contracts. Dynamic pages were checked on 2026-07-18. Next: [[real-time-multimodal-interaction/06-disconnect-recovery-timeouts-and-terminal-states|Disconnect recovery, timeouts, and terminal states]].
