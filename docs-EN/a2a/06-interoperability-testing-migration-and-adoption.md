---
title: "Interoperability Testing, Migration, and Adoption Decisions"
aliases:
  - A2A interoperability testing
  - A2A migration and adoption
tags:
  - a2a
  - interoperability-testing
  - migration
  - technology-radar
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0, the v1.0 migration guide, and the official roadmap
lang: en
translation_key: A2A/06-互操作测试迁移与采用决策.md
translation_source_hash: 328f85e12214267b8527d24b3eee83dd1fe07a54453d7673787390bc140e0e87
translation_route: zh-CN/A2A/06-互操作测试迁移与采用决策
translation_default_route: zh-CN/A2A/06-互操作测试迁移与采用决策
---

# Interoperability Testing, Migration, and Adoption Decisions

## Goals of this lesson

- Upgrade “the SDK starts” into evidence of cross-implementation interoperability.
- Identify the important breaking changes from A2A \`0.3\` to \`1.0\`.
- Manage frontier technologies through entry, observation, and exit conditions.

## Interoperability is not one party's unit test

At least four layers of evidence are needed:

1. **Structural contracts**: required fields, one-of constraints, enums, timestamps, and error formats.
2. **Behavioral contracts**: Task states, cancellation, subscription, retries, and Artifact aggregation.
3. **Cross-implementation matrix**: combinations of languages/SDKs, clients/servers, bindings, and versions.
4. **Production boundaries**: identity, tenants, gateways, rate limiting, logging, faults, and rollback.

An official TCK or SDK test can strengthen the first two layers, but cannot replace your business authorization, data policy, or production SLOs.

## A minimal test matrix

| Dimension | Positive case | Required negative cases |
| --- | --- | --- |
| Agent Card | Select a compatible preferred interface | Missing fields, wrong version, unknown required extension, signature failure |
| Message/Part | One each of text, data, and file URL | Multiple content fields, legacy \`kind\`, oversized payload, malicious URL |
| Task | Completion, failure, cancellation, input/authorization recovery | Terminal-state rollback, cross-Task/Context access, duplicate side effects |
| Streaming | Status and incremental Artifact updates | Disconnect, duplicate, reordering, missing \`lastChunk\` |
| Webhook | Authenticated callback and idempotent receipt | Replay, forged origin, SSRF, exhausted failed-delivery retries |
| Multitenancy | Read and subscribe within the same tenant | Cross-tenant list/get/cancel/subscribe |
| Multiple bindings | Semantically equivalent results | Inconsistent capability, error, or authentication |

## Moving from \`0.3\` to \`1.0\` is not a version-string edit

The A2A official migration notes list these high-impact changes:

- Enum values become \`TASK_STATE_*\` and \`ROLE_*\` in \`SCREAMING_SNAKE_CASE\`.
- Part removes \`kind\` and nested file structures, becoming a one-of among \`text\`, \`raw\`, \`url\`, and \`data\` members.
- \`protocolVersion\`, URLs, and bindings converge into \`supportedInterfaces[]\`.
- Streaming events remove the old discriminator and are distinguished by member presence.
- Operation names, error representations, pagination, and HTTP paths change.
- Production capabilities such as multitenancy, Agent Card signatures, and explicit version parameters are added.

Migration should use a compatibility window:

\`\`\`mermaid
flowchart LR
    A["Inventory 0.3 clients and servers"] --> B["Build dual-version contract tests"]
    B --> C["Declare compatible interfaces together in the Agent Card"]
    C --> D["Run shadow traffic and negative security tests"]
    D --> E["Switch callers to 1.0 in batches"]
    E --> F["Observe error, state, and Artifact differences"]
    F --> G["Stop accepting new 0.3 integrations"]
    G --> H["Remove the compatibility layer after exit gates are met"]
\`\`\`

The rollback unit must include the protocol adapter, Agent Card, gateway configuration, business schema, and observability queries. Rolling back only an SDK package can leave a mismatched Card or route behind.

## Adoption states for frontier topics

This project uses four states rather than “popular” or “unpopular”:

| State | Entry condition | Allowed action |
| --- | --- | --- |
| observe | Primary sources exist, but the specification or ecosystem is still changing quickly | Record facts and run offline experiments; do not enter a critical path |
| trial | There is a versioned contract and a reversible experiment | Controlled traffic, noncritical business, and explicit exit conditions |
| adopt | Value, interoperability, security, and operations evidence all meet requirements | Enter the support matrix and production governance |
| hold/retire | Value is insufficient, compatibility fails, or risk exceeds limits | Stop new integrations; migrate and archive the evidence |

The release state of A2A \`1.0\` does not automatically mean your organization should \`adopt\` it. Whether an organization adopts it still depends on cross-boundary needs, partner support, the identity model, TCK/contract results, and total cost of ownership.

## Adoption decision record

At minimum, write down:

- The existing problem and why an ordinary API, MCP, or framework-internal orchestration is insufficient.
- The pinned protocol, SDK, binding, and business-schema versions.
- Callers, service providers, identity providers, and data owners.
- Results of positive, negative, interoperability, and fault-injection tests.
- The acceptable version window and deprecation-notice period.
- Rollback triggers, the compatibility-layer owner, and the exit date.
- Unvalidated vendors, extensions, transports, and regulatory environments.

## Self-check

1. Why cannot an official SDK's unit tests prove that two vendor implementations interoperate?
2. Which structural changes would be missed by only changing the version on a \`0.3\` Card to \`1.0\`?
3. What evidence would move a topic from \`trial\` to \`adopt\`?

## References

- [A2A v1.0 change notes](https://a2a-protocol.org/latest/whats-new-v1/)
- [A2A 1.0 Interoperability Testing](https://a2a-protocol.org/latest/specification/#128-interoperability-testing)
- [A2A official roadmap](https://a2a-protocol.org/latest/roadmap/)
- [A2A GitHub Releases](https://github.com/a2aproject/A2A/releases)
