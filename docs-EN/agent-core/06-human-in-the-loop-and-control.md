---
title: "Human-in-the-Loop and Control"
tags:
  - agent-core
  - human-in-the-loop
  - approval
aliases:
  - Agent Human Approval
  - Human-in-the-Loop
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: Agent 核心/06-人在回路与控制权.md
translation_source_hash: a40079e2942eb43c0851b13249eb08bb1b552438c1c4a2c3b78f38b220f84321
translation_route: zh-CN/Agent-核心/06-人在回路与控制权
translation_default_route: zh-CN/Agent-核心/06-人在回路与控制权
---

# Human-in-the-Loop and Control

## Objective

After this lesson, you should be able to:

- Distinguish clarification, approval, review, intervention, takeover, rejection, and cancellation.
- Design an approval contract that binds a high-risk action to its parameters, state version, and expiry.
- Model a human wait as durable, recoverable state rather than a chat window that blocks a worker.
- Recognize automation bias, approval fatigue, and rubber-stamp supervision.

## Human-in-the-loop is more than a confirmation dialog

Effective control makes the following explicit:

- Which role is responsible for what.
- Which risk or uncertainty triggers the interaction.
- What evidence and impact the person can see.
- How the person can edit, reject, take over, or cancel.
- How the decision is bound to the current action.
- How state is preserved while waiting.
- How execution is audited and compensated afterward.

NIST AI RMF 1.0 emphasizes defining and differentiating roles and oversight responsibilities in human–AI configurations. As of 2026-07-21, the NIST site stated that version 1.0 was under revision. This lesson uses its general risk-management principles; it does not treat a particular version as a conclusion about industry-specific compliance.

## Six kinds of human interaction

| Type | What the system asks | Example |
| --- | --- | --- |
| clarification | What does the goal or parameter mean? | “Which project should be processed?” |
| approval | May this frozen high-risk action proceed? | “Send this email to the customer?” |
| review | Is this candidate result acceptable? | A code diff or report draft |
| intervention | Should the plan or scope be corrected while running? | Exclude one directory |
| takeover | Should a person assume control and stop autonomy? | Respond to a production incident |
| cancel/reject | Should this action or run no longer execute? | Reject a payment or cancel a task |

Do not treat a clarification answer as general authorization, and do not interpret a passed review as permission for arbitrary later changes.

## When execution must pause

- The goal or a critical parameter is materially ambiguous.
- An action is irreversible, high-value, public-facing, a payment, a deletion, or a deployment.
- Sensitive data would cross a new boundary.
- Sources conflict or the verifier cannot decide.
- The run is about to exceed the user-authorized scope, cost, time, or geographic boundary.
- Failures recur, progress stops, or policy detects an anomaly.
- Prompt injection, tool poisoning, or a request for privilege escalation is detected.
- A legal or industry process requires an authorized role.

High model confidence cannot remove these deterministic gates.

## Approval contract

At minimum, an approval record binds the following:

~~~jsonc
{ // An unambiguous record of one human approval
  "run_id": "run-42", // This approval belongs only to this run and cannot be replayed across runs
  "action_id": "publish-report", // The approved action ID, not a vague permission to publish
  "action_fingerprint": "sha256(tool + target + normalized_args + policy_version)", // Binds tool, target, parameters, and policy version to prevent approval substitution
  "state_version": 12, // Valid only for the state version the approver saw; changes require a new approval
  "decision": "approve", // An explicit human decision; reject and cancel are also possible
  "approver_identity": "user-123", // An auditable identity for the approving principal
  "approver_role": "publisher", // A role used for authorization, not a model self-description
  "scope": {"project": "demo", "max_items": 1}, // Resources covered by the approval and their maximum quantity
  "created_at": "...", // Creation time for audit and temporal validation
  "expires_at": "...", // Execution cannot continue after expiry even when parameters are unchanged
  "policy_version": "approval-v2" // The policy version used for approval; policy changes require reevaluation
}
~~~

> [!note] JSONC teaching notation
> The end-of-line comments use JSONC for readability. Remove them before strict JSON serialization.

Revalidate before execution:

1. The approver’s current identity and role.
2. The run, action, and fingerprint.
3. That the state version is unchanged.
4. That the approval has neither expired nor been revoked.
5. That the scope is still satisfied.
6. That the target resource has not materially changed version.

Changing the body by one URL, the destination account, or the amount must invalidate an old approval.

## What an approval card should show

The smallest useful UI presents:

- **Action:** which tool will be called.
- **Target:** the specific file, account, user, or URL.
- **Impact:** writes, deletion, publication, cost, and reversibility.
- **Key parameters or diff:** the exact content being approved.
- **Source:** why the action was proposed and which observations support it.
- **Risk:** uncertainties and consequences of failure.
- **Scope and expiry:** whether it covers this one action or a time window.
- **Choices:** approve, reject, edit parameters, view more, take over, or cancel.

