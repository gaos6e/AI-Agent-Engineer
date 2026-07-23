---
title: "Incident Response and Postmortems"
tags:
  - observability
  - incident-response
aliases:
  - Monitoring Incident Response
source_checked: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "NIST SP 800-61 Rev. 3 and Google SRE primary materials on
  incident management and postmortems, checked through 2026-07-21."
lang: en
translation_key: 运行监控/02-生产监控/07-事件响应与复盘.md
translation_source_hash: 509b6faeab4e49ac9c65543e916bc42bceabe5cd0a002c92e9b837818021bc09
translation_route: zh-CN/运行监控/02-生产监控/07-事件响应与复盘
translation_default_route: zh-CN/运行监控/02-生产监控/07-事件响应与复盘
---

# Incident Response and Postmortems

## Goal

Turn an alert or external report into an incident-response process with command, timeline, user protection, evidence preservation, recovery verification, and continuous improvement.

## Alerts, incidents, and problems

- **Alert** — a rule indicates a state that may need action. It may be a real incident, noise, or an observability failure.
- **Incident** — a service deviates from expectation and causes or threatens material impact to users, data, safety, or the business, requiring controlled response.
- **Problem** — a condition needing a long-term root-cause repair. It can remain tracked after incident recovery.

The first goal of runtime response is to limit harm and restore acceptable service, not to discover a perfect root cause under pressure.

## Incident severity

Severity should account for:

- scope of affected users/tenants, tasks, and regions;
- availability, latency, quality, safety, privacy, cost, and compliance consequences;
- whether impact is spreading and whether it is reversible;
- availability of safety degradation or a manual substitute;
- whether reliable evidence is missing.

Do not grade severity only by request count. A low-volume unauthorized write can be more severe than many transient, retryable 5xx responses. Business, security, legal/compliance, and engineering functions need to define the severity contract together; a tutorial cannot provide universal thresholds.

## Key roles

| Role | Responsibility |
| --- | --- |
| Incident commander | Set objectives, assign work, control risk and escalation, and avoid being drawn into one diagnostic clue |
| Operations/technical lead | Perform containment, diagnosis, repair, and recovery verification |
| Scribe | Preserve a timeline of decisions and events with timestamps and evidence links |
| Communications lead | Send accurate, regularly paced updates internally and to affected parties |
| Domain specialist | Join as needed for security, privacy, model, provider, or business expertise |

In a small team, one person can hold several roles, but responsibilities must remain explicit. Asking the same person to make a high-risk change, maintain the timeline, and communicate externally tends to lose important evidence.

## Response process

### 1. Declare the incident and establish shared state

Record declaration time, known impact, severity, commander, communication channel, and next update time. Keep confirmed facts, hypotheses under verification, and unknowns separate.

### 2. Contain

Stop releases, switch to a trusted release, disable a high-risk tool, rate limit, hand off to people, or isolate affected data. Containment can reduce functionality, but verify that degraded operation does not create a greater safety risk.

### 3. Preserve evidence and assess scope

Freeze release/configuration/policy versions, monitoring queries, and redacted trace samples; record clocks, time zones, sampling, and data delay. Security-incident evidence preservation, access, and external notification must follow the organization's legal/security process; a tutorial must not define it unilaterally.

### 4. Diagnose and repair

Use version differences, SLI breakdowns, traces, and controlled comparisons to test hypotheses. Do not change several unrelated variables in production simultaneously; even if metrics recover, you will not know what worked.

### 5. Recover and verify

Verify with user SLIs, task-quality/safety samples, data completeness, side-effect audit, and external black-box tests. The observability pipeline itself must recover too, or “normal metrics” may only mean no data. Restore traffic gradually instead of jumping from full degradation to full volume.

## Recovery is not closure

A recovered service curve shows only that the current symptom has eased. Before closing, record the recovery observation window and evidence coverage; remaining user/data side effects; residual risks and temporary controls; an owner and due date for every long-term action; and the signals that would reopen the incident. If duplicate orders stop but historical duplicates remain unrolled back, the incident can leave emergency response without calling user harm resolved.

Actions must flow back into development and operations: deterministic defects enter regression evaluation, observation blind spots enter the telemetry contract, unactionable alerts enter rule revision, and operating gaps enter runbooks and exercises. Close an item with acceptance evidence, not merely because code merged.

## Incident communication

Each update should include known impact, current containment/recovery state, actions users can take if any, and the next update time. Do not guess a root cause without evidence or replace recovery verification with “fully fixed.” Follow specialized notification and approval processes for security, privacy, and compliance incidents.

## Blameless postmortems and verifiable actions

A postmortem includes:

- user impact and evidence boundaries;
- a linked timeline;
- root cause, contributing factors, and unresolved questions;
- why tests, Canary, SLI, alerts, or runbooks failed to prevent or shorten the incident;
- which containment and recovery actions worked and which raised risk;
- action items with owner, deadline, and acceptance evidence.

“Add an idempotency-contract test for the write tool and prove during an incident exercise that retries cannot write twice” is an acceptably testable action. “Be more careful next time” is not. Blamelessness does not mean no owner or responsibility boundary.

## Exercises and continuing preparation

Regularly exercise provider outage, observability interruption, duplicate tool writes, data-contract breakage, and cost explosion. Avoid real side effects using a sandbox, simulation, or controlled fault injection, and assess detection, declaration, containment, communication, and recovery.

## Exercise and self-check

Scenario: an online Agent's tool-success metric is normal, but users report that the same order is created twice; trace completeness has fallen to 40%. State the facts needed for severity, actions for the first 30 minutes, evidence preservation, and recovery verification. Answer:

1. Why cannot a normal tool “success” metric rule out the incident?
2. Why does trace loss itself increase uncertainty and risk?
3. How do you verify duplicate orders already created are remediated, rather than merely that new duplicates stopped?

## Summary and next step

Incident response turns monitoring signals into user protection and a learning loop. Use [[runtime-monitoring/project-and-self-check/08-offline-monitoring-audit-project-and-self-check|Offline Monitoring Audit Project and Self-Check]] to practice calculating explainable signals from raw events.

## References

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — published 2025-04, checked 2026-07-21; current NIST incident-response resource.
- [Google SRE: Managing Incidents](https://sre.google/sre-book/managing-incidents/) — checked 2026-07-21.
- [Google SRE: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) — checked 2026-07-21.

