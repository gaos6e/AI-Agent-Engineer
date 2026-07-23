---
title: "Red Teaming, Monitoring, and Incident Response"
aliases:
  - AI Red Team and Incident Response
  - Agent Security Operations
tags:
  - ai-security
  - red-team
  - incident-response
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: AI安全/02-控制与治理/06-红队监控与事件响应.md
translation_source_hash: 0fe333e8289734201278cb00cc0d9c0a68c27850d5cb9744808ca4df99454806
translation_route: zh-CN/AI安全/02-控制与治理/06-红队监控与事件响应
translation_default_route: zh-CN/AI安全/02-控制与治理/06-红队监控与事件响应
---

# Red Teaming, Monitoring, and Incident Response

## Learning objective

Build security red-team cases from a threat model and turn their results into release gates. Design minimum-sufficient security telemetry, and detect, contain, preserve evidence, recover from, and learn from an Agent incident.

## Red teaming is not a jailbreak-quote contest

The purpose of red teaming is to verify whether a real attacker can cross a trust boundary and cause a defined loss. Test cases follow from the assets and paths in [[ai-safety/01-foundations-and-risks/01-assets-trust-boundaries-and-threat-modeling|the threat model]], not from collecting an unlimited number of unusual prompts.

Coverage should include at least:

- direct, indirect, encoded, multilingual, and multimodal prompt injection;
- poisoned tool lists or descriptions, parameter injection, overreach, and confused deputies;
- sensitive-data egress through email, URLs, search, logs, or collaborating Agents;
- memory, RAG-data, and cross-tenant context poisoning;
- forged or replayed inter-Agent messages, trust propagation, error aggregation, and cross-workflow cascades;
- substitutions in the supply chain for models, Skills, MCP servers, dependencies, or update channels;
- duplicate calls, infinite loops, resource or cost exhaustion, and rate-limit bypass;
- approval replay, parameter substitution, credential-revocation failure, and emergency-shutdown failure.

For multi-Agent systems, review delegation identities, authorization references, message integrity, replay, and cross-boundary token handling together with the contracts in [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, Authorization, and Cross-Boundary Trust for Multi-Agent Systems]]. A red team must not automatically elevate a natural-language message “from the coordinator” into a trusted control fact.

For every case, record prerequisite permissions, attack input, system version, permitted actions, prohibited end states, observable evidence, and cleanup steps. Prefer synthetic data and controlled accounts in isolated environments. Do not test production or third-party systems without explicit authorization.

## From cases to release gates

A single success or failure is not comparable. Freeze the data set, version, policy, and judgment criteria, then report attack success rate, critical-asset impact, severity, false positives, variance, and coverage blind spots. Use zero tolerance or explicit thresholds for high-risk paths. Turn new discoveries into regression samples and add them to the version-change gate.

Red teaming cannot prove “absolute security.” It provides evidence only for the tested scope, assumptions, time, and versions. Attackers, models, and tools change, so continuous evaluation and monitoring are necessary.

## Security-monitoring signals

Correlate security events and operational monitoring through the same run or trace, but avoid logging complete secrets. You can observe:

| Layer | Example signals |
| --- | --- |
| Input and context | Proportion of untrusted sources, unusual encodings, cross-tenant references, denied memory writes |
| Policy and tools | Unknown tools or fields, destination denials, object-authorization failures, approval replays |
| Behavior | Surges in tool calls, duplication or loops, unusual egress volume, budget exhaustion |
| Identity and supply chain | Scope changes, use after revocation, model/prompt/dependency drift, unverified components |
| Outcome | Sensitive-field hits, human takeover, emergency shutdown, rollback, and recovery time |

For multi-Agent or multi-workflow systems, also correlate parent and child runs; message sender and recipient; delegation chain; hop count; fan-out; retries; and impact on shared resources. Watching only one Agent's final answer misses failures amplified through coordinators, queues, and downstream automation.

