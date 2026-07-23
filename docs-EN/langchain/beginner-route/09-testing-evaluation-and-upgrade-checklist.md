---
title: "LangChain Testing, Evaluation, and Upgrade Checklist"
aliases:
  - LangChain Upgrade Checklist
  - LangGraph Testing Path
tags:
  - langchain
  - langgraph
  - testing
  - evaluation
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: LangChain/00-初学者路线/09-测试评测与升级清单.md
translation_source_hash: af70f8ab0de19968fcc58bc8e588ff86e36cf35c877b65a0dc8be6546e9bafe9
translation_route: zh-CN/LangChain/00-初学者路线/09-测试评测与升级清单
translation_default_route: zh-CN/LangChain/00-初学者路线/09-测试评测与升级清单
---

# LangChain Testing, Evaluation, and Upgrade Checklist

## Objectives

Build layered verification for LCEL, tool Agents, RAG, and LangGraph; use data rather than a demo to decide model or framework changes; and upgrade rapidly changing packages and provider integrations through a reversible process.

## “It can invoke” is only the first layer

A framework project needs at least seven kinds of evidence:

1. **Pure functions and schemas:** parsing, chunking, routing, parameters, and state reducers.
2. **Tool execution:** authorization, timeout, error classification, idempotency, result size, and redaction.
3. **Nodes and graphs:** state updates, edges, loop limits, interrupts, and terminal states.
4. **Model behavior:** structured output, tool selection, refusal, and citations, allowing reasonable variation in expression.
5. **RAG layers:** parsing, chunks, recall, ranking, generation support, and permission filtering.
6. **Recovery and compatibility:** old checkpoints, duplicate events, post-commit crashes, and changes to model/Prompt/tool versions.
7. **System metrics:** end-to-end success rate, p95/p99, tokens/cost, human takeover, and safety violations.

Unit tests suit deterministic contracts. Model behavior requires fixed datasets, repeated trials, and statistics. Do not use one chat screenshot to prove a regression has passed.

## Choosing test doubles

- Use ordinary functions or deterministic fakes for pure-node tests to isolate state logic.
- Use a model stub that emits fixed tool calls/errors for Agent loops to validate the executor and budget.
- Keep a small number of real API smoke tests for provider integrations; clearly require credentials and control cost.
- Use datasets representative of the real distribution for quality evaluation; do not treat all samples used to train a Prompt as final validation.
- Use mock services for high-risk tools to validate authorization, idempotency, and failure behavior; do not send content to real users.

An all-green mock run proves only the local contract. An all-green real-model smoke test proves only that it was callable at that time. Neither substitutes for the other.

## LangGraph test layers

Official testing guidance recommends making nodes independently callable pure functions where possible; you can also compile a single-node graph to test runtime behavior. To begin from the middle of a graph, use a test checkpointer, `update_state(..., as_node=...)`, and the same thread ID to construct a paused state.

Test at least the following on every critical path:

- normal completion and no-answer/business refusal;
- every conditional-edge enumeration value and a safe default for unknown values;
- loops reaching completion, failure, budget, and deadline;
- interrupt pause, approve, edit, reject, expiry, and an incorrect thread ID;
- re-execution of code before an interrupt when a node resumes;
- no duplicate side effect after a crash that follows the same side-effect commit;
- migration or explicit rejection for old state schemas and graph versions.

`InMemorySaver` is appropriate for tests; it does not prove database-checkpointer concurrency, backup, or access control.

The adjacent Layer B project uses a scripted model in real `create_agent` to validate messages, tool dispatch, and schema-error contracts. It does not prove provider schema conversion or real-model quality. Layer C then uses a SQLite saver to validate cross-process recovery, while rejecting unknown threads, owner mismatches, completed/non-paused threads, incompatible versions, or inconsistent state at the application layer. Neither proves multiple-worker concurrency, disaster recovery, or exactly-once external side effects for a production database.

## What to record in an Agent evaluation

Every evaluation case needs at least a task, input files, environment fixtures, allowed tools, expected outcome, and mechanical assertions. Record for each trial:

- whether the real task completed, rather than whether the model claimed completion;
- tool name, arguments, order, count, error recovery, and attempts to exceed authority;
- final environment state and citation evidence;
- model, Prompt, tool, data, and dependency versions;
- tokens, cost, latency, and human intervention.

