---
title: "Environment Evaluation and Integrated Project"
tags:
  - environment-agent
  - agent-evaluation
  - practice-project
aliases:
  - Environment Agent Evaluation
source_checked: 2026-07-22
lang: en
translation_key: 环境型Agent/07-环境评测与综合项目.md
translation_source_hash: e43b52f497cf0dc537a1b11f4a579eb87a7db3e674c46587527957a87ed56b35
translation_route: zh-CN/环境型Agent/07-环境评测与综合项目
translation_default_route: zh-CN/环境型Agent/07-环境评测与综合项目
---

# Environment Evaluation and Integrated Project

## Objectives

- Evaluate environment-based Agents through tasks, trials, traces, graders, and outcomes.
- Check final state, trajectory, side effects, cost, latency, and recovery together.
- Run and extend a standard-library-only offline environment runtime.

## Why “the final result looks right” is still insufficient

The same task can start from different initial states, and an Agent can succeed along an accidental trajectory. Looking only at a final screenshot misses duplicate sends, out-of-scope access, and intermediate data exposure; looking only at trajectory similarity punishes valid new paths. Environment evaluation should center executable outcomes while using trajectories and control metrics to explain failure and risk.

WebArena emphasizes functional correctness in real interactive websites; OSWorld includes initial-state setup and custom executable evaluators; SWE-bench evaluates patches against repository baselines and tests. Together they support reproducible initial state, executable verification of final state, and auditable process side effects—not one universal score.

## How to implement evaluation objects

| Object | Meaning for an environment-based Agent |
| --- | --- |
| Task | Goal, fixed initial state, identity/permission, allowed side effects, budget, and grader version |
| Trial | One independent run with run ID, random seed, environment image, and adapter/model version |
| Trace | Observation, proposal, rejection/approval, action, receipt, checkpoint, and verifier event |
| Grader | Deterministic check reading real final state, business object, file, test, or system setting |
| Outcome | Success/failure/cancelled/waiting plus side effects, cost, latency, and termination reason |

At minimum report task success rate and variance over repeated trials; illegal-action/authorization-bypass/approval-bypass rate; unexpected side effects and duplicate-write count; steps, tool errors, and recovery success rate; end-to-end and human-wait latency; and model/tool/environment cost. Retain environment-specific failure categories rather than using an average success rate to hide a high-risk failure type.

When using a benchmark, record data/task version, harness, environment image, model, and adapter. A public score answers only for that task distribution. Production gates must add their own identity, data, tools, exception, concurrency, and incident scenarios.

### The evaluation card must cover the control plane too

Execution success and safety do not replace each other. A system that always refuses action may never overreach but also never completes tasks; a system with a correct final screenshot may already have sent duplicates or leaked data. Every evaluation card should state these dimensions and their independent evidence:

| Dimension | Question | Example evidence |
| --- | --- | --- |
| Function and integrity | Does an allowed initial state reach the correct final state? | Independent grader, backend object, file hash, target and regression tests |
| Authorization and injection resilience | Can hostile observation, cross-tenant/account access, expired approval, or replay cause a side effect? | Rejection trace, zero-side-effect assertion, policy/approval/receipt binding checks |
| Privacy and audit | Does trace support reconciliation without exposing raw secrets, PII, or hidden answers? | Field classification, redaction test, access control, traceable digest |
| Recovery and operation | Does the system converge safely after timeout, crash, concurrency, cancellation, or environment drift? | Crash-window trial, idempotent receipt, human handoff, cleanup record |
| Release reproducibility | Which change caused a metric change, and did it cover a new attack surface? | Fixture/harness/image/model/adapter/policy versions and post-change abuse-case regression |

A `trace` is not itself a compliance-audit conclusion. Separate rerunnable trace from protected raw evidence: the former stores versioned IDs/digests for run, policy, environment, action, receipt, and grader; the latter follows least-privilege and retention policy. Evaluators must not obtain production credentials through graders, logs, or hidden answers. After a material change to prompt, tool, memory, retrieval, policy, adapter, or model provider, rerun corresponding functional and adversarial cases rather than comparing one overall score.

## Integrated project

`examples/` contains an in-memory file environment with no network, model, or third-party package:

- `environment_fixture.json` — strict task initial/final state, task/policy version, permission, path/test-target allowlists, and proposal/step budgets.
- `environment_runtime.py` — strict action schema with environment version, preconditions, risk, and deadline; model-external HMAC approval store; environment instance/pre-post-state fingerprint/generation; dual expiry and safe refresh of expired pending work; permission gate, in-memory sandbox, pending intent, adapter-authoritative idempotent receipt; `needs_review` with trusted human `replan/abort` for receipt conflict; checkpoint HMAC with prechecks, external monotonic high-water mark, and versioned verifier.
- `test_environment_runtime.py` — 103 positive and negative tests.

