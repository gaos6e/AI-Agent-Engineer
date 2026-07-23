---
title: "Agent Cards, Discovery, and Trust"
aliases:
  - A2A Agent Card
  - Agent discovery and trust
tags:
  - a2a
  - discovery
  - trust
  - security
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 AgentCard and discovery sections
lang: en
translation_key: A2A/02-Agent Card发现与信任.md
translation_source_hash: 88a7dedfa0e7c26f8faa21a610bca2aecf1fa456a4cdc5678553999d30afc00b
translation_route: zh-CN/A2A/02-Agent-Card发现与信任
translation_default_route: zh-CN/A2A/02-Agent-Card发现与信任
---

# Agent Cards, Discovery, and Trust

## Goals of this lesson

- Read the required fields of an A2A 1.0 Agent Card.
- Distinguish capability discovery, identity authenticity, and actual authorization.
- Design a public Card, extended Card, cache, and rotation policy.

## An Agent Card is a machine-readable service declaration

An A2A 1.0 Agent Card describes at least:

- \`name\`, \`description\`, and the Agent's own \`version\`;
- preference-ordered \`supportedInterfaces\`;
- \`capabilities\`;
- default input and output media types;
- one or more \`skills\`; and
- providers, security schemes and requirements, signatures, and documentation URLs when applicable.

Every \`supportedInterfaces\` entry supplies \`url\`, \`protocolBinding\`, and \`protocolVersion\`. \`protocolVersion\` belongs to an interface, not to the top level of the Agent Card; this is an important structural difference between A2A \`1.0\` and \`0.3\`.

\`\`\`jsonc
{ // An Agent Card used during discovery; declaring a capability does not verify identity, authorization, or trust.
  "name": "Research Brief Agent", // A human-facing Agent name; it cannot serve as the sole identity credential.
  "description": "Produces source-bounded research briefs.", // Briefly states the task scope; actual behavior still needs evaluation and contract validation.
  "version": "2.3.1", // Card/Agent version; re-evaluate compatibility and trust after an upgrade.
  "supportedInterfaces": [ // Interfaces through which the Agent can be called; the client must select and validate each one.
    { // One HTTP+JSON interface declaration.
      "url": "https://agents.example.com/research/a2a", // Target endpoint; in production, validate its certificate, domain, and allowlist.
      "protocolBinding": "HTTP+JSON", // Transport binding, which determines request/response encoding.
      "protocolVersion": "1.0" // Protocol version supported by this interface; compatibility must still be negotiated before a call.
    } // End interface declaration.
  ], // End supportedInterfaces array.
  "capabilities": { // Capability flags the Agent claims to support; they do not replace runtime permission checks.
    "streaming": true, // The client can prepare to receive streamed Task/Artifact updates.
    "pushNotifications": false // The Agent will not proactively push notifications to the client; the client must poll or subscribe through another mechanism.
  }, // End capability object.
  "defaultInputModes": ["text/plain", "application/json"], // Default accepted input MIME types; validate every payload separately.
  "defaultOutputModes": ["application/json"], // Default output MIME types; the client must not blindly execute their contents.
  "skills": [ // Finer-grained, discoverable task capabilities.
    { // A selectable research skill.
      "id": "research-brief", // Stable skill ID for request, evaluation, and audit correlation.
      "name": "Research brief", // Human-facing capability name.
      "description": "Builds a cited brief from an approved source set.", // Explicitly limits work to approved sources, avoiding a promise of unbounded open-ended retrieval.
      "tags": ["research", "citations"] // Tags for search/routing assistance; they cannot determine authorization on their own.
    } // End skill object.
  ] // End skills array.
}
\`\`\`

> [!note] JSONC teaching representation
> This Card includes explanatory end-of-line comments. Remove the \`//\` comments before publishing or validating strict JSON.

This example is a teaching-oriented minimal structure; it does not mean that a production service may be exposed without authentication.

## Three discovery methods

The official specification lists three types of entry point:

1. \`https://{server}/.well-known/agent-card.json\`;
2. An organization-maintained registry or catalog.
3. An Agent Card URL or Card content configured directly by the client.

They correspond to different control planes. A well-known URI supports open discovery; a registry can add review, ownership, and lifecycle controls; direct configuration suits fixed partners. Production systems normally also need an owner, environment, data classification, support window, and decommissioning status. Do not infer these from free-text \`description\` fields.

## Discovery is not trust

\`\`\`mermaid
flowchart TD
    A["Discover Agent Card"] --> B["Validate URL, schema, and protocol version"]
    B --> C["Validate TLS and origin domain"]
    C --> D{"Is a signature present?"}
    D -->|"Yes"| E["Canonicalize with RFC 8785 and verify JWS"]
    D -->|"No"| F["Apply the local unsigned-Card policy"]
    E --> G["Validate key trust, validity period, and revocation"]
    F --> H["Restrict to low risk or reject"]
    G --> I["Then apply business authorization and output validation"]
    H --> I
\`\`\`

A signature only proves that a party holding a key signed the Card. You must also determine:

- Whether the key source indicated by \`kid\` or \`jku\` is trustworthy.
- Whether the key is expired, revoked, or incorrectly reused.
- Whether the normalized signed content matches the content received.
- Whether the domain, organizational identity, and contractual party match.
- Whether skill declarations pass independent tests rather than self-promotion alone.

## Public Cards and authenticated extended Cards

When \`capabilities.extendedAgentCard\` is true, a client may request a more detailed Agent Card after authenticating. Reasonable uses include exposing restricted skills, dedicated interfaces, or more specific policy information only to partners.

Key boundaries:

- A public Card must not contain credentials, internal topology, or unnecessary sensitive skill details.
- An extended-Card request must authenticate with the security scheme declared by the public Card.
- Returned content must still be filtered by the caller's permissions; “signed in” is not blanket authorization.
- Cache entries must bind identity, Card version, and expiry; clear extended-Card caches after logout or a permission change.

## Caching and change

An Agent Card is a runtime dependency and cannot be cached forever. Record at least:

- The fetch URL, time, content digest, and Agent \`version\`.
- The A2A \`protocolVersion\` of every interface.
- Signature-verification outcome and the trust anchor used.
- Which binding was selected and why other entries were not selected.
- Compatibility tests and approval triggered by a Card change.

Do not merge an Agent's product version and the A2A protocol version into one field, and do not decide compatibility only by comparing version strings.

## Common mistakes

- Automatically call every skill after reading a Card.
- Treat \`skills.tags\` as an authorization scope.
- Embed an API key or internal address in the Card.
- Verify the mathematics of a JWS signature without verifying key ownership.
- Still parse the \`0.3\` top-level \`url\`, \`preferredTransport\`, and \`protocolVersion\`.
- Take only the first of several interfaces without checking whether the client supports its binding and version.

## Self-check

1. Why can HTTPS, JWS, and object-level authorization not replace one another?
2. What does \`version: 2.3.1\` version, and what does \`protocolVersion: 1.0\` version?
3. What information belongs in a public Card, and what should go in an authenticated extended Card?

## References

- [A2A 1.0 AgentCard definition](https://a2a-protocol.org/latest/specification/#441-agentcard)
- [A2A Agent Discovery](https://a2a-protocol.org/latest/specification/#8-agent-discovery-the-agent-card)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
- [RFC 7515: JSON Web Signature](https://www.rfc-editor.org/rfc/rfc7515)
