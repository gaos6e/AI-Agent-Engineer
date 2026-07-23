---
title: "Conflicts, Synchronization, and Failure Recovery"
tags:
  - multi-agent
  - concurrency
  - recovery
aliases:
  - Multi-Agent Conflict Handling
  - Agent Failure Recovery
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/02-工程与质量/05-冲突、同步与失败恢复.md
translation_source_hash: 9cd82bab97aa17b3523b0ae3006c2e8fcbbd7a84d1fa163f4771d6b095ff7863
translation_route: zh-CN/多Agent协作/02-工程与质量/05-冲突、同步与失败恢复
translation_default_route: zh-CN/多Agent协作/02-工程与质量/05-冲突、同步与失败恢复
---

# Conflicts, Synchronization, and Failure Recovery

## Goal

Understand the main failure modes of concurrent collaboration — duplicate, reordering, write conflict, partial failure, and lost connection — and use resource ownership, versions, checkpoints, and bounded retry to reach an explainable result.

## Eliminate unnecessary shared writes first

The most reliable way to handle a conflict is to avoid it:

- Assign one write owner to every file, record, or task.
- Have parallel specialists produce immutable suggestions and one aggregator write the final artifact.
- Partition temporary results by `task_id` instead of sharing `latest.json`.
- Snapshot input or record its version so one run does not read different facts at different times.

If several agents must write one object, choose among:

1. **Optimistic concurrency control** — read version `v` and require the current version still be `v` at commit; reread and merge on conflict.
2. **Lock or lease** — hold a resource exclusively for a limited time. A lease must expire and its holder must heartbeat so a crashed process cannot lock forever.
3. **Serialized queue** — route all changes through one writer, trading throughput for simpler consistency.
4. **Domain merge rules** — a tag set may be unioned, but an amount, permission, or publication state must not merge automatically.

Never default to last-write-wins. It silently discards an earlier result that may be more correct.

### Separate an idempotent duplicate from a result conflict

An idempotency key is not permission to ignore every message with the same key. A durable record stores the key, algorithm-and-version-qualified intent/result digest, acceptance state, and external receipt reference. Reuse a result only when the key and digest match. If one key has different digests, that is an evidence conflict: freeze the task, stop downstream side-effect scheduling that has not yet started, and move it to `needs_review`. A human decision binds the current `state_version`, both digests, receipt fingerprints, and a one-time decision ID; it is not an agent choosing which result “seems more reasonable.”

One state transition cannot withdraw downstream work that has already begun or committed. After a conflict, isolate publication or further writing, mark the receipt and impact scope already produced, and let an authorized person decide whether to query, compensate, revoke, or disclose externally. Compensation is itself a new, audited action that can require approval.

This is the same class of problem as the idempotency record in [[workflow-automation/durable-state-recovery-and-idempotency|Workflow Automation]] and the receipt conflict in [[environmental-agents/06-long-running-task-checkpoints-and-idempotent-recovery#receipt-conflict-is-not-an-ordinary-exception|Environmental Agents]]: the names differ, but external fact is no longer unique and automation must stop writing.

## Failure class determines recovery

| Failure class | Example | Retry? |
| --- | --- | --- |
| Input error | Missing field or invalid format | No; return to upstream |
| Policy denied | Agent has no write permission | No; do not switch roles to evade it |
| Transient fault | Connection interruption or busy service | Bounded backoff retry |
| Permanent fault | Resource absent or capability unsupported | No; change plan or use a human |
| Quality failure | Output structure is valid but evidence is insufficient | Rework with feedback, bounded attempts |
| Budget exhaustion | Step, time, or cost limit reached | No; save progress and stop |

“Retry every exception three times” can repeat irreversible effects. Replay safely only when the action is confirmed idempotent or an idempotency key can identify a result already committed.

## Checkpoint and recovery

A checkpoint stores recoverable state, not a full internal chain of thought:

- task and dependency state;
- accepted artifact references and hashes;
- current budget and attempt count;
- idempotency keys for performed side effects;
- pending approvals;
- the most recent verifiable event position.

Recovery loads the checkpoint, validates schema and version, checks whether an external side effect already occurred, moves expired `running` tasks to a decidable state, and schedules only unfinished work. Write checkpoints atomically — for example, write a temporary file, synchronize, then replace the target.

## Compensate; do not promise to undo everything

Distributed side effects often cannot be rolled back. Deleting a local record after sending an email does not recall the email. Design compensation instead: cancel a reservation, send a correction, or restore a prior version, and make clear that compensation can fail too. High-risk action is better approved before execution.

## Deadlock, livelock, and duplicate work

- **Deadlock** — A waits for B and B waits for A. Prevent it with DAG cycle detection, lock order, and timeout.
- **Livelock** — Agents repeatedly yield or rework, state changes but nothing advances. Set a maximum rework count and a progress measure.
- **Duplicate work** — Two agents do the same task because neither knows the other is working. Use a task lease and unique owner.
- **Split brain** — Two managers both believe they lead. Production systems need reliable leader election or one scheduler service.

## Practice and self-check

For two reviewers submitting suggestions concurrently, design immutable review reports, one merger, a draft version, and the response to a conflict. Then simulate receiving the same `task_result` twice and verify that final state updates once.

1. When is a lease better than a permanent lock?
2. Why may `policy_denied` not be retried by changing agents?
3. If a checkpoint says `running` but the process no longer exists, may it be marked `succeeded` immediately?
4. Which side effects require querying external commit state before retry?

## Next step

Continue with [[multi-agent-collaboration/engineering-and-quality/06-budgets-stopping-and-human-intervention|Budgets, Stopping, and Human Intervention]].

## References

- [OpenAI Agents SDK: Running agents](https://openai.github.io/openai-agents-python/running_agents/) — accessed 2026-07-22.
- [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) — accessed 2026-07-22.
