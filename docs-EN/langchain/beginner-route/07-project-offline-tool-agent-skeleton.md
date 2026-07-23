---
title: "Project: Offline Tool-Agent Skeleton"
aliases:
  - Offline Tool Agent Skeleton
  - LangChain Offline Concept Project
tags:
  - langchain
  - project
  - python
source_checked: 2026-07-19
execution_verified: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: "LangChain/00-初学者路线/07-项目-离线工具代理骨架.md"
translation_source_hash: a2b77c07319dbfa6cf56edb7bd7c4f09c9593001c3307ff74105efff25a2ef39
translation_route: zh-CN/LangChain/00-初学者路线/07-项目-离线工具代理骨架
translation_default_route: zh-CN/LangChain/00-初学者路线/07-项目-离线工具代理骨架
---

# Project: Offline Tool-Agent Skeleton

## Project objective

Without installing LangChain, calling a model, or using a key, verify the framework-independent responsibilities in a model–tool loop: the model proposes a structured call; the executor validates it strictly; tools run only from an allowlist; observations return through a call ID; the runtime limits steps, tool count, and repeated calls; and final output retains an auditable trace.

This project is not “rewriting LangChain yourself.” It provides a deterministic control group: after migrating to `create_agent` or LangGraph, if permission, error, budget, or test boundaries disappear, the framework integration has broken the engineering contract.

## File structure

~~~text
beginner-route/examples/
├── offline_agent_loop.py       # Dependency-free model stub, two read-only tools, and a bounded loop
├── lcel_no_key.py              # LCEL example needing langchain-core but no model key
└── test_offline_agent_loop.py  # 63 offline regression tests
~~~

## Loop data flow

~~~text
user message
    ↓
deterministic model stub
    ├─ final ───────────────→ done
    └─ tool_call
         ↓ exact schema + call ID
      allowlist executor
         ↓ argument validation
      calculator / local policy lookup
         ↓ ID-bound tool message
      model stub ───────────→ final
~~~

A model response is allowed exactly two shapes: `final` or `tool_call`. The executor does not trust a tool name or its parameters, and a tool message must return the same `tool_call_id`. Default CLI results do not print raw messages, so full input is not treated as ordinary observability output.

## Run it in PowerShell 7

Run each block below from the project root containing both `docs-EN/` and `.website/`. They do not depend on a previous block having changed the current directory:

~~~powershell
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py 'calculate 12 * (3 + 2)'  # Trigger the bounded calculator tool and verify one normal tool call.
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py 'look up policy privacy'  # Trigger read-only local policy retrieval and check the returned source ID.
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py 'explain tool calling'  # Verify the direct-answer branch without a tool call.
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py --self-test  # Run the script's deterministic built-in self-test without network or model access.
~~~

The expected outcomes are, respectively: one `calculator` call with result 60; a local policy carrying the `offline-policy:privacy:v1` source; a direct answer with no tool call; and five explicit self-checks passing. The script writes no files and makes no network requests.

## Safe-calculator verification

~~~powershell
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py "calculate __import__('os').getcwd()"  # Verify that the AST allowlist rejects a function call instead of running system access.
python -B .\docs-EN\langchain\beginner-route\examples\offline_agent_loop.py 'calculate 2 ** 1000000'  # Verify that an exponentiation with excessive resource risk is rejected structurally.
~~~

The calculator uses a Python AST allowlist and accepts only finite numbers, addition, subtraction, multiplication, division, floor division, modulo, and unary plus/minus. Function calls, attributes, variables, exponentiation, excessively long/deep expressions, division by zero, non-finite numbers, and excessively large results all become structured tool errors. It does not use `eval`.

## Keyless LCEL example

`lcel_no_key.py` demonstrates `RunnableLambda | RunnableParallel`. It needs no model key but does require the project to have `langchain-core` installed. The version below is the verified 2026-07-19 snapshot, not a permanent recommendation; new projects should check PyPI, release notes, and Python constraints again.

~~~powershell
# Run once in isolation; do not create a .venv inside the vault.
uv run --isolated --with 'langchain-core==1.4.9' python -B .\docs-EN\langchain\beginner-route\examples\lcel_no_key.py '  hello   agent  '  # Install the pinned core version temporarily and run the keyless LCEL example.
~~~

