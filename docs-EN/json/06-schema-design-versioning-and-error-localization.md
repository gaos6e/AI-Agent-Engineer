---
title: "Schema Design, Versioning, and Error Localization"
tags:
  - ai-agent-engineer
  - JSON
  - JSON-Schema
  - data-contract
aliases:
  - Advanced JSON Schema
  - Schema Version Migration
source_checked: 2026-07-14
lang: en
translation_key: JSON/06-Schema设计、版本与错误定位.md
translation_source_hash: d3294711e16c13fe4ea0e88038d47fc30ede508f5b39e09eacb892d671c1df6c
translation_route: zh-CN/JSON/06-Schema设计、版本与错误定位
translation_default_route: zh-CN/JSON/06-Schema设计、版本与错误定位
---

# Schema Design, Versioning, and Error Localization

## Goal

Use `$defs` / `$ref`, composition, and conditionals to remove repetition; design explicit discriminators for tool unions; handle incompatible change through versions and migration functions; and turn validation errors into RFC 6901 JSON Pointers, keywords, and safe error codes.

## Put reusable units in `$defs` first

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/schemas/tool-suggestion-v1",
  "$defs": {
    "request_id": {
      "type": "string",
      "pattern": "^req-[0-9]{4}$"
    }
  },
  "type": "object",
  "properties": {
    "request_id": {
      "$ref": "#/$defs/request_id"
    }
  }
}
```

- `$id` gives the Schema a base identifier. The example uses the reserved `.invalid` domain and is not a real endpoint.
- `$defs` stores reusable subschemas.
- `#/$defs/request_id` is an in-document JSON Pointer.
- Remote `$ref` introduces resolution, caching, versioning, and supply-chain boundaries. Production systems should preregister trusted Schemas rather than letting an untrusted instance select arbitrary URLs.

## `allOf`, `anyOf`, and `oneOf` are not synonyms

| Keyword | Meaning | Common use |
| --- | --- | --- |
| `allOf` | Every subschema must match | Add independent constraints; it is not object-oriented inheritance. |
| `anyOf` | At least one subschema matches | Permit several possibly overlapping shapes. |
| `oneOf` | Exactly one subschema matches | Model a disjoint union; overlapping branches fail unexpectedly. |
| `not` | The subschema must not match | Exclude a stated shape. |

For a union of tool parameters, prefer a clear discriminator:

```json
{
  "oneOf": [
    {
      "properties": {
        "tool": {"const": "search_notes"},
        "arguments": {"$ref": "#/$defs/search_arguments"}
      }
    },
    {
      "properties": {
        "tool": {"const": "send_email"},
        "arguments": {"$ref": "#/$defs/email_arguments"}
      }
    }
  ]
}
```

The outer object still needs `required` and `additionalProperties`. Without mutually exclusive conditions such as `const`, the same instance can match two branches and therefore violate `oneOf`.

## Express local conditions with `if` / `then` / `else`

```json
{
  "if": {
    "properties": {"mode": {"const": "write"}},
    "required": ["mode"]
  },
  "then": {
    "properties": {"requires_approval": {"const": true}}
  }
}
```

This expresses “a configuration that declares a write action must require approval.” But `requires_approval: true` is still only a configuration claim. A real approval fact at runtime must come from a trusted approval system; a model must not self-report `approved: true` in its parameters.

## The `additionalProperties` and composition trap

`additionalProperties` knows only the `properties` declared in the same Schema object. Complex `allOf` composition can therefore reject fields defined by another branch unexpectedly. Draft 2020-12 provides `unevaluatedProperties` for properties already evaluated by other subschemas, but its support and semantics are more complex.

For a beginner project, prefer:

1. Put shared outer fields in one object Schema.
2. Use a discriminator only to refine `arguments`.
3. Set `additionalProperties: false` on every concrete `arguments` object.
4. Write success and extra-field-failure tests for every branch.

Do not stack composition merely to show off. A readable, testable contract matters more.

## Schema version and data version are separate concepts

- `$schema`: the JSON Schema dialect, such as Draft 2020-12.
- `$id`: the identifier for this Schema resource.
- `schema_version` in an instance: your business-data-format version.

```json
{
  "schema_version": 1,
  "name": "meeting-assistant"
}
```

When a business version changes incompatibly:

1. Retain the v1 Schema and its tests.
2. Define a pure v1 → v2 migration function.
3. Validate v1 strictly, migrate, then validate v2.
4. Record migration source and version; do not guess field meaning in place.
5. Design rollback, or at least preserve the original input.
6. Write new records only in the current version; support legacy reads only for a stated period.

Renaming a field, changing a unit, deleting an enum member, or changing the meaning of `null` can all be incompatible. Changing only a Schema file without migrating data turns old data into a runtime incident.

