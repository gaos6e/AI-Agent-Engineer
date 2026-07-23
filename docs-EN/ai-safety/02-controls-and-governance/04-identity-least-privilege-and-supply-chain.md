---
title: "Identity, Least Privilege, and the Supply Chain"
aliases:
  - Identity, Least Privilege, and Supply Chain
  - Agent Identity and Supply Chain Security
tags:
  - ai-security
  - identity
  - supply-chain
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: AI安全/02-控制与治理/04-身份最小权限与供应链.md
translation_source_hash: c2fe92d8b6982f29e56d8b8a20f5ae253b9c808a5cb2485db5c93a307d32e5a7
translation_route: zh-CN/AI安全/02-控制与治理/04-身份最小权限与供应链
translation_default_route: zh-CN/AI安全/02-控制与治理/04-身份最小权限与供应链
---

# Identity, Least Privilege, and the Supply Chain

## Learning objective

Define identity boundaries for users, Agents, tools, and administrators; derive the minimum scopes from intended use; manage short-lived credentials; and establish a chain of provenance, version, verification, and rollback for models, data, prompts, Skills, MCP servers, dependencies, and deployment artifacts.

## Identity is the root of capability

The model can propose an action, but the identity used to execute it supplies the actual permission. Distinguish at least:

- the end-user identity and tenant;
- the workload identity for one Agent run;
- the tool's service identity;
- development, CI/CD, operations, and emergency administrators; and
- an external vendor or hosted-model identity.

A shared “all-powerful service account” creates two problems: any injection inherits its full capability, and audit can see only the service account rather than prove which user authorized the action. A better pattern carries the trusted login subject to the policy layer and issues a short-lived, narrow-scope workload credential bound to user, tenant, and environment for this task.

## Least privilege is not a one-time setting

### Function, scope, object, time, and environment

Least privilege has at least five dimensions: expose only the tools required for the intended use; issue only the required action scopes; access only the current object or tenant; make credentials short-lived; and keep development, test, and production separate. `mail.read` is narrower than `mail.*`, but it can still be too broad if it reads every mailbox in a company.

### Reauthorize every execution

Model-provided user names, roles, and “already approved” claims are not authentication evidence. A tool executor obtains its subject from a trusted session and checks the action, object, tenant, data classification, approval, and current state. Cached authorization decisions must account for revocation and expiry.

Component-provenance verification and runtime authorization are separate evidence chains. A signature, hash, or trusted publisher helps answer “is this the component we expected?” It cannot answer “may this component now access this object for this user?” Conversely, an OAuth token cannot prove that tool code, a description, or an update was not replaced.

### Secrets do not enter model context

Do not put API keys, tokens, connection strings, or other secrets in prompts, long-term memory, tool errors, example repositories, or complete traces. Use environment injection or a secrets-management service, and provide only placeholder values in `.env.example`. When a secret leaks, recovery means revocation and rotation; deleting it from a file does not invalidate the old credential.

## The AI Agent supply chain is broader than Python packages

| Component | Record | Typical risk |
| --- | --- | --- |
| Python or system dependencies; containers | Name, immutable version, source, hash or signature, license | Malicious update, dependency confusion, installation-script execution |
| Base or fine-tuned model | Supplier, model identifier and version, weight source, terms of use | Behavior drift, custom code, weight poisoning |
| Dataset and RAG knowledge source | Source, date, license, tenant, processing record | Data or context poisoning, privacy contamination, stale facts |
| Prompt, policy, and evaluation set | Version, approval, changer, regression result | Weakened controls, test leakage |
| Tool, MCP, Skill, or plugin | Publisher, version, permissions, tool schema, data destinations | Tool poisoning, description injection, overreach, changed remote behavior |
| Hosted API | Vendor, region, retention policy, version policy, disablement plan | Silent upgrade, data egress, service interruption |

“From an official marketplace” or “the vendor is certified” is one signal. It does not establish the safety of your particular version, configuration, permissions, or data path.

## Executable supply-chain controls

1. **Inventory**: maintain an AI-component inventory in addition to a software bill of materials (SBOM), so one run can be traced to model, prompt, tool, data snapshot, and dependency versions.
2. **Pin**: use lockfiles, immutable image digests, and explicit model and tool versions; avoid `latest` in production.
3. **Verify**: obtain components from trusted sources, verify hashes, signatures, or attestations where the ecosystem supports them, and inspect installation scripts and model custom code in an isolated environment.
4. **Least privilege**: allow a third-party component only the declared data, files, and network access it needs. An MCP server's tool list does not automatically receive all execution authority.
5. **Change gates**: before updating, run security, quality, privacy, and performance regressions; scrutinize changes to tool lists, schemas, destinations, and scopes.
6. **Rollback and disablement**: retain the previous known-good artifact, an emergency tool shutdown, and vendor substitution or degradation paths, then exercise them in practice.
7. **Continuous monitoring**: route vulnerability advisories, maintenance status, version drift, and vendor-term changes to an accountable owner's queue.

