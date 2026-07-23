---
title: "Incident Response and Continuous Improvement"
tags:
  - llmops
  - incident-response
aliases:
  - LLM Application Incident Response
source_checked: 2026-07-21
lang: en
translation_key: LLMOps/02-生产工程/07-事故响应与持续改进.md
translation_source_hash: f6f4a3f5a5f8464c3e634c4c623bc3213ef71705c3192c690fe6dc1a82fbf8f2
translation_route: zh-CN/LLMOps/02-生产工程/07-事故响应与持续改进
translation_default_route: zh-CN/LLMOps/02-生产工程/07-事故响应与持续改进
---

# Incident Response and Continuous Improvement

## Goal

When an LLM application has a quality, safety, cost, or provider failure, protect users and preserve evidence first, then locate the concrete change in prompt, context, retrieval, model, tool, or policy.

## An LLM incident is not only a 5xx

All of the following can be incidents:

- The service returns 200 while producing many factual errors or unsupported answers.
- Tool parameters are well formed, but a tool queries beyond its authority or writes repeatedly.
- Prompt injection makes the system reveal context that should not be shown.
- Provider or gateway retries make costs or queues explode.
- A retrieval snapshot is not updated, so the system reliably returns an obsolete policy.
- The observability pipeline drops crucial spans, so impact cannot be determined.

Classify severity from user impact, data and safety consequences, reversibility, scope, and duration—not HTTP error rate alone.

## Principles for the first 30 minutes

1. **Declare the incident and an owner.** Record start time, known impact, incident commander, and communication channel.
2. **Contain it.** Stop Canary expansion; disable high-risk tools; move to a read-only or human workflow; or roll back the complete manifest.
3. **Preserve evidence.** Freeze the release, release manifest, and candidate-gate full SHA-256 digest; gateway routing; policy; retrieval snapshot; evaluation report; redacted Trace references; and provider request IDs. A short fingerprint helps a human read records but cannot bind incident evidence by itself.
4. **Assess scope.** Group controlled metadata by time, release, task, tenant, or region. Do not broaden access to sensitive data merely for statistical convenience.
5. **Communicate known facts.** Separate confirmed impact, hypotheses under investigation, and scope that is still unknown.

Do not bulk-clean logs or overwrite snapshots before preserving evidence. Do not turn on full sensitive-prompt logging ad hoc just to investigate: that can create a second incident.

## Triage by component

| Evidence | Check first | Do not conclude immediately |
| --- | --- | --- |
| A regression appears only in a new release | Manifest difference, cache isolation, routing | The model must have become worse |
| Every release fails | Provider, shared gateway, data source, shared tool | Rolling back the application will fix it |
| Only retrieval-backed requests fail | Index snapshot, authorization filtering, chunking, reranker | The prompt must be rewritten |
| Tool writes repeat | Retry, timeout, idempotency key, tool implementation | The model is “too eager” |
| Cost spikes | Agent loop, retry, cache hit, output length, pricing version | There are simply more users |

A metric change is a clue. Root cause needs a timeline, version differences, and testable hypotheses.

## Recovery and verification

Before repairing, define evidence that the service has recovered: key-path smoke tests, user SLIs, audit of tool side effects, quality and safety samples, and observability completeness. A successful control-plane rollback does not prove user impact stopped. External effects already written still need to be found, reversed, or communicated.

Restore traffic progressively, verify that monitoring itself works, and avoid jumping from total degradation directly to full load.

## Turning a postmortem into an engineering loop

A blameless postmortem focuses on how the system allowed a failure to happen and expand, while still making responsibility boundaries and action-item owners explicit. Useful outputs include:

- an evidence-based timeline plus root cause and contributing factors;
- why an offline gate, Canary, or alert did not intercept it earlier;
- new regression samples accepted only after human triage, redaction, deduplication, permission, and minimal reproduction, together with new assertions, runbooks, or automated containment;
- verifiable action items such as “add an idempotency-key contract test for the write tool,” not “be more careful next time”;
- when and how the improvement will be rehearsed.

## Exercise and self-check

Scenario: after a new release deploys, cost doubles while total request count is unchanged. Repeated tool writes increase, and some Traces show retries around model calls. Write the first 30 minutes of containment, evidence preservation, scope assessment, and recovery verification. Then answer:

1. Which evidence supports rollback, and which items remain only correlating clues?
2. Why might rolling back only the model fail to stop repeated writes?
3. Which new regression samples and contract tests should this incident create?

## Summary and next step

Incident response succeeds not when “errors disappear,” but when user risk is controlled, evidence is complete, recovery is verified, and lessons enter the regression suite and release policy through controlled acceptance. Respect the role boundaries in the Evaluation Framework's offline-to-online evidence handoff, then integrate the course through [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|Offline Release Gate Project and Self-Check]].

## References

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — published 2025-04; accessed 2026-07-21.
- [NIST AI RMF: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — accessed 2026-07-21.
- [Google SRE: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) — accessed 2026-07-21.
