---
title: "Text, JSON, and Time Normalization"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - Semistructured data cleaning
source_checked: 2026-07-14
source_baseline:
  - RFC 8259 JSON
  - RFC 3339 timestamps
  - JSON Schema 2020-12
  - Python 3 standard-library documentation
lang: en
translation_key: 数据清洗/05-文本JSON与时间规范化.md
translation_source_hash: 6b4cb5f374667584239ab5cc2266ddc029314409ffcdb092a733e3a37a398cc0
translation_route: zh-CN/数据清洗/05-文本JSON与时间规范化
translation_default_route: zh-CN/数据清洗/05-文本JSON与时间规范化
---

# Text, JSON, and Time Normalization

## Objective

Normalize text, JSON, and time without damaging code, Markdown, identifiers, or credential boundaries, and preserve provenance and audit evidence for every lossy change.

## Text

Use UTF-8 consistently for reading and writing. Preserve the original text before producing normalized fields. For natural-language fields, trim leading and trailing whitespace and normalize line endings only when the contract permits it. Do not collapse internal repeated whitespace by default: it changes Python indentation, Markdown code blocks, tables, and user formatting. Unicode NFC/NFKC can change character representation; NFKC merges some compatibility characters and must not be applied blindly to passwords, code, identifiers, or legal originals.

Case, punctuation, emoji, code blocks, and Markdown structure can carry meaning. RAG cleaning should not delete headings, lists, tables, or page-level provenance merely to look “clean.”

## JSON

Validate required fields, types, enumerations, and nested structure in JSON objects. Remember:

- JSON does not permit comments, and object keys must be strings.
- **null** and an absent field must remain distinct under the contract.
- Numeric ranges depend on consumer implementations; very large integers can lose precision in other languages.
- Do not silently discard unknown fields; record the schema version and compatibility policy.

JSON Schema should declare a specific **$schema** version; the current specification is 2020-12. Across validators, **format: "date-time"** can be an annotation only. Whether it is a blocking assertion must be configured explicitly and tested with invalid examples; a schema file that merely contains **format** is not enough.

## Time

Time must include at least event moment, time zone, and precision. Systems often normalize internally to UTC and convert to a local zone only for display. A timestamp such as **2026-07-13 09:00** without a zone cannot order events across regions reliably.

Distinguish event time, service-receipt time, and database-ingest time. Late arrival and clock skew can make them differ. Do not substitute file modification time for the business event time.

## Privacy and credentials

Before and after cleaning, do not emit tokens, cookies, API keys, complete email addresses, or unnecessary user content in logs. Run and test redaction rules against copies of source fields; do not assume one regular expression covers every secret format.

Hashes are useful for integrity and correlation summaries, but they are not automatic anonymization: low-entropy identifiers can be enumerated and inferred, and equal inputs reveal correlation. Sensitive data still requires minimization, access control, retention, and deletion policies.

## Exercise

Design one tool-call JSON event containing **schema_version**, **event_id**, a UTC timestamp, tool name, status, error code, and a redacted parameter summary. State which fields are prohibited from training data.

## Mastery check

- [ ] I know when normalization may touch only line endings and leading/trailing whitespace, rather than internal whitespace or NFKC.
- [ ] I can distinguish JSON **null**, a missing field, and an empty string, and declare an unknown-field policy.
- [ ] I convert time-zone-aware timestamps to UTC while retaining the semantics of event, receipt, and ingestion time.
- [ ] I do not call hashes, masking, or regular-expression replacement anonymization by default.

Next: [[data-cleaning/06-quality-validation-and-reproducible-pipelines|Quality validation and reproducible pipelines]].

## References

Sources were checked on 2026-07-14.

- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 3339: Date and Time on the Internet](https://www.rfc-editor.org/rfc/rfc3339)
- [JSON Schema 2020-12 specification](https://json-schema.org/specification)
- [Python unicodedata](https://docs.python.org/3/library/unicodedata.html)
- [Python datetime](https://docs.python.org/3/library/datetime.html)
