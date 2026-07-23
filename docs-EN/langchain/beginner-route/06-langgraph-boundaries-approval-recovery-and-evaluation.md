---
title: "LangGraph Boundaries, Approval, Recovery, and Evaluation"
aliases:
  - LangGraph Control Boundary
  - LangGraph Human Approval and Recovery
tags:
  - langgraph
  - human-in-the-loop
  - evaluation
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: "LangChain/00-初学者路线/06-LangGraph边界审批恢复与评测.md"
translation_source_hash: 7548f7f1fd896f35c7bdc141af3b49b7721d3df0307ffe8d8df2edbb3fb0a6b6
translation_route: zh-CN/LangChain/00-初学者路线/06-LangGraph边界审批恢复与评测
translation_default_route: zh-CN/LangChain/00-初学者路线/06-LangGraph边界审批恢复与评测
---

# LangGraph Boundaries, Approval, Recovery, and Evaluation

## Objectives

Decide when to move from a high-level LangChain Agent down to LangGraph. Express a task as explicit state, nodes, edges, and terminal states; use persistence and interrupts correctly; and establish layered tests for nodes, traces, recovery, and final results.

## When to move down to LangGraph

Choose the lowest complexity first:

| Need | First choice | Why |
| --- | --- | --- |
| Two or three fixed steps | Ordinary Python / LCEL | The path is deterministic and needs no state runtime |
| Standard model–tool loop | LangChain `create_agent` | The high-level entry point reduces boilerplate |
| Explicit branches, loops, parallelism, or long waits | LangGraph | Topology and state are visible |
| Paused approval, checkpoint recovery, or old-state migration | LangGraph + durable backend | A runtime-state contract is needed |
| Multiple independent teams or permission domains | Design the system first, then consider subgraphs/multi-Agent | “More nodes” does not mean “add an Agent” |

LangGraph offers the Graph API and Functional API. They are ways of expressing a workflow, not a capability ranking: the Graph API makes topology immediately visible, while the Functional API makes it convenient to add durable-execution semantics to existing functions. A team should select one primary style and avoid moving the same business flow back and forth between two abstractions.

## Begin with a state contract

Do not draw nodes first and then put arbitrary objects into a shared dictionary. State should distinguish at least:

- Original, immutable request references.
- Normalized business fields.
- Model candidate outputs and validation results.
- Tool receipts or references to external results.
- Routing decisions, budgets, error categories, and terminal states.
- Versions of the schema, prompt, model, tools, and graph definition.

A node returns a state update. When parallel branches write the same field, define a reducer; if order changes meaning, do not rely on default overwrite behavior. Sensitive documents and large model responses should usually be stored as controlled references and fingerprints instead of copying their full text into every checkpoint.

## Designing nodes and edges

A good node is a work unit that can be independently tested and whose failures can be classified:

1. Its input and output schemas are explicit.
2. Pure computation is separate from external side effects.
3. Errors are classified as retryable, permanent, business rejection, or outcome unknown.
4. Every loop has a maximum step count, deadline, completion criterion, and human exit.
5. Routing returns only an allowed-node enum; model text cannot become an arbitrary node name.
6. External actions have object-level authorization, an idempotency key, and a completion verifier.

Conditional edges in the Graph API select a path only; they do not replace business validation. Run nodes in parallel only when there is no data dependency, no shared-write conflict, and a bounded total concurrency level.

## The precise boundary of persistence

Official current documentation says that after a graph is compiled with a checkpointer, checkpoints are saved and loaded by `thread_id`. Persistence supports conversational state, human-in-the-loop behavior, time travel, and failure recovery. `InMemorySaver` is appropriate for tests; production needs a durable backend whose tenant isolation, concurrency, backups, encryption, retention, deletion, and schema migration have been verified.

A checkpoint is not a cross-system transaction. If a node crashes after a payment succeeds but before state is written, recovery can still enter the node again. Use a stable idempotency key for external side effects, or query the receipt for the same intent first.

## Real interrupt-resume semantics

The current official Interrupts documentation requires:

