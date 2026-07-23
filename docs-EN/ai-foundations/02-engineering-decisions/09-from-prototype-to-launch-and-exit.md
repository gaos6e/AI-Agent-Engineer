---
title: "From Prototype to Launch and Exit"
tags:
  - ai-agent-engineer
  - ai-foundations
  - engineering-lifecycle
aliases:
  - Introduction to the AI engineering lifecycle
  - AI launch gates
content_origin: original
content_status: dynamic
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/02-工程决策/09-从原型到上线与退出.md
translation_source_hash: 279a9a34235ad0d4b64fc3374e604c0e48a2d21bd734cb577714e7df3438263a
translation_route: zh-CN/AI基础认知/02-工程决策/09-从原型到上线与退出
translation_default_route: zh-CN/AI基础认知/02-工程决策/09-从原型到上线与退出
---

# From Prototype to Launch and Exit

## Learning objective

After this lesson, you should be able to move a selected AI solution toward a rollback-ready pilot, explain eight lifecycle deliverables, three launch gates, shadow mode, third-party dependency control, and exit conditions.

## Where this lesson starts

Before entering this lesson, [[ai-foundations/02-engineering-decisions/08-when-to-use-ai-and-system-shape-selection|When to Use AI and Select a System Shape]] should already have produced target users, a current baseline, allowed and forbidden scope, candidate system shapes, major risks, decidable metrics, and owners. This lesson no longer asks whether to use AI; it asks how the selected scope becomes subject to evidence and gates.

## Lifecycle: eight deliverable stages

### 1. Context and responsibility

Identify users, affected people, data owners, business owners, technical owners, and incident recipients. Record applicable policies, risk tolerance, approvers, and review dates.

**Deliverables:** responsibility matrix, applicable-requirements inventory, and risk-register entry point.

### 2. Requirements and boundaries

Define inputs, outputs, non-goals, forbidden actions, human responsibilities, permissions, and system stop conditions. Scope changes must be re-reviewed; they cannot silently expand from the prototype’s defaults.

**Deliverables:** requirement card, trust-boundary diagram, output and tool contracts.

### 3. Data and evidence

State where examples came from, whether they contain sensitive information, and whether they cover actual populations and exceptions. Training data, prompt examples, retrieved documents, feedback, and online logs are different objects and must be governed separately.

**Deliverables:** data inventory, provenance and permissions, test-set version, deletion and retention rules.

### 4. Prototype and baseline

Use the simplest approach to establish comparable results. A prototype uses de-identified or synthetic data, does not connect high-permission production tools, and treats model output as a candidate rather than a direct business side effect.

**Deliverables:** reproducible prototype, rules or human baseline, and known-failures record.

### 5. Offline evaluation

Freeze representative tests and define task, safety, cost, and latency thresholds as described in [[ai-foundations/01-concept-map/04-evaluation-evidence-and-feedback-loops|Evaluation Evidence and Feedback Loops]]. Analyze errors by type and critical slice rather than average score alone.

> [!note] Offline evidence needs a handoff package
> Passing offline evaluation is not a release conclusion. Before a pilot, hand off the test set and system version, uncovered or unpassed risks, release rationale, online signals to observe, and rollback triggers. Otherwise an online incident cannot be traced to its original hypothesis. The concrete handoff contract for evidence, decisions, and regression is described in [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]].

**Deliverables:** evaluation report, version comparison, unresolved risks, and release recommendation.

### 6. Shadow and limited-scope pilot

**Shadow mode** lets a new system receive real or near-real inputs and produce results without directly using them for user or business actions; the team compares them with the existing process. “Generate drafts only” instead allows real users to review candidate results within a controlled scope.

Both need lawful data use, access control, minimized logging, an observation period, and exit conditions. A pilot is not a “half launch” that bypasses review.

**Deliverables:** pilot plan, user notice, human process, observation metrics, and daily or weekly review.

### 7. Release and operational monitoring

Preserve versions of the model, prompts, tools, knowledge base, code, policies, and dependencies; expand traffic gradually through staged rollout. Monitor task quality, errors, latency, cost, refusals, human overrides, degradation, and security incidents. Logs themselves must minimize sensitive data and restrict access.

