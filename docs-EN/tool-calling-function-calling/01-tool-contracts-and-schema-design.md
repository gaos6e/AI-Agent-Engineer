---
title: "Tool Contracts and Schema Design"
tags:
  - ai-agent-engineer
  - tool-calling
  - json-schema
aliases:
  - Function Schema Design
  - Tool Contract
source_checked: 2026-07-19
content_origin: original
content_status: dynamic
lang: en
translation_key: "Tool Calling（含 Function Calling）/01-工具契约与Schema设计.md"
translation_source_hash: e453965261a04ac6335e2ae0bf2893c3ef0072f68721ec3a1474e2896482b7d6
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/01-工具契约与Schema设计
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/01-工具契约与Schema设计
---

# Tool Contracts and Schema Design

## Goals

- Distinguish function tools, free-form tools, built-in tools, and their execution locations.
- Define a complete contract with a name, description, inputs, outputs, risk, and version.
- Make structurally illegal states hard to express.
- Understand the boundary of JSON Schema and provider strict modes.

## A tool is not the function itself

A tool definition is the capability sheet the model sees; a handler is the code that actually runs in the application.

| Type | Input shape | Who executes it | Typical use |
| --- | --- | --- | --- |
| Function tool | JSON Schema arguments | Usually your application | Business APIs, databases, controlled actions |
| Custom / free-form tool | Free text or grammar-constrained text | Application or platform | Code and query languages that do not naturally fit JSON |
| Built-in / server tool | Provider-defined | Provider infrastructure | Web search, code sandboxes, and other platform features |
| MCP tool | Declared by an MCP server | Client, remote service, or platform connector | Capabilities reused across clients |

Provider categories can change. When designing the business layer, ask where the code runs, who holds credentials, and who enforces authorization; the label alone is not an answer.

## The six parts of a complete contract

1. **Name:** verb plus object, such as **get_order** or **create_refund_draft**.
2. **Description:** when to use it, when not to use it, whether it has side effects, and what its result means.
3. **Input schema:** types, enums, ranges, formats, required fields, and the policy for extra fields.
4. **Output contract:** successful data, stable errors, provenance, and truncation or incompleteness states.
5. **Execution policy:** risk, timeout, retry, approval, idempotency, and data classification.
6. **Version:** a stable revision for schema and semantics.

A tool that defines only the first three parts is still difficult to operate safely in production.

## Names and descriptions

### Good names describe a specific action

- **get_order** reads one order.
- **list_open_orders** returns a collection.
- **create_refund_draft** creates a draft; it does not submit a refund.
- **submit_refund** has a real side effect.

Avoid vague names such as **process**, **handle**, and **do_action**. Near-neighbor tools must state their mutual exclusions: for example, “reads current status only; it does not create or modify an order.”

### Write the description like a docstring for a new teammate

At minimum, specify:

- where input IDs originate;
- units, currencies, time zones, and date formats;
- maximum list size, pagination, and empty-result semantics;
- side effects, approval, and idempotency requirements;
- situations in which the tool is not applicable; and
- whether output fields are fresh, complete, or cacheable.

A useful OpenAI guideline is the “intern test”: could a new teammate use the tool correctly from its contract alone? If not, put the answer in the contract or eliminate that parameter in application code.

## Use a schema to shrink the error space

~~~jsonc
{
  "type": "function",
  "name": "create_refund_draft",
  "description": "Create a refund draft for a currently authorized order; do not submit a real refund.",
  "parameters": {
    "type": "object",
    "properties": {
      "order_ref": {
        "type": "string",
        "minLength": 1,
        "description": "Order reference shown to the user by trusted application state."
      },
      "reason": {
        "type": "string",
        "enum": ["duplicate", "damaged", "other"]
      }
    },
    "required": ["order_ref", "reason"],
    "additionalProperties": false
  },
  "strict": true
}
~~~

> [!note] JSONC is used only for teaching
> The comments in a JSONC teaching example explain the contract line by line. Remove comments before submitting strict JSON Schema to an API.

The structure can reject a missing **order_ref**, arbitrary prompt-injection text in **reason**, an invented **is_admin: true** field, and wrong types. It cannot prove that the order exists, belongs to the current user or tenant, is eligible for a refund, has a truthful reason, has been approved, or will not be duplicated on retry. Those are business and security contracts.

## Make illegal states hard to express

| Weak design | Problem | Better design |
| --- | --- | --- |
| **set_light(on, off)** with two booleans | Both can be true or both false | **state: "on" \| "off"** |
| **amount: "ten dollars"** | Unit and type are ambiguous | **amount_minor: integer** plus a **currency** enum |
| Model supplies **user_id** | It can guess or cross an authorization boundary | Inject it from the trusted session |
| **execute(command: string)** | Arbitrary command space | Several narrow tools or a controlled enum |
| Unrestricted **send_email(to: string)** | Data exfiltration | Recipient policy, preview, and approval |

