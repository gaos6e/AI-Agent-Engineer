---
title: "Project: Recoverable Task Workflow"
aliases:
  - Resilient Workflow Project
  - Offline Recoverable Workflow Project
tags:
  - ai-agent
  - project
  - python
source_checked: 2026-07-22
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/07-项目-可恢复任务工作流.md
translation_source_hash: 560e4431346f81431bd9aeb00d3f5c647d5b3a65f3533a2ffecdac09f5d006c0
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/07-项目-可恢复任务工作流
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/07-项目-可恢复任务工作流
---

# Project: Recoverable Task Workflow

## Project goal

Implement and verify an offline workflow using only the Python standard library: rule-based routing, parallel read-only fan-out and join, high-risk approval, strict JSON checkpoints that reject duplicate keys, error classification, approval-context fingerprints, idempotent receipts, and recovery after an action committed but the process crashed.

The implementation is [resilient_workflow.py](agentic-design-patterns/beginner-route/examples/resilient_workflow.py), with [test_resilient_workflow.py](agentic-design-patterns/beginner-route/examples/test_resilient_workflow.py). It calls no model, network, or real business service and needs no secret. It demonstrates architecture semantics, not a production approval, distributed locking, or durability solution.

## State machine

```text
start -> checks -> evaluate
  ├─ checks fail -> failed
  ├─ low         -> execute -> done
  └─ high        -> awaiting_approval
                     ├─ reject  -> canceled
                     └─ approve -> execute -> done

checks fail -> failed
commit then crash -> still execute -> recover receipt -> done
```

The check workers never mutate shared state. The main thread writes their results once after joining. On the high-risk path, both read-only checks finish before approval is requested. The approval fingerprint binds normalized action, passed check evidence, risk, and `policy_revision`, so a change rejects an old approval. A stable `action_id` writes the local receipt; recovery reuses a matching receipt rather than submitting again.

> [!warning] Teaching boundary
>
> The checkpoint hash has no secret. It detects accidental corruption or ordinary tampering, not identity. Duplicate JSON keys and incompatible schema version or `policy_revision` fail closed, but the project is not a database transaction, signature, or migration solution. A production system still needs concurrency and access control, encryption, audit retention, explicit migration, and disaster recovery.

## Environment

From the repository root, create an isolated temporary output directory and enter the English course directory:

```powershell
$demo = Join-Path $env:TEMP ("agentic-pattern-" + [guid]::NewGuid()) # Unique temporary artifacts for this run.
New-Item -ItemType Directory -Path $demo | Out-Null # Create the directory without unrelated output.
Push-Location -LiteralPath 'docs-EN\agentic-design-patterns' # Enter the English course tree.
$script = Resolve-Path .\beginner-route\examples\resilient_workflow.py # Resolve the script once.
```

`$demo` is in the user temporary directory and does not create vault artifacts.

## Experiment 1: low risk completes directly

```powershell
python -B $script --checkpoint "$demo\low-state.json" --receipt "$demo\low-receipt.json" --task-id "low-001" --risk low
```

Expected terminal state: `done`. The event history records routing, parallel join, successful evaluation, and action commit. Confirm state and receipt contain the same `task_id` and action fingerprint.

## Experiment 2: high risk pauses, approves, or rejects

First run without a decision:

```powershell
python -B $script --checkpoint "$demo\high-state.json" --receipt "$demo\high-receipt.json" --task-id "high-001" --risk high
$LASTEXITCODE
```

Expected state: `awaiting_approval`; exit code `3`; no receipt file. The checkpoint already holds complete read-only checks. The script rejects an initial `--decision approve` so a CLI argument cannot masquerade as a human approval already displayed. Resume with the same task, risk, and checkpoint:

```powershell
python -B $script --checkpoint "$demo\high-state.json" --receipt "$demo\high-receipt.json" --task-id "high-001" --risk high --decision approve
```

Expected state: `done`. Run another fresh path with `reject` instead: expected `canceled`, exit code `4`, and no receipt. Rejection is not retryable.

## Experiment 3: classified retry

```powershell
python -B $script --checkpoint "$demo\retry-state.json" --receipt "$demo\retry-receipt.json" --task-id "retry-001" --risk low --simulate-transient-once
```

Expected: `done` and `attempts.policy` equal to `2`. On a fresh path, add `--simulate-permanent-policy-failure`. Expect `failed`, exit code `1`, one policy attempt, and no receipt. Retry depends on the error category, not error wording.

## Experiment 4: committed action, stale checkpoint