## Locate errors with RFC 6901 JSON Pointer

JSON Pointer encodes a path such as `/tools/1/name`. Its two escape rules are:

- `~` → `~0`
- `/` → `~1`

The root value's pointer is the empty string. The project function is:

```python
from collections.abc import Iterable


def json_pointer(parts: Iterable[str | int]) -> str:
    encoded: list[str] = []
    for part in parts:
        token = str(part).replace("~", "~0").replace("/", "~1")
        encoded.append(token)
    return "" if not encoded else "/" + "/".join(encoded)
```

Do not confuse JSON Pointer with JSONPath: Pointer is a standard syntax for locating one value, while JSONPath (RFC 9535) is a query expression.

## Sort, normalize, and redact validation errors

A validator may return multiple errors, and traversal order must not become an unstable API. One controlled policy is:

1. Sort consistently by instance path and validator keyword.
2. Return only the first error externally, or a bounded array of errors.
3. Record `code=schema_validation`, Pointer, and keyword.
4. Do not emit instance values from `ValidationError.message` directly.
5. Keep detailed diagnostics in access-controlled development environments and redact them.

For example:

```json
{
  "status": "rejected",
  "code": "schema_validation",
  "pointer": "/arguments/limit",
  "keyword": "maximum"
}
```

This tells the caller what to fix without copying a search query or email body.

## Test Schema boundaries and evolution

For every important field, test at least:

- smallest and largest valid values;
- one below and one above each bound;
- missing, `null`, and wrong-type values;
- unknown fields;
- every union branch;
- inputs matching zero or multiple `oneOf` branches;
- old versions and unknown future versions;
- that the Schema itself passes `check_schema`;
- stable error Pointer and keyword with no sensitive value.

Test the Schema files and application-level business checks together. Constraints that Schema cannot express—such as unique tool names, existence of an ID in a database, or approval of a write—need independent unit tests.

## Vendor profiles versus the full specification

An LLM provider's strict or structured-output feature often supports only a JSON Schema subset. It may also require every field to be listed in `required`, every object to set `additionalProperties: false`, or optionality to use `null`. Current MCP tool-Schema profiles impose their own constraints too.

Those are dynamic implementation constraints, not universal Draft 2020-12 semantics. In practice:

1. Write the domain contract first.
2. State the target dialect.
3. Compile or trim a profile for the provider.
4. Validate model output again locally.
5. Record the retrieval date of provider documentation and its Schema-subset limits.

## Common mistakes and diagnosis

- Treating `$schema`, `$id`, and `schema_version` as one version: record dialect, resource, and business format separately.
- Letting `oneOf` branches overlap: add `const` discriminators and overlap-failure tests.
- Letting an instance provide a `$ref` URL: load Schemas only from a trusted registry.
- Echoing third-party error messages verbatim: convert them into controlled code, Pointer, and keyword.
- Overwriting the original file during migration: validate, migrate to a new object, validate the new version, then write atomically.
- Describing a vendor subset as “JSON Schema does not support it”: identify the implementation and date.

## Exercises

1. Extract a reusable `request_id` with `$defs` / `$ref` and write valid/invalid tests.
2. Design a `oneOf` with `const` discriminators for `search_notes` and `send_email`.
3. Construct a counterexample that matches two `oneOf` branches, then make the branches disjoint.
4. Design migration, validation, and rollback from v1 `timeout` to v2 `timeout_seconds`.
5. Encode the path `items/a~b/2` as a JSON Pointer and verify the escaping.

## Self-check

1. What is the difference between `anyOf` and `oneOf`?
2. What do `$schema` and an instance's `schema_version` control respectively?
3. Why cannot `requires_approval: true` prove that approval happened?
4. What is the JSON Pointer for the root value?
5. Why should a raw validator error not go into an ordinary log?

## Summary and next step

A Schema is a versioned structural contract, and an error report is a public interface too. Next, place it at API, LLM, and tool-call boundaries in [[json/07-json-in-api-llm-and-tool-calling|JSON in API, LLM, and Tool Calling]]. Return to [[json/00-index|the JSON learning index]].

## References

Sources checked: **2026-07-14**.

- [Draft 2020-12: Core](https://json-schema.org/draft/2020-12/json-schema-core.html)
- [Draft 2020-12: Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html)
- [Understanding JSON Schema: Schema Composition](https://json-schema.org/understanding-json-schema/reference/combining)
- [RFC 6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901.html)
- [RFC 9535: JSONPath](https://www.rfc-editor.org/rfc/rfc9535.html)
- [`jsonschema` validator selection](https://python-jsonschema.readthedocs.io/en/stable/creating/)
