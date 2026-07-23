---
title: "Schema and Quality Thresholds"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - Data contract
  - Data schema
source_checked: 2026-07-22
source_baseline:
  - JSON Schema 2020-12
  - pandas 3.0 stable user guide
lang: en
translation_key: 数据清洗/01-Schema与质量门槛.md
translation_source_hash: cf3d8c7d166ecbb7d34d7bb966472499155ac818bf7846dfd45f609cf50eaf2f
translation_route: zh-CN/数据清洗/01-Schema与质量门槛
translation_default_route: zh-CN/数据清洗/01-Schema与质量门槛
---

# Schema and Quality Thresholds

## Objective

Define the data unit, field semantics, and failure actions first, then turn “the data is clean” into an executable, versioned, auditable contract.

## Define what one row represents

The first cleaning step is not calling **dropna()**; it is defining the **data unit**. A row can represent one Agent run, one tool call, one document, or one chunk. If a row's meaning is unclear, uniqueness, statistics, and labels lose their interpretation.

## A minimum data contract

| Field | Meaning | Type | Example constraint |
| --- | --- | --- | --- |
| **run_id** | Stable identity of one run | string | Required, unique, never reused |
| **started_at** | Start time | datetime | Includes a time zone; must not be implausibly later than collection time |
| **status** | Terminal state | category | **success/error/cancelled** |
| **latency_ms** | End-to-end latency | integer | **>=0**; unit is fixed as milliseconds |
| **query** | User input | string | Nullability policy is explicit; retain original text |

At minimum, a contract includes field name, business meaning, data type, requiredness, allowed values or ranges, uniqueness, units, time zone, sensitivity level, and the point at which the field is produced.

The contract itself needs a version. Adding an optional field is usually backward compatible, while deleting a field, changing a type, or tightening an enumeration can break old consumers. A production system must define whether unknown fields are rejected, retained, or quarantined; it must not silently discard them.

## Schema, data contract, and release manifest are different

A schema describes **what fields look like**. A **data contract** also declares who produces and consumes the data, the business point at which each field is true, how changes are negotiated, and who handles failure. A **release manifest** freezes the input snapshot, rules, outputs, hashes, and quality results actually used by a particular run. JSON Schema alone cannot prove that a release batch used the correct source or tell a downstream consumer which version to read.

A minimum operational contract for Agent-run events should also state:

- **schema_version**, producer version, and change owner; incompatible changes need a migration window and exit conditions for legacy consumers.
- **source_snapshot_id**, collection window, and the business meaning of **group_id**. Use **group_id** to split by user, session, document, or incident family; do not infer it afterward from labels or future outcomes.
- **access_scope**, sensitivity level, retention category, and a deletion or revocation reference. These fields are control and traceability clues, not proof that data is anonymized or authorized.
- Owners, reason codes, and escalation conditions for blocking, quarantine, alerts, and deterministic repairs.

When field semantics, grouping rules, source scope, or rejection policy changes, the dataset's measured object can change even if column names do not. Release a new data version and recheck whether downstream comparisons remain valid.

## Completeness, validity, consistency, and uniqueness

- **Completeness**: required fields exist and coverage meets the threshold.
- **Validity**: values parse and satisfy a range or enumeration.
- **Consistency**: related fields do not conflict, such as **success** with a required **error_code**.
- **Uniqueness**: primary keys are not duplicated, and a duplicate is classified as replay, retry, or collection error.
- **Timeliness**: data arrives within the allowed delay.

Quality thresholds should be quantified. For example: “**run_id** non-null rate is 100%, duplicate rate is 0%, and unknown **status** is below 0.1% and all such rows are quarantined.” A threshold is an engineering decision, not a natural constant; record its owner and reason for change.

## Reject, quarantine, or repair

- A deterministic, lossless format issue can be normalized automatically, such as leading and trailing whitespace.
- A problem that can change meaning should be quarantined, such as a conflicting primary key or an invalid timestamp.
- Missing unrecoverable critical fields should be rejected rather than guessed silently.
- Preserve raw data read-only; attach a rule version and time to cleaned results.

## Exercise

Write a contract for a RAG document that includes **document_id**, **source_uri**, **title**, **content**, **updated_at**, and **access_scope**. State which missing field prevents the document from entering the knowledge base.

## Mastery check

- [ ] I can explain what one row represents and which entity or event a primary key identifies.
- [ ] I can specify a type, nullability, enumeration or range, unit, time zone, and sensitivity level for every field.
- [ ] I can distinguish blocking, quarantine, alerting, and deterministic repair, and record the rule version.
- [ ] I can explain how schema changes affect upstream producers and downstream consumers.
- [ ] I can identify what the schema, contract, and manifest of a release each prove, and what each cannot prove.

Next: [[data-cleaning/02-missing-values-and-missingness-mechanisms|Missing values and missingness mechanisms]].

## References

Sources were checked on 2026-07-22.

- [pandas: Intro to data structures](https://pandas.pydata.org/docs/user_guide/dsintro.html)
- [JSON Schema 2020-12 specification](https://json-schema.org/specification)
- [JSON Schema: Getting started](https://json-schema.org/learn/getting-started-step-by-step)
