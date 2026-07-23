---
title: "Execution Loop and Call Correlation"
tags:
  - ai-agent-engineer
  - tool-calling
  - agent-loop
aliases:
  - Tool Execution Loop
source_checked: 2026-07-19
content_origin: original
content_status: dynamic
lang: en
translation_key: "Tool Calling（含 Function Calling）/03-执行循环与调用关联.md"
translation_source_hash: d75f12cc9e49c47f849b3fd74efdd4f909a8b1cea895915d956eed6e3f1bbc44
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/03-执行循环与调用关联
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/03-执行循环与调用关联
---

# Execution Loop and Call Correlation

## Goals

- Build a provider-neutral state machine for tool calling.
- Correlate every call with its result correctly.
- Distinguish completion, tool need, approval need, refusal, truncation, and failure.
- Stop infinite loops with budgets, duplicate detection, and progress conditions.

## The minimal five-step loop

Current OpenAI documentation summarizes client-side function calling in five steps:

1. Request the model with tools.
2. Receive a tool call from the model.
3. Execute application-side code.
4. Request the model again with the matching tool output.
5. Receive a final answer or further tool calls.

Anthropic client tools likewise need an application-driven loop, although their message blocks and stop reasons differ. Gemini also makes clear that the model does not execute functions for the application.

## Isolate provider differences with an internal state machine

Do not scatter checks for 'function_call' or 'tool_use' throughout business code. An adapter normalizes them into finite states:

~~~text
MODEL_REQUESTED
  ├─ FINAL_TEXT ─────────────→ COMPLETED
  ├─ TOOL_PROPOSALS ─────────→ VALIDATING
  │     ├─ approval needed ──→ WAITING_APPROVAL
  │     ├─ executable ───────→ EXECUTING → RESULTS_READY
  │     └─ invalid/denied ───→ RESULTS_READY(error envelope)
  ├─ REFUSAL ────────────────→ REFUSED
  ├─ TRUNCATED ──────────────→ INCOMPLETE
  └─ API_FAILURE ────────────→ FAILED/RETRY
~~~

'RESULTS_READY' is sent back to the model and can return to 'TOOL_PROPOSALS'. Only an explicit completion reason is success; “no tool call” can instead mean refusal, max tokens, or a service error.

## Five kinds of ID

| ID | Scope | Purpose |
| --- | --- | --- |
| Provider response/item ID | A provider response | Troubleshooting and continuing API state |
| Call ID | One call proposed by the model | Match a tool result to the correct call |
| Operation ID | The business task as a whole | Track across model turns, services, and approvals |
| Idempotency key | Business intent | Prevent retries from creating duplicate side effects |
| Approval ID | Human confirmation record | Audit who approved which action |

A call ID cannot replace an idempotency key: a model retry can emit a new call ID while still representing the same refund intent.

## Call correlation is not result binding

Copying only a 'call_id' onto a result does not stop a well-formed result for A from being substituted for B. The project binds all of the following in protected audit data:

- provider + API family + response ID + call ID;
- operation ID, idempotency key, and adapter revision;
- references to the current tenant and subject;
- input, output, effect, handler, producer, and policy revisions;
- full request SHA-256, result SHA-256, and call-binding SHA-256.

Recompute those values from current trusted context before returning the result; do not only check field presence or digest length. Store a multi-call set by '(response_id, call_id)' and reject missing, duplicate, and unknown results. Array order may change, but correlation identity must not be swapped. See [[tool-calling-function-calling/05-results-errors-and-untrusted-data|Results, errors, and untrusted data]].

## Provider adapter responsibilities

An adapter should:

- parse zero, one, or many calls;
- retain the call ID, name, and raw completion reason;
- parse arguments strictly;
- transform an internal result into the provider's required return shape;
- handle streamed-argument completeness and done events;
- carry conversation or reasoning items required by the provider for continuation;
- map API errors to finite internal states;
- record provider, API, SDK, model, and adapter revision.

This repository's offline adapters currently cover OpenAI Responses 'function_call_output', Anthropic Messages 'tool_result', and Gemini Interactions 'function_result'. They validate the internal dual projection first and place only 'model_result' into the provider payload; 'protected_audit' stays outside the model. Anthropic result blocks must precede ordinary text, and Gemini Interactions currently uses a 'result' field rather than pretending that the three providers share one external message shape.

