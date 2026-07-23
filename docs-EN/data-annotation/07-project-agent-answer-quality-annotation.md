---
title: "Project: Agent Answer-Quality Annotation"
tags:
  - ai-agent-engineer
  - data-annotation
  - project
aliases:
  - Agent Answer Annotation Project
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Cohen 1960 original kappa paper
  - Python 3 json and unittest documentation
  - W3C PROV-O
lang: en
translation_key: 数据标注/07-项目-Agent回答质量标注.md
translation_source_hash: 3ae39e7f9095644e2aefd202fa74bd7fff8ef6d003ee720837fac7fbe90025e6
translation_route: zh-CN/数据标注/07-项目-Agent回答质量标注
translation_default_route: zh-CN/数据标注/07-项目-Agent回答质量标注
---

# Project: Agent Answer-Quality Annotation

## Goal and boundary

Use the fixed two-annotator initial labels in [[data-annotation/examples/sample_annotations.jsonl|sample_annotations.jsonl]] to calculate percent agreement, Cohen’s kappa, confusion counts, and a conflict list. Then turn conflicts into a plan for the guideline additions and adjudication work that are needed. [[data-annotation/examples/audit_annotations.py|audit_annotations.py]] first validates JSONL, input snapshots, contract versions, and whole-batch pairing. [[data-annotation/examples/test_audit_annotations.py|test_audit_annotations.py]] covers 12 normal and failure behaviors.

The example content is entirely fictional: it contains only anonymous IDs, versions, and short fictional evidence. It makes no network request, reads no real log, and calls no model. It is a **teaching auditor for two-annotator nominal labels**, not an annotation platform, adjudication system, privacy or licensing reviewer, or production-release tool.

## Environment and execution

Run from the repository root in Windows PowerShell. Keep the environment outside the vault; the scripts read input only and generate no data files:

