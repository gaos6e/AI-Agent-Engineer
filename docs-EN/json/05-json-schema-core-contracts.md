---
title: "JSON Schema Core Contracts"
tags:
  - ai-agent-engineer
  - JSON
  - JSON-Schema
aliases:
  - Introduction to JSON Schema
  - JSON data contracts
source_checked: 2026-07-22
lang: en
translation_key: "JSON/05-JSON Schema基础契约.md"
translation_source_hash: 47382bb142562810c223c7c2767fc60c13faaf2be57a65302c75fc55e557d20f
translation_route: zh-CN/JSON/05-JSON-Schema基础契约
translation_default_route: zh-CN/JSON/05-JSON-Schema基础契约
---

# JSON Schema Core Contracts

## Goals

Distinguish syntax, Schema, and business validation; read and write an object Schema using Draft 2020-12; correctly use `type`, `properties`, `required`, `additionalProperties`, arrays, and range keywords; and execute validation with Python `jsonschema` rather than merely describing it.

## Where Schema validation fits

Take `{"amount": 1000}` as an example:

1. **Syntax layer**: can the text be parsed strictly, without duplicate keys, non-standard numbers, or resource-limit violations?
2. **Schema layer**: do top-level type, fields, ranges, and compositions meet the declaration?
3. **Business layer**: does the account exist, is the balance sufficient, and is the unit correct?
4. **Authorization layer**: may the current identity perform the action?
5. **Side-effect layer**: are idempotency, approval, execution result, and audit correct?

JSON Schema primarily handles layer 2. Do not expect one keyword to replace an external database, permission system, or human approval.

## Instance, Schema, and dialect

- **instance**: the JSON value being validated;
- **schema**: the JSON document describing constraints;
- **dialect/draft**: the version of keywords and their semantics.

This knowledge base uses Draft 2020-12 and declares it explicitly at the top of every Schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object"
}
```

As of 2026-07-22, the official JSON Schema site still lists Draft 2020-12 as the current formally released dialect. A validator may support only an older draft, and vendor structured output may support only a subset; check implementation documentation and `$schema` before using it rather than relying on a “latest default.”

## A runnable Agent-configuration Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "name", "max_steps", "tools"],
  "properties": {
    "schema_version": {"const": 1},
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 64
    },
    "max_steps": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20
    },
    "tools": {
      "type": "array",
      "minItems": 1,
      "maxItems": 20,
      "items": {"type": "string"}
    }
  }
}
```

### `properties` does not mean required

`properties` says only how a field is validated when it appears. To require the field, put its name in `required`.

### Optional and nullable are different

Leaving a field out of `required` means it may be absent. Permitting `null` means the field may be empty when present:

```json
{
  "type": ["string", "null"]
}
```

Their business meanings need separate documentation.

### `additionalProperties` permits unknown fields by default

Tool arguments and internal commands should explicitly decide whether unknown fields are rejected. `false` catches typos and narrows the attack surface, but raises the cost of version upgrades. Long-lived open configurations may allow extensions, retain unknown fields, or warn; do not depend on the default unconsciously.

## Common validation keywords

| Data type | Common keywords | Caution |
| --- | --- | --- |
| General | `type`, `enum`, `const` | `enum` candidates should remain stable and have a migration plan. |
| object | `properties`, `required`, `additionalProperties`, `minProperties` | Field presence, field constraints, and unknown fields are three separate choices. |
| array | `items`, `prefixItems`, `minItems`, `maxItems`, `uniqueItems` | Draft 2020-12 tuple semantics use `prefixItems`; objects are deduplicated by whole value. |
| string | `minLength`, `maxLength`, `pattern`, `format` | `pattern` is a regular expression; `format` is often annotation by default. |
| number | `minimum`, `maximum`, `exclusiveMinimum`, `multipleOf` | JSON Schema `integer` is mathematical, not the same as Python `type is int`. |