```powershell
python -B $script --checkpoint "$demo\crash-state.json" --receipt "$demo\crash-receipt.json" --task-id "crash-001" --risk low --crash-after-commit
$LASTEXITCODE
```

Expected exit code: `5`. The receipt exists but the checkpoint remains in `execute`. Re-run the same parameters without `--crash-after-commit`:

```powershell
python -B $script --checkpoint "$demo\crash-state.json" --receipt "$demo\crash-receipt.json" --task-id "crash-001" --risk low
```

Expected event: `action:recovered_existing_receipt`, not a second commit. A receipt belonging to another task is rejected rather than overwritten.

## Exit-code contract

| Exit code | Meaning |
| --- | --- |
| `0` | `done` |
| `1` | Deterministic check failed |
| `2` | Input, checkpoint, receipt, or unpersisted approval decision is unsafe |
| `3` | Waiting for approval; recoverable later |
| `4` | Human rejected; task canceled |
| `5` | Teaching-only crash after commit |

Automation uses exit code and structured JSON together; it must not parse natural-language log messages.

## Code-reading order

1. `new_state` / `validate_state`: strict schema, versions, policy revision, and invariants.
2. `save_state` / `load_state`: hashing, duplicate-key rejection, and atomic replace.
3. `route`: rule-first risk routing.
4. `run_parallel_checks`: no shared worker mutation; one main-thread join.
5. `approval_fingerprint_for`: bind approval to action, evidence, risk, and policy revision.
6. `perform_action`: stable action ID and receipt recovery.
7. `run`: explicit checks → approval → execution transition.
8. `main`: CLI arguments, JSON output, and exit codes.

## Run tests

```powershell
Push-Location -LiteralPath 'docs-EN\agentic-design-patterns\beginner-route\examples'
$env:PYTHONDONTWRITEBYTECODE = '1'
try {
    python -B -m unittest -v .\test_resilient_workflow.py
    python -B -O -m unittest -v .\test_resilient_workflow.py
    python -B -W error -m unittest -v .\test_resilient_workflow.py
    python -B -O -W error -m unittest -v .\test_resilient_workflow.py
} finally {
    Pop-Location
}
```

The suite covers strict state validation, duplicate JSON keys, policy revisions, routing, parallel join, transient and permanent errors, pause only after successful checks, changed approval context, first-call approval bypass, approval and rejection, terminal resume, post-commit crash, and CLI exit codes. `unittest` assertions remain meaningful under `-O`.

## Integrated task

Without weakening current tests, add a third read-only `compliance` branch:

1. Update branch constants, default checks, and strict schema.
2. Make the joiner reject a missing branch.
3. Add transient compliance failure, permanent refusal, and full-success tests.
4. Explain why the branch is independent of the other two.
5. Record test count and normal, `-O`, warnings-as-errors, and combined results.

Passing means more than “the code starts”: a missing new branch must fail closed and existing recovery semantics must remain unchanged.

## Project acceptance

- [ ] Low-risk work reaches `done` and receipt matches task.
- [ ] High-risk work without a decision pauses; rejection creates no receipt.
- [ ] High-risk policy-check failure cannot enter approval; approval binds current action, evidence, risk, and policy revision, and any change is rejected.
- [ ] First invocation cannot treat `--decision` as a displayed human approval.
- [ ] Only `transient` checks retry within budget.
- [ ] Corrupt checkpoints, duplicate keys, unknown fields, and schema/policy mismatch fail closed.
- [ ] A post-commit crash recovers from the matching receipt without a repeated action.
- [ ] Ordinary, `-O`, warnings-as-errors, and combined tests pass.
- [ ] The vault contains no checkpoint, receipt, cache, key, or real credential.

## Course connections

- [[agentic-design-patterns/beginner-route/02-routing-parallelism-and-joining|Routing, Parallelism, and Joining]]
- [[agentic-design-patterns/beginner-route/05-human-approval-and-safety-boundaries|Human Approval and Safety Boundaries]]
- [[agentic-design-patterns/beginner-route/06-failure-recovery-evaluation-and-observability|Failure Recovery, Evaluation, and Observability]]

## References

- [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — recovery and idempotency cautions; checked 2026-07-14.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — checkpoint concepts; checked 2026-07-14.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — evaluation objects; checked 2026-07-14.
- [MCP 2025-11-25: Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) and [A2A 1.0: Security Considerations](https://a2a-protocol.org/latest/specification/) — production protocols still require identity, object-scope, and token verification; checked 2026-07-22.
