---
title: "Filtering, Deduplication, and Group-Level Splits"
aliases:
  - Synthetic Data Filtering and Deduplication
  - Synthetic Data Cleaning
tags:
  - synthetic-data
  - deduplication
  - data-splits
source_checked: 2026-07-14
lang: en
translation_key: "数据合成/02-方法与质量/04-过滤去重与组级划分.md"
translation_source_hash: 50ed9ab9ff78c2898e3b5161b1aa8692d6faeed217fd1fd095c19a279c61da86
translation_route: zh-CN/数据合成/02-方法与质量/04-过滤去重与组级划分
translation_default_route: zh-CN/数据合成/02-方法与质量/04-过滤去重与组级划分
---

# Filtering, Deduplication, and Group-Level Splits

## Objective

Build an auditable quarantine → validate → filter → deduplicate → group → split process. Prevent low-quality records, duplicates, and common-origin variants from entering independent tests.

## Intuition

Raw generator output is a candidate pool, not a finished dataset. A structurally correct sample can still contain a contradictory answer, and two different sentences can be rewrites of one template. Cleaning must retain rejection reason and source, or quality loss and reruns cannot be understood.

## Core concepts

- **Quarantine** — an isolation area for raw candidates; nothing enters the formal dataset before passing gates.
- **Schema validation** — checks fields, types, enums, and formats.
- **Semantic validation** — rules, simulators, or people verify that task and label hold.
- **Exact / normalized duplicate** — text is identical before or after declared normalization.
- **Near duplicate** — lexically or semantically very similar, but not exact.
- **Family grouping** — group variants from one template, original event, document, or rewrite chain.
- **Rejection log** — sample ID, rule, reason, processing version, and review status.

## Deduplication is not a boolean switch

Build candidate pairs from low to high cost: stable-ID/source duplicates, normalized exact hashes, character/token n-grams, edit distance, Embedding neighbors, then rules or human decisions. Similarity only proposes a possible common origin; it cannot decide which sample is correct. Calibrate thresholds on labeled duplicate/nonduplicate pairs and inspect by language and task slice.

Deduplication unit also depends on purpose. In training, repeats alter weight; in evaluation, common-origin variants inflate evidence; RAG questions can share origin through source document or answer leakage. Report row count, family count, condition-cell count, and rejection rate together so a dataset does not claim the same effective scale after deleting many rewrites.

## Method

1. Append-only store raw output with stable candidate ID and provenance.
2. Apply parsing/Schema gates first; log errors rather than silently filling defaults.
3. Check business invariants, label verifiability, sensitive content, and prohibited actions.
4. Normalize whitespace, case, and known equivalent formats, then exact-hash deduplicate.
5. Inspect near duplicates across the full candidate pool with n-gram/MinHash, edit distance, Embedding retrieval, or human review.
6. Set a family ID for remaining samples. Similarity alone does not justify deletion; decide whether meaningful condition variation remains.
7. Split train/dev/test by family, with one group on one side only.
8. Emit input count, rejection count, reason, and version for every gate, retaining a replayable manifest.

Determine the true generation unit before splitting: one user/session, document, template, original incident, code repository, or time window can be a family. If a synthesizer rewrites a prompt from a test answer, different generated text is still test contamination. Quarantine or mark uncertain samples whose lineage cannot be determined; a hash cannot prove no leakage.

## Example

These three belong to one family, not three independent test evidence points:

```text
"Look up A-1 for me."
"Please check order A-1."
"Where is order A-1?"
```

If the second adds a `tool-timeout` environmental condition, it may be worth retaining while still sharing a family. All three must stay on one side of a dev/test split. A deduplication key must not include a model-generated answer, or the same input with two conflicting answers is falsely treated as two tasks.

## Common mistakes and diagnosis

- **Deduplicate inside each split only.** Leakage remains across splits; audit global similarity first and split by family.
- **One near-duplicate threshold for everything.** It can delete important boundaries; sample borderline pairs and record decisions.
- **Keep anything a model judge passes.** Add deterministic rules and human calibration.
- **Delete rejected samples outright.** You lose generator-quality evidence; preserve a log but keep it out of the release set.
- **Random line-level split.** Variants cross sets; split by group/family ID.

## Exercises

1. Write five Schema/business gates for JSON tool-call samples.
2. Design a text-normalization function and name two semantic differences it must not normalize away.
3. Design a family ID for multiple chunks and multi-turn Q&A from one document.

## Self-check

1. Must every near duplicate lose one member? No. Retain a variant covering a distinct critical condition, but prevent cross-split leakage and duplicate weighting.
2. Does deduplication change distribution? Yes; report before/after slice statistics.
3. Is it safe to split before generating rewrites? Only if each rewrite is rigorously constrained to its original family's same split and lineage is retained.

## Summary and next step

Filtering and deduplication turn generation volume into auditable valid candidates, while group-level split protects independence. Next, use [[data-synthesis/methods-and-quality/05-quality-utility-and-real-data-calibration|Quality, Utility, and Real-Data Calibration]] to decide whether the data is useful.

## References

- [Deduplicating Training Data Makes Language Models Better original paper](https://aclanthology.org/2022.acl-long.577/) — accessed 2026-07-14.
- [SELF-INSTRUCT original paper](https://aclanthology.org/2023.acl-long.754/) — accessed 2026-07-14.
- [NIST AI 600-1: cross-contamination of training and TEVV data](https://doi.org/10.6028/NIST.AI.600-1) — accessed 2026-07-14.
