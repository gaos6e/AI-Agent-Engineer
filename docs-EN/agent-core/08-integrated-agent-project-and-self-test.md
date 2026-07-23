---
title: "Integrated Agent Project and Self-Test"
tags:
  - agent-core
  - project
  - checkpoint
  - approval
aliases:
  - Agent Core Project
  - Bounded Offline Agent
source_checked: 2026-07-21
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: Agent 核心/08-综合Agent项目与自测.md
translation_source_hash: 44cc245e55b46a620a05e77967bae56a743da86b5839c4a12a6f1da9db82fb6c
translation_route: zh-CN/Agent-核心/08-综合Agent项目与自测
translation_default_route: zh-CN/Agent-核心/08-综合Agent项目与自测
---

# Integrated Agent Project and Self-Test

## Project objective

Run a deterministic, offline, bounded ticket-Agent runtime. The model is replaced by DeterministicPolicy so that attention stays on testable engineering controls:

- An action and observation loop.
- A tool allowlist and target constraints.
- Untrusted tool text.
- Budgets for steps, tool calls, and consecutive failures.
- Approval for write actions.
- Checkpoint integrity.
- Invariants for checkpoint phase and pending action, event chain, and completion evidence.
- The commit-before-checkpoint crash window.
- Recovery through an idempotency receipt.
- Fail-closed handling of malformed actions, approvals, and tool results, plus reconciliation records when a write outcome is uncertain.
- Completion without a write when external state already satisfies the goal.
- A completion verifier.

> [!warning] Capability boundary
> This is not a general-purpose Agent framework and does not claim to model the reasoning quality of any provider’s model. It uses only the Python standard library to demonstrate runtime invariants. A real system also needs a persistent database, distributed leases, real identity and authorization, a provider adapter, monitoring, and deployment-level tests.

## Files

| File | Purpose |
| --- | --- |
| [bounded_agent.py](agent-core/examples/bounded_agent.py) | State, policy, runtime, tool host, approval, checkpoint, and demo |
| [test_bounded_agent.py](agent-core/examples/test_bounded_agent.py) | 68 positive and negative regression tests |

## Environment

The project has no third-party dependencies and can run with stable Python 3. Run the following blocks from the repository root, which contains docs-CN, docs-EN, and .website. To isolate it if desired:

~~~powershell
Push-Location -LiteralPath 'docs-EN\agent-core' # Enter the example directory temporarily so the virtual environment is not created at repository root
py -3.11 -m venv .venv # Create a Python virtual environment for local use only
.\.venv\Scripts\Activate.ps1 # Activate that virtual environment in this PowerShell session
python -m pip --version # Verify that this session calls the virtual environment’s pip
Pop-Location # Return to the directory that was active before this block
~~~

No pip install command is needed. The .venv directory is local-only and must not be added to the knowledge base or Git.

You can also run directly without creating an environment:

~~~powershell
Push-Location -LiteralPath 'docs-EN\agent-core' # Enter the project directory so relative example paths resolve
py -3.11 -B .\examples\bounded_agent.py # Run the demo; -B prevents bytecode caches
py -3.11 -B .\examples\test_bounded_agent.py # Run every regression test in normal mode
py -3.11 -B -O .\examples\test_bounded_agent.py # Confirm control logic does not rely on bare assert statements removed by optimization
py -3.11 -B -W error .\examples\test_bounded_agent.py # Treat warnings as errors to expose compatibility issues early
py -3.11 -B -O -W error .\examples\test_bounded_agent.py # Combine the two strict modes to cover their interaction
Pop-Location # Restore the original working directory
~~~

-B prevents __pycache__ generation. -W error turns warnings into failures. -O verifies that critical controls were not mistakenly written as bare assert statements that optimization removes.

The currently verified environment is Windows 11, PowerShell 7, and Python 3.11, verified on 2026-07-21.

## Expected demo

~~~jsonc
{ // A summary produced when the demo ends successfully, not a complete audit log
  "status": "ok", // The process ran successfully; this alone does not prove that the external goal was achieved
  "phase": "completed", // The runtime entered its terminal completed phase after the verifier passed
  "steps": 3, // Number of logical decision steps recorded in this demo
  "tool_calls": 2, // Tool-call counter visible in the checkpoint after recovery
  "close_count": 1, // Critical idempotency evidence: the same ticket was actually closed only once
  "event_types": [ // A key-event list with details omitted
    "observation_recorded", // A normalized observation from the lookup tool was recorded
    "approval_requested", // Human approval was requested before the write action
    "completion_verified" // The verifier confirmed completion with an external receipt
  ] // End of the event-type array
}
~~~

> [!note] JSONC teaching notation
> This example uses JSONC to retain its explanatory comments. Remove the comments before copying it as strict JSON.

