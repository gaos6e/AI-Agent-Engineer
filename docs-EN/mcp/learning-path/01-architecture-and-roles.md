---
title: "MCP Architecture and Roles"
aliases:
  - MCP host client server
  - MCP bidirectional architecture
tags:
  - MCP
  - architecture
source_checked: 2026-07-19
lang: en
translation_key: "MCP/学习路线/01-架构与角色.md"
translation_source_hash: 36e92b068c14bc60dfccad4b94dbe947e96b70bd817fa89caf557cd3faa7a882
translation_route: zh-CN/MCP/学习路线/01-架构与角色
translation_default_route: zh-CN/MCP/学习路线/01-架构与角色
---

# MCP Architecture and Roles

## Learning objectives

After this lesson, you should be able to:

- Draw the relationship among a host, client, and server, and explain why a host normally creates one client for each server.
- Separate the data layer from the transport layer, rather than treating “HTTP is connected” as proof that the protocol is compatible.
- Explain why MCP is bidirectional: a server offers capabilities to a client, and can also ask the client for roots, sampling, and elicitation.
- Draw responsibility and trust boundaries among the model, user interface, protocol adapter, and business systems.

## Start with a real integration problem

Suppose a desktop AI application needs to access a local project, an internal knowledge base, and an issue-tracking system. Without a shared protocol, the application must separately implement discovery, parameter descriptions, invocation, results, errors, and authorization for every system. MCP standardizes the messages and capability negotiation at that integration boundary. It does not specify how an Agent plans, and it does not make authorization decisions for a business system.

One sentence is worth remembering:

> MCP is a stateful JSON-RPC protocol between a host-managed client and server. It is not “an Agent that can think for itself.”

## The three roles

| Role | Intuition | Main responsibility | Should not be assumed to do |
| --- | --- | --- | --- |
| host | The AI application the user actually uses | Manages user experience, the model, consent, permission policy, and multiple connections | Send all context to every server without conditions |
| client | One MCP protocol connection inside the host | Initializes, negotiates capabilities, sends and receives messages, and maintains request and session state | Decide the server's business permissions or grant user consent for high-risk actions |
| server | A program that exposes a set of domain capabilities | Offers tools/resources/prompts, handles approved requests, and may request client features | Control which model the host uses or treat model intent as authorization |

The official architecture treats one client–server relationship as one stateful session. A host can manage multiple clients at once:

```text
host (IDE / desktop AI application)
├─ client A ── server A (local project)
├─ client B ── server B (issue-tracking system)
└─ client C ── server C (enterprise knowledge base)
```

The value is not merely a tidy diagram; it is isolation:

- Each connection has its own protocol version, capabilities, request IDs, and lifecycle state.
- The host can apply different data-disclosure policies, tool confirmations, and credentials to different servers.
- A failed or deauthorized server does not have to break every other connection.

## A two-layer architecture

### Data layer

The data layer answers, “What do the two sides exchange, and in what order?” It includes:

- JSON-RPC requests, responses, and notifications;
- `initialize`, capability negotiation, and the session lifecycle;
- server features, client features, and shared utilities;
- schemas, errors, progress, cancellation, and experimental Tasks.

### Transport layer

The transport layer answers, “How do message bytes reach the other side?” The current specification defines two standard transports:

- `stdio`: the client starts a local server subprocess and exchanges newline-delimited UTF-8 JSON-RPC through stdin/stdout.
- Streamable HTTP: a remote or standalone server handles POST and GET on an MCP endpoint, optionally carrying streamed messages through SSE.

The evidence for failures differs by layer:

| Symptom | First belongs to | Does not prove |
| --- | --- | --- |
| Subprocess not found, port unreachable, HTTP 401 | Process/transport/authorization | The tool schema must be wrong |
| `method not found`, undeclared capability | Protocol/negotiation | The network must be down |
| A tool argument is missing | Tool contract | `initialize` must have failed |
| A downstream issue system rejects a write | Business/authorization | The MCP message must be invalid |

## MCP is a bidirectional protocol

