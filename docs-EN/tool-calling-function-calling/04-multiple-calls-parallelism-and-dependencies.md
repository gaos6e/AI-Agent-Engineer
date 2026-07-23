---
title: "Multiple Calls, Parallelism, and Dependencies"
tags:
  - ai-agent-engineer
  - tool-calling
  - concurrency
aliases:
  - Parallel Tool Calling
  - Multiple Tool Calls
source_checked: 2026-07-19
content_origin: original
content_status: dynamic
lang: en
translation_key: "Tool Calling（含 Function Calling）/04-多调用、并行与依赖.md"
translation_source_hash: b4374bfc9a95926d8a903583dc9764754c41236cb0353da266cea88fd5812b06
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/04-多调用、并行与依赖
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/04-多调用、并行与依赖
---

# Multiple Calls, Parallelism, and Dependencies

## Goals

- Distinguish multiple calls in one turn from permission to run them in parallel.
- Use a dependency graph, not model-output order, to schedule work.
- Define join semantics such as all, best effort, and first success.
- Handle partial success, concurrent conflict, compensation, and approval.

## Multiple calls do not grant parallelism

When a model returns several calls in one turn, it has only proposed several actions. Before execution, label every call with:

- resources it reads or writes;
- input dependencies;
- whether it needs output from a previous step;
- tenant, permission, and approval requirements;
- idempotency and concurrency controls;
- how its failure affects other actions;
- whether it can be cancelled or compensated.

Run calls concurrently only when they are independent, have no resource conflict, are separately authorized, can join failures safely, and parallelism does not change business semantics.

## Build a DAG

Example: “create an order for a customer and send a confirmation email”:

~~~text
lookup_customer ─┐
                 ├→ create_order → send_confirmation
check_inventory ─┘
~~~

- 'lookup_customer' and 'check_inventory' can run in parallel.
- 'create_order' depends on both.
- 'send_confirmation' needs the new order ID and must come later.
- If order creation succeeds but email delivery fails, business policy decides whether the order remains.

The model's call-array order cannot replace this dependency graph. If a dependency can only be discovered at runtime, split it into the next model turn or use a deterministic workflow orchestrator.

## Four join strategies

| Strategy | When to use it | Output requirement |
| --- | --- | --- |
| all | Every result is required | A failure prevents downstream work |
| best effort | Independent search or collection | Retain successful items and explicit missing items |
| first success | Race equivalent sources | Cancel or ignore the rest and record the winner |
| quorum | Multi-source consistency | Define the required count and conflict handling beforehand |

Each result still has its own call-ID envelope. Do not concatenate results into prose and make the model guess their correspondence.

Joining must not “zip by array position” either. This repository's 'validate_result_set' first creates a unique mapping by '(provider response ID, call ID)', then recomputes the operation, principal, tool contract, and call binding for every item. Reordering the result list is acceptable; missing, duplicate, unknown, or swapped audit identity must fail. This check establishes correlation integrity, not that the handlers can safely run in parallel.

## Concurrency limits and tail latency

Parallelism can reduce total duration, but it can also:

- amplify downstream bursts;
- trigger rate limits;
- increase partial failures;
- create head-of-line blocking;
- make retry storms worse.

Use maximum concurrency, per-dependency connection pools, a total deadline, cancellation, and circuit breaking. Observe both single-call and fan-out p95/p99, not only the average.

## Writes and races

Two calls that modify the same order at once can lose an update. Common controls include:

- database transactions;
- optimistic version numbers / 'If-Match';
- compare-and-set;
- per-resource serial queues;
- unique constraints;
- idempotency keys;
- business state machines.

“The model believes these can run in parallel” is not concurrency control.

## Approval must cover the whole preview

Several write calls can first produce one plan:

~~~text
1. Create order: item A × 2, ¥200
2. Apply coupon C10, -¥10
3. Send confirmation to user@example.com
~~~

Approval must bind the arguments for every item and the combined version. Reapprove if parameters or the plan change during execution. Do not approve “place an order” first and then let the model freely add a recipient or amount.

## Partial success and compensation

Across services there is usually no single ACID transaction. Define explicitly:

- **Continue:** email fails but the order remains valid; enter 'PARTIAL_SUCCESS' and retry the email.
- **Compensate:** the order is created but inventory reservation fails; cancel the order.
- **Human repair:** compensation also fails; produce diagnostics and a work item.
- **Irreversible:** a message has been sent; deleting a record does not “revoke” it.

Compensation is not synonymous with rollback. It can fail and needs idempotency too.

## Provider parallel capabilities

As of 2026-07-19:

- OpenAI documentation says a model can propose several function calls in a turn and that 'parallel_tool_calls=false' limits it to zero or one. Parallel function calling cannot be used with built-in tools at present, and strict mode is disabled when a fine-tuned model calls multiple functions in a turn.
- Gemini documentation describes parallel and compositional function calling.
- Anthropic client tool use can return multiple 'tool_use' blocks.

These capabilities affect only how calls are expressed. The application must still decide scheduling, dependencies, concurrency, permissions, and joins. Where support is unavailable, serialize safely and prove unchanged semantics with end-to-end tests.

## Practice

Given:

1. Look up a customer.
2. Check inventory.
3. Create an order.
4. Charge payment.
5. Send confirmation.
6. Write an audit record.

Complete the following:

- draw a DAG;
- label read and write resources;
- choose a join strategy for each fan-out;
- define the final state when creation succeeds but payment fails;
- assign idempotency keys for retries;
- explain which calls need one preview approval;
- write the human path after compensation fails.

## Common mistakes

- Running every call in parallel because the provider returned several.
- Correlating results by array position rather than call ID.
- Showing an order as never having happened because email failed.
- Giving several writes one ambiguous approval.
- Writing concurrently with no version or unique constraint.
- Compensating with no idempotency or monitoring.
- Retrying every branch forever after a concurrent failure.

## Self-check

1. What conditions must hold before two calls can run in parallel?
2. How do all and best effort differ in user-visible semantics?
3. Why is compensation not the same as a database rollback?
4. How do provider parallel tool calls differ from application concurrency scheduling?
5. Why must approval for several writes bind the entire plan?

Next: [[tool-calling-function-calling/05-results-errors-and-untrusted-data|Results, errors, and untrusted data]].

## References

- [OpenAI API: Parallel function calling](https://developers.openai.com/api/docs/guides/function-calling#parallel-function-calling)
- [Google AI: Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Anthropic: Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)

Sources accessed: 2026-07-19. Recheck parallelism and built-in-tool compatibility rules against the target API and model version.
