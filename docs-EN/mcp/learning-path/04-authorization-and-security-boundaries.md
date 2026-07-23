---
title: "MCP Authorization and Security Boundaries"
aliases:
  - MCP security
  - MCP threat model
tags:
  - MCP
  - security
source_checked: 2026-07-21
lang: en
translation_key: "MCP/学习路线/04-授权与安全边界.md"
translation_source_hash: 908ba38acb0aef5e6f7a95221ac3b8005fb4ebf84eed901a167de5cfc8208356
translation_route: zh-CN/MCP/学习路线/04-授权与安全边界
translation_default_route: zh-CN/MCP/学习路线/04-授权与安全边界
---

# MCP Authorization and Security Boundaries

## Learning objectives

After this lesson, you should be able to:

- List assets, principals, trust boundaries, and attack entry points before connecting to a server.
- Distinguish MCP Authorization, third-party downstream authorization, a session, and user consent.
- Explain the risks of token passthrough, confused deputy, SSRF, DNS rebinding, path traversal, and prompt injection.
- Apply proportionate controls to local stdio, remote Streamable HTTP, roots, sampling, elicitation, and tools.

## Security starts with “who acts for whom, to do what”

Do not start with “does it use OAuth?” For every connection, answer:

1. **Principals:** who are the user, host, client, MCP server, and downstream API?
2. **Assets:** which conversations, files, databases, tokens, write permissions, and model-call budget are valuable?
3. **Boundaries:** where does data cross from one component to another, and which component can see plaintext?
4. **Authorization:** which credential authorizes which audience, scopes, and user?
5. **Consent:** what did the user see, can they decline, and how does revocation take effect?
6. **Recovery:** can writes be idempotent, reversed, or audited?

Capability answers only a protocol-feature question; authentication proves identity; authorization determines permission; and consent lets a user understand and choose. None can replace another.

## A basic threat diagram

```text
user
  │ consent / input
  ▼
host + client ── MCP credential ──► MCP server ── downstream credential ──► third-party API
  │ roots / model / UI               │ tools / resources
  └──────── untrusted content and requests ◄─────┘
```

Focus on two sets of credentials:

- Credentials used by the client to access the MCP server.
- Credentials used by the MCP server to access a third-party API.

They serve different audiences. The first set must not simply be passed through as the second.

## Remote authorization: do not do token passthrough

Official security best practices explicitly prohibit token passthrough. After an MCP server receives a token, it must verify that:

- The token is issued for the current resource server—that its audience/resource is correct.
- Its issuer, signature, expiration, and scope meet expectations.
- The current subject is authorized for the target resource.
- The token is not forwarded unchanged to a downstream service.

In the `2025-11-25` HTTP authorization flow, the client must send the RFC 8707 `resource` for the target MCP server's canonical URI in both the authorization request and token request. Every subsequent HTTP request must carry the bearer token again. A server must not check only that “the token can be decoded” or “a scope name exists”; it must also verify that a trusted authorization server issued the token and that its audience is the current MCP server. Invalid, expired, or wrong-issuer/audience tokens should receive 401; insufficient permission or scope should receive 403; malformed authorization requests should receive 400. stdio does not use this HTTP OAuth wire flow and should instead obtain credentials from a controlled environment.

> [!note] Control plane of the teaching validator
> The [[mcp/learning-path/06-project-offline-mcp-message-validation|offline project]] uses out-of-wire `transport_context` and `authorization_revision` to model an identity snapshot after upstream token verification. They are not MCP message fields and cannot prove correct token signatures, issuers, expiration, introspection, or 401/403 behavior.

The [[mcp/learning-path/08-project-loopback-streamable-http-and-oauth-resource-boundaries|Loopback HTTP project]] goes further by performing real POST/GET/DELETE, 401/403, `WWW-Authenticate`, Protected Resource Metadata document/challenge shape, and session round trips, and by checking audience/resource/scope/tenant/revision/expiration/revocation. Its tokens still come from an explicitly labeled offline policy, and its `http://127.0.0.1` resource does not meet RFC 9728's HTTPS requirement. It therefore still does not prove correct authorization code, PKCE, signature/JWKS, issuer discovery, introspection, or PRM deployment.

Otherwise, a confused-deputy problem appears: an attacker causes a trusted MCP server to use credentials not intended for that downstream audience. Logs also cannot accurately state whom a call represented.

The correct downstream authorization pattern is normally for the MCP server itself to act as a third-party OAuth client, obtain and securely retain a downstream token bound to the user's identity. URL elicitation in `2025-11-25` can guide the user to an HTTPS page controlled by the server for third-party authorization; secrets do not pass through the client or LLM. It **cannot** replace MCP Authorization from client to MCP server.

