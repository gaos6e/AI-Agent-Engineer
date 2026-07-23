---
title: "Responsible Use and Risk Controls"
tags:
  - ai-agent-engineer
  - ai-foundations
  - responsible-ai
aliases:
  - Introduction to trustworthy AI
content_origin: original
content_status: dynamic
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/02-工程决策/10-负责任使用与风险控制.md
translation_source_hash: 0425d9210e41116c87ea513d5bb2e7f2021f2c8280571f972570925f3cf473e7
translation_route: zh-CN/AI基础认知/02-工程决策/10-负责任使用与风险控制
translation_default_route: zh-CN/AI基础认知/02-工程决策/10-负责任使用与风险控制
---

# Responsible Use and Risk Controls

## Learning objective

You will turn “responsible” from a slogan into design questions: who is affected, which data may be used, how errors are found, who can veto the system, and who handles incidents.

## Trustworthiness is not one overall score

The NIST AI RMF lists trustworthy-AI characteristics including validity and reliability; safety; security and resilience; accountability and transparency; explainability and interpretability; privacy enhancement; and fairness with harmful bias managed. **Resilience** means that a system can sustain or recover necessary functions under failure, attack, or change. **Accountability** means that responsibility and decisions can be assigned to organizations and people. **Explainability and interpretability** concern whether people can understand an output, mechanism, or rationale in its specific context.

**Stable fact:** These characteristics interact and can require tradeoffs; doing well on one does not make the whole system “trustworthy.” For example, recording more logs can support accountability while increasing privacy exposure; completely hiding inputs can support privacy while preventing a reviewer from judging evidence.

Responsible use needs a contextual statement of what is protected first, what residual risk is accepted, who approves it, and when it is reviewed.

## Minimum control surface

### 1. Data boundaries

- Collect only data needed for the task; state source, purpose, retention period, and deletion method.
- Classify public, internal, confidential, and sensitive personal information. Do not send highly sensitive data to unapproved external services by default.
- Test sets, logs, and feedback samples can also contain sensitive information; do not protect only the “production database.”
- When using synthetic or de-identified data for development, still check whether it exposes real templates or can be combined with other information to re-identify a person.

### 2. Permissions and security

- Give every tool a separate identity and least privilege; authorize reading, writing, deletion, and sending separately.
- Treat untrusted documents, web pages, and user input as data; they must not change system-level permissions.
- Do not place secrets in prompts, notes, source code, or logs; inject them through secure configuration and support rotation.
- Apply argument validation, rate limits, idempotency, approvals, and audit to write actions.

### 3. Transparency and accountability

- Tell users where AI is used, whether output is advice or a decision, and how they can give feedback or appeal.
- Preserve the system’s intended and prohibited uses, data, evaluation, limitations, versions, and owners.
- Make key outputs traceable to input evidence, tool results, and approval records.
- Assign responsibility to organizations and people; never write that “the model decided on its own.”

A Model Card can record a model’s intended use, evaluation conditions, and limitations. A Datasheet can record data motivation, composition, collection, and recommended use. They are transparency tools, not automatic proof of safety.

### 4. Effective human oversight

“Human review exists” is a control only if all of these are true:

- The reviewer has time, domain knowledge, and original evidence.
- The interface clearly shows uncertainty, sources, and system limitations.
- The reviewer can reject, change, stop, or escalate an incident.
- The organization checks whether reviewers mechanically accept AI advice.
- Final responsibility and the appeal path are clear.

### 5. Fairness and accessibility

Average accuracy can conceal systematic errors for particular languages, regions, devices, or groups. First identify which groups may be affected differently, then check errors across reasonable groupings and include domain experts and affected people in review. Not every sensitive attribute can lawfully or appropriately be collected; when measurement is impossible, record the limitation rather than assuming no problem exists.

### 6. Resource and environmental impacts

Training, inference, data storage, and hardware refresh all consume compute, energy, water, and materials. Impact depends on models, hardware, regional electricity, utilization, request volume, and lifecycle; one universal number cannot replace measurement. In engineering, compare smaller models, caches, batching, on-demand retrieval, operating region, and retention period, and record quality–cost–environment tradeoffs.