Baseline by user, tenant, tool, and version; otherwise normal high-volume customers can mask an anomaly in a small tenant. Alerts should identify an executable runbook and owner, and false positives and negatives should be measured. Apply data minimization, access control, integrity protection, and retention management to logs. Security logs are sensitive assets too.

## Agent incident-response process

### 1. Prepare

Maintain contacts, severity levels, and runbooks for tool disablement, credential revocation, knowledge-source isolation, queue pausing, read-only degradation, version rollback, and notification decisions. Run tabletop and technical exercises regularly.

### 2. Detect and analyze

Confirm that an incident is real. Identify affected assets, users and tenants, time window, model, prompt, tool, and data versions, and the attack path. Distinguish a model error, policy flaw, credential abuse, supply-chain change, or ordinary operational failure.

### 3. Contain

First limit blast radius: disable a specific tool, revoke an identity, block a destination, isolate a knowledge source, or pause automatic execution. Do not allow dangerous actions to continue merely to collect evidence. Record short-term containment separately from a permanent fix.

### 4. Preserve evidence and eradicate

Preserve the minimum necessary and controlled events, hashes, configuration, and version snapshots, and record the chain of custody. Remove poisoned memory or data; repair authorization or policy; rotate exposed credentials; replace contaminated artifacts. Organizational security, privacy, and legal responsibilities must determine which evidence can be retained and notification timing.

### 5. Recover safely

Replay attack and normal cases in isolation. Restore service in stages only after the gates pass, then continue watching for recurrence. Recovery is not merely restarting a service: confirm that identities, data, memory, and the supply chain have returned to a known-good state.

### 6. Review and improve

Write a blameless timeline, root cause, and contributing conditions. Do not stop at “the model did not listen.” Give every permanent remediation an owner, due date, and verification. Feed the real path into the threat model, regression set, monitoring, and runbook.

These six phases are an Agent-focused teaching adaptation, not a chapter-for-chapter reproduction of NIST SP 800-61 Rev. 3 or a compliance checklist. That revision places incident-response recommendations back into ongoing cybersecurity risk-management activity. Organizations must still design exercisable runbooks around their own CSF and security process, legal and privacy escalations, and system roles.

## Minimum incident-record fields

Incident ID; first-observed and actual-occurrence times; detection channel; assets and impact; scope; versions; attack path; containment actions; evidence location; credential and data handling; recovery gate; communication decision; residual risk; and follow-up owner.

## Common mistakes

- Saving only the final answer, without tool, identity, policy, or version evidence.
- Testing only model refusal in a red team, not real side effects and data flows.
- Raising alerts without a run ID, tenant, or runbook, making them impossible to act on during an incident.
- Recording every prompt and secret “for evidence,” thereby creating a secondary disclosure.
- Closing an incident after changing a prompt, without revoking access, removing poisoned memory, or adding regression coverage.

## Exercise and self-check

For an attempted email send caused by indirect injection, complete a one-page incident record: timeline, assets, attack path, evidence, immediate containment, root cause, permanent fix, and recovery gate. Then design an emergency-shutdown exercise and measure time from detection to disablement and from disablement to safe recovery.

- [ ] Can bind every red-team sample to real assets, permissions, and prohibited end states.
- [ ] Can detect, investigate, and contain anomalies with minimum-sufficient telemetry.
- [ ] Can quickly disable tools, revoke identities, isolate data, and roll back.
- [ ] Can turn an incident path into lasting regression coverage rather than only writing a retrospective.

## Next step

Complete [[ai-safety/03-project-and-self-assessment/07-project-offline-agent-threat-review|Offline Agent Threat Review]] to put every concept in this course into a runnable contract.

## References

- [MITRE ATLAS](https://atlas.mitre.org/) (continuously updated; accessed 2026-07-22)
- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework) (accessed 2026-07-22)
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) (*Incident Response Recommendations and Considerations for Cybersecurity Risk Management*, final April 2025; accessed 2026-07-22)
