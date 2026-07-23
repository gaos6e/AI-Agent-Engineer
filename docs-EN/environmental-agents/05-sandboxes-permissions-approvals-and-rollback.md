---
title: "Sandboxes, Permissions, Approvals, and Rollback"
tags:
  - environment-agent
  - sandbox
  - human-in-the-loop
aliases:
  - Environment Agent Security Controls
source_checked: 2026-07-22
lang: en
translation_key: 环境型Agent/05-沙箱权限审批与回滚.md
translation_source_hash: 418e0858cfa16fca7cefd108d2ade2668e3124c052b529094104dd39c9a6aec7
translation_route: zh-CN/环境型Agent/05-沙箱权限审批与回滚
translation_default_route: zh-CN/环境型Agent/05-沙箱权限审批与回滚
---

# Sandboxes, Permissions, Approvals, and Rollback

## Objectives

- Separate capability, identity, policy, approval, and sandbox into independent control layers.
- Tier actions by their side effects instead of tool names.
- Define stopping, approval, rollback, or compensation strategy for irreversible work.

## Why “the model will be careful” is not a security control

An environment-based Agent handles user instructions together with untrusted webpages, documents, issues, and terminal output. The model may misunderstand, follow prompt injection, or continue an old plan after state changes. A prompt saying “do not delete files” cannot stop an adapter that has delete permission; a sandbox cannot replace business authorization when an isolated environment can still message a real API or place an order.

Controls must be combined outside the model: identity answers “who”; capability describes “what can be requested”; policy decides “is it allowed in this context”; approval handles a specific decision a human must own; sandbox limits blast radius; and receipt/audit records what actually happened.

### Identity, delegation, credentials, and approval are four different pieces of evidence

| Evidence | Issuer or verifier | What it must bind | Typical error |
| --- | --- | --- | --- |
| Subject identity | Identity provider, trusted session, or service identity | User/service subject, tenant, authentication strength, session/service ID | Treat model-claimed username or page avatar as identity |
| Delegation/capability | Policy service or runtime | Purpose, tool/resource scope, budget, expiry, run | Give an Agent a human administrator's long-lived global token |
| Adapter credential | Credential service and adapter | This environment only, minimal scope, short lifetime, revocability | Infer any site/system is operable because “the user is logged in” |
| Approval | Trusted approver or workflow | One normalized high-impact intent, target, amount/data range, current environment, nonce | Treat “allow continuation” or model output as a general approval |

Runtime records should preserve integrity-protected, verifiable correlations among subject, delegation, adapter actor, policy decision, approval, and receipt for later reconciliation. Audit does not mean indefinitely copying full prompts, pages, files, tokens, and PII into logs. Define classification, minimum retention, protected raw-content location, hash/digest, redaction rule, and reader permission for every field. When necessary safety evidence for a high-impact action cannot be written, fail closed or hand off to a human according to risk rather than proceeding silently.

## How to implement it

| Risk tier | Example | Default controls |
| --- | --- | --- |
| Read-only, low sensitivity | Read an allowed directory or query test state | Scope allowlist, rate/budget, audit |
| Reversible local write | Edit a file in an isolated worktree | Snapshot/diff, idempotency, path restriction, automatic rollback |
| Compensable external write | Create a draft or cancellable appointment | Exact identity, preview, idempotency, compensation step, required approval |
| Irreversible or high impact | Pay, send, delete, publish, change permission | Deny by default; strong identity, short-lived exact approval, two-person or human execution |

An approval object should contain task/run/policy; action ID, kind, and normalized parameter digest; idempotency key; target identity/path/origin; amount or data range; environment instance ID; state fingerprint/generation; expiry; approver; and one-time nonce. Any critical field change invalidates approval. Matching a version number alone does not prove the environment remains in the state that was approved.

