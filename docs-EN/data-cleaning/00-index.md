---
title: "Data Cleaning"
tags:
  - ai-agent-engineer
  - data-quality
  - learning-path
aliases:
  - Data Cleaning index
  - Data Cleaning learning path
source_checked: 2026-07-22
source_baseline:
  - pandas 3.0 stable user guide
  - Python 3.14 standard-library documentation
  - JSON Schema 2020-12
  - RFC 4180 and RFC 3339
ai_learning_stage: 2. Mathematical and data foundations
ai_learning_order: 16
ai_learning_schema: 2
ai_learning_id: data-cleaning
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 1600
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 425
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 850
ai_learning_track_agent_platform_kind: recommended
lang: en
translation_key: 数据清洗/00-目录.md
translation_source_hash: a5023867e7c9d6ccd713096ed22b0c59d3e983281d1829ba21b7ea16fb317784
translation_route: zh-CN/数据清洗/00-目录
translation_default_route: zh-CN/数据清洗/00-目录
---

# Data Cleaning

## Course overview

Data cleaning is not “removing rows that look abnormal.” It transforms raw data into interpretable, verifiable, and traceable input under an explicit data contract. Dirty data in Agent, RAG, and evaluation systems appears as parsing failures, duplicated knowledge, incorrect timelines, inflated metrics, and irreproducible results.

## Where this fits in the overall path

This course is in the Mathematical and data foundations stage. It builds on Python, JSON, and regular expressions, and directly supports machine learning, knowledge-base construction, data annotation, evaluation, and runtime monitoring.

## Learning objectives

- Write a schema and quality threshold for a table or JSON event.
- Distinguish missing, invalid, duplicate, conflicting, and statistically unusual data.
- Normalize text, time, categories, and numeric values while retaining raw data and an audit record.
- Build repeatable cleaning processes and automatic quality checks.
- Distinguish a schema, a cross-team data contract, and a consumer-facing release manifest; understand that they cannot replace one another.
- Complete an Agent run-log cleaning project with no third-party packages.

## Prerequisites

You should be able to use basic Python 3 syntax and understand CSV, JSON, fields, and data types. Complete [[python-fundamentals/00-index|Python Fundamentals]], [[json/00-index|JSON]], and [[regular-expressions/00-index|Regular Expressions]] first if possible. Learn **venv + pip** first; the project in this course uses only the standard library and requires no additional package.

## Recommended order

1. [[data-cleaning/01-schema-and-quality-thresholds|Schema and quality thresholds]]: define what is valid before discussing repairs.
2. [[data-cleaning/02-missing-values-and-missingness-mechanisms|Missing values and missingness mechanisms]]: make missing-data treatment follow business meaning and evaluation boundaries.
3. [[data-cleaning/03-duplicates-and-entity-identity|Duplicates and entity identity]]: prevent duplicate counting, retrieval contamination, and data leakage.
4. [[data-cleaning/04-outliers-and-range-rules|Outliers and range rules]]: distinguish invalid data, rare but real events, and distribution drift.
5. [[data-cleaning/05-text-json-and-time-normalization|Text, JSON, and time normalization]]: handle the semistructured data most common in Agent engineering.
6. [[data-cleaning/06-quality-validation-and-reproducible-pipelines|Quality validation and reproducible pipelines]]: replace visual spot checks with quality reports and gates.
7. [[data-cleaning/07-project-agent-run-log-cleaning|Project: Agent run-log cleaning]]: run the complete cleaning, quarantine, and reporting workflow.

## Hands-on entry point

[[data-cleaning/examples/clean_agent_runs.py|clean_agent_runs.py]] reads [[data-cleaning/examples/dirty_agent_runs.csv|dirty_agent_runs.csv]], validates the schema strictly, normalizes status and UTC timestamps, rejects duplicate IDs, validates latency, and writes clean data and a privacy-aware issue report separately. [[data-cleaning/examples/test_clean_agent_runs.py|test_clean_agent_runs.py]] covers ten normal, boundary, and failure behaviors. The script refuses to overwrite its source; an existing output is replaced only with an explicit **--overwrite** option.

## Mastery criteria

- [ ] I can state a field name, type, nullability, allowed range, uniqueness rule, and unit.
- [ ] I can explain why missing values must not always become zero and outliers must not always be deleted.
- [ ] I can distinguish row-level duplicates, entity duplicates, and semantic near-duplicates.
- [ ] I can record input count, output count, rejection reasons, and rule version in a cleaning report.
- [ ] I can freeze entity or document-level grouping and an evaluation split before learning statistics, and explain how it prevents leakage.
- [ ] I can ensure that repeated runs with the same input and rules produce the same result.
- [ ] I can run normal and **-O** modes plus the ten tests, proving that the source file is unchanged, output is byte-for-byte reproducible, and caches are cleaned.

## Connections to other knowledge bases

- [[machine-learning/00-index|Machine Learning]] must fit any cleaning step that learns statistics after splitting data, to prevent leakage.
- [[data-annotation/00-index|Data Annotation]] should exclude corrupted, duplicated, and privacy-noncompliant examples first.
- [[document-parsing/00-index|Document Parsing]] and [[chunking-strategies/00-index|Chunking Strategies]] need provenance, page numbers, heading hierarchy, and stable document IDs.
- [[runtime-monitoring/00-index|Runtime Monitoring]] depends on consistent time, status, error-code, and latency units.
- [[privacy-computing/00-index|Privacy Computing]] and [[ai-governance/00-index|AI Governance]] define sensitive fields, retention, access, and deletion boundaries. Data cleaning must not mistake a hash for anonymization.

## Primary references

Sources were checked on 2026-07-22. The pandas **stable** documentation is currently in the 3.0 series and will continue to change. This course's project does not depend on pandas; its examples were verified with Python 3.11.9. When using pandas or a data-quality framework, pin the project version and rerun contract tests.

- [pandas User Guide](https://pandas.pydata.org/docs/user_guide/)
- [pandas: Working with missing data](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [pandas: Working with text data](https://pandas.pydata.org/docs/user_guide/text.html)
- [pandas: Duplicate Labels](https://pandas.pydata.org/docs/user_guide/duplicates.html)
- [Python csv module](https://docs.python.org/3/library/csv.html)
- [Python datetime module](https://docs.python.org/3/library/datetime.html)
- [Python tempfile module](https://docs.python.org/3/library/tempfile.html)
- [JSON Schema 2020-12 specification](https://json-schema.org/specification)
- [RFC 8259: The JavaScript Object Notation Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 4180: Common Format and MIME Type for CSV Files](https://www.rfc-editor.org/rfc/rfc4180)
- [RFC 3339: Date and Time on the Internet](https://www.rfc-editor.org/rfc/rfc3339)
