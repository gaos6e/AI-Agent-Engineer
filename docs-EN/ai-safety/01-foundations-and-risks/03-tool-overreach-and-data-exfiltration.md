---
title: "Tool Overreach and Data Exfiltration"
aliases:
  - Excessive Agency and Exfiltration
  - Agent Tool Security
tags:
  - ai-security
  - tools
  - data-exfiltration
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: AI安全/01-基础与风险/03-工具越权与数据外泄.md
translation_source_hash: 9288235f3591c19f7abcd156b15637e1970b63715d2c623a98707c244a61cd29
translation_route: zh-CN/AI安全/01-基础与风险/03-工具越权与数据外泄
translation_default_route: zh-CN/AI安全/01-基础与风险/03-工具越权与数据外泄
---

# Tool Overreach and Data Exfiltration

## Learning objective

Review a tool-using Agent through functionality, permissions, autonomy, and data flow. Understand that a tool schema is not authorization, and design read/write separation, object-level authorization, egress controls, idempotency, and rate limits.

## The risk jump from “chat” to action

A conventional model can output incorrect text. A tool-using Agent can turn an error into a database write, payment, email, or code execution. OWASP's Excessive Agency can be divided into:

1. **Excessive functionality**: a task only needs to read, but can send, delete, or execute arbitrary code.
2. **Excessive permissions**: a tool uses a shared administrator identity and can access other users or tenants.
3. **Excessive autonomy**: a high-impact action needs no preview, approval, or budget limit.

Add a frequently overlooked fourth dimension: **overbroad data flow**. Any tool that can move sensitive context to an external destination can become an exfiltration channel.

## The confused-deputy problem

An Agent can possess a legitimate service identity yet perform an action for a user who lacks permission. This is a confused deputy. For example, a user supplies someone else's file ID in a prompt and the model calls the read tool anyway. The executor must authorize on the server using the authenticated user, tenant, object, and action; it must not trust a model-provided `user_role="admin"`.

Authentication answers “who are you?” Authorization answers “what may you do to this object?” Human approval answers “is this specific high-impact action informed and consented to?” None substitutes for another.

## Seven layers of a secure tool contract

### 1. Intended use to capability

Derive the minimum tool set from the task purpose. Separate read and write tools. In production, do not expose general-purpose capabilities such as debug access, shells, arbitrary HTTP, or arbitrary SQL by default.

### 2. Strict input structure

Reject unknown fields, invalid types, overlong values, and nonstandard JSON. Validate enumerations, ranges, and formats. A structured schema can only ensure that input looks like the right arguments; business authorization is still required.

### 3. Identity and object-level authorization

The tool adapter obtains user and tenant identity from a trusted session. The server checks object ownership, scope, and policy. Do not let the model choose a service account or construct an authorization context.

Recompute authorization for every call and cover at least the caller; delegated subject and tenant; workload identity; action; object; purpose; environment; and current state version. Even if an object ID passes schema validation, the server must resolve it to the real tenant and verify it. Roles and scopes from model arguments, tool descriptions, MCP Resources or Roots, or a previous cached result are not authorization facts.

### 4. Parameter and interpreter boundaries

Use parameterized queries for databases. Avoid shell concatenation for commands. Resolve file paths and confine them to permitted roots. Recheck URLs by scheme, host, port, DNS-resolution result, and redirects. A string-prefix check is usually insufficient.

### 5. Destinations and data egress

Deny destinations by default, with allowlists configured by environment, user, and tenant. Minimize sensitive fields both before they enter the model and before they leave a boundary. Inspect covert channels including email, webhooks, search queries, URL parameters, logs, filenames, and messages between Agents.

### 6. Side-effect controls

For writes, start with dry-run or preview, then obtain confirmation through a trusted channel. Use idempotency keys to prevent duplicates, state versions to prevent TOCTOU, and rate, amount, and quantity budgets to constrain blast radius. Retry only operations that are explicitly retryable and idempotent.