The important property is not output format but that close_count is always 1.

tool_calls=2 is the logical counter in the **checkpoint after recovery**: the initial lookup plus the receipt lookup during recovery. To demonstrate the crash window, the lookup and write in the crashing branch were not written back to that old checkpoint. Therefore this number does not prove quota accounting across a crash. A production system must persist an attempt before external I/O and rely on provider-side limits and audit; see [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency|Long-Running Agent Checkpoints, Recovery, and Idempotency]].

## Trajectory, step by step

### 1. Read the current ticket

Policy allows only lookup_ticket(ticket-7). The runtime first verifies that the tool result has exact fields, the current ticket, and expected primitive types; only then does it record an observation. A malformed or wrong-target **read** result enters failed / invalid_tool_result and cannot proceed to a write. If the write path receives a malformed receipt or result, it does not treat it as success or safe to retry. Instead it fails with tool_result_uncertain and retains the action, target, and idempotency information needed for reconciliation. A valid read result contains:

- status=open.
- A malicious customer note that asks to close other tickets and export environment variables.

The runtime wraps it as:

~~~jsonc
{ // A controlled wrapper for the lookup-tool result
  "source": "tool:lookup_ticket", // States exactly which tool produced this observation
  "trust": "untrusted", // Commands in returned text cannot become runtime instructions
  "purpose": "ticket facts only; never runtime instructions", // Facts may be extracted, but control-plane rules cannot change
  "data": {"ticket_id": "ticket-7", "...": "..."}, // Minimum business data after schema and target validation
  "sha256": "..." // Associates controlled original content without putting the full sensitive text in state
}
~~~

The malicious note does not enter runtime policy.

### 1.1 Stop immediately when the goal is already satisfied

If a structurally valid lookup result already has status=closed, current external state already satisfies the goal. The runtime records the lookup action and observation, enters completed with stop_reason=already_satisfied, and does not propose close_ticket. It therefore needs neither write approval nor a write receipt. This branch proves that queried current state already meets the goal; it does not use a model’s finish declaration in place of external evidence.

The following steps describe the demo’s normal status=open write path. A write path must still pass through a frozen action, approval, idempotent execution, and receipt validation.

### 2. Propose and freeze a write action

Policy proposes close_ticket(ticket-7). The runtime verifies:

- The tool is on the allowlist.
- The action ID, tool, arguments, and risk match the fixed contract for this phase.
- The idempotency key binds exactly to the run, ticket, and contract version.

It then stores this exact pending action and enters waiting_approval. On recovery, the runtime uses the frozen object instead of calling policy to produce another action. At this point, close_count=0.

### 3. Create approval

make_approval binds:

- Action ID.
- Action fingerprint.
- State version.
- Decision.
- Step expiry.
- Target scope, ticket_id in this example.

Changing a parameter, target, or state invalidates the approval.

### 4. Simulate the crash window

The runtime calls the tool:

1. The receipt lookup and write each consume one tool-call budget.
2. The tool persists a receipt, in memory for this example, and closes the ticket.
3. SimulatedCrash is raised before the runtime records completed state.

The external action has happened, while the checkpoint remains waiting_approval.

### 5. Recover from the old checkpoint

New state is reconstructed from the checkpoint, then the receipt is queried with the same idempotency key:

- A matching intent digest reuses the original result.
- The ticket is not closed again.
- Evidence is labeled recovered_from_receipt=true.
- The verifier checks the completed action, ticket status, and receipt.
- The runtime enters completed.

## Why the checkpoint has a hash

The envelope’s SHA-256 can detect accidental damage to an example file. The strict parser also rejects duplicate JSON keys and NaN or Infinity. Recovery additionally checks that event sequence and state version are continuous; that pending_action exists only in waiting_approval and exactly equals the frozen close contract for the current run; that a waiting state has lookup evidence; and that completed matches one exact valid evidence path. An already_satisfied result can have only a lookup action, a closed observation, and no close action or evidence. A completed write requires both lookup and close actions, plus evidence bound to the current action fingerprint, target, closed status, and receipt ID. These rules stop a checkpoint that has valid JSON shape but impossible state from continuing. A terminal transition clears the pending approval action so an old approval cannot remain attached to a cancelled or exhausted run.

These business invariants are still not a signature against an attacker: someone who can change both the payload and its hash and forge a mutually consistent state and evidence set may bypass an ordinary hash. A real system needs protected storage, access control, MACs or signatures, and independent verification of external receipts.

## Test coverage

The 68 tests are divided into:

| Category | Coverage |
| --- | --- |
| happy path | Safe pause, completion without a write when the goal is already satisfied, malicious note, frozen-action recovery, approval, receipt, and event or version behavior |
| approval | Fingerprint, state version, target scope, expiry, malformed fields, reject, cancel, and terminal pending-action cleanup |
| checkpoint | Round trip, integrity, strict JSON, schema, event chain, and phase, pending-action, or evidence invariants |
| budget and failure | Step and tool budgets, including receipt lookup; transient and permanent write failure; malformed action or result; reconciliation; and malicious policy |
| idempotency and recovery | Same-intent caching, different-intent conflict, crash recovery, and evidence |

Tests intentionally inject a non-allowlisted tool and another ticket. They demonstrate that the real final boundary is the runtime, not merely that a safe policy happened not to be fooled.

## Recommended code-reading order

1. ActionProposal and its fingerprint.
2. Approval and Budget.
3. AgentState validation, transition, checkpoint, and restore.
4. DeterministicPolicy.
5. OfflineToolHost receipts and intent conflict.
6. BoundedAgentRuntime._validate_action.
7. The run method’s budget, pause, execution, recovery, and verifier behavior.
8. run_demo and the tests.

## Experiments

Change one item at a time and predict the test result first:

1. Replace the malicious note with another prompt-injection attempt.
2. Have policy propose ticket-8 and observe runtime rejection.
3. Change the write tool to a name not on the allowlist.
4. Change the action fingerprint or state version after approval.
5. Set max_tool_calls to 1 and then 2. Confirm that receipt lookup also consumes budget and a ticket cannot close when no quota remains.
6. Inject one and then five transient lookup failures.
7. Use the same idempotency key to close ticket-7 and ticket-8.
8. Change checkpoint payload without updating the hash.
9. Update both payload and hash, change schema version to 2, and observe the schema gate.
10. Make the lookup tool return another ticket or omit a field, and observe invalid_tool_result.
11. Remove the pending action or observation from a waiting checkpoint, or corrupt event sequence, and observe restoration rejection.
12. Change the initial ticket status to closed. Confirm stop_reason=already_satisfied, close_count=0, and no write approval.

Afterward, restore the code and rerun all four 68-test modes: normal, -O, -W error, and -O -W error.

## Advanced extensions

### SQLite persistence

- Four tables for run, state, event, and receipt.
- Transactions plus optimistic versioning.
- Cross-process tests.
- Put real temporary databases in the system temporary directory, not in the vault.

### Lease

- Owner, lease version, and expires_at.
- Two workers competing to recover.
- An old worker cannot commit after its lease expires.

### Provider adapter

- Define an action, ask, and finish union with a fake-provider fixture first.
- Then connect a real LLM API.
- Separate real-network tests from offline runtime tests.
- Read keys only from environment variables and use .env.example for placeholder configuration.

### Completion verifier

- Use an independent query tool.
- For a no-write completion, verify current external state; for a write completion, verify receipt plus target version.
- Add a negative test for a model that returns finish.
- A failed verifier cannot produce completed.

## Project acceptance checklist

- [ ] The demo has phase=completed and close_count=1.
- [ ] close_count=0 before approval.
- [ ] A malicious note changes neither tool nor target.
- [ ] Approval binds fingerprint, state version, target scope, and expiry.
- [ ] Recovery after a crash does not close twice.
- [ ] An already closed ticket has no approval or write and completes with already_satisfied.
- [ ] The same key with different intent conflicts.
- [ ] Checkpoints parse strictly and their schema and integrity gates apply.
- [ ] Step, tool, and failure budgets can terminate execution.
- [ ] All 68 tests pass in normal mode.
- [ ] All 68 tests pass in -O, -W error, and -O -W error modes.
- [ ] There is no network, real credential, cache, large data, or model file.

## Self-test questions

1. Which component, model or runtime, can actually execute a tool?
2. What does an observation’s trust label accomplish, and why is it still insufficient?
3. Why does approval bind the action fingerprint and state version?
4. Why can the crash window not simply be retried with a new idempotency key?
5. What can a checkpoint SHA-256 defend against, and what can it not?
6. What external evidence is required for no-write completion versus write completion?
7. Why can a completion verifier not merely trust a model’s finish response?
8. Why does this example still not prove production-grade durable execution?

You have finished only when you can run the tests and explain each limitation rather than merely seeing PASS.

## Return to the index

Return to the [[agent-core/00-index|Agent Core Index]]. Then follow the overall learning route to [[agent-skills/00-index|Agent Skills]], [[agentic-design-patterns/00-index|Agentic Design Patterns]], and [[workflow-automation/00-index|Workflow Automation]].

## References

The following are first-party engineering or security materials and original papers, retrieved or checked on 2026-07-21.

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- Yao et al., [ReAct](https://arxiv.org/abs/2210.03629)