If two functions are always safe and necessarily consecutive, combine them into one business tool. Do not make the model repeatedly send arguments the application already knows.

## Strict mode and JSON Schema dialects

JSON Schema 2020-12 defines a general data model and vocabularies, but providers usually implement a subset. As checked on 2026-07-19, OpenAI documentation states that strict function calling requires **additionalProperties: false** on every object and lists every property as required; a nullable field can be represented with a type that includes **null**.

OpenAI Responses and Chat Completions have different defaults. Chat Completions functions are non-strict by default. Responses tries to normalize an omitted strict setting as strict; if the schema cannot be made compatible, it falls back to best effort and reports **strict: false** on the parsed tool. Therefore:

- declare the desired mode explicitly and test the resulting behavior in adapters and contract tests;
- record provider, API, model, and schema revision;
- do not assume another provider gives strict the same meaning;
- validate independently on the server; and
- fail before release for unsupported schema keywords instead of guessing at runtime.

Strict mode constrains structure. It does not establish authorization, ownership, current business state, or safe execution.

## Output contracts matter just as much

“Returns JSON” is not an output contract. Define exact fields, types, enums or formats, size, nesting depth, provenance revision, and bindings from output fields to input arguments for every tool. **get_order** may define **data.status** as a business field; **create_refund_draft** must reject it if it is undeclared. A loose global schema must not accept every tool’s output.

This course uses separate model and audit projections. The model-visible projection contains only the data required to continue work and bounded recovery state:

~~~jsonc
{
  "schema_version": "tool-model-result-v2",
  "status": "failed",
  "data": null,
  "error": {
    "code": "APPROVAL_REQUIRED",
    "category": "approval",
    "safe_message": "This action requires approval bound to the current arguments.",
    "recovery": "request_approval",
    "retry_after_ms": null
  },
  "execution": {
    "outcome": "not_started",
    "delivery": "fresh",
    "complete": true,
    "truncated": false
  },
  "provenance": {
    "source_label": "offline-dispatcher",
    "producer_revision": "offline-dispatcher-v2",
    "resource_revision": null,
    "observed_at": "2026-07-19T00:00:00Z",
    "trust": "trusted_control"
  }
}
~~~

The status means the action was not allowed to continue; it is not success that the model may retry freely. There is no business data because no execution started. The safe message contains no sensitive arguments or internal exception. Stable code, outcome, and recovery fields drive program logic; programs do not parse free text.

Keep principal references, provider response/call identity, operation, tool-contract revision, downstream receipts, and full SHA-256 bindings in a separate **protected_audit** record that is never sent to the model. Continue with [[tool-calling-function-calling/05-results-errors-and-untrusted-data|Results, errors, and untrusted data]] for the full design.

## Tool count and versions

Tool definitions consume context and increase selection error. Expose the small set most relevant to the current task. When capabilities are numerous, use a domain namespace, routing, or provider-supported tool search; those optimize discovery only and never grant authorization.

For schema changes:

- assess strict compatibility even when adding optional semantics;
- raise a major revision when units, meanings, or side effects change;
- let adapters support transition revisions while handlers retain one internal domain model; and
- pin the schema revision in the evaluation set to prevent same-name semantic drift.

## Practice

Design two tools:

1. **get_inventory(product_ref)**, a read.
2. **reserve_inventory(product_ref, quantity)**, a reversible write.

For each, write its name and use/non-use conditions, input schema, model-supplied versus session-injected parameters, a success result plus five error codes, timeout/idempotency/approval/freshness policy, and revision-upgrade conditions. Then ask someone unfamiliar with the business domain to restate the execution semantics from the contract alone; record every remaining ambiguity.

## Common mistakes

- Using a description to compensate for a constraint that an enum or type could encode.
- Treating **strict: true** as business correctness.
- Returning only natural language from a tool.
- Failing to distinguish read, draft, and submit in names.
- Giving the model tenant, user, or role identity.
- Exposing many synonymous tools without routing evaluation.

## Self-check

1. What is the difference between a tool definition and a handler?
2. What does **additionalProperties: false** prevent, and what does it not prevent?
3. Why should creating a draft and submitting it normally be separate tools?
4. Why should an already-known order ID be injected by the application?
5. Why can provider strict mode not replace server-side validation?

Next: [[tool-calling-function-calling/02-call-proposals-validation-and-authorization|Call proposals, validation, and authorization]].

## References

- [OpenAI: Defining functions](https://developers.openai.com/api/docs/guides/function-calling#defining-functions)
- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
- [JSON Schema: The basics](https://json-schema.org/understanding-json-schema/basics)

Sources were checked on 2026-07-19. Provider-supported schema subsets and strict defaults may change.