### 7. Output and audit

Tool output is untrusted too. Validate it first against an exact per-tool output schema, enumerations, size and depth limits; then classify fields and create a model-visible projection. Raw errors, stacks, receipts, subjects, and internal operation IDs belong only in protected audit. The model result and audit record should be generated from the same internal outcome, but the whole audit object must not be sent to the model. A complete request/result/call binding prevents swapping and tampering within one trusted pipeline; it is not cross-service identity authentication.

For a write with `OUTCOME_UNKNOWN`, do not interpret “failed” as “not executed” and automatically repeat it. The trusted host must independently query state, reauthorize, and check the subject, tool, request hash, effect or producer revision, and receipt. Without evidence, remain unknown; resolve conflicts manually. See [[tool-calling-function-calling/05-results-errors-and-untrusted-data|Tool Results, Errors, and Untrusted Data]] and [[tool-calling-function-calling/06-idempotency-timeouts-and-observability|Idempotency, Timeouts, and Observability]] for the complete offline contract.

Audit records capture the subject, tool, normalized-argument summary, policy decision, object, outcome, and correlated run ID while minimizing sensitive data. MCP Resources, Roots, and capability declarations likewise cannot replace object-level authorization. See [[mcp/learning-path/04-authorization-and-security-boundaries|MCP Authorization and Security Boundaries]] for the relevant protocol boundary.

## Analyze data-exfiltration paths

Treat a path as high priority when all three are present:

```text
Sensitive asset + attacker-controlled content + reachable external channel
```

For example, a malicious web page convinces an Agent to encode a retrieved customer list in a search URL. Even without a tool named `send_secret`, search, image URLs, DNS, logs, or collaborating Agents can carry the data out. Data-loss prevention should inspect what category of data flows to what category of destination, not merely match a few sensitive words.

## A safer send flow

```text
Model proposes a draft
  → schema validation
  → identity / object / destination / data-classification policy
  → display normalized recipient, subject, and body summary
  → user approves in a trusted UI
  → approval binds parameter hash and state version
  → idempotent execution + audit + rate limit
```

If state changes at any step, the old approval expires. The model must not generate, alter, or “interpret” an approval token.

## Common mistakes and investigation prompts

- **A JSON Schema makes it safe**: check for object-level authorization, destinations, and business rules as well.
- **A shared service account is convenient during development**: check whether the final-user subject is recoverable and whether tenancy crosses boundaries.
- **The tool description says “internal only”**: a description is a prompt, not executor policy.
- **Retry automatically on failure**: check whether the write is idempotent and whether retries can duplicate a payment or email.
- **More logs are always safer**: logs can become a new secret store, so redact them, limit access, and set retention periods.

## Exercise and self-check

Review a drafting assistant with `read_inbox`, `send_email`, `fetch_url`, and `run_shell`:

1. Remove tools not needed for its purpose.
2. Define strict arguments and object authorization for the retained tools.
3. Find at least three exfiltration channels.
4. Design approval, idempotency, rate limits, and audit fields for sending.
5. Write negative tests for cross-tenant access, parameter substitution, unknown destinations, and duplicate submission.

- [ ] Can explain the difference between a tool schema and authorization.
- [ ] Can identify confused deputies and covert exfiltration channels.
- [ ] Can prevent the model from expanding its own permissions or generating approval.
- [ ] Can make high-impact tools fail safely and leave the minimum sufficient evidence.
- [ ] Can distinguish a model-visible tool result from protected audit and handle an unknown execution result with an explicit state query.

## Next step

Continue with [[ai-safety/02-controls-and-governance/04-identity-least-privilege-and-supply-chain|Identity, Least Privilege, and the Supply Chain]].

## References

- [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) (accessed 2026-07-21)
- [OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) (accessed 2026-07-21)
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) (published December 2025; accessed 2026-07-21)
