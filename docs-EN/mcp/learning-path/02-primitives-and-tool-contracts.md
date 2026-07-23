---
title: "MCP Primitives and Tool Contracts"
aliases:
  - MCP tools resources prompts
  - MCP roots sampling elicitation
tags:
  - MCP
  - tool-calling
source_checked: 2026-07-19
lang: en
translation_key: "MCP/学习路线/02-Primitives与工具契约.md"
translation_source_hash: 2b9ed818b6ff07c11de9425a2d2bc87ffcf35d5e2b4ca483afde857efecea8c8
translation_route: zh-CN/MCP/学习路线/02-Primitives与工具契约
translation_default_route: zh-CN/MCP/学习路线/02-Primitives与工具契约
---

# MCP Primitives and Tool Contracts

## Learning objectives

After this lesson, you should be able to:

- Choose a tool, resource, prompt, root, sampling, or elicitation feature for a requirement.
- Write tool input and output contracts that can be validated deterministically.
- Distinguish a protocol error from a tool-execution error.
- Explain why pagination, change notifications, user consent, and experimental Tasks are all part of the contract.

## Start by grouping features by their owner

“Primitive” is often used as a catch-all label. A more useful question for a beginner is: **which side provides this feature, who controls it, and what problem does it solve?**

### Server features

| Feature | Best for | Example | Primary control |
| --- | --- | --- | --- |
| tools | A one-off computation or action that may have side effects | Look up an order, create an issue, run an analysis | The model may suggest it; the host sets confirmation policy; the server executes and validates |
| resources | Addressable, readable context | A file, database schema, log, or knowledge item | The application chooses how to read and inject it |
| prompts | Reusable prompt templates supplied by the server | A weekly-report template or code-review procedure | Usually selected explicitly by the user or application |

### Client features

| Feature | Best for | Example | Primary control |
| --- | --- | --- | --- |
| roots | Declare the root scope that the host wants the server to focus on; not an authorization or sandbox boundary | `file:///D:/project` | The host/user chooses a coordination scope; system permissions enforce actual limits |
| sampling | A server asks the host to generate with its model | Ask the host to choose a model and summarize a result | The host retains the model, permissions, and review |
| elicitation | A server obtains more information through the client | Choose an output language or open an external authorization page | The user can accept, decline, or cancel |

The two groups are not interchangeable. A resource lets the client read content supplied by the server; a root lets the server ask which file scope the client suggests it focus on. Roots do not replace operating-system permissions, sandboxing, path validation, or authorization policy.

## Choosing a server feature

### Tool: an action or computation

Use a tool when a requirement has clear parameters, an execution boundary, and a result. At teaching level, a description should include at least:

- `name`: unique and stable within a session. The current specification recommends 1–128 ASCII letters, digits, `_`, `-`, or `.`.
- `description`: what it does, when to use it, and its important side effects.
- `inputSchema`: a JSON Schema object.
- Optional `outputSchema`: a JSON Schema for structured output.
- Optional `annotations` and `execution.taskSupport`.

```jsonc
{ // A teaching-level tool contract that a server can declare in a response such as tools/list
  "name": "lookup_weather", // Stable tool name; the model may only suggest it, while host and server still decide whether to allow the call
  "description": "Reads sample weather data offline; does not access the network.", // Describe capability and boundary to support selection, not authorization
  "inputSchema": { // JSON Schema for arguments that the caller must provide
    "type": "object", // Top-level arguments must be an object, avoiding positional-argument ambiguity
    "properties": { // Declare the constraint for each allowed field
      "city": {"type": "string", "minLength": 1}, // City must be non-empty text
      "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]} // Unit must be one of two explicit values
    }, // End argument definitions
    "required": ["city"], // Reject a request before execution when city is missing
    "additionalProperties": false // Do not let undeclared arguments silently expand the tool's capability surface
  }, // End input schema
  "outputSchema": { // The server's result also has a verifiable output contract
    "type": "object", // The return value must be an object, not free text
    "properties": { // Declare result fields that the client/host may read
      "temperature": {"type": "number"}, // Temperature may be any numeric value, including a decimal
      "conditions": {"type": "string"}, // Weather description is text
      "unit": {"type": "string"} // Echo the unit so that the caller does not have to guess the quantity's unit
    }, // End output fields
    "required": ["temperature", "conditions", "unit"], // All three fields are required for a complete successful result
    "additionalProperties": false // Output must not smuggle in unreviewed fields or prompt-injection payloads
  } // End output schema
}
```