1. The graph uses a checkpointer.
2. The invocation configuration provides `thread_id`.
3. A node calls `interrupt()` with a JSON-serializable payload.
4. Recovery uses the same thread ID and supplies a value through `Command(resume=...)`.

The easiest fact to miss is: **recovery re-executes from the beginning of the node containing the interrupt, rather than continuing from the line after it.** Therefore:

- Do not swallow the interrupt runtime exception with a broad `try/except`.
- Do not change the order of interrupts in the same node under unstable conditions.
- Side effects before an interrupt must be idempotent; preferably move them to a separate node after approval.
- Keep approval payloads simple, serializable, and trimmed.
- Do not use `while True + interrupt()` in one node for a complex form. The official guide recommends one interrupt per node invocation, then using a conditional edge to ask again.

The application must also inspect the checkpoint **before** calling `Command(resume=...)`. Experiments pinned to `langgraph==1.2.9` show that resuming a completed thread can merely return old state, while sending resume to a nonexistent thread can even start a new run from `START`. Do not treat the runtime’s default behavior as a business rejection. At minimum check thread ownership, `snapshot.next`, pending-interrupt count, and the approval-action fingerprint.

## What approval must bind

`approved=true` is not enough to authorize an action. Bind an approval request to at least:

- The thread/workflow instance and target node.
- Tool name, normalized parameters, and action fingerprint.
- State, graph, policy, and tool versions.
- Approver identity, role, decision, reason, and time.
- Expiration time and a one-time request ID.

After recovery, verify resources, permissions, and parameters again. If the amount, recipient, or SQL changes, the old approval immediately becomes invalid. Even with `HumanInTheLoopMiddleware` or an interrupt, the tool service must still enforce real authorization server-side.

## Four evaluation layers

1. **Node tests**: use fixed inputs to check state updates, error categories, and side-effect-free branches.
2. **Graph/trace tests**: assert allowed nodes, routing, tools, loop count, and terminal state without requiring brittle token-by-token equality.
3. **Recovery tests**: resume at interrupts, crashes after tool commit, old checkpoints, duplicate events, and late results.
4. **Task evaluation**: assess final business results, evidence, cost, latency, safety violations, and human-takeover rate.

LangGraph’s official testing guide demonstrates compiling nodes separately, using a test checkpointer, `update_state(..., as_node=...)`, and specifying interrupt positions. A passing in-memory saver test does not prove production persistence, concurrency, or disaster recovery is correct.

## Practice

Draw a graph for “generate read-only SQL → static validation → human approval → execution → result verification”:

1. Write the state fields and the source of each field.
2. Mark the interrupt node and the code that recovery will re-execute.
3. Design object-level authorization, an idempotency key, and unknown-outcome lookup for the execution node.
4. Write 12 tests covering at least tampered approvals, expiration, an incorrect thread ID, a crash after tool commit, and an old schema.

## Self-check

- [ ] Explain the boundary between ordinary Python, `create_agent`, and LangGraph.
- [ ] Explain the differences among a thread ID, checkpointer, checkpoint, and store.
- [ ] Explain why code before an interrupt runs again.
- [ ] Bind approval to an action rather than trusting a natural-language description.
- [ ] Distinguish node, trace, recovery, and task-result evaluation.

## Next

First complete [[langchain/beginner-route/07-project-offline-tool-agent-skeleton|Layer A: Offline Tool-Agent Skeleton]], then run [[langchain/beginner-route/10-project-keyless-create-agent-runtime-contract|Layer B: Keyless `create_agent` Runtime Contract]], and finally continue to [[langchain/beginner-route/08-project-langgraph-recoverable-approval-flow|Layer C: LangGraph Recoverable Approval Flow]]. These three steps verify, respectively, a framework-independent executor, the current LangChain harness, and real-runtime recovery semantics. None replaces production tests for provider integration, authorization, or external side effects.

## Source baseline

Official facts and the locked runtime were checked on 2026-07-21.

- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Test](https://docs.langchain.com/oss/python/langgraph/test)
- [LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [[langchain/upstream-references/conceptual-overviews/graph-api|Existing official translation: Graph API]]
