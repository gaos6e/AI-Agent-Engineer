---
title: "Offline Collaboration Simulator Project"
tags:
  - multi-agent
  - project
  - python
aliases:
  - Multi-Agent Offline Project
  - Collaboration Scheduling Simulator
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/03-项目与自测/08-离线协作模拟项目.md
translation_source_hash: a2477fa3c8bce25d0a38eaa5efe921899009cde8f1c0840156bc5af0affa53b2
translation_route: zh-CN/多Agent协作/03-项目与自测/08-离线协作模拟项目
translation_default_route: zh-CN/多Agent协作/03-项目与自测/08-离线协作模拟项目
---

# Offline Collaboration Simulator Project

## Project goal

Simulate multi-agent collaboration with a fully deterministic scheduler and no model calls. You will verify that work runs only after dependencies are satisfied, role permissions are bounded, failures receive only bounded retry, budget is global, results with the same key and the same local sorted-key JSON digest do not commit twice, same-key/different-result conflicts freeze as `needs_review`, and every step emits a state-version trace event.

## Files

- [collaboration_simulator.py](multi-agent-collaboration/project-and-self-check/examples/collaboration_simulator.py) — standard-library implementation that reads a scenario and runs the state machine.
- [scenario.json](multi-agent-collaboration/project-and-self-check/examples/scenario.json) — synthetic roles, tasks, failure plan, and budget.
- [test_collaboration_simulator.py](multi-agent-collaboration/project-and-self-check/examples/test_collaboration_simulator.py) — success, permission denial, retry, and budget-stop coverage.
- [test_contract_and_cli.py](multi-agent-collaboration/project-and-self-check/examples/test_contract_and_cli.py) — strict scenario contracts, CLI, and idempotent-result conflict freezing.

These fixtures contain no real conversation, credential, or external data.

## Scenario structure

Roles declare capabilities. Tasks declare `owner`, `requires`, `capability`, `max_attempts`, and `outcome_plan`. An `outcome_plan` is a deterministic result sequence — for example, `transient_error` followed by `success` — used to test retry, not model reasoning.

Each scheduler round:

1. finds pending tasks whose dependencies succeeded;
2. checks the global `step_budget`;
3. verifies that the task owner has the needed capability;
4. produces one planned result;
5. moves through `running` to an allowlisted `succeeded`, `pending`, `failed`, or `denied` state according to that result and `max_attempts`;
6. blocks every unstarted dependent descendant of a failure, denial, or conflict to a fixed point, then distinguishes success, upstream-failure blocking, and dependency deadlock.

The result receiver accepts a success only for a `running` task. It stores `(task_id, idempotency_key, payload digest)`, where the digest is this example's fixed Python sorted-key JSON serialization. It is reproducible, but not a cross-language canonical-JSON standard. Same key/same digest produces `duplicate_result_ignored`. Same key/different digest produces `result_conflict_detected`, raises the task to `needs_review`, clears the public `result`, and marks `result_trust: conflicted`. To make offline assertions reviewable, the report deep-copies both **synthetic** payloads, digests, arrival order, and state version into `result_conflicts`, and blocks unstarted dependent descendants. A real system stores protected evidence references, `state_version`, lease, and external receipt durably, and isolates downstream side effects that have already started for human query or compensation.

## Run it

In PowerShell 7, enter this directory and run:

```powershell
python -B .\examples\collaboration_simulator.py .\examples\scenario.json
python -B -m unittest discover -s .\examples -p 'test_*.py' -v
python -B -O -m unittest discover -s .\examples -p 'test_*.py'
python -B -W error -m unittest discover -s .\examples -p 'test_*.py'
python -B -O -W error -m unittest discover -s .\examples -p 'test_*.py'
```

You can also write a report to a temporary location:

```powershell
python -B .\examples\collaboration_simulator.py .\examples\scenario.json --output "$env:TEMP\multi-agent-report.json"
```

The script never accesses the network and does not generate runtime artifacts inside the knowledge base.

Successful completion exits with code 0. A workflow ending in a non-success terminal state such as `failed`, `deadlock`, `needs_review`, or `budget_exhausted` exits with code 1. A scenario-contract error exits with code 2. The 66 tests cover strict JSON, role/task contracts, permissions, allowlisted state transitions, reverse-order multilayer dependencies, retry, deadlock, idempotency, conflict freezing, budget, event sequence, and CLI behavior.

## Read the output

The report contains `status`, `steps_used`, `tasks`, and `events`. Check:

- after `transient_error`, there is only the permitted next attempt;
- absent capability leads to `denied` rather than changing roles to evade policy;
- a failed dependency blocks its downstream task;
- same key/different result produces `needs_review`, clears public `result`, and retains synthetic conflict evidence only for reconciliation;
- each event has `task_id`, `attempt`, `state_version`, `from`, `to`, and `reason`;
- `steps_used` does not exceed `step_budget`.

## Modification exercises

1. Add a review task parallel to the aggregation task and observe the critical path.
2. Remove a role capability and confirm policy denial.
3. Lower `step_budget` and confirm the terminal state becomes `budget_exhausted`.
4. Make A depend on B and B depend on A, then confirm the report identifies `deadlock`.
5. For one `(task_id, idempotency_key)`, submit equivalent JSON with different field order and then different JSON. The first must not change state repeatedly. The second must retain digest/evidence, freeze as `needs_review`, clear public result, and block unstarted downstream tasks.

## Mastery checklist

- [ ] I can explain why this project simulates runtime collaboration rather than multiple “personas.”
- [ ] I can point out the layer that validates task contract, state machine, budget, and permission.
- [ ] I can distinguish retryable, denied, blocked, deadlock, and budget_exhausted.
- [ ] I can distinguish a safely replayable duplicate result from a same-key conflict that requires human reconciliation, and explain why this example's digest rule is not an interoperability standard.
- [ ] I can find the earliest failure from event tracing.
- [ ] I can explain why a real system still needs model-call adapters, durable storage, authentication, rate limiting, and sensitive-log governance.

## Self-check

1. If a task already `succeeded`, how should a late `failed` result be handled?
2. Why may individual agents not each count the global budget independently?
3. If a downstream task cannot run because its dependency failed, should it be `failed` or `blocked`?
4. How would you make this simulator recoverable without repeating side effects?
5. Why must a same-key but different-payload result not continue automatically with the first or last arrival?

## Limits

The project has no concurrent threads, network transport, real model, durable queue, or human-approval UI. It validates control semantics only. In particular, it does not prove cross-process leasing, atomic compare-and-set, real identity, protected evidence storage, or human-reconciliation recovery. Before moving it into a framework, preserve the same state, budget, and acceptance tests and add those durable control planes.

## References and next step

Return to [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]], then combine it with [[runtime-monitoring/00-index|Runtime Monitoring]] to establish tracing for a real system.