> [!note] JSONC used for teaching
> The trailing `//` comments explain control boundaries in the schema. Remove them before sending the object to an implementation that accepts only strict JSON.

If an `outputSchema` is defined, the server must make `structuredContent` conform to it, and the client should validate it. To remain compatible with older clients, the specification recommends also providing a serialized result in text content. A schema answers “can this structure be processed?”; a description answers “did the model choose the right tool?” Neither is authorization.

Tool errors have two layers:

| Error | Applies when | Representation | Can the model usually repair it? |
| --- | --- | --- | --- |
| JSON-RPC protocol error | Unknown method, invalid request shape, server internal error | `error` in the response | Less likely |
| Tool-execution error | Argument value out of range, downstream API failure, business-rule rejection | `isError: true` and actionable content in the tool result | More likely |

### Resource: addressable context

When content needs browsing, reading, pagination, caching, subscription, or reuse, a resource is clearer than “a tool that returns a large block of text.” Keep these points in mind:

- A URI is an identity boundary; do not rely on a display name as the unique identifier.
- The stable `2025-11-25` core methods are `resources/list`, `resources/read`, `resources/templates/list`, `resources/subscribe`, and `resources/unsubscribe`. There is no generic `resources/delete`.
- Both list and templates/list can return an opaque `nextCursor`. Do not assume the first page contains everything or parse a cursor's internal form.
- `resources.listChanged` and per-item `resources.subscribe` are independent sub-capabilities. The former says that the visible list may have changed; the latter permits `notifications/resources/updated` only for a successfully subscribed URI.
- Sending a subscribe request does not mean the subscription has taken effect. Wait for a successful response. Likewise, a failed unsubscribe must not remove local state early.
- An updated URI may be a sub-resource of a subscribed resource, but the protocol does not define “matching string prefix means parent/child” as an authorization rule. A production system should use the server's resource model or an explicit relationship.
- Resource contents are untrusted input and may contain prompt injection. Preserve provenance and limit what enters the model.
- A capability says that a protocol feature is available; it does not prove that the current subject is authorized for a URI. Continue to check token, scope, tenant/owner, and revocation state.

### Prompt: a reusable interaction template

A prompt is appropriate when a user chooses a way of working, such as “perform a code review using the team template.” It is not a back door around host system instructions, nor is it a place to store secrets. Template arguments still need validation, and prompt messages returned by the server remain subject to host policy.

## Choosing a client feature

### Root: a work-scope hint, not a sandbox

In the current specification, a root URI must use `file://`. A client can declare `roots.listChanged`, after which a server can send `roots/list`. An implementation must still:

- Normalize a path before deciding whether it falls under an allowed root.
- Handle `..`, case differences, junctions, and symlinks.
- Never interpret “appears in a root” as “arbitrary read/write is authorized.”
- Refresh caches and authorization decisions when a root changes.

### Sampling: borrow the host's model capability

A server sends `sampling/createMessage`, while the host keeps model selection, access control, and user review. The current specification also permits tools in a sampling request, but the client must explicitly declare `sampling.tools`. The `thisServer`/`allServers` values of `includeContext` are soft-deprecated; a server should not rely on them unless the client declares `sampling.context`.

The key boundary is this: the server proposes a generation request; it does not own the host's model, context, or final approval.

### Elicitation: obtain additional information from the user

`elicitation/create` has two modes:

- **form**: collect ordinary structured information using a flat, restricted JSON Schema within MCP. It must not request passwords, API keys, access tokens, payment credentials, or other secrets.
- **url**: direct the user to an external HTTPS page for sensitive input or third-party authorization. Secrets must not pass through the client or LLM; it also cannot replace the MCP Authorization from client to MCP server.

The client must clearly show which server made the request and let the user accept, decline, or cancel. URL mode is new in `2025-11-25`; verify actual SDK support before adopting it.

## Tasks: a persistent execution wrapper for a request

Tasks were introduced in `2025-11-25` and are still experimental. A Task is not a new business primitive. It wraps an existing request with “return a task now, then poll status and retrieve the result” execution:

1. The request includes `task` parameters, such as a TTL.
2. The receiver returns a `CreateTaskResult` immediately rather than the final tool result.
3. The requestor polls `tasks/get` for status and calls `tasks/result` for the final result of the original request.

Both sides must declare the precise task capability. A tool must also declare `forbidden`, `optional`, or `required` through `execution.taskSupport`. Seeing a top-level `tasks` capability is not enough to prove that a particular `tools/call` can be task-augmented.

## A decision tree for feature selection

When facing a requirement, ask in this order:

1. Is it reusable context to read, or a one-off action to execute? Prefer a resource for the former and a tool for the latter.
2. Is the server giving a capability to the host, or does the server need a capability from the host or user? For the latter, consider roots, sampling, or elicitation.
3. Does the user need a fixed prompt template to choose? Consider a prompt.
4. Is the work long-running and in need of persistent state? Consider Tasks only when both sides explicitly support it; do not disguise a long task as an ordinary synchronous call.
5. Whatever you choose: who consents, who validates, who has least privilege, and who records the audit trail?

## Running exercise

Requirement: “The user selects a code project, reads its README, generates a review summary, chooses an output language, and creates an issue after confirmation.”

- Project scope: root.
- README: resource.
- Summary generation: the host calls its model itself, or the server requests sampling when explicit support exists.
- Output language: form elicitation.
- Creating the issue: tool.
- Team review format: prompt.
- If report creation takes a long time: task augmentation only when both capability-level and tool-level support are present.

For every item, also write its input schema, output schema, consent point, and failure mode before treating the design as complete.

## Common mistakes

- One tool queries, modifies, and sends messages at once, making permissions and retries impossible to reason about.
- An `inputSchema` contains only `type: object`, with no required fields, enumerations, or policy for unknown fields.
- An `outputSchema` is declared, but the server returns only free text.
- An annotation that says “read-only” is treated as fact, although the specification requires annotations from an untrusted server to be treated as untrusted.
- Form elicitation is used to request secrets.
- A server sends roots/sampling/elicitation requests without checking client capability.
- Tasks are treated as a stable, universally available queueing system.

## Self-check and mastery standard

1. Which feature fits “a database schema,” “delete a record,” “a weekly-report template,” and “the project directory selected by the user”?
2. Why must resource contents and tool annotations both be treated as untrusted input?
3. What responsibilities do `outputSchema` and `structuredContent` have, respectively?
4. Why does `sampling.tools` need its own sub-capability?
5. What is the secret boundary between form elicitation and URL elicitation?
6. Why do Tasks need both a session capability and tool-level support?

You have mastered the lesson when you can independently complete the running exercise and explain the direction, control owner, contract, and failure mode for every choice.

## Next step

Continue to [[mcp/learning-path/03-lifecycle-capability-negotiation-and-transports|Lifecycle, Capability Negotiation, and Transports]] to place these features in a real session sequence.

## References

The following are first-party MCP materials. Specification links were retrieved or checked on 2026-07-14; the non-security boundary of Roots was checked on 2026-07-19.

- [Server Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Server Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [Server Prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts)
- [Client Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [Client Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- [Client Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [Tasks utility](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [MCP Client concepts](https://modelcontextprotocol.io/docs/learn/client-concepts)
