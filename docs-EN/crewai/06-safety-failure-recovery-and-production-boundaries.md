---
title: "Safety, Failure Recovery, and Production Boundaries"
aliases:
  - CrewAI Production Safety
  - CrewAI Failure Recovery
tags:
  - ai-agent-engineer
  - crewai
  - safety
  - reliability
  - production
source_checked: 2026-07-21
concept_source_checked: 2026-07-21
package_source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: CrewAI/06-安全失败恢复与生产边界.md
translation_source_hash: da26803b187558097d44223e70c10a321f40562b8339c304854de85c6281d7be
translation_route: zh-CN/CrewAI/06-安全失败恢复与生产边界
translation_default_route: zh-CN/CrewAI/06-安全失败恢复与生产边界
---

# Safety, Failure Recovery, and Production Boundaries

## Learning objectives

You will draw the trust boundaries of a CrewAI system, limit authority for every Agent and Tool, distinguish retry, revision, recovery, and human takeover, and understand why a checkpoint cannot by itself guarantee “exactly once.” The lesson ends with an acceptance checklist for moving from a local demonstration toward production.

> [!important] Version and evidence boundary
> The latest stable release observed on PyPI on 2026-07-21 was <code>crewai==1.15.5</code>, while the course’s real runtime remains pinned and revalidated at <code>1.15.4</code>. Checkpointing, Tools, Flows, Human Feedback, and telemetry pages were rechecked on 2026-07-21. Security policy is engineering guidance that must be revalidated against the target organization’s data classification, regulations, and infrastructure.

## Start with a threat model

List these four categories before writing a Prompt:

1. **Assets:** user data, internal Knowledge, credentials, budgets, files, databases, and external-send authority.
2. **Entry points:** user text, email, web pages, PDFs, Knowledge, Memory, Tool returns, and artifacts from other Agents.
3. **Trust boundaries:** tenants, development versus production, model providers, browser/code-execution environments, and external APIs.
4. **High-impact actions:** payment, deletion, sending, publication, permission change, code execution, and production-database writes.

External content can contain prompt injection. Reliable defenses use Tool allowlists, strict parameter schemas, least privilege, network and file isolation, quota limits, and human approval. A Prompt can remind a model, but cannot elevate system-layer authority or replace authorization checks.

## Put authority at the Tool boundary, not in an Agent’s self-description

Each Agent receives only Tools needed for its Task. For example, a writer can draft text but should not have an email-sending Tool; a publisher accepts only a reviewed draft carrying an approval token. Before execution, a Tool still checks:

- caller, tenant, and resource scope;
- parameter type, length, enumeration, and path;
- business preconditions and approval state;
- network-domain, file-directory, and command allowlists;
- idempotency key, rate, amount, and total budget;
- whether output must be redacted or trimmed.

Inject secrets through the environment or a secret-management system, and read them only at code that actually calls an external service. Never place secrets in Task descriptions, Memory, Knowledge, events, exception messages, or example files.

## Failure classification determines treatment

| Failure class | Example | Recommended treatment |
| --- | --- | --- |
| Invalid input | Missing field or path escape | Reject immediately with actionable information. |
| Permission denial | Agent lacks send authority | Stop and record; do not bypass it with another Tool. |
| Business rejection | Human does not approve publication | Valid terminal state; do not retry automatically. |
| Transient failure | Rate limit or brief network interruption | Bounded backoff retry that respects service guidance. |
| Permanent failure | Resource absent or API removed | Stop and repair configuration or code. |
| Unacceptable content | Missing citation or schema failure | Bounded revision; human takeover after budget exhaustion. |
| Incompatible state | Old schema cannot be read | Reject recovery or migrate explicitly; do not guess fields. |

“Try again” is not a general recovery policy. Attempts, wait time, retryable exceptions, and total budget must be explicitly bounded in code or configuration.

## Checkpointing, persistence, and idempotency are different

- **Persistence** saves Flow state so it can be read after process restart.
- **Checkpointing** saves execution progress at agreed boundaries so recovery skips completed parts.
- **Idempotency** ensures repeat requests for one business action do not create a second side effect.

