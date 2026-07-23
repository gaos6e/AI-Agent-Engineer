---
title: "Release Approval and Change Management"
aliases:
  - AI Release Approval and Change Management
tags:
  - ai-governance
  - approval
  - change-management
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/02-控制与治理/05-上线审批与变更管理.md
translation_source_hash: 3c42826889f5d0c54e81214b62fd59a085d565d1860ecb635449c544edf6fef1
translation_route: zh-CN/AI治理/02-控制与治理/05-上线审批与变更管理
translation_default_route: zh-CN/AI治理/02-控制与治理/05-上线审批与变更管理
---

# Release Approval and Change Management

## Goal of this lesson

Turn “this system may be released” into a traceable decision bound to a specific version, use, conditions, and expiry, and make changes trigger review proportional to risk. A single approval is not a permanent pass for a product name.

## Begin with stage gates

Governance gates should fit the development cadence, not arrive to stamp paperwork at the end of a project:

1. **Intake**: define the problem, affected people, non-AI alternative, owners, and prohibited uses; stop clearly unacceptable proposals before development investment.
2. **Controlled experiment**: use only synthetic or authorized data, limit users and tools, register the system and vendor, and record early risks.
3. **Pre-production review**: complete impact assessment, technical evaluation, security and privacy review, operating instructions, monitoring, rollback, and incident runbooks.
4. **Release decision**: the approver chooses rejection, a time-limited pilot, conditional release, or formal production release; “review passed” is not enough.
5. **Expansion and change**: reassess by impact when adding regions, users, data, tools, or autonomy.
6. **Periodic review and retirement**: even without an intentional change, re-evaluate the basis for continued use according to risk, incidents, and the external environment.

A low-risk drafting tool can use a lightweight approval path. A system affecting rights, safety, or significant opportunities needs multidisciplinary review and independent challenge. Fewer documents never means less responsibility.

## Release evidence pack

At minimum, an approver should see the system inventory and owners; intended and prohibited uses; benefits and non-AI baseline; impact assessment; data, model, and vendor records; scenario-based evaluation; threat and privacy review; human oversight; user information; monitoring thresholds; incident, rollback, and retirement plans; and every unresolved risk.

The approval record includes:

- the decision and rationale, approver, and their authority;
- the bound model, prompt, index, tool, policy, code, and evaluation versions;
- permitted users, regions, data, traffic, autonomy, and expiry;
- mandatory release conditions, exceptions, residual-risk owner, and review date; and
- triggers to pause or re-review when limits, complaints, incidents, or changes occur.

Record immutable versions or content hashes for critical artifacts, and have a controlled release gate compare the approved artifact with the actual release before deployment. That enables the system to **detect and block** “A was approved but B was deployed.” Storing an isolated hash can neither prevent substitution nor prove that A is safe, effective, or lawful. See [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]] for the handoff contract between offline evidence, release gates, and online regression.

## What changes need re-review?

Changes include, but are not limited to, a model or vendor version; system or developer prompt; fine-tuning data; RAG knowledge source; embeddings and index; threshold; guardrail; tools and permissions; the business workflow receiving output; degree of autonomous execution; target group; region; language; data category; retention policy; and dependency terms.

Begin with impact analysis: does the change alter the purpose, affected people, reversibility, data flow, attack surface, performance distribution, transparency information, or legal role? A spelling correction can take a lightweight path. A seemingly small prompt or tool-schema change may alter behavior and needs relevant regression testing. A silent vendor update is also a change; when it cannot be detected or pinned, compensate with continuous benchmarks and disablement conditions.

The result of impact analysis is not only `material=true/false`. It should list the affected risks, controls, evaluations, disclosures, approval conditions, and runtime thresholds. Artifact owners then confirm whether reuse, incremental validation, or full re-review is required. When the impact scope cannot be determined, expand review rather than assume old evidence still applies.

## Release and exceptions

Release with limited traffic, a clear observation window, a rollback-capable version, and manual fallback. On validation failure, stop expansion by default rather than lower a threshold until it passes. An emergency fix can shorten the pre-change process, but its scope must be bounded, its approval named, its evidence retained, and its post-change review completed promptly.

An exception record states its reason, compensating controls, owner, deadline, and revocation condition. An exception without expiry becomes an undeclared policy; repeated renewals of the same exception should escalate to the governance body for decision.

## Exercise and self-check

Write a change review for adding a ticket-creation tool to a read-only FAQ Agent. List the new assets, permissions, attack paths, tests, approval conditions, gradual rollout, rollback, and user information that must be updated. Explain why the prior approval cannot simply carry over.

- [ ] Approval is bound to exact version, purpose, scope, and expiry.
- [ ] A developer cannot accept their own material residual risk alone.
- [ ] Can identify changes in prompts, data, tools, and workflows as well as the model itself.
- [ ] Emergency changes and exceptions have boundaries, evidence, and exit conditions.

## Next step and source baseline

Continue with [[ai-governance/02-controls-and-governance/06-runtime-monitoring-incidents-and-retirement|Runtime Monitoring, Incidents, and Retirement]]. Sources were accessed on 2026-07-22. See the [NIST AI RMF Manage Playbook](https://airc.nist.gov/airmf-resources/playbook/manage/), the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), and [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1). Frameworks provide decision-making ideas; an organization must express its real authorization matrix and change process in its own policies.
