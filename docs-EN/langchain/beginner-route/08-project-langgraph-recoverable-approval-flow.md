---
title: "Project: LangGraph Recoverable Approval Flow"
aliases:
  - LangGraph Durable Approval Flow
  - LangGraph Layer C
  - LangGraph Layer B
tags:
  - langgraph
  - persistence
  - human-in-the-loop
  - project
source_checked: 2026-07-22
content_origin: original
content_status: validated
execution_verified: 2026-07-22
lang: en
translation_key: "LangChain/00-初学者路线/08-项目-LangGraph可恢复审批流.md"
translation_source_hash: ab097ff7b43358bfc127f853940981c92dca8e7dfc9bff6c3060e54b5f31909c
translation_route: zh-CN/LangChain/00-初学者路线/08-项目-LangGraph可恢复审批流
translation_default_route: zh-CN/LangChain/00-初学者路线/08-项目-LangGraph可恢复审批流
---

# Project: LangGraph Recoverable Approval Flow

## Project objective

This layer runs `langgraph==1.2.9` directly with a SQLite checkpointer, does not call a model, and needs no API key. It proves four concrete facts: the graph pauses at `interrupt()`; checkpoints survive across Python processes; the same `thread_id` can resume through `Command(resume=...)`; and the node containing an interrupt restarts from its beginning.

The example action is only a deterministic text-normalization dry run. It does not send email, charge money, or write a business system, so “checkpoint recovery succeeded” must not be described as “external side effects ran exactly once.”

## What the three project layers each prove

| Layer | Files | Scope of proof |
| --- | --- | --- |
| Layer A | `offline_agent_loop.py` | Framework-independent tool schema, allowlist, call ID, budget, and fail-closed behavior |
| Layer B | `langchain_layer_b/` | Message flow, ToolNode dispatch, and explicit schema-error policy in real `create_agent` at a pinned version; no provider-protocol proof |
| Layer C | `langgraph_layer_b/` | `StateGraph`, SQLite checkpointer, interrupts, recovery, and thread guards at a pinned version |

All three layers are necessary. Layer A prevents safety responsibilities from being handed to the framework; Layer B prevents the course from discussing only `create_agent` conceptually; Layer C places recoverable control flow in a real runtime. This page retains the `LangGraph Layer B` alias for compatibility with old links, but the current learning route positions it as Layer C.

## Graph and recovery boundary

~~~mermaid
flowchart LR
    A["new thread: start"] --> B["prepare: normalize and fingerprint the action"]
    B --> C["review: interrupt"]
    C -. "durability=sync" .-> D[("SQLite checkpoint")]
    E["new Python process"] --> F["validate trusted owner, next node, and pending interrupt"]
    F -->|"same thread_id + Command(resume)"| D
    D --> C
    C --> G{"are approval object and fingerprint valid?"}
    G -->|"approved"| H["execute: create dry-run receipt"]
    G -->|"rejected"| I["rejected"]
~~~

Recovery does not “continue from the line after `interrupt()`.” LangGraph reruns the `review` node from its beginning, then makes the resume value the return value of `interrupt()`. The example observes two entries with a counter in tests, but real business code must not put non-idempotent writes before an interrupt.

## File structure and dependencies

~~~text
examples/langgraph_layer_b/
├── langgraph_approval_flow.py
├── requirements.txt
└── test_langgraph_approval_flow.py
~~~

`requirements.txt` pins only two direct dependencies:

~~~text
langgraph==1.2.9
langgraph-checkpoint-sqlite==3.1.0
~~~

The isolated installation on 2026-07-22 also resolved `langgraph-checkpoint==4.1.1` and `langchain-core==1.5.0`. The teaching files are not a complete production lock; a later resolution can obtain different transitive dependencies, and a long-lived project must preserve the fully resolved lockfile.

## Create an environment outside the vault

Run the following commands from `docs-EN/langchain/beginner-route/examples/langgraph_layer_b`:

~~~powershell
$practice = Join-Path $env:TEMP ("langgraph-layer-b-{0}" -f [guid]::NewGuid())  # Create a unique temporary environment directory outside the vault for this verification run.
py -3.11 -m venv $practice  # Create an isolated virtual environment with the course-verified Python 3.11.
$python = Join-Path $practice "Scripts\python.exe"  # Keep the interpreter's absolute path instead of depending on PowerShell activation state.
& $python -m pip install --upgrade pip  # Upgrade pip in the temporary environment so it uses the current resolver.
& $python -m pip install --requirement .\requirements.txt  # Install LangGraph and the direct dependencies required by the checkpoint example.
& $python -m pip check  # Verify that the installed dependency graph has no missing or conflicting packages.
~~~

Before importing LangGraph, the example sets `LANGGRAPH_STRICT_MSGPACK=true` in its **subprocess** to restrict msgpack deserialization to LangGraph’s built-in safe-type allowlist. Any other Python type in a checkpoint fails closed. A production service should set the same policy before importing the framework or supply an equivalent allowlist; do not depend on a stale interactive-shell environment variable. This setting is not the same as the separate pickle option in `JsonPlusSerializer(pickle_fallback=False)`, which the current default configuration already disables. Strict msgpack lowers the risk of malicious type import/construction, but it does not provide encryption at rest, tenant authorization, or database access control.

## Pause and resume with two processes

~~~powershell
$db = Join-Path $env:TEMP ("langgraph-approval-{0}.sqlite3" -f [guid]::NewGuid())  # Create a unique temporary SQLite path for approval checkpoints.
$thread = "tenant-a:approval-001"  # Set the example's durable thread identifier; it is not an authorization credential.
$owner = "tenant-a"  # Simulate the trusted owner identity obtained by the server after authentication.