An approval record must not be an optional field in the model action schema. This course runtime makes `Action.from_dict` fail closed for unknown fields. Model-external `register_approval` receives evidence and verifies it with a trusted approver's HMAC key. Its signed payload binds `task_id`, `run_id`, `policy_version`, `action_id`, `idempotency_key`, `intent_digest`, `environment_version`, `environment_instance_id`, `state_fingerprint`, `environment_generation`, `expires_at_proposal`, `expires_at_unix_ms`, and `nonce`.

Proposal-count expiry limits the last proposal at which a record is valid (equality is valid); trusted wall-clock expiry prevents approval remaining valid forever when the Agent stops proposing (the exact expiry instant is invalid). The runtime consumes the nonce when an action passes the authorization gate. If a write enters pending, it checkpoints complete signed evidence and the consumed set. Recovery revalidates the signature, trust root, and state binding but does not mistake expired historical evidence for a corrupted checkpoint: pending execution remains frozen. Only `refresh_pending_approval` with fresh trusted evidence bound to the same action/key/intent/instance/fingerprint/generation can replace active evidence, while the old evidence remains in the trace. Unknown issuer, signature tampering, replay across task/run/policy/action/idempotency key, same version but different state, automatic execution after expiry, and attempts to use idempotent replay to bypass approval all fail closed.

> [!warning] Boundary of teaching HMAC
> Symmetric HMAC is used only to demonstrate that issuance authority is outside the model process. A production system normally needs a separate approval service, KMS/HSM, or verifiable asymmetric signatures, with issuance, registration, consumption, revocation, and key rotation audited. If the model can read the approval key, all field binding becomes meaningless.

Rollback depends on the environment: a browser draft can be deleted or withdrawn, a desktop file can be restored from a snapshot, and code can apply an exact inverse patch. External messages, payments, and data disclosure often cannot be truly rolled back; they need compensation or incident response, so preview and approval need to be stronger before execution.

## Common failures

- The Agent uses a human administrator account and all tools share one long-lived token.
- Approval says only “continue,” or the model generates an approval field with its action; it remains valid after target, amount, or content changed.
- The sandbox allows arbitrary network access, so file-system isolation does not prevent data exfiltration.
- Text in a webpage, issue, or test output is promoted into an authorization source.
- A non-idempotent write is retried; a rollback script overwrites a user's newer changes.
- Success logs exist, but refusal, approval, cancellation, takeover, and recovery audit does not.

## How to validate

Build an authorization matrix: test allow and deny for every identity/action/scope pair, and assert denial happens before side effects. Independently tamper with signature, task/run/policy/action, idempotency key, intent, environment instance, state fingerprint/generation, and both expiry kinds; verify that a consumed nonce cannot replay before or after checkpoint recovery. Also test “same version but different content,” “same state but another environment instance,” “wait without new proposals until wall-clock expiry,” “expired pending remains non-executable after recovery until fresh exact approval,” and “existing receipt without new approval.”

Inject indirect prompts, network exfiltration, path traversal, symlink/redirect, repeated requests, and human cancellation, then inspect result and environment diff. Exercise compensation rather than merely verifying that a revoke button exists.

## Practice task

For “read a ticket, draft a response, send email,” design three capabilities: read ticket, save draft, and send. Specify identity, data scope, network destination, idempotency key, and approval for each. Prove hostile ticket content cannot change the recipient; changing body or recipient after approval triggers reapproval; and a send timeout checks receipt before resending.

## References

- [[ai-safety/00-index|AI Safety]] — prompt injection, least privilege, supply chain, sandboxes, and incident recovery.
- [[agent-core/06-human-in-the-loop-and-control|Human-in-the-loop and Control]] — approval fingerprints, state version, scope, and expiry.
- [Playwright: Best Practices](https://playwright.dev/docs/best-practices) — engineering examples of isolated tests and avoiding uncontrollable third-party environments.
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) — minimal tool permissions, external-data boundaries, sensitive operations, and security testing; checked 2026-07-22.
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) — confused deputy, cross-service permission aggregation, tool-result injection, and audit boundaries; checked 2026-07-22.