The official Checkpointing page still called the feature early release on 2026-07-21. It introduces <code>CheckpointConfig</code> for Crew, Flow, or Agent checkpoints; <code>checkpoint=True</code> uses <code>./.checkpoints</code> by default and saves after Task completion. It lists JSON and SQLite providers plus recovery with <code>from_checkpoint(...)</code> that skips completed Tasks. Verify exact signatures against the pinned version; the offline project does not execute these APIs.

The same page says manual checkpoint writes are best effort: a write error is recorded while execution may continue. Therefore enabling checkpoints does not mean every side effect is reliably recorded. If an email succeeds but the next checkpoint fails, recovery can send it again. A side-effecting Tool still needs a stable idempotency key and an external-system check for completed action.

A safe publication sequence is:

1. build an idempotency key from stable <code>operation_id + artifact_fingerprint</code>, not a Flow-execution UUID;
2. ask the external system whether that key already has a result;
3. execute only when it has not completed;
4. store the external result ID;
5. update Flow state;
6. on recovery, check the external result before deciding to retry.

This course’s <code>publish_report</code> demonstrates same-content recovery, different-content overwrite rejection, and temporary-file atomic replacement. It is a local-file example, not a transaction guarantee for a database or remote API.

## Code execution needs a separate sandbox

When checked on 2026-07-14, the official Agents page said <code>allow_code_execution</code> and <code>code_execution_mode</code> were deprecated and that <code>CodeInterpreterTool</code> had been removed; the official Tools page still listed a Code Interpreter Tool. This observable documentation disagreement cannot establish that any pinned version supports a particular path.

The engineering conclusion does not depend on that contradiction: run all model-generated code in a dedicated sandbox with restricted image, user, CPU, memory, duration, network, mounted directories, and output size. Do not execute it directly on a developer machine holding credentials, SSH configuration, or research data.

## Human approval is business state, not natural language

For a high-risk action, use <code>preview → approve/reject → execute → verify</code>. An approval record binds:

- approver identity and authority;
- exact parameters and content fingerprint to execute;
- validity interval and one-time-use rule;
- associated <code>run_id</code> and resource;
- execution result and external record ID.

If content changes after approval, the old approval expires. Human rejection must enter an explicit terminal state; an Agent cannot treat it as an instruction to “continue with another Tool.”

### <code>@human_feedback</code> is a pause mechanism, not an authorization service

CrewAI currently supplies <code>@human_feedback</code> to pause a Flow, collect feedback, and route outcomes configured through <code>emit</code>; the official documentation explicitly says an LLM maps free text to these outcomes. This improves the experience of waiting for feedback and selecting a next workflow branch, but supplies neither an authenticated approver, target resource, content digest, expiry, one-time use, nor an external-action receipt.

So a high-impact Tool must not only check <code>state.outcome == "approved"</code>. Treat the Flow feedback result as **input to validate**. An application approval service issues an authorization record bound to <code>actor_id + resource + canonical_payload_hash + expiry + nonce</code>; the execution layer verifies it again, consumes the nonce, and stores an external receipt. Layer B’s SQLite example tests receipt recovery only; it does not implement human identity or an approval service and must not be read as a HITL authorization implementation.

## Production-release checklist

### Dependencies and environment

- Pin CrewAI, Python, model SDKs, and Tool dependencies.
- Use different credentials, storage, and data in development, testing, and production.
- Validate required configuration at startup without printing secrets.
- Explicitly record whether built-in telemetry is disabled, whether <code>share_crew</code> is disabled, and where observability data goes.
- Record anonymous telemetry, AMP tracing, and application-log policies separately. Prefer <code>CREWAI_DISABLE_TELEMETRY</code> for CrewAI anonymous telemetry and use <code>OTEL_SDK_DISABLED</code> only for a required global shutdown. In pinned <code>1.15.4</code>, set <code>tracing=False</code> explicitly on Crew/Flow instances or manage persistent consent through the official CLI; do not depend only on an environment value of <code>false</code>.
- Check authority, capacity, backup, and recovery for <code>CREWAI_STORAGE_DIR</code> and similar paths.
- Record deployment artifact and schema versions.