# The backticks only continue the same CLI command across lines.
& $python -B .\langgraph_approval_flow.py `
  --db $db --thread-id $thread --owner-id $owner `
  start --text "  agent   reliability  "  # Pass a draft that will be normalized, then stop at the approval interrupt.

# Inspect the persisted, trimmed state read-only; do not print the full checkpoint.
& $python -B .\langgraph_approval_flow.py `
  --db $db --thread-id $thread --owner-id $owner inspect  # Query the current recoverable state for the same thread.

# Resume as the same trusted owner with an explicit human decision and reviewer record.
& $python -B .\langgraph_approval_flow.py `
  --db $db --thread-id $thread --owner-id $owner resume `
  --decision approve --reviewer "reviewer-a"  # Submit approval and let a new process complete the recovery path.
~~~

The first command should return `status=awaiting_approval`, `next=["review"]`, and an interrupt bound to an action fingerprint. The second prints only trimmed state rather than the complete checkpoint. The third reopens SQLite in a new Python process; the terminal state should be `completed` and persist `dry_run_result` together with a deterministic receipt.

The application wrapper calls `get_state()` first and allows resume only for a thread that exists, is bound to the trusted `owner_id`, has `next == ("review",)`, and has exactly one pending interrupt. It also rejects mismatched schema, graph, or policy versions **before** `Command(resume=...)`, and recomputes bindings among normalized input, action fingerprint, and approval request ID. Thus stale or inconsistent state fails closed rather than being handed to the runtime. The example CLI’s `--owner-id` only simulates a subject derived by a server from an authenticated session; it does not authenticate on its own. A real API must not trust an arbitrary client claim. This contract guard is not cryptographic integrity or database access control against an attacker who can directly tamper with SQLite; storage, keys, and authentication/authorization layers must provide those controls. A `thread_id` is only a durable cursor, not an approval credential.

## Run the 10 real-runtime tests

~~~powershell
& $python -B -m unittest -v test_langgraph_approval_flow.py  # Run all 10 real-runtime regression tests in normal mode.
& $python -B -O -m unittest -v test_langgraph_approval_flow.py  # Confirm that critical validation does not rely on bare assert removed by optimization.
& $python -B -W error -m unittest -v test_langgraph_approval_flow.py  # Rerun with every warning treated as a failure.
& $python -B -O -W error -m unittest -v test_langgraph_approval_flow.py  # Cover the combined optimized, strict-warning condition.
~~~

The tests cover: pause payload, recovery across connections, rejection terminal state, unknown thread, duplicate start, `thread_id` normalization of surrounding whitespace, owner mismatch, erroneous resume of a completed thread, tampered approval fingerprints, node replay, and two independent Python processes. Two additional pause-shaped snapshot fakes prove that the application wrapper rejects incompatible schema/graph/policy versions and inconsistent normalized state before calling the runtime, while confirming that the original paused thread in SQLite was not consumed. The normalization case closes and reopens SQLite to confirm inspect and resume use the same durable key; `-O` proves production validation does not depend on bare `assert` statements.

Using isolated dependencies on 2026-07-22, all 10 tests passed once in normal, `-O`, `-W error`, and `-O -W error` modes. The cross-process case actually launched start, inspect, and resume CLI processes that shared a temporary SQLite database; its directory was cleaned up at the end of testing.

## The precise meaning of `durability="sync"`

This project passes `durability="sync"` to `invoke()` explicitly, so a checkpoint is written synchronously before the next step begins. The current runtime also offers durability modes such as `async` and `exit`, which trade throughput against crash windows.

A synchronous checkpoint is still not a cross-system transaction. A real write tool needs its own idempotency key, external receipt lookup, unknown-outcome handling, and reconciliation. A production checkpointer must also verify concurrency, backups, migration, deletion, encryption, and tenant access control. The example’s `SqliteSaver` is positioned only for local learning and small synchronous experiments.

## Acceptance checklist

- [ ] The first process pauses at one unique `review` interrupt.
- [ ] A new process resumes the same thread, and approval and rejection reach different terminal states.
- [ ] A new, owner-mismatched, completed, or unpaused thread cannot be resumed by the application wrapper.
- [ ] Schema, graph, and policy versions, together with approval request ID, action fingerprint, decision, and reviewer shape, are validated.
- [ ] Tests prove the interrupt node reruns, while no business side effect occurs before the interrupt.
- [ ] Explain the distinct roles of the strict msgpack allowlist, the default-disabled pickle fallback, synchronous checkpoints, idempotency, and encryption.
- [ ] Do not describe the SQLite example as a production exactly-once guarantee.

## Next

Continue to [[langchain/beginner-route/09-testing-evaluation-and-upgrade-checklist|Testing, Evaluation, and Upgrade Checklist]] to bring real recovery tests into the dependency-upgrade gate.

## Primary references

API, package versions, and isolated execution were checked on 2026-07-22.

- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [LangGraph Testing](https://docs.langchain.com/oss/python/langgraph/test)
- [SqliteSaver API](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver)
- [PyPI: langgraph 1.2.9](https://pypi.org/project/langgraph/1.2.9/)
- [PyPI: langgraph-checkpoint 4.1.1](https://pypi.org/project/langgraph-checkpoint/4.1.1/)
- [PyPI: langgraph-checkpoint-sqlite 3.1.0](https://pypi.org/project/langgraph-checkpoint-sqlite/3.1.0/)