Do not collapse several adjacent risks into “they are all OAuth problems”:

| Risk | Minimal condition | Can occur without the other risks | Primary controls |
| --- | --- | --- | --- |
| token passthrough | The MCP server passes an access token issued to itself unchanged to a downstream API | Yes; the downstream address can be completely trusted | Obtain a separate credential with the right audience for every resource; validate the MCP token only at the MCP resource server |
| confused deputy | An attacker causes a server that legitimately has authority to exercise it for the wrong subject, tenant, resource, or intent | Yes; the server may use its own legitimate downstream token | Bind subject/tenant/resource/intent to the authorization decision, recheck just before execution, and confirm/audit high-risk actions |
| SSRF | Untrusted input controls the server's outbound destination or redirect chain | Yes; the request may have no token | Scheme/host allowlists, post-resolution IP policy, recheck every hop, outbound-network isolation, and timeout/size budgets |
| prompt injection | Text in a resource, prompt, or tool output attempts to rewrite control flow | Yes; it needs no network request | Keep data and instructions layered, let trusted host/policy decide tool authorization, and never let content authorize itself |

Thus, verifying an audience proves only that a token is addressed to the current MCP resource; it does not prove that a downstream call represents the right user or prevent a URL parameter from accessing cloud metadata. Conversely, an SSRF allowlist cannot turn a token with the wrong audience into a usable credential.

## The secret boundary of elicitation

### Form mode

Form mode is for ordinary structured information: language, date, display name, and options. A server must not use it to request:

- Passwords, API keys, or access tokens.
- Payment credentials or secrets that can authorize a transaction.
- Any credential that must not enter client logs or model context.

The client must show the requesting server, fields, and purpose, and allow review, modification, decline, and cancellation. Both sides should validate the restricted schema.

### URL mode

URL mode is for sensitive input or third-party authorization. The client should:

- Clearly display the target domain/host.
- Obtain consent before navigation.
- Accept only a secure URL policy that defends against `javascript:`, `data:`, untrusted redirects, and look-alike domains.
- Never copy secrets entered into the page back into MCP messages.

A server must not use only a session ID to associate a user. In remote scenarios, it should preferentially bind state to identity obtained through MCP Authorization, such as a subject.

## A local stdio server is also executable supply chain

“Runs only on my machine” does not mean safe. A stdio server normally inherits the current Windows user's permissions and may obtain:

- Environment variables passed by the host.
- Its working directory and readable files within it.
- Network access and credential caches accessible to the user account.
- The ability to execute downstream commands.

Installing a third-party server is equivalent to installing a code dependency:

- Verify source, maintainer, package name, and release channel; watch for typosquatting.
- Pin and review versions; inspect changes and regression-test capabilities before upgrading.
- Use an absolute command/path and limit the working directory and allowed roots.
- Pass only required environment variables; do not give the server the full shell environment or general cloud credentials.
- Isolate with a low-privilege account, container, or sandbox when feasible; do not mistake containerization itself for authorization.

## Roots and the file-system boundary

A root is the client's suggested operating scope for a server, not an automatic file-system sandbox. A secure implementation needs at least:

1. Convert an input URI to a normalized absolute path.
2. Allow only explicit schemes; current Roots use `file://`.
3. After resolving `..`, junctions, and symlinks, check again that the final path remains inside an allowed root.
4. Handle drive letters, case differences, and UNC boundaries in Windows path comparisons.
5. Separate read and write permissions; a visible root does not imply write access.
6. Invalidate old caches, watchers, and authorization decisions when roots change.

Do not return content outside a root in an error message, or send full sensitive paths to the model without need.

## Tools, resources, prompts, and sampling are all untrusted input surfaces

### Tool

- Tool annotations from an untrusted server must be treated as untrusted; `readOnly` and `destructive=false` need verification through policy and code.
- For a high-risk write, show its target, impact, and important parameters, then confirm just before execution.
- Revalidate schema, identity, resource ownership, and business rules on the server.
- Use idempotency keys or check state before retrying so that creation and billing are not duplicated.

### Resource and prompt

- Contents may include prompt injection such as “ignore previous rules.”
- Retain provenance, limit length and MIME, and isolate model use from tool authorization when appropriate.
- Never allow a resource to trigger a tool on another server merely because it came from a connected server.
- A prompt template is untrusted input and cannot be elevated into system-level permission.

### Sampling