**Deliverables:** release checklist, dashboard, alert ownership, runbook, and rollback steps.

### 8. Incident response and exit

Predefine degradation, rollback, notification, isolation, post-incident review, data deletion, and retirement processes. Exit may be required because risk becomes uncontrollable, benefit disappears, a vendor changes, data authorization ends, or a simpler solution becomes sufficient—not only because “the system broke.”

**Deliverables:** incident severity levels, rollback drill, retirement and migration plan, and post-incident record.

NIST AI RMF organizes risk-management outcomes as **Govern, Map, Measure, and Manage**. They interrelate and iterate; they are neither the original wording of the eight stages above nor a waterfall that must be completed once in order. The eight stages are an engineering mapping for learning.

## Third-party dependencies are part of the release unit

Model services, tool APIs, data sources, SDKs, content filters, identity services, and vendor terms can all change. A dependency inventory should record at least:

- Name, purpose, owner, and data flow.
- Pinned version or current service identifier.
- Rate limits, timeouts, error semantics, and availability assumptions.
- Data retention, training use, region, and subprocessor requirements.
- Change notices and re-evaluation triggers.
- Degradation, alternative vendors, human processes, and data-export methods.

After a service update, “it still returns HTTP 200” does not mean quality, format, and risk remain unchanged. Critical changes require regression, reapproval, and a preserved rollback target.

## Three launch gates

### Value gate

- Does the solution genuinely improve the goal compared with rules, people, or the previous stable version?
- Are cost, latency, human workload, and maintenance cost acceptable?

### Quality gate

- Do core, boundary, adversarial, permission, and dependency-failure tests meet preset thresholds?
- Does the test data represent real use and remain independent from development?
- Are versions, data, reviews, and results reproducible?

### Risk gate

- Are there clear owners, least privilege, effective human oversight, monitoring, and fallback?
- Are unmeasurable risks recorded along with a decision to accept, reduce, avoid, or stop?
- Do high-impact cases retain qualified professional review and an appeal path?

If any gate fails, keep the original scope, narrow the capability, or stop deployment. “We will observe after launch” cannot replace a gate.

## Release, degradation, rollback, and retirement are different

| Action | When to use it | Example |
| --- | --- | --- |
| Degrade | A dependency or advanced capability is temporarily unavailable | When a reranker times out, use basic retrieval and mark the result as degraded |
| Roll back | A new version regresses | Restore the previous model, prompt, and tool combination |
| Rate-limit/isolate | Load, misuse, or an incident requires reducing impact | Pause write tools and retain read-only queries only |
| Retire | The use is no longer justified or risk is unacceptable | Turn off automatic actions, restore the human process, and handle retained data |

Rollback requires old versions, configuration, and data compatibility to remain usable. Writing only “roll back when necessary” without a drill is not a control.

## Exercise: design a controlled release

Scenario: internal policy question answering is upgraded from keyword retrieval to LLM-generated answers with citations.

1. Write one deliverable for each of the eight stages.
2. Design shadow mode and say who still supplies the real answer.
3. Write two decidable conditions for each of the value, quality, and risk gates.
4. List dependency controls for the model API, vector store, identity service, and document source.
5. Define degradation for empty retrieval, model timeout, citation-validation failure, and permission-data anomaly.
6. Define two rollback conditions and two permanent-retirement conditions.

## Self-check

1. What is the difference between shadow mode and direct low-traffic automatic execution?
2. Why is a pilot still needed after passing offline evaluation?
3. Why is a dependency version part of the system version?
4. What do degradation, rollback, and retirement each solve?
5. When should a system retire rather than keep tuning the prompt?

## Scope and next step

This lesson defines release gates and exit only. Failure categories are maintained by [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability Boundaries and Failure Modes]]; metrics and evidence by [[ai-foundations/01-concept-map/04-evaluation-evidence-and-feedback-loops|Evaluation Evidence and Feedback Loops]]; organizational responsibility and tradeoffs for affected people continue in [[ai-foundations/02-engineering-decisions/10-responsible-use-and-risk-controls|Responsible Use and Risk Controls]].

## References

Accessed **2026-07-22**.

- [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)
- Gebru et al., [Datasheets for Datasets](https://doi.org/10.1145/3458723)
- Sculley et al., [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)
