---
title: "Transports, Streaming, Asynchrony, and Version Negotiation"
aliases:
  - A2A transport and versioning
  - A2A streaming and asynchronous operations
tags:
  - a2a
  - transport
  - streaming
  - versioning
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 binding and streaming sections
lang: en
translation_key: A2A/04-传输流式异步与版本协商.md
translation_source_hash: 104d89b23ca91a7427da50fa08b2c8c5669263fc37a32487218d615e4d098047
translation_route: zh-CN/A2A/04-传输流式异步与版本协商
translation_default_route: zh-CN/A2A/04-传输流式异步与版本协商
---

# Transports, Streaming, Asynchrony, and Version Negotiation

## Goals of this lesson

- Understand the layering of A2A 1.0 abstract operations and bindings.
- Choose a delivery mechanism for synchronous work, long-running Tasks, and disconnects.
- Let protocol versions, bindings, and business versions evolve independently.

## Unify semantics before choosing a binding

A2A 1.0 establishes a common semantic layer through its specified data model and abstract operations, then maps it to three standard bindings:

- \`JSONRPC\`;
- \`GRPC\`; and
- \`HTTP+JSON\`.

When one Agent exposes multiple bindings, the specification requires them to provide the same operation capabilities, semantically equivalent results, mappable errors, and equivalent authentication. You cannot make the HTTP interface complete and the gRPC interface incomplete while still claiming that they are interchangeable.

An Agent Card's \`supportedInterfaces\` are ordered by preference. A client chooses the first entry it supports, but it must still check the URL, binding, protocol version, tenant fields, and local security policy.

## Three ways to obtain results

| Method | Suitable scenario | Main risks | Minimum recovery evidence |
| --- | --- | --- | --- |
| Poll \`GetTask\` | Low frequency; the client cannot keep a connection | Polling storms, latency, duplicate reads | \`ETag\`/throttling policy, most recent state, and terminal state |
| Streaming send/subscription | Low-latency progress or incremental Artifacts are needed | Disconnects, duplicates, missed events, backpressure | Task ID, processed event/Artifact cursor, and reconnect policy |
| Push notification | Long-running Tasks while the client is temporarily offline | SSRF, forged callbacks, replay, delivery failure | Callback identity, idempotency key, permitted targets, retries, and dead-letter records |

A streaming connection is not a durable queue. The official specification explicitly warns that, after a client disconnects and reconnects, it might not receive all previous status messages. Critical facts must remain readable through the Task and Artifacts.

## A version is not one number

Manage at least four versions simultaneously:

1. The A2A protocol version, such as the interface-declared \`1.0\`.
2. The binding/SDK version, which governs a concrete implementation and serialization behavior.
3. The Agent product version: the top-level Agent Card \`version\`.
4. The business-contract version: input data, Artifact schema, skill semantics, and quality gates.

For HTTP-style requests, an A2A 1.0 client should send the \`A2A-Version\` service parameter and call only versions declared as supported by the Agent Card. Do not automatically fall back and continue a high-risk action: a fallback can silently lose signatures, tenant information, or extension capabilities.

\`\`\`mermaid
flowchart TD
    A["Read supportedInterfaces"] --> B["Filter to bindings supported by the client"]
    B --> C["Filter to permitted protocol major/minor versions"]
    C --> D["Check tenant, security scheme, and extensions"]
    D --> E{"Is a compatible interface available?"}
    E -->|"No"| F["Fail closed and record evidence"]
    E -->|"Yes"| G["Pin the interface and send version parameter"]
    G --> H["Run handshake/negative contract tests"]
\`\`\`

## Consuming streaming events correctly

Task-status updates and Artifact updates are distinct events. A client should:

- Correlate events by Task/Context rather than guessing ownership from the connection on which they arrive.
- Validate that each stream response carries exactly one legal variant.
- Aggregate incremental Artifacts by \`artifactId\`, \`append\`, and \`lastChunk\`.
- Close or stop consuming after a terminal state while allowing idempotent duplicate terminal states.
- Limit the size of one event, one Artifact, and the complete Task.
- Apply content validation and policies for malicious URLs and sensitive information to every Part.

## Webhooks need two-way security

When the Remote Agent calls a webhook, restrict destination addresses and block internal, loopback, cloud-metadata addresses, and redirect bypasses. When the client receives a webhook, validate the caller identity, Task ownership, time window, and replay. Do not register an arbitrary user-supplied URL unchanged as a notification destination.

At minimum, record:

- Who created the notification configuration.
- The permitted destination domains, resolved IPs, and redirect policy.
- The authentication scheme, key rotation, and expiry mechanism used.
- Retry limit, backoff, timeout, dead letter, and alerting.
- The result of idempotent handling for duplicate deliveries.

## Extensions and custom bindings

Extensions are identified by URI. If a required extension is not supported by the client, the operation should fail rather than silently ignore it or automatically downgrade to an older version. A custom binding must likewise preserve core operations, data semantics, error mapping, authentication, and interoperability tests; “using WebSocket” alone is not a valid binding specification.

## Self-check

1. Can several bindings all returning \`200\` prove semantic equivalence?
2. Why is \`GetTask\` or Artifact retrieval still necessary after a stream reconnects?
3. Why can a protocol fallback be a security change rather than merely a compatibility change?

## References

- [A2A Protocol Binding Requirements](https://a2a-protocol.org/latest/specification/#5-protocol-binding-requirements-and-interoperability)
- [A2A Streaming and Asynchronous Operations](https://a2a-protocol.org/latest/topics/streaming-and-async/)
- [A2A Custom Protocol Bindings](https://a2a-protocol.org/latest/topics/custom-protocol-bindings/)