NIST SP 800-218A is a Secure Software Development Framework community profile for generative AI and dual-use foundation models, finalized in July 2024. It helps incorporate AI-specific concerns into secure software development, but does not automatically prove that an Agent deployment is safe.

## Special cautions for MCP and tool ecosystems

Remote tool descriptions, results, and updates can all become untrusted input. The client still needs independent tool allowlists, user authorization, destination controls, and data-egress controls. An OAuth access token validated by a resource server for issuer, audience, expiration, and applicable scope is an input to the authorization decision; it does not prove that the model's particular call matches user intent. Do not treat a third-party server's error text as a trusted instruction or forward tokens between servers without boundaries.

### An MCP token boundary is not a tool-authorization boundary

For MCP that uses HTTP authorization, a client's access token is for the MCP server. That server must verify the token's intended audience and resource binding before processing the request. If the server must access a third-party API, it acts as that API's OAuth client and obtains and manages a **separate** downstream token; it must not pass the received MCP client token through unchanged. This prevents token passthrough and confused-deputy behavior while preserving an audit subject at every hop.

Even with a valid token, the executor must still perform business authorization for the current caller; delegated user and tenant; object; purpose; state; and data destination. MCP identity or scope is neither proof that “the model intended this correctly” nor proof of human approval or risk acceptance. Recording “transport-layer token validated” and “object-level action authorized” as two independent pieces of evidence makes it possible to identify which layer failed.

Treat dynamically discovered servers, tools, schemas, descriptions, and authorization scopes as runtime configuration changes. Record source and version or snapshot; compare additions, removals, and permission changes; and expose them to the model only after policy allows them again. Successful discovery does not mean installed, trusted, or authorized to execute.

### From dynamic discovery to a controlled release

An external component approaching a production decision must be preserved as a reviewable snapshot, not as a mutable name. At minimum, a snapshot records the available server identity or publishing channel; transport and protocol version; an inventory and digest of Tool, Resource, and Prompt schemas; declared execution identity and scope or audience where applicable; Roots or data range; and egress destinations. It never records a bearer token or other secret. Added or removed tools, schema, permission, identity, data-range, or destination changes—and inability to verify source again—trigger fresh risk analysis, negative testing, and approval. Do not carry forward trust merely because it was connected last time.

Bind the snapshot, regression results, and approval conditions to a `release_id` and a complete release-gate evidence digest so an incident record can identify what was allowed at the time. A digest can help detect whether a handoff artifact changed; it is not a digital signature, authorization fact, or proof of component provenance. Controlled artifact storage, access control, and named decisions are still required. See [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]] for the handoff boundary covering offline evidence, release gates, canaries, and human triage.

## Common mistakes

- Sharing keys between development and production, or using a non-auditable identity across tenants.
- Pinning only top-level packages while transitive dependencies, container base layers, or model revisions can drift.
- Treating a version number as provenance verification; an attacker can publish a versioned artifact too.
- Running only functional tests on an update rather than checking tool, permission, destination, and data-flow changes.
- Keeping backups without exercising disablement, credential revocation, and rollback.

## Exercise and self-check

Build a component table for a RAG Agent: model, embedding, knowledge source, vector store, prompt, MCP server, Python packages, image, and hosted API. For each, record source, pinning method, accessible resources, update gate, and rollback. Then split a “shared production administrator key” into at least two short-lived, least-privilege identities.

- [ ] Can distinguish authentication, authorization, approval, and risk acceptance.
- [ ] Can calculate boundaries for tools, scopes, objects, time, and environment from intended use.
- [ ] Can trace all critical component versions and provenance from one run.
- [ ] Can revoke access, disable components, and roll back when a vendor, model, or tool is abnormal.

## Next step

Put these boundaries into practice in [[ai-safety/02-controls-and-governance/05-guardrails-sandboxes-and-human-approval|Guardrails, Sandboxes, and Human Approval]].

## References

- [NIST SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final) (final, July 2024; accessed 2026-07-22)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/Projects/ssdf) (accessed 2026-07-22)
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) (published December 2025; accessed 2026-07-22)
- [MCP Authorization specification](https://modelcontextprotocol.io/specification/draft/basic/authorization) and [MCP Security Best Practices: Token Passthrough](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) (accessed 2026-07-22; used for authorization-audience validation and the protocol boundary prohibiting token passthrough)