Raw logs create approval fatigue; a bare “Continue?” button is uninformed. Use progressive disclosure: show key impact first and allow the person to inspect complete evidence.

## Pause and resume

To enter waiting_approval:

1. Freeze the pending action and its fingerprint.
2. Persist state, event, budget, and deadline.
3. Release workers and connection resources.
4. Send a notification that contains no secrets.
5. Wait for a decision from an authorized role.

To resume:

1. Acquire the run lease.
2. Reauthenticate the approver.
3. Validate the approval contract.
4. Recheck the current resource and authorization.
5. Execute the frozen action rather than asking the model what to do again.
6. Execute once with the idempotency key.
7. Save the receipt and audit event.

Approval is not an in-memory Boolean. Recovery after a process restart must still be safe, and multiple workers must not consume the same approval twice.

> [!note] Scope of this repository’s example
> bounded_agent.py uses scope=ticket_id to demonstrate that an approval applies only to the current target, and includes the complete tool, arguments, and idempotency key in the action fingerprint. Its expiry is a logical step rather than real time; it also has no approver identity, signature, revocation list, or distributed consumption. A production approval must use the complete contract above and reauthenticate, check expires_at, and check the resource version during recovery.

## Rejection and cancellation are normal states

- **reject:** rejects the current action. The Agent may propose a no-side-effect alternative or enter rejected.
- **cancel:** terminates the complete run. Stop new actions, try to cancel in-flight calls, and report side effects that have already occurred.
- **timeout:** the approval expires. It must not default to approval, nor does it have to mean permanent rejection.
- **edit:** creates a new action and fingerprint, then requires fresh approval.

When a run enters a terminal state such as rejected, cancelled, failed, or budget_exhausted, remove the pending action from executable state and retain the audit facts in historical events. Otherwise an old approval could still appear consumable after termination. Do not communicate a rejection to the user as an exception stack trace; it is a normal control path.

## Cognitive risks in oversight

### Automation bias

People can over-trust fluent recommendations. Mitigations include:

- Show raw evidence and uncertainty.
- Do not preselect Approve.
- Require active entry or a second confirmation for high-impact actions.
- Use sampled audits and an independent verifier.
- Monitor anomalous approval rates.

### Approval fatigue

Too many low-value confirmations encourage mechanical clicks. Grade by risk:

- Automate low-risk reads.
- Approve reversible small writes by scope.
- Approve high-risk actions one by one.
- Require fresh approval for anomalies or boundary changes.

Bulk authorization must limit resources, tools, money or quantity, duration, and revocation.

### Skill mismatch

An approver who cannot understand the evidence cannot provide genuine oversight. NIST emphasizes role responsibility and personnel capability. A system should distinguish domain experts, operators, security or legal roles, and other responsibilities instead of handing every decision to the end user.

## High-risk control matrix

| Action | Default control |
| --- | --- |
| Read a public web page | Automatic; its content remains untrusted |
| Read a user’s private file | Explicit scope and minimum disclosure |
| Modify a local draft | Diff plus reversibility; product-specific approval |
| Send an external message | Preview recipient and body; approval immediately before execution |
| Delete, pay, or deploy | Strong identity, role-based, dual or graduated approval, and recovery |
| Write long-term memory | Show content, scope, TTL, and deletion method |
| Install a tool or expand privileges | An independent security decision that tool content cannot trigger |

Specific thresholds belong to an application’s risk policy; a general tutorial should not invent them.

## Exercise

For publishing a public announcement, design:

1. An approval contract.
2. The target, body diff, URL, audience, impact, and sources shown on the card.
3. The invalidation rule when the body changes after approval.
4. A checkpoint for the waiting state.
5. The approver’s role and authentication.
6. Reject, timeout, cancel, and takeover paths.
7. A publication receipt plus rollback or correction.

Then design a bulk authorization and explain how it constrains maximum items, allowed domains, lifetime, and revocation.

## Self-check

1. Why do clarification and approval have different semantics?
2. What should an action fingerprint include?
3. Why must an approval become invalid when the state version changes?
4. Why can a human confirmation still be merely performative oversight?
5. How do reject and cancel differ in scope?

You have mastered this topic only when you can make approval a durable, auditable, invalidatable contract.

## Next

Continue to [[agent-core/07-untrusted-tool-results-and-defenses|Untrusted Tool Results and Defenses]] to ensure that neither people nor the runtime are misled by environment text.

## References

The following are official risk frameworks and first-party engineering materials, retrieved or checked on 2026-07-21.

- [NIST AI Risk Management Framework](https://airc.nist.gov/airmf-resources/airmf/)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST AI RMF Appendix C: Human-AI Interaction](https://airc.nist.gov/airmf-resources/airmf/appendices/app-c-ai-risk-management-and-human-ai-interaction/)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