`uniqueItems: true` can reject exactly identical array elements, but cannot directly express “the `name` field in an array of objects must be unique.” Application code normally checks such cross-item invariants.

## The real semantics of `default` and `format`

- `default` is an annotation; standard validation does not guarantee that a missing field is written into the instance.
- Draft 2020-12 divides `format` into annotation and assertion vocabularies; whether a particular validator rejects an invalid email/date needs explicit configuration.
- If the application must apply defaults, normalize times, or check domains, it must execute and test code rather than assume a Schema changes data automatically.

## Actually validate in Python

This project pins `jsonschema==4.26.0`. After installation:

```python
from jsonschema import Draft202012Validator

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["max_steps"],
    "properties": {
        "max_steps": {"type": "integer", "minimum": 1, "maximum": 20}
    },
    "additionalProperties": False,
}

Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
errors = list(validator.iter_errors({"max_steps": 0}))

if errors:
    print(errors[0].validator)  # minimum
```

The engineering sequence is: strictly parse the Schema itself and call `check_schema`; construct a validator for an explicit draft; then call `iter_errors` on the instance. Do not let a validator auto-select the “current latest draft” in place of an explicit contract.

## Error messages must be stable and redacted

A third-party `ValidationError.message` can contain real values. Ordinary logs can record:

- an internal error code such as `schema_validation`;
- the instance’s JSON Pointer;
- the failed keyword such as `required` or `maximum`;
- request ID, Schema version, and source;
- whether the caller can retry or must repair input.

Do not record a complete instance, email body, token, or uncleaned model text. The project converts the first deterministically sorted error into `code + pointer + keyword`.

## What Schema cannot prove

Even if `{"document_id":"doc-42"}` passes Schema, it cannot prove:

- the document actually exists;
- the ID belongs to the current tenant;
- the caller is allowed to read it;
- the document contents are trustworthy;
- the model had factual grounds to choose that ID;
- the tool executed successfully.

Those checks must remain in trusted application code.

## Common errors and troubleshooting

- Writing `properties` but forgetting `required`: add a failing test for the absent field.
- Assuming `default` fills in a value automatically: apply it explicitly in application code and retain the migration result.
- Assuming `format: email` necessarily rejects: check the validator’s format-assertion configuration.
- Equating Python types directly with JSON Schema types: test `True`, `1`, and `1.0` in particular.
- Testing only successful samples: for every important keyword, test exactly at the boundary and one beyond it.
- Executing a tool right after Schema succeeds: continue through business, authorization, and approval layers.

## Exercises

1. Write an integer constraint of 1–120 for `timeout_seconds` and test 1, 120, 0, 121, and `true`.
2. Give `log_level` four enum values and design a compatibility policy for a future added value.
3. Compare an optional string with a required string that may be null.
4. Design unknown-field policy as rejection, allowance, and a nested extension object, explaining the trade-offs.
5. Run `Draft202012Validator.check_schema`, deliberately misspell a `type`, and observe `SchemaError`.

## Self-test

1. Does `properties` require a field to be present?
2. Does `required` guarantee a non-empty string?
3. Does `default` guarantee that a validator modifies the instance?
4. Why declare `$schema` explicitly?
5. What layers of checking remain after a Schema succeeds?

## Summary and next step

Basic Schemas express individual values and local structure; complex contracts also need reuse, composition, versioning, and stable error paths. Continue to [[json/06-schema-design-versioning-and-error-localization|Schema Design, Versioning, and Error Location]]. Return to the [[json/00-index|JSON Learning Index]].

## References

Source review date: **2026-07-22**.

- [JSON Schema Specification](https://json-schema.org/specification)
- [Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
- [`jsonschema` 4.26.0 documentation](https://python-jsonschema.readthedocs.io/en/stable/)
- [`jsonschema` 4.26.0 on PyPI](https://pypi.org/project/jsonschema/)