Resource and environmental impacts are part of lifecycle risk and impact assessment. They should not be described as an additional independent characteristic in NIST’s trustworthy-AI list.

## Conservative principles for high-impact contexts

When output affects medicine, employment, credit, educational opportunity, legal rights, physical safety, or significant financial impact:

1. First check applicable laws, industry standards, and organizational policies; this lesson is not legal advice.
2. Do not allow a general-purpose LLM to make the final decision alone.
3. Provide review by qualified professionals, access to evidence, objections, and appeal channels.
4. Validate in real contexts and on relevant groups rather than adopting a generic benchmark.
5. If risk cannot be shown to be within tolerance, do not deploy or substantially narrow the use.

## Risk register: leave evidence for decisions

For every risk, write at least:

| Field | Question |
| --- | --- |
| Scenario and affected people | Who is affected, when, and how? |
| Trigger and consequence | What condition triggers it, and what is the worst plausible consequence? |
| Existing controls | What are the preventive, detective, and response controls? |
| Evidence and metrics | How will you know the controls work? |
| Residual risk | What uncertainty remains after controls? |
| Owner and deadline | Who is responsible, and when is review due? |
| Decision | Accept, reduce, transfer, avoid, or retire? |

## Exercise: review “automatically send meeting minutes”

A team wants a system to read meeting recordings, generate minutes, and automatically send them to all attendees. Complete the following:

1. List data subjects (people whose information is collected, recorded, or inferred), data types, authorization questions, and retention questions.
2. Find at least five consequences of failure, including misidentified speakers, omitted objections, and incorrect recipients.
3. Split the function into transcription, summarization, action items, recipient selection, and sending, marking the responsibilities of AI, rules, and people for each.
4. Design a low-risk version: generate a draft only, show source evidence, and require the meeting owner to confirm recipients and content before sending.
5. Fill in three risk-register entries for that version and state shutdown conditions.

## Self-check

1. Why does “the data is public” not automatically mean “it may be used for any AI processing”?
2. When is human review merely a formal control?
3. What can a Model Card not solve?
4. What should happen when privacy and auditability conflict?

Suggested answer points: purpose, licensing, contextual expectations, and harms still matter; review is ineffective when a reviewer lacks time, evidence, authority, or independence from system over-trust; documentation cannot replace actual evaluation and controls; minimize records, use tiered access, retain necessary evidence with clear retention periods, and record tradeoffs with an accountable owner.

## Related concepts

- [[ai-safety/00-index|AI Safety]] focuses on deliberate attacks and system defenses, while [[privacy-computing/00-index|Privacy Computing]] focuses on privacy techniques and their applicability boundaries in data processing.
- [[ai-governance/00-index|AI Governance]] owns responsible people, policies, review, and evidence chains; technical controls do not replace organizational accountability.
- [[data-annotation/00-index|Data Annotation]] and [[data-synthesis/00-index|Data Synthesis]] affect representativeness, bias, permissions, and traceability.

> [!note] Scope of this lesson
> This lesson identifies affected people, tradeoffs, effective human oversight, and responsibility assignment. For concrete failure diagnosis, see [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability Boundaries and Failure Modes]]. For go/no-go release conditions, see [[ai-foundations/02-engineering-decisions/09-from-prototype-to-launch-and-exit|From Prototype to Launch and Exit]].

## Summary and next step

Responsibility boundaries must become data, permissions, tests, oversight, and incident response. Now continue with [[ai-foundations/03-project-and-self-assessment/11-integrated-project-meeting-action-item-assistant|Integrated Project: Meeting Action-Item Assistant]], which combines the first ten lessons into an acceptable system plan.

## References

Accessed **2026-07-22**.

- [NIST: AI Risks and Trustworthiness](https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/)
- [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
- Gebru et al., [Datasheets for Datasets](https://doi.org/10.1145/3458723)
- [Stanford HAI: 2026 AI Index Report](https://hai.stanford.edu/ai-index/2026-ai-index-report) (used to track capability, transparency, responsibility, and resource trends; trends do not replace measurements of a specific system)