~~~powershell
$exampleDir = (Resolve-Path '.\docs-EN\data-annotation\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\annotation-audit'
$python = Join-Path $venv 'Scripts\python.exe'

py -3.11 -m venv $venv
& $python --version
& $python -B (Join-Path $exampleDir 'audit_annotations.py') (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -O -B (Join-Path $exampleDir 'audit_annotations.py') (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -O -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
~~~

The project depends only on the Python 3.11+ standard library. -B prevents __pycache__ generation; -O verifies that critical contract checks do not depend on bare assert statements that optimization removes; -W error turns unexpected warnings into failures.

## Input contract

Each line must be a standard JSON object with no duplicate keys and no NaN or Infinity. The example requires these nonempty strings:

| Field | Purpose | Scope validated by this project |
| --- | --- | --- |
| annotation_id | Unique identifier for an appended initial-annotation event | Must be unique across the JSONL |
| sample_id | Logical sample | Exactly one record for each of two fixed annotators |
| source_revision | Fictional input version actually visible to the annotator | The two records for one sample_id must match |
| data_version | Data snapshot for this batch | Unique across the whole batch |
| guideline_version | Decision rules | Unique across the whole batch |
| label_set_version | Label ontology | Unique across the whole batch |
| task_config_version | UI or schema contract | Unique across the whole batch |
| annotator | Anonymous annotator role | Exactly two across the whole batch |
| label | helpful, not_helpful, unsafe, cannot_judge, or exclude | Enumeration validation |
| evidence | Short evidence for this initial annotation | Only nonemptiness is validated; factuality is not evaluated |
| created_at | Time of the initial annotation | Only the UTC, second-level teaching format YYYY-MM-DDTHH:MM:SSZ is accepted |

source_revision is only input traceability. It does not prove that content was authorized, contains no personal information, or received the correct label. The example intentionally refuses arbitrary extension fields so contract drift is visible during teaching. A real system can add assignment, access, model-suggestion, review, and adjudication fields in a versioned schema rather than inserting them into initial annotation records and overwriting history.

## Expected result and hand calculation

The sample has 8 sample_id values. Each has independent annotations from ann-a and ann-b on the same source_revision, and every record uses data_version=v1, guideline_version=1.0, label_set_version=1.0, and task_config_version=agent-answer-v1:

- Six match, so $p_o=6/8=0.75$.
- The helpful, not_helpful, and unsafe counts are 4/2/2 for A and 3/4/1 for B.
- $p_e=(4/8)(3/8)+(2/8)(4/8)+(2/8)(1/8)=22/64=0.34375$.
- $\kappa=(0.75-0.34375)/(1-0.34375)=13/21\approx0.619$.
- The conflicts are s-003 (demo-s-003-r1): unsafe ↔ not_helpful and s-005 (demo-s-005-r1): helpful ↔ not_helpful.

This result describes agreement between two nominal-label annotators on eight fictional samples only. It does not prove the guideline is correct, samples represent an online distribution, final_label exists, licensing or privacy has passed, or any real system meets a quality threshold.

## This round’s verification

> [!success] Verified 2026-07-22
> python -B -W error -m unittest discover and python -O -B -W error -m unittest discover both passed all 12 tests. CLI output in normal and -O modes is identical. Tests use temporary directories and leave no cache or data artifact inside the project.

Tests cover the sample contract and pairs, hand-calculated metrics, conflicts and confusion, kappa=undefined for perfect agreement on a constant label, duplicate or missing annotators, a third annotator, mixed data, label, or UI versions, unknown labels, duplicate annotation_id values, mismatched input snapshots, missing traceability fields, empty evidence, non-UTC timestamps, unknown fields, invalid or duplicate-key JSON, nonstandard constants, empty pairs, and CLI context.

## Project steps

1. Read the JSONL first. Confirm that every sample_id has ann-a and ann-b records, then compare source_revision and contract versions.
2. Run the normal and -O CLIs. Record observed agreement, expected agreement, kappa, confusion, and conflicts.
3. For each conflict, state which current guideline rule or evidence is missing. Do not arbitrarily choose between people. Design an appended adjudication record with a rule citation, adjudicator role, and final_label.
4. Add five **fictional** samples and two independent answers for each. Each pair uses the same new source_revision; do not change historical records for existing samples.
5. Design a release manifest covering purpose, input scope, split, versions, quality gates, access scope, and known limitations. Then explain why this teaching batch cannot be released directly as an evaluation set.

For the full adjudication, release, and online-candidate boundary, see [[data-annotation/09-versioning-release-and-production-feedback|Versioning, Release, and Production Feedback]]. Before sensitive or real content enters a task, complete [[data-annotation/08-data-governance-privacy-licensing-and-worker-safety|the governance review]].

## Acceptance criteria

- [ ] I can explain how the script pairs records by sample_id and rejects a pseudo-pair where two annotators saw different source_revision values.
- [ ] I can calculate observed agreement, expected agreement, and kappa by hand and explain why none equals correctness or representativeness.
- [ ] I can propose at least one guideline revision, one sampling improvement, and one appended adjudication record.
- [ ] I can list the artifacts a production system must still add between annotation_id and release_id.
- [ ] I do not treat fictional-example results as conclusions about a real system’s quality, licensing, privacy, or worker safety.

## Self-test

1. Why cannot two labels with the same sample_id but different source_revision values yield meaningful agreement?
2. Why can kappa and percent agreement differ markedly under severe class imbalance?
3. If annotators see a model suggestion and agreement rises, is that necessarily good?
4. If a source is withdrawn, which releases and downstream uses require querying, and why can you not simply say that the model has forgotten?

Completion means you can run the audit, explain every value, locate conflicts, and turn them into an actionable guideline, adjudication, and release plan.

Return to the [[data-annotation/00-index|Data Annotation Index]].

## References

Sources checked on 2026-07-22.

- Cohen, J. (1960). [A coefficient of agreement for nominal scales](https://doi.org/10.1177/001316446002000104)
- [Python json](https://docs.python.org/3/library/json.html) and [Python unittest](https://docs.python.org/3/library/unittest.html)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
