---
title: "Data Contracts and Version Evolution"
tags: [ workflow-automation, data-contract, json-schema ]
aliases: [ Workflow Data Contracts ]
source_checked: 2026-07-22
lang: en
translation_key: 工作流自动化/02-数据契约与版本演进.md
translation_source_hash: 6461b777f12d6bc48467c3886868e10e63a09adc2088c1c44b4c6937fc7aa348
translation_route: zh-CN/工作流自动化/02-数据契约与版本演进
translation_default_route: zh-CN/工作流自动化/02-数据契约与版本演进
---

# Data Contracts and Version Evolution

## Goal

Define verifiable contracts for trigger events, step inputs/outputs, and checkpoints, and evolve them without breaking in-flight instances.

## Why one shared large dictionary loses control

Beginners often let every step read and write one `context`. It is quick, but dependencies hide in field names: an upstream change from integer `amount` to string may fail only hours later downstream. An LLM node can add an unexpected field that a later high-privilege step then misuses.

Use four layers instead:

1. **Raw event:** immutable after receipt, for audit and reparsing.
2. **Normalized domain object:** converts multi-version input into one internal model.
3. **Step input/output:** each edge carries only fields needed by its consumer.
4. **Runtime metadata:** attempt, status, definition version, idempotency key, and result reference; never mix it with business data.

## A complete step contract

| Item | Question | Example |
| --- | --- | --- |
| Input schema | Which fields and types are accepted? | `order_id: string`, `amount_cents: integer` |
| Business precondition | What remains true after structural validation? | Amount is positive; order belongs to current tenant |
| Output schema | Which fields can downstream rely on? | `reservation_id`, `expires_at` |
| Error classification | Transient, permanent, or business rejection? | `UPSTREAM_BUSY`, `INVALID_ORDER` |
| Side effect | Does it change the external world? | Reserve inventory |
| Idempotency strategy | How does duplicate execution identify the same intent? | Instance + step + order + v1 |
| Version | Which handler/schema produced it? | `reserve_inventory@2` |
| Data class | May it be persisted, logged, or sent to a model? | Internal, confidential, restricted |
| Trusted subject and authorization | Who is currently permitted to act on which resource? | Server-derived actor/tenant, policy version, resource ACL |
| Receipt and terminal outcome | What did downstream accept, and what business result is final? | `receipt_id`, `outcome: succeeded | failed | unknown` |

JSON Schema Draft 2020-12 describes JSON structure, and `$schema` should declare its dialect. It can check required fields, types, enums, and additional fields, but cannot prove that an order belongs to a user or a referenced document exists; those remain business validation. Review [[json/05-json-schema-core-contracts|JSON Schema foundations and contracts]] for schema/profile practice.

Do not collapse several levels of identity into one `id`:

| Identifier | Question answered | Cannot replace |
| --- | --- | --- |
| `event_id` + `source` | Which input delivery is this? | Sender authentication; deduplication of an unbound business action |
| `instance_id` | Which workflow instance is this? | An automatic idempotency key for every external side effect |
| `operation_id` / `action_id` | Which permitted business intent is this? | A record of each execution attempt |
| `attempt_id` | Which actual claim/execution number is this? | Idempotent result or final business outcome |
| `trace_id` | How can diagnostic signals be correlated? | Identity, tenant, or authorization |

For high-risk action, bind `operation_id` to immutable intent: action, target resource, parameter digest, and definition/policy version. A downstream **receipt** proves only that it accepted or recorded that intent. A timeout, asynchronous processing, or unknown state still requires query, reconciliation, or human handling to establish a verifiable `outcome`; never equate HTTP 202/200 with business success.

## Event envelope and business payload

CloudEvents `id/source/type/specversion` are envelope fields. `data` is the business payload and can use `dataschema` to identify its schema. Do not put personal data, secrets, or a full prompt into context fields readable by routers and log systems; CloudEvents also warns that middleware can inspect and record context attributes.

One event can have three versions at once:

- CloudEvents specification version, for example `specversion: "1.0"`;
- event-type version, for example `com.example.order.submitted.v2`; and
- `data` schema version.

They solve different problems. Do not replace all three with an ambiguous `version` field.

## Compatible evolution

### Usually safer changes

- Add a truly optional field with explicit default semantics.
- Extend metadata that downstream explicitly permits it to ignore.
- Add an error code while retaining a safe fallback for unknown errors.
- Let a new handler read an old checkpoint and migrate it explicitly in memory.

### Usually breaking changes

- Remove or rename a required field.
- Change type, unit, time zone, or meaning.
- Change cents to dollars but retain the field name.
- Narrow an enum without handling persisted values.
- Replay old events in a different order with new code.

“Usually” is engineering judgement, not an automatic JSON Schema compatibility guarantee. Run producer/consumer contract tests against real old fixtures before release.

## Version strategy for long processes

A workflow can wait for days. When code changes, choose one of three strategies:

1. **Pin old instances to old definition/workers:** simple, but resource-intensive.
2. **Make new workers compatible with old history:** requires replay and migration tests.
3. **Migrate instances explicitly:** migrations need versioning, auditability, rollback, and human handling for dangerous defaults.

Never make an in-flight instance silently follow `latest`. Write definition, handler, and schema versions into its checkpoint. On recovery, fail explicitly if they are incompatible; do not guess a missing currency, permission, or approval meaning.

## Large results and sensitive data

Store only small recovery metadata in the checkpoint. Put documents, raw model output, and binaries in object storage; state retains object ID, `source_revision`, content hash, size, type, sensitivity class, and access policy. At recovery, verify reference existence, revision, and hash again, and ensure the **current** service identity remains allowed to read it. A URI, old ACL decision, or model self-report does not replace execution-time authorization. If a source object was deleted, revoked, or changed, enter explicit `unknown/blocked` or human handling rather than reading “the latest” silently.

Use a log-field allowlist: record `instance_id`, step, error code, and result fingerprint, not complete credentials, customer documents, prompts, or tool arguments. LLM nodes must also declare which fields may be sent to which provider/region.

## Contract-test checklist

- Minimum legal input, upper bounds, and empty collections.
- Missing required fields, wrong types, unknown enums, and additional fields.
- Current version, at least one real old version, and an unknown future version.
- Same idempotency key with a different payload.
- Correct query/reconciliation path for a receipt, delayed terminal state, and unknown result for one `operation_id`.
- Fail-closed behavior before object read and side effect for unauthenticated or revoked actor/tenant.
- Unicode, overlong strings, and nesting-depth limits.
- Sensitive fields never entering events, logs, or errors unexpectedly.
- Upstream output satisfying every direct downstream input contract.

## Exercise

Write simplified schemas for `parse_invoice -> approve_invoice`: v1 contains amount only; v2 adds `currency`.

1. Choose default-currency migration, rejection, or human confirmation, and explain the risk.
2. Design a conflict test for same event ID with a different amount.
3. List fields allowed in logs and fields that must retain only a reference.
4. Explain whether an old approval remains valid after migrated amount or currency changes.

## Self-check

1. How does schema validation differ from business validation?
2. Why should raw events be immutable?
3. What do `specversion`, event-type version, and payload-schema version each solve?
4. When can adding an optional field still break consumers?

## Next

Continue with [[workflow-automation/conditions-parallelism-and-joins|Conditions, parallelism, and joins]].

## References

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [CloudEvents Specification 1.0.2](https://github.com/cloudevents/spec/tree/v1.0.2)
- [Open Workflow Specification 1.0.3](https://serverlessworkflow.io/)
- [OWASP Business Logic Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html) (server-side recomputation of security values and per-resource authorization)