An adapter should not:

- decide whether a user may refund an order;
- automatically correct an amount or path and execute it;
- call any function name given by the model;
- use provider error text as a business status.

## Registry and dispatcher

~~~python
registry = { # The host maintains a fixed registry rather than importing functions from model output.
    "get_order": ToolSpec( # Establish an explicit contract for the one allowed read tool.
        schema_version="get-order-v1", # Argument/result parsing must match this version.
        risk="read", # A read-only risk class can still be subject to tenant and data policy.
        timeout_ms=500, # Bound external calls so the loop cannot wait forever.
        handler=get_order, # Bind a reviewed local handler function object.
    ) # End get_order specification.
} # End allowlist registry.
~~~

The dispatcher obtains schema, risk, timeout, authorization policy, and handler from the registry. It rejects unknown names. Do not do this:

~~~python
# Dangerous illustration: model text must never choose an executable object from global scope.
handler = globals()[model_name] # Unsafe: any global name can be selected, bypassing the allowlist and risk class.
handler(**model_arguments) # Unsafe: this creates side effects without schema, authorization, budget, approval, or target-scope checks.
~~~

An explicit registry makes the capability surface auditable, testable, and reducible by user or task.

## Per-turn algorithm

~~~text
initialize deadline / budgets
while not terminal:
    call the model
    parse completion reason and calls
    if final → validate and finish
    if refusal/truncated/error → finish in the matching state or recover in a controlled way
    for each call:
        deduplicate call ID
        schema + authorization + policy
        if approval required → persist pause state
        otherwise execute and produce a strict result
    correlate every result and return them
    update progress, cost, and duplicate trace
~~~

Do not occupy a process while waiting for approval. Persist the operation, conversation continuation, call, argument digest, policy version, and expiry; after the user approves, resume and revalidate.

## Loop protection

Set at least:

- a maximum number of model turns;
- a maximum number of tool calls;
- per-tool and overall deadlines;
- token and cost budgets;
- maximum parallelism;
- duplicate detection for 'tool + canonical arguments';
- a no-progress counter;
- result-size limits;
- a human-escalation or safe-stop path.

If the model repeatedly calls the same tool with the same arguments without new information, return structured 'NO_PROGRESS' or escalate to a human instead of feeding the same result back forever.

## Streaming calls

Streaming APIs can send tool arguments in fragments. Parse and execute only after the provider's explicit completion event:

- correlate fragments by item/output index;
- limit accumulated bytes;
- do not run the handler until JSON is complete;
- treat an interrupted stream as incomplete rather than “adding a closing brace” and executing;
- send the final parse through schema, authorization, and approval again.

A progress UI can show “the model is preparing to call X,” but it must not present incomplete arguments as executed.

## Practice

Draw a state machine for “look up order → create refund draft → wait for approval → submit refund → final explanation,” marking:

1. call ID, operation ID, approval ID, and idempotency key;
2. API max tokens;
3. an unknown tool;
4. an expired approval;
5. submission timeout where the downstream system may already have succeeded;
6. the model proposing the identical call again.

For every branch, write a terminal or recovery state; “report an error” is not enough.

## Common mistakes

- Treating 'stop_reason != tool_use' as success.
- Giving multiple calls one unlabelled result string.
- Saving only the call ID and not the business operation.
- Executing streamed arguments before they are complete.
- Keeping approval waits only in process memory.
- Having no deadline or progress condition for an infinite loop.
- Letting provider message shapes leak directly into handlers.

## Self-check

1. Why does no tool call not necessarily mean completion?
2. What do a call ID and an idempotency key each solve?
3. Where is the boundary between adapter and dispatcher?
4. What state must be saved to resume after an approval pause?
5. Why must streamed arguments wait for a done event before execution?

Next: [[tool-calling-function-calling/04-multiple-calls-parallelism-and-dependencies|Multiple calls, parallelism, and dependencies]].

## References

- [OpenAI API: Function calling — The tool calling flow](https://developers.openai.com/api/docs/guides/function-calling#the-tool-calling-flow)
- [Anthropic: How tool use works — The agentic loop](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [Anthropic: Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)

Sources accessed: 2026-07-19. Provider message fields and continuation rules are dynamic adaptation material.
