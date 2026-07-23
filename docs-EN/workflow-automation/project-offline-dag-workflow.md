---
title: "Project: Offline DAG Workflow"
tags: [ workflow-automation, dag, project ]
aliases: [ Workflow Automation Project ]
source_checked: 2026-07-22
lang: en
translation_key: 工作流自动化/08-离线DAG工作流项目.md
translation_source_hash: a32291fede8a80406fc63066fe9d4b87c0bd460bcb1af19b155af957622a2d88
translation_route: zh-CN/工作流自动化/08-离线DAG工作流项目
translation_default_route: zh-CN/工作流自动化/08-离线DAG工作流项目
---

# Project: Offline DAG Workflow

## Project goal

Run an order workflow from scratch: validate a CloudEvent under a **strict order application profile**, execute `validate`, place `reserve_inventory` and `risk_check` in the same ready batch, wait for approval bound to `charge`, then charge and notify. Failure paths use finite retry, idempotent recovery of a committed result, and compensation for completed side effects after permanent failure.

The project uses Python standard library only and is intended for offline Windows 11 + PowerShell 7 practice. It is a teaching single-process simulator; it does not claim production transactions, queues, or exactly-once.

## Files

- [workflow_engine.py](workflow-automation/examples/workflow_engine.py): definition validation, strict CloudEvent application profile, state machine, retry, approval, checkpoints, idempotent side effects, compensation, and security events.
- [workflow.json](workflow-automation/examples/workflow.json): fixed-version DAG and per-step policy.
- [test_workflow_engine.py](workflow-automation/examples/test_workflow_engine.py): standard-library tests for happy and failure paths.

## Prepare the environment

Use `venv + pip` first. The project has no third-party dependency, so nothing needs installation. Run these commands from the project root that contains both `docs/` and `.website/`; testing returns you to that root.

```powershell
Push-Location -LiteralPath 'docs-EN\workflow-automation' # Enter this course temporarily; Pop-Location restores the original path afterwards.
python -m venv .venv # Create a virtual environment used only for local practice.
.\.venv\Scripts\Activate.ps1 # Activate it in this PowerShell session.
python -m pip --version # Confirm this session actually uses the virtual environment's pip.
```

`.venv` is local learning state and must not enter version control. An existing Python 3 installation also works.

## Step 1: validate the definition

```powershell
python -B .\examples\workflow_engine.py --validate # Validate DAG definition, edges, and contracts only; -B does not produce __pycache__.
```

Definition validation rejects unknown top-level fields, duplicate nodes, unknown dependencies, self-dependencies, cycles, invalid retry configuration, and invalid error types. It prints definition name, version, and SHA-256 fingerprint. The fingerprint detects a different loaded definition on recovery; it is not a security signature.

The trigger profile accepts only this project's event type/data shape. Optional `time` must be a standard-library-parsable RFC 3339 subset with explicit UTC offset; generic CloudEvents extensions are deliberately refused. Event identity is canonical `(source, id)` encoding rather than delimiter concatenation, so `/a + b::c` and `/a::b + c` cannot collide. A real HTTP/webhook ingress must still verify raw-body signature/caller, size, freshness/nonce, and server-side authorization before calling this function.

## Step 2: run the demonstration

```powershell
python -B .\examples\workflow_engine.py # Run the local workflow demo; observe success, waiting, and recovery without contacting external services.
```

The demo establishes three evidence chains:

1. An order event simulates one unknown process result after inventory commits; retry reuses the same idempotent result, producing only one inventory reservation.
2. The workflow pauses for approval, serializes a checkpoint, resumes, and completes through an approval bound to instance, step, payload, version, and expiry.
3. Notification permanently fails for a second instance; registered compensation refunds before releasing inventory, ending at `failed_compensated`.

It uses a temporary directory for checkpoint inspection and leaves no runtime artifact in the knowledge base.

## Step 3: run tests

```powershell
$env:PYTHONWARNINGS = 'error' # Turn warnings into errors so resource/compatibility problems are not ignored.
python -B -m unittest discover -s .\examples -p 'test_*.py' -v # Run workflow-engine regression tests normally and verbosely.
python -B -O -m unittest discover -s .\examples -p 'test_*.py' -v # Verify control flow does not rely on bare assert under optimized mode.
Remove-Item Env:PYTHONWARNINGS # Remove the temporary test setting so it cannot affect later commands.
Pop-Location # Return to the PowerShell directory that was active before entering this course.
```