Remembering only tools/resources/prompts gives an incomplete model. The main capability directions in the current specification are:

| Capability owner | Capability | Who initiates the related request | Purpose |
| --- | --- | --- | --- |
| server | tools | client → server | Invoke computation or an external action |
| server | resources | client → server | List, read, or subscribe to context |
| server | prompts | client → server | Obtain reusable prompt templates |
| client | roots | server → client | Ask which root scope the host wants the server to focus on; this is not an authorization or sandbox boundary |
| client | sampling | server → client | Ask the host to generate with its model; the host retains model and permission control |
| client | elicitation | server → client | Ask the user for more information or an external interaction through the host |

There are also logging, completion, ping, progress, cancellation, and Tasks, which were introduced in `2025-11-25` and remain experimental. A capability declares what protocol functionality is available in this session; it is not permanent authorization for any data or action.

## Who controls what

Separate “a protocol request may be initiated” from “who has final control”:

- A model may suggest a tool call, but the host should make exposed tools visible to the user and require confirmation for high-risk actions.
- A server may request sampling, but the host decides the model, scope of access, presentation, and whether to approve the request.
- A server may request elicitation, but the client must show the requester and let the user accept, decline, or cancel.
- A client may provide roots, but a root is only a suggested coordination scope. Operating-system permissions, sandboxes, and host policy enforce actual file-access restrictions; the server must still defend against path traversal and unauthorized access.
- Tool annotations, resource contents, and server instructions are all inputs. When a server is untrusted, a description that claims “read-only” is not evidence.

## Running example: a document-review assistant

Requirement: in an IDE, the user selects a project; the AI reads Markdown, summarizes risks, and creates an issue after confirmation.

1. The host owns the conversation, model, and user confirmation.
2. A project server exposes resources; the client exposes only the root selected by the user.
3. An issue server exposes a `create_issue` tool and uses a least-privilege account.
4. If the project server needs a model summary, it can send a sampling request, but the host still reviews the input and model call.
5. If an issue label is missing, form elicitation can request ordinary structured information; it must not be used to ask for an API key.
6. Each server connection has separate authorization, recording, and revocation.

This example also shows the boundary clearly: MCP owns the composition boundary. An Agent's planning loop, business authorization, and downstream idempotency still need separate design.

## Common misconceptions

- **“One server is one Agent.”** A server may be a very thin adapter with no planning, memory, or model.
- **“The client is the desktop application.”** In protocol terminology, a client is normally one connection component inside the host.
- **“A server can only be called.”** A server can also request roots, sampling, and elicitation from the client.
- **“Declaring a capability means it is authorized.”** A capability only says that a protocol feature can be negotiated. Real resources and actions still need identity, scope, business authorization, and consent.
- **“MCP automatically eliminates prompt injection.”** Untrusted protocol content can still enter the model context.

## Hands-on exercise

For an “IDE connected to a code repository, database, and messaging system,” complete an architecture table:

1. Draw one host, three clients, and three servers.
2. For each connection, write the server capabilities and client capabilities.
3. Mark who stores credentials, where the user confirms actions, and which data must not cross connections.
4. For one failed connection, write separate transport, protocol, and business evidence.

## Self-check

1. Why does a host normally establish an independent client for each server?
2. Why is `sampling/createMessage` server → client while `tools/call` is normally client → server?
3. Is HTTP 200 enough to prove that MCP initialization succeeded? Why or why not?
4. When a server says that a tool is `readOnly`, what must the host still verify?

You have mastered this lesson only when you can explain the four ideas—roles, two layers, six bidirectional capability types, and control authority—without consulting the tables.

## Next step

Continue to [[mcp/learning-path/02-primitives-and-tool-contracts|Primitives and Tool Contracts]] to learn what each capability solves and how to choose among them.

## References

The following are first-party MCP materials. Specification links were retrieved or checked on 2026-07-14; the non-security boundary of Roots was checked on 2026-07-19.

- [MCP Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Lifecycle and capability negotiation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP Client concepts](https://modelcontextprotocol.io/docs/learn/client-concepts)