- Review the prompt, tools, and context scope proposed by the server.
- The host decides the model and quota; retain human-in-the-loop for high-risk requests.
- `sampling.tools` makes a request more Agent-like and expands its side-effect surface, so restrict every tool individually.
- Do not treat model output as authorization evidence or trusted data.

## Network risks of Streamable HTTP

### DNS rebinding and Origin

If a local HTTP server listens on every network interface and does not validate Origin, a malicious web page may access it through DNS rebinding. The specification requires Origin validation; local deployment should bind only to `127.0.0.1`, while remote connections also need correct authentication.

### Session hijacking

`Mcp-Session-Id` correlates protocol sessions; it is not a bearer credential. A server should bind a session to an authenticated user, use a cryptographically secure random value, apply expiration and concurrency policy, and prevent one user from continuing another user's session.

### SSRF

OAuth metadata, dynamic resource addresses, URL elicitation, or a URL passed as a tool argument can all cause a server to make a request. Controls include:

- Allow explicit schemes and hosts.
- After DNS resolution, block loopback, link-local, private-network, and cloud-metadata addresses.
- Revalidate every redirect.
- Set request-size, timeout, and outbound-network policies.
- Do not automatically hand a URL returned by the server to a browser or downloader.

## Tasks and ownership across requests

Tasks let state outlive an ordinary request/response cycle. An implementation needs to:

- Bind a task to the creator's authorization context rather than only a high-entropy task ID.
- Expose `tasks/list` only when the requestor can be identified; otherwise it can leak other users' task metadata.
- Check ownership for `tasks/get/result/cancel`.
- Clean up at TTL expiry and limit polling, concurrency, and result size.
- Avoid relying on optional status notifications; poll sensibly according to `pollInterval`.
- Attach related metadata to elicitation/sampling in a task while preserving their individual consent boundaries.

## Logging and errors

Logs should record time, server/connection identifier, request ID, method, outcome category, duration, authorization decision, and retry/cancellation. By default, do not record:

- Bearer tokens, cookies, or API keys.
- Full prompts, resource bodies, or sensitive form information.
- Unnecessary local absolute paths or personal data.

Use field-level allowlists and irreversible digests to correlate events. Debug mode is not an exception that permits secret leakage.

## Security review checklist

| Area | Evidence required |
| --- | --- |
| Source | Server package, version, maintainer, and update channel have been checked |
| Identity | How remote user and server identity are established |
| Tokens | How issuer/audience/resource/scope/expiration are validated, with no passthrough |
| Consent | Which tools, parameters, domains, and side effects the user sees |
| Data | Minimum disclosure of roots, resources, and sampling context |
| Network | HTTPS, Origin, bind address, SSRF, and redirect policy |
| Tools | Server-side parameter/business-permission validation; write idempotency and recovery |
| Tasks | Task ownership, TTL, polling, and result access |
| Logs | Correlatable and redacted; secrets do not land on disk |

## Threat-modeling exercise

Scenario: “Read local Markdown, ask a model for a summary, then publish it to a remote issue-tracking system.”

Complete this table rather than writing only “use OAuth”:

| Item | Your answer |
| --- | --- |
| Principals and identity | User, host, file server, issue server, downstream API |
| High-value assets | Local body text, model context, MCP token, downstream token, publishing permission |
| Entry points | File URI, resource content, tool arguments, URL, downstream response |
| Worst misuse | Escape a root, use prompt injection to call a tool across servers, publish to the wrong project, leak a token |
| Prevention | Normalize paths, isolate provenance, allowlist projects, preview and confirm, least scope |
| Detection/recovery | Redacted audit trail, idempotency key, state query, delete/rollback procedure |

## Self-check

1. What questions do capability, authorization, and consent answer respectively?
2. Why may a client's MCP token not be sent directly to a third-party API?
3. Why may form elicitation not ask for an API key, and what boundary does URL mode address?
4. If roots already limit access to the project directory, why must you still handle symlinks/junctions?
5. Why cannot a session ID serve as user identity?
6. How can one malicious instruction in a resource cross into a tool on another server, and where should it be stopped?

You have mastered the lesson when you can provide preventive, detective, and recovery controls for the scenario above.

## Next step

Continue to [[mcp/learning-path/05-inspector-debugging-and-versioning|Inspector, Debugging, and Version Management]] to learn how to collect evidence without leaking secrets.

## References

The following are first-party MCP materials, retrieved or checked on 2026-07-21.

- [Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [Streamable HTTP security requirements](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Elicitation security considerations](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Roots security considerations](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Sampling security considerations](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Tasks security considerations](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