For nondeterministic models, run repeated trials and report averages, distributions, and failure types. Separate the tuning set from the locked validation set so that descriptions or Prompts do not merely memorize test questions.

## How to use the current-version snapshot

On 2026-07-22, PyPI was checked for:

| Package | Current release | Release date | Course use |
| --- | --- | --- | --- |
| `langchain` | 1.3.14 | 2026-07-16 | High-level Agent API |
| `langgraph` | 1.2.9 | 2026-07-10 | Stateful graph runtime |
| `langchain-core` | 1.5.0 | 2026-07-21 | Foundational abstractions such as Runnables, messages, and tools |

These are material snapshots, not instructions to manually combine three exact versions in a production requirements file. Install `langchain` and the needed integration packages, let dependency resolution choose compatible dependencies, then preserve the complete lockfile and runtime evidence. [[langchain/beginner-route/10-project-keyless-create-agent-runtime-contract|Lesson 10]] intentionally pins the older but verified `langchain-core==1.4.9` for an isolated teaching harness and fails closed on version verification before it runs. It is a repeatable minimum runtime contract, not a substitute for dependency resolution and a lockfile. Recheck during upgrades rather than treating this table as permanently “latest.”

## Safe upgrade process

1. Preserve the current lockfile, Python version, key configuration, and passing evaluation report.
2. Reproduce production dependencies in a new venv; do not overwrite the only working environment in place.
3. Read official release notes, versioning policy, and migration guides; inspect yanked releases and provider packages.
4. Upgrade one dependency family at a time and record the complete resolved versions, not only top-level packages.
5. Run import checks, static checks, keyless LCEL, offline tools, and the full unit suite.
6. Run graph recovery/old-checkpoint, tool-schema snapshot, and RAG-index compatibility tests.
7. Use controlled credentials for a small number of provider integrations and the locked quality set; record cost and region.
8. Canary-release new instances; pin compatible workers for running old instances or use a verified migration.
9. Use task success, safety, p95, cost, and human-takeover thresholds to decide whether to continue or roll back.

A code rollback cannot undo an email already sent, SQL already executed, or an external system already written. High-risk releases also need reconciliation and compensation plans.

## Common upgrade traps

- Looking only at a successful `pip install` rather than resolved transitive versions.
- Updating an old `LLMChain` example until it imports, then claiming the v1 migration is complete.
- Changing a tool schema or message content blocks without a snapshot/contract test.
- A new model has more reliable structured output, but a deterioration in factual quality or cost goes unnoticed.
- A new worker restores an old checkpoint but changes routing or repeats a side effect.
- A provider package supports parameters differently from a unified-interface description, but there is no real integration test.

## Integrated exercise

For a project that “retrieves a policy and creates a ticket after approval,” write an upgrade acceptance matrix with at least 20 cases:

- 5 deterministic tool and schema cases;
- 5 retrieval and citation cases;
- 4 approval and recovery cases;
- 3 safety/authorization cases;
- 3 real-model quality and cost cases.

Then design the canary, rollback, old-instance handling, and external-side-effect reconciliation steps for moving from the old version to the new one.

## Mastery criteria

- [ ] Distinguish unit, contract, graph, model, RAG, recovery, and system tests.
- [ ] Make an evaluation judge environment outcome rather than final natural-language output alone.
- [ ] Explain what fakes and real-provider smoke tests each prove.
- [ ] Upgrade from a lockfile in a new venv while retaining a rollback environment.
- [ ] Write compatibility acceptance for old checkpoints, tool schemas, and RAG indexes.

## Return to the index

Return to the [[langchain/00-index|LangChain learning route]], then consult the official reference layer as a project requires.

## Source baseline

Official facts and package versions were checked on 2026-07-22.

- [LangGraph Test](https://docs.langchain.com/oss/python/langgraph/test)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangChain Agent Evals](https://docs.langchain.com/oss/python/langchain/test/evals)
- [LangChain Versioning](https://docs.langchain.com/oss/python/versioning)
- [LangChain v1 migration](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [PyPI langchain](https://pypi.org/project/langchain/)
- [PyPI langgraph](https://pypi.org/project/langgraph/)
- [PyPI langchain-core](https://pypi.org/project/langchain-core/)