### Runtime boundaries

- Limit concurrency, maximum steps, retries, total duration, tokens, and cost.
- Set connection and read timeouts for external calls.
- Add circuit breakers, degradation, and alerts for repeated failure.
- Roll out read-only scenarios first; writes need a higher gate.
- Define human takeover, a stop switch, and rollback conditions.

### Data and audit

- Isolate Knowledge, Memory, logs, and checkpoints by tenant.
- Do not collect sensitive fields or redact them; set retention and deletion policies.
- In private or regulated environments, disable unneeded CrewAI data egress by default. If it remains enabled, verify fields, destination, retention, and deletion.
- Do not set <code>share_crew=True</code> without explicit privacy approval: the official description says it shares detailed execution data such as goal, backstory, context, and Task output.
- Audit records answer who did what, when, and to which resource.
- Review data-processing terms for model and observability backends.
- Deletion covers indexes, caches, backups, and derived data.

### Release evidence

- Deterministic tests, fault injection, and recovery tests pass.
- A minimal Crew/Flow integration test passes on the pinned version.
- A startup test asserts telemetry policy and prevents an upgrade from silently changing egress.
- The regression set meets task, safety, cost, and latency gates.
- Key rotation, dependency rollback, and human takeover have been rehearsed.
- Remaining unvalidated risks are explicit.

## What the framework cannot guarantee for you

CrewAI can offer Agents, Tasks, Crews, Flows, Tools, events, and persistence. It cannot automatically prove model output correct, a Tool safe, Memory compliant, multiple Agents better than one, or recovery free from repeated external side effects. Acceptance must address your data, authority, terminal states, and failure modes.

## Hands-on exercise

For a system that reads customer email, drafts a reply, and sends it:

1. draw trust boundaries around email service, model, Knowledge, logs, and the send Tool;
2. design <code>drafted</code>, <code>awaiting_approval</code>, <code>approved</code>, <code>sent</code>, <code>rejected</code>, and <code>human_review</code> states;
3. define an approval content fingerprint and a send idempotency key;
4. inject “send succeeds but checkpoint fails”;
5. verify recovery does not send twice;
6. verify prompt injection in the email body cannot expand Tool authority.

## Mastery check

- [ ] Explain why a Prompt cannot replace Tool authority and parameter validation.
- [ ] Distinguish retryable, non-retryable, revisable, and human-rejected cases.
- [ ] Explain which problem checkpointing, persistence, and idempotency each solve.
- [ ] Design repeat-recovery tests for side-effecting Tools.
- [ ] Explain the different boundaries of default telemetry, AMP tracing, <code>share_crew</code>, the CrewAI-specific disable variable, and global <code>OTEL_SDK_DISABLED</code>.
- [ ] List evidence still required before a CrewAI demonstration enters production.

## Next step

Build the contract first with [[crewai/07-project-offline-research-brief-flow|Offline Research-Brief Flow]], then inject a post-receipt crash and verify recovery with [[crewai/08-project-real-crewai-persistent-flow|Real CrewAI Persistent Flow]].

## Primary references

Checkpointing, Flow, Tool, Human Feedback, Telemetry, and Tracing pages were rechecked on 2026-07-21. The historical Agents/Code Interpreter documentation inconsistency retains 2026-07-14 as its evidence boundary; PyPI was checked on 2026-07-21.

- [CrewAI Checkpointing](https://docs.crewai.com/en/concepts/checkpointing)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Agents](https://docs.crewai.com/en/concepts/agents)
- [CrewAI Tools](https://docs.crewai.com/en/concepts/tools)
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener)
- [CrewAI Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)
- [CrewAI on PyPI](https://pypi.org/project/crewai/1.15.4/)
- [CrewAI telemetry on PyPI](https://pypi.org/project/crewai/#telemetry)
