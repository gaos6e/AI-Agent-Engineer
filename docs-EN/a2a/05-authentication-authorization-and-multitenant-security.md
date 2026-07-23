---
title: "Authentication, Authorization, and Multitenant Security"
aliases:
  - A2A security
  - A2A multitenancy
tags:
  - a2a
  - authentication
  - authorization
  - multi-tenancy
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 security considerations
lang: en
translation_key: A2A/05-认证授权与多租户安全.md
translation_source_hash: b5b3503628984eddf255dfab088985bde3921bf0bcb540f3638a1b4adc55965f
translation_route: zh-CN/A2A/05-认证授权与多租户安全
translation_default_route: zh-CN/A2A/05-认证授权与多租户安全
---

# Authentication, Authorization, and Multitenant Security

## Goals of this lesson

- Separate discovery, authentication, authorization, approval, and credential acquisition into independent steps.
- Apply object-level and tenant-level scope limits to every Task and operation.
- Defend against credential leakage, SSRF, injection, and untrusted Artifacts across Agent chains.

## A2A reuses enterprise identity systems

A2A does not create its own Identity Provider. An Agent Card may declare security schemes such as API keys, HTTP auth, OAuth 2.0, OpenID Connect, and mTLS; the client obtains credentials through an out-of-protocol flow and then carries them with requests according to binding rules.

That creates five distinct questions:

| Question | Responsible boundary |
| --- | --- |
| Who is this? | Authentication and server-side identity verification |
| Which Agent or skill may it access? | Service-level and skill-level authorization |
| Which Task or Artifact may it access? | Object-level authorization |
| Which user or organization may it represent? | Delegation, tenant, and scope |
| Has this dangerous action been approved? | Transaction-level approval and policy enforcement |

Successful authentication answers only the first question; it does not automatically answer the rest.

## Authorize every operation before querying

The specification requires the server to restrict Task lists, reads, cancellations, subscriptions, and notification configuration to the caller's authorized scope. In particular, do not query global objects first and filter only when forming the response; existence, count, timing, and error differences can all leak information about another tenant.

At minimum, the server binds the following values together:

- The authenticated principal and delegated user.
- Agent or skill.
- Task and Context.
- Tenant, workspace, or project.
- Data classification and permitted purpose.
- Permitted operations, time window, and risk limit.

> [!danger] \`tenant\` is not proof of authorization
> In A2A 1.0, \`tenant\` is an opaque routing value. The client carries it for the selected interface, and the server interprets it; an attacker can alter the request field as well. The server must bind it again to the authenticated principal and its own tenant model.

## The credential boundary of \`AUTH_REQUIRED\`

An Agent may use \`TASK_STATE_AUTH_REQUIRED\` to express that additional authorization is needed during execution. The specification recommends supplying credentials directly through a secure out-of-band channel to the Agent that originally requested them. If credentials are forwarded in Messages along an Agent chain, every intermediary Agent may see and misuse them.

A secure design should prioritize:

- An audience bound to the original Agent.
- A scope limited to the current action and object.
- A short lifetime, single use, or immediate revocability.
- No writing to Task history, ordinary traces, or Artifacts.
- Revalidation of user intent and parameters before resuming execution.
- Revocation of unused credentials after failure, timeout, or cancellation.

## Content from another Agent is still untrusted input

A Remote Agent's Messages and Artifacts may contain:

- Prompt injection or forged system instructions.
- Malicious files, oversized payloads, or parser bombs.
- URLs pointing to internal, loopback, or cloud-metadata services.
- Fabricated citations, unauthorized data, and sensitive information.
- Text intended to induce the upstream Agent to initiate payment, deletion, or permission changes.

The receiver must treat all of these as external input and validate schema, size, media type, origin, malicious content, data classification, and action policy. A2A defines an exchange structure; it does not vouch for an Artifact's authenticity.

## Minimal multitenant threat model

\`\`\`mermaid
flowchart LR
    A["Tenant A client"] --> G["A2A gateway"]
    B["Tenant B client"] --> G
    G --> P["Authentication and authorization policy"]
    P --> R["Agent router"]
    R --> TA["Tenant A Tasks"]
    R --> TB["Tenant B Tasks"]
    G -. "Cross-tenant enumeration prohibited" .-> X["Task/List/Subscribe/Cancel"]
\`\`\`

Negative tests must cover at least:

- Reading, listing, cancelling, or subscribing to Tenant B Tasks with Tenant A credentials.
- Altering \`tenant\`, Task ID, Context ID, or webhook configuration ID.
- Inferring another object's existence from error codes, pagination tokens, or latency differences.
- A public Agent Card leaking private skills or internal URLs.
- DNS rebinding, redirects, and private-network resolution for webhook URLs.
- Replacing action parameters or the approval object while resuming \`AUTH_REQUIRED\`.

## Production checklist

- [ ] Every production binding uses TLS and verifies server identity.
- [ ] Agent Card security declarations match actual gateway policy.
- [ ] Every operation performs object-level authorization before data access.
- [ ] \`tenant\` is used for routing, not as the sole basis for permission.
- [ ] Credentials never enter Messages, Artifacts, ordinary logs, or model context.
- [ ] Webhooks have permitted targets, identity verification, replay protection, and idempotent handling.
- [ ] Part URLs, files, structured data, and text are validated separately.
- [ ] High-risk side effects go through model-external policy and approval bound to parameters.
- [ ] Events and audit records support revocation, investigation, and tenant-isolation verification.

## Self-check

1. Why can cross-tenant authorization failure still occur after a JWT has been verified?
2. Why should a user not paste a token directly into a Message during \`AUTH_REQUIRED\`?
3. After receiving a signed Agent Card, may an Artifact skip content validation?

## References

- [A2A Authentication and Authorization](https://a2a-protocol.org/latest/specification/#7-authentication-and-authorization)
- [A2A Security Considerations](https://a2a-protocol.org/latest/specification/#13-security-considerations)
- [A2A Multi-Tenancy](https://a2a-protocol.org/latest/topics/multi-tenancy/)
- [[ai-safety/00-index|AI Safety]]