Run:

```powershell
Set-Location ".\docs-EN\environmental-agents" # Enter the course project directory so fixture and example relative paths resolve correctly.
$env:PYTHONDONTWRITEBYTECODE = "1" # Do not create __pycache__, keeping local cache out of the knowledge base.
python -B .\examples\environment_runtime.py # Run the offline environment-runtime demo; -B also avoids bytecode cache.
python -B -W error .\examples\test_environment_runtime.py # Treat warnings as failures and run full environment-security regression.
python -B -O -W error .\examples\test_environment_runtime.py # Combine optimized and strict-warning modes to prove gates do not depend on bare assert.
```

The expected demo output is `phase=completed`, `terminal_reason=verified_outcome`, `environment_version=1`, `write_count=1`, `proposal_count=4`, and `event_count=5`. Tests cover duplicate/non-finite JSON, unknown fields, path traversal, stale observations, action risk/deadline, permission, and `run_tests` target allowlist; rejection of raw Action self-approval; approval HMAC binding task/run/policy/action/idempotency key/intent, environment instance/pre-post fingerprint/generation, proposal/wall-clock expiry, and nonce; authenticated recovery of expired pending evidence, execution freeze, and fresh exact approval refresh; rejection/conflict/replay traces; proposal/step-budget failure states; ordinary-checksum recomputation, checkpoint-HMAC tampering, structural prechecks, and external-generation anti-rollback; same-version state drift, cross-environment instance, external task/policy-version mismatch, and forged-completed state; adapter-receipt deletion and cache/adapter full-field drift rejection; recovery after an approved write commits but runtime receipt is not persisted; frozen receipt-intent conflict, trusted human continue/abort, and liveness; stale verification, cancellation, and terminal-state closure.

This sandbox demonstrates only the control plane. File environment, approval/reviewer store, adapter receipt, checkpoint-generation store, trusted clock, and test grader are deterministic in-process substitutes. It does not start a subprocess and cannot prove isolation of a real browser, desktop, shell, durable database, approval service, or key service. Teaching code uses shared-key HMAC and provides no production-grade key rotation, revocation, two-person approval, trusted time source, durable high-water mark, atomic checkpoint/high-water persistence, or concurrent transaction.

The sandbox also treats its synchronous in-memory adapter as a trusted execution boundary. Its receipt does not bind approval fingerprint or trusted commit timestamp, so it cannot prove that an external call bypassing the runtime happened before approval expired. When connecting a real adapter, retain these contract tests and add adapter-side expiry; receipt–approval–commit-time binding; human review for missing evidence; process/VM isolation; real identity; network policy; durable approval/receipt/anti-rollback storage; concurrent conflict; and environment-cleanup tests.

## Common failures

- Each trial lacks an independent environment, so a previous write contaminates the next result.
- The grader reads a report generated by the Agent, creating a self-verification loop.
- Only the happy path is tested; hostile observation, permission denial, timeout, and crash are absent.
- A run occurs only once, so incidental success of a nondeterministic Agent is presented as stable ability.
- Cancellation, human waiting, partial success, and budget exhaustion are ignored as non-binary outcomes.
- Evaluation itself has excessive permission or exposes hidden answers.

## How to validate

Run warnings-as-errors in both normal and `-O` mode so vital checks cannot depend on `assert` removed by optimization. Start every test with a new runtime/fixture; on rejection, check zero side effects; on success, check current-version test receipt, exactly one write, and terminal-state closure. Then use mutation-testing thinking: remove a permission or version check and confirm at least one test fails.

## Practice task

Extend the example without connecting to a real shell. Add a `delete_file` action requiring independent permission, explicit path, idempotency key, and human approval. Its receipt must survive checkpoint recovery, and the grader may complete only when the fixture explicitly permits deletion. Write at least six negative tests before implementing the action. Finally submit an evaluation card stating what the simulator can and cannot prove, and which integration tests a browser/desktop/coding adapter needs.

## References

- Zhou et al., [WebArena](https://arxiv.org/abs/2307.13854) and [official repository](https://github.com/web-arena-x/webarena).
- Xie et al., [OSWorld](https://arxiv.org/abs/2404.07972) and [official repository](https://github.com/xlang-ai/OSWorld).
- Jimenez et al., [SWE-bench](https://openreview.net/forum?id=VTF8yNQM66) and [official repository](https://github.com/SWE-bench/SWE-bench).
- [[evaluation-framework/00-index|Evaluation Framework]] — task/trial/trace/grader/outcome and release gates.
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) — adversarial tests after material change, release gates, and verification evidence; checked 2026-07-22.
- [NIST AI RMF and Generative AI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — organization-level context for risk management, measurement, and human oversight; checked 2026-07-22.

