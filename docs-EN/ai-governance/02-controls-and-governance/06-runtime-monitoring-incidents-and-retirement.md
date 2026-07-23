---
title: "Runtime Monitoring, Incidents, and Retirement"
aliases:
  - AI Monitoring Incident and Retirement
tags:
  - ai-governance
  - monitoring
  - incident-management
  - retirement
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/02-控制与治理/06-运行监控事故与退役.md
translation_source_hash: 9f7b4bc8d4c93fb7d5fc0ce5284655aae26a0e870b94e66f80f0c7343bab831f
translation_route: zh-CN/AI治理/02-控制与治理/06-运行监控事故与退役
translation_default_route: zh-CN/AI治理/02-控制与治理/06-运行监控事故与退役
---

# Runtime Monitoring, Incidents, and Retirement

## Goal of this lesson

Turn pre-release risk assumptions into runtime thresholds, actions, and owners; identify hazards that have not yet caused harm as well as incidents that have; and fully retire a system when it is no longer worthwhile or safe to operate.

## From risk register to monitoring

Every important risk needs a signal, denominator, subgroup, threshold, observation window, data-quality check, owner, and action on breach. For example, “incorrect advice harms speakers of a low-resource language” cannot be monitored only through overall satisfaction. Measure a human-adjudicated serious-error rate by language and state when to rate-limit, switch to people, or disable the system.

Monitoring can be organized into four layers:

- **System and supply chain**: availability, latency, cost, dependency or model-version drift, and permission or configuration changes.
- **Quality and behavior**: task success, hallucinations or citation errors, refusals, repeated tool calls, human overrides, overreach, and failure modes.
- **Human and social impact**: complaints, appeals, differences between groups, overreliance, accessibility, worker burden, and actual harm.
- **Control health**: approval bypasses, missing logs, stale evaluations, incident drills, deletion failures, and vendor notices.

Key performance indicators (KPIs) state whether goals are being achieved; key risk indicators (KRIs) state whether risk is rising. High adoption may be a KPI but can also accompany overreliance, so interpret the two together.

## Incidents, hazards, and issues

The OECD's 2024 terminology work calls an event that has caused actual harm an AI incident, and an event with potential harm an AI hazard. An organization can use that distinction, but must define its own escalation scope: an attempted unauthorized action, severe subgroup drift, or a vendor security notice should enter the hazard or issue process even before confirmed harm.

This broad AI incident and hazard record does not replace cybersecurity, privacy, product-safety, or sector incident processes. Where an attack or vulnerability is involved, also record the attack vector, identities and permissions, affected components, exploitation status, and containment evidence. The same facts may link to several tickets, but share a stable incident ID so teams do not create conflicting timelines.

The minimum record includes an incident ID; discovery time and channel; system and version; actual or potential impact; affected people and regions; evidence source; known uncertainty; severity; owner; actions to limit impact; notification assessment; recovery conditions; and post-incident actions. Do not copy unnecessary personal data or secrets into ordinary tickets.

## Response loop

Detect and triage → contain impact (disable tools, rate-limit, roll back, hand off to people, revoke identities) → preserve controlled evidence → establish scope and root cause → authorized teams decide internal and external notifications → remediate and validate independently → restore in stages → review afterward. Add the real path to the regression set and inspect other systems affected by the same vendor or component.

Fixed regulatory recipients and deadlines vary by region, role, industry, data, and harm type. This course does not prescribe universal time limits. An incident runbook should list legal, privacy, and security escalation contacts in advance; qualified people decide under the rules in effect at the time.

## Safe retirement

Retirement is not turning off the interface. A plan should:

1. Stop entry points, jobs, APIs, tools, and automatic triggers; revoke identities, keys, and network permissions.
2. Notify users, affected business units, vendors, and downstream systems, and provide a manual or replacement process.
3. Handle data, indexes, caches, logs, evaluation sets, backups, and vendor copies under authorization and retention rules.
4. Retain the minimum necessary approval, version, incident, and decision evidence; record when, by whom, and on what basis the system was retired.
5. End contracts, release resources, and verify that costs and calls have stopped; confirm that downstream systems do not still rely on old outputs.
6. Handle appeals, corrections, and continuing effects of historical decisions, and recheck residual copies and access at the agreed time.

## Exercise and self-check

For a “customer-support drafting Agent,” select three KPIs and five KRIs. For each, write a denominator, subgroup, threshold, owner, and action. Then simulate a silent vendor model change that increases complaints, and complete the hazard or incident record and retirement checklist.

- [ ] Monitoring signals can be traced to a specific risk in the impact assessment.
- [ ] A threshold breach triggers a clear action rather than merely updating a dashboard.
- [ ] Can distinguish actual harm, potential hazard, and an ordinary defect while preserving escalation room.
- [ ] Retirement covers identities, data, vendors, downstream systems, users, and historical redress.

## Next step and source baseline

Continue with [[ai-governance/02-controls-and-governance/07-regulations-standards-and-regional-review|Regulations, Standards, and Regional Review]]. Sources were accessed on 2026-07-21. See the [OECD definition of AI incidents and hazards](https://oecd.ai/en/ai-publications/defining-ai-incidents-and-related-terms), the [OECD common reporting framework for AI incidents](https://oecd.ai/en/ai-publications/towards-a-common-reporting-framework-for-ai-incidents), and the continuing-governance and retirement requirements in the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).