When the dependency is absent, the script ends explicitly with exit code `4` and `dependency_missing`. That means the branch was skipped and must not be reported as LCEL having run. On 2026-07-22, the example ran with Python 3.11.9 and isolated `langchain-core==1.4.9`, producing normalized text `hello agent`, character count 11, and word count 2. If you use a persistent venv instead, create it in an exercise project outside the vault, pin the same dependency, and run `python -m pip check`. A team project should also preserve a lockfile and rerun this example and adjacent tests after upgrades.

## Comparison with LangChain concepts

| Offline skeleton | LangChain / LangGraph counterpart | Still owned by the application |
| --- | --- | --- |
| `model_stub` | Chat-model response | Model selection, version, and quality evaluation |
| `validate_model_response` | Message/tool-call schema | Business enums, factual validation, and provenance checks |
| `TOOLS` / `ToolSpec` | `@tool` and tool registration | Object-level authorization, network behavior, and side effects |
| `execute_tool` | Tool executor / middleware | Timeouts, idempotency, credentials, and isolation |
| `tool_call_id` | AI tool call ↔ ToolMessage | Correlation, auditing, and late results |
| `max_model_steps` / `max_tool_calls` | Recursion/run budget | Cost, deadline, and human exit |
| `trace` | LangSmith or custom observability | Redaction, retention, and business outcome |

## Run the 63 tests

~~~powershell
$examples = '.\docs-EN\langchain\beginner-route\examples'  # Keep the test-discovery directory in one variable rather than repeating a long path.
python -B -m unittest discover -s $examples -p 'test_*.py' -v  # Discover and run every adjacent test in normal mode.
python -B -O -m unittest discover -s $examples -p 'test_*.py' -v  # Verify that production validation does not rely on bare assert.
python -B -W error -m unittest discover -s $examples -p 'test_*.py' -v  # Promote warnings to failures to discover compatibility issues early.
python -B -O -W error -m unittest discover -s $examples -p 'test_*.py' -v  # Combine both strict execution conditions for regression verification.
~~~

The tests cover AST resource limits; tool and parameter allowlists; exact message shape; call-ID binding; tool errors; direct answers; both tools; step and tool budgets; stopping repeated calls; raw messages staying out of default CLI output; and both legal LCEL dependency states (present and absent). `-O` proves that tests do not rely on bare `assert` statements removed by optimization. A green run of the base environment’s 63 tests can include `dependency_missing`, so report “the core offline loop passed” and “LCEL passed under the locked dependency” separately. The latter was independently verified with the preceding command.

## Integrated extension task

Add a read-only `lookup_order` tool, but write its contract first:

1. How are `order_id` syntax, length, and current-caller authorization validated?
2. Which fields return to the model and which remain application-only artifacts?
3. How are not-found, unauthorized, and transient errors classified?
4. What are the size limits for one result and for the overall trace?
5. How do you prevent the model from using another user’s order ID for unauthorized lookup?
6. Add tests for a success case, unauthorized access, malformed ID, unknown tool, repeated call, and exhausted budget.

If you turn it into a write tool, add preview, approval, an idempotency key, unknown-outcome lookup, and completion verification. Do not merely change its name from `lookup` to `update`.

## Project acceptance

- [ ] The three example paths produce the expected tool count and terminal state.
- [ ] Dangerous calculations cannot execute arbitrary Python.
- [ ] Tool results correspond strictly to the original call ID.
- [ ] Unknown tools, invalid parameters, repeated calls, and exhausted budgets all fail closed.
- [ ] All 63 tests pass in normal, `-O`, `-W error`, and `-O -W error` modes.
- [ ] The LCEL example runs in a locked `langchain-core` environment rather than only returning `dependency_missing`.
- [ ] Explain what the offline skeleton proves—and what it does not prove about real LangChain APIs, model quality, or production persistence.

## Next

First continue to [[langchain/beginner-route/10-project-keyless-create-agent-runtime-contract|Layer B: Keyless `create_agent` Runtime Contract]] to map the framework-independent tool loop to a real LangChain harness. Then continue to [[langchain/beginner-route/08-project-langgraph-recoverable-approval-flow|Layer C: LangGraph Recoverable Approval Flow]] to map control flow to `StateGraph`, a SQLite checkpointer, and interrupts.

## Source baseline

LangChain concept documentation was checked on 2026-07-14; the `langchain-core` package version and LCEL execution were checked on 2026-07-19.

- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [LangChain Messages](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain Core Runnables](https://reference.langchain.com/python/langchain-core/runnables)
- [PyPI: langchain-core 1.4.9](https://pypi.org/project/langchain-core/1.4.9/)