Normal and `-O` modes must pass. `-O` strips bare `assert`, so the project uses explicit exceptions and `unittest` assertions; this reveals tests that would work only outside optimized mode.

This baseline has 74 tests and is additionally rerun with `PYTHONWARNINGS=error`. Count is only a coverage clue: the evidence is observable assertion for invalid definition shape, RFC 3339 time profile, structured event identity, duplicate event, idempotency conflict, unknown result, approval tampering, checkpoint corruption, exhausted retry, and compensation failure.

## Recommended code-reading order

1. `load_definition()`: strict JSON-shape checks and DAG cycle detection.
2. `validate_event()`, `event_identity_key()`, and `WorkflowCoordinator.start()`: narrow CloudEvents to an application profile, deduplicate canonical `(source, id)`, reject same identity/different payload.
3. `EffectStore.perform()`: bind idempotency key, intent hash, and existing result.
4. `run_until_blocked()`: ready batch, finite retry, approval wait, and terminal state.
5. `encode_checkpoint()/decode_checkpoint()`: checkpoint integrity and strict recovery.
6. `_compensate()`: independent compensation idempotency key, failure state, and observable events.

## Extensions you should complete

### Basic extensions

1. Add `manual_review` branch in `workflow.json`, with a safe default for unknown decision.
2. Give `notify` a maximum delay; do not send stale notification after deadline.
3. Add same-key/different-amount conflict and prove it cannot reuse an old charge result.

### Engineering extensions

1. Store instance, step attempt, lease, and idempotency result in SQLite transactions; an in-process dictionary ceases to be the guarantee boundary.
2. Add a conditional-update test where two workers concurrently claim one step.
3. Add schedule logical fire time plus time-zone/catch-up policy.
4. Replace `risk_check` with a mock LLM node: output schema, fixed evaluation set, model/prompt version, and invalid-output fallback are all required.
5. Add a human queue for `compensation_failed` that permits controlled operations only.

## Production gap checklist

- State and idempotency tables need transactional persistent storage, backup, and access control.
- Multiple workers need leases, heartbeats, and compare-and-set.
- External callbacks need real authentication, replay prevention, and server-side authorization.
- `source + id` becomes usable event identity only after authentication. This example merely requires a nonempty `source`; production gateway should validate URI-reference with protocol library and persist a structured key, payload fingerprint, TTL/retention policy, and conflict handling in its deduplication ledger.
- Checkpoints need protected integrity/authentication, not a plain hash only.
- Logs, metrics, traces, and alerts need controlled backends.
- Credentials belong in secret management, never definition or example environment values.
- Release needs compatibility with old instances and recovery/replay tests on redacted history.

## Runbook exercise

Assume a payment provider returns persistent 503 while queue age rises:

1. Which new triggers stop, and which approved instances stay retained?
2. How do you prove retry budget is no longer amplifying the failure?
3. Which payment state needs reconciliation by idempotency key?
4. After recovery, how do you drain in small batches and which rollback gate do you set?
5. Which instances need human handling rather than automatic replay?

## Self-check questions

1. What does a ready batch represent, and why does it not prove parallel execution occurred?
2. Why compare payload hash for same `source + id`, and why must a key not use an unescaped delimiter?
3. Why does a transient error after side-effect commit not make retry commit again?
4. Why does approval bind payload fingerprint, definition version, state version, and expiry together?
5. Why cannot a compensation failure be marked ordinary `failed`?
6. What can checkpoint SHA-256 detect, and what attack cannot it prevent?

## Mastery check

- [ ] I can run definition validation, demo, and both test modes.
- [ ] I can explain transitions for normal flow, waiting approval, retry exhaustion, rejection/compensation, and compensation failure.
- [ ] I can prove a duplicate event and post-crash retry do not create a second logical side effect.
- [ ] I can construct and recognize same idempotency key/different intent conflict.
- [ ] I can write a runbook for release, pause, drain, rollback, and human handling.
- [ ] I will not advertise a single-process example's in-memory records as production exactly-once.

## Return to index

Return to [[workflow-automation/00-index|Workflow Automation Learning Path]].

## References

- [Open Workflow Specification 1.0.3](https://serverlessworkflow.io/)
- [CloudEvents Specification 1.0.2](https://github.com/cloudevents/spec/tree/v1.0.2)
- [Temporal Platform Documentation](https://docs.temporal.io/) (product implementation reference)
- [Microsoft: Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
- [GitHub: Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) (signatures cover raw payload)
