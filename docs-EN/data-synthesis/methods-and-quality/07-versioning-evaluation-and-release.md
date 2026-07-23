---
title: "Versioning, Evaluation, and Release"
aliases:
  - Synthetic Dataset Versioning
  - Data Card and Release
tags:
  - synthetic-data
  - versioning
  - Data-Card
source_checked: 2026-07-22
lang: en
translation_key: "数据合成/02-方法与质量/07-版本评测与发布.md"
translation_source_hash: da13becf21c775f7d0258eb8c4b6d2e85ab5af4fefcc7123198e58602fee61b2
translation_route: zh-CN/数据合成/02-方法与质量/07-版本评测与发布
translation_default_route: zh-CN/数据合成/02-方法与质量/07-版本评测与发布
---

# Versioning, Evaluation, and Release

## Objective

Manage a synthetic dataset lifecycle through immutable raw candidates, lineage, content fingerprints, semantic versioning, Data Cards, and release gates.

## Intuition

If generator, prompt, or filter changes while the file remains `dataset-final.json`, old results cannot be explained. Versioning is not adding a date to a filename: it lets every sample and evaluation trace back through its generation and processing chain.

## Core concepts

- **Lineage** — processing relationships from source through generation, filtering, review, and release.
- **Immutable raw** — raw candidates are append-only and never overwritten in place.
- **Manifest** — data files, Schema, counts, hashes, splits, and generation configuration.
- **Semantic versioning** — major/minor/patch compatibility levels; a dataset must define what changes belong to each.
- **Content fingerprint** — normalized-content hash used to establish content identity.
- **Data Card / datasheet** — user-facing purpose, source, composition, processing, risk, maintenance, and limitation documentation.
- **Release gate** — quality, privacy, license, reproduction, and approval checks required before release.

## Release package, not one data file

A minimal release package contains immutable data file, Schema, manifest, Data Card, rejection/audit summary, generator/filter versions, split mapping, quality/utility/risk report, changelog, and license/access statement. It also needs source-to-derived mapping plus source/authorization/privacy-review state and evidence reference for each release scope. Those references point to controlled artifacts; do not leak credentials, raw candidates, or sensitive audit evidence merely to make a package look complete.

Release decisions need priority. Unknown source/authorization, a critical-label error, or privacy hard-gate failure should `BLOCK` first. Duplicate rate, coverage, real-holdout utility, and small-slice issues can enter `REVIEW` under frozen policy. Publish only if every hard gate passes. A hash proves input bytes match prior bytes; it does not prove source truth, quality, or valid approval.

## Method

1. Store raw candidates, processed dataset, rejection log, and report separately.
2. Retain candidate ID, family, generator, prompt/template, seed, and processing version per sample.
3. Record Schema, condition matrix, split, count, content hash, and dependency version in the manifest.
4. Define version policy, for example: correct label = patch, add compatible samples = minor, change Schema/task meaning = major.
5. Repeat Schema, deduplication, slice-quality, real-holdout utility, privacy, and license review for a new version.
6. Use a Data Card for motivation, source, generation, filtering, composition, intended/prohibited uses, risk, access, and maintainer.
7. Publish changelog and migration guidance. Do not automatically compare old Benchmark results with a new major version.
8. Set a procedure for withdrawal, correction, deletion request, and end of maintenance.

Maintenance triggers include generator/model-alias change, prompt/template revision, discovered contamination/leakage, real-distribution drift, changed label rule, license/policy change, and feedback from a newly affected group. First decide whether semantics or comparison boundary changed, then choose patch/minor/major. Do not conceal a discontinuity merely to keep a leaderboard continuous.

## Withdrawal, correction, and deletion-request runbook

Withdrawal is not “delete the newest file.” When a source, permission, privacy, or label problem appears:

1. Stop new downloads, indexing, training, or evaluation consumption; mark the affected release `withdrawn`, `under-review`, or equivalent. Do not silently replace the same version.
2. Use the source-to-derived mapping to find candidates, released records, family/split, vector index/cache, training/evaluation inputs, leaderboards, and derived reports.
3. Preserve necessary controlled audit evidence; delete/quarantine/revoke access, rebuild affected indexes and packages, and rerun quality/utility gates.
4. Publish a new version and change/withdrawal notice with a comparison break. Historic results may remain as evidence with status but cannot remain current-data conclusions.
5. Record owner, time, impact range, copies not fully removed, and follow-up checks. Responsible personnel determine legal/contract/regulatory deadlines; engineering process does not replace their decision.

When a dataset supports one model or Agent release, its version cannot replace the runtime release identity. Use `release_id` to bind suite/dataset/rubric/grader/harness versions, per-case results, and approval status, then write `release_id` into the evidence report. See the Evaluation Framework's [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]] for direction and terminology.

## Example

A minimal manifest:

```json
{
  "dataset_id": "order-agent-synthetic-eval",
  "version": "1.0.0",
  "schema_version": "1",
  "generator": {
    "type": "template",
    "version": "template-pipeline-1.0.0",
    "seed": 13
  },
  "release_scope": "offline-teaching-only",
  "source_declaration": "author-designed fictional templates; no external or real records",
  "counts": {"raw": 14, "released": 12},
  "splits": {"dev": 4, "test": 8},
  "fingerprint": "sha256:...",
  "source_checked": "2026-07-14"
}
```

This is an extended manifest for a releasable dataset. The [[data-synthesis/project-and-self-check/08-project-offline-synthetic-evaluation-data-pipeline|offline teaching project]] deliberately emits only the minimal `generator` declaration its template requires and explicitly does not claim authorization, privacy, or public-release eligibility. Treating a teaching fixture's `contains_real_data: false` as the complete review record above is wrong.

A changed hash shows content is different; it cannot say that the difference is justified. Read the changelog and repeat evaluation.

## Common mistakes and diagnosis

- **Version only final JSON.** Version generator, prompt/template, filter, and Schema too.
- **Correct label without a version bump.** Old results are no longer reproducible; publish a patch and change list.
- **Data Card lists only strengths.** It must state non-goals, gaps, risk, and unverified items.
- **Reshuffle splits on every export.** Fix family → split mapping to prevent evaluation drift.
- **No owner after public release.** Assign owner, update triggers, and retirement date/condition.

## Exercises

1. Define major/minor/patch rules for a dataset.
2. Write a ten-field Data Card checklist.
3. Design approval from a real failure becoming a new synthetic family through releasing a minor version.

## Self-check

1. Is one version number with different hash acceptable? Unless a clear immutability exception exists, it is a version-discipline problem.
2. Can a fixed seed replace a manifest? No. It does not include code, template, source, or processing chain.
3. Can old scores be compared directly after new samples? Only if protocol defines compatibility and results rerun on the same frozen version; data from different versions is not the same measurement.

## Summary and next step

Versioning turns synthetic data into a replayable, auditable, withdrawable engineering asset. Finish with [[data-synthesis/project-and-self-check/08-project-offline-synthetic-evaluation-data-pipeline|Offline Synthetic Evaluation Data Pipeline]], which turns contract, filtering, coverage, split, hash, and limitations into code.

## References

- [Data Cards original paper and official page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/) — accessed 2026-07-22.
- [Google Data Cards Playbook](https://sites.research.google/datacardsplaybook/) — accessed 2026-07-22.
- [Datasheets for Datasets original paper](https://arxiv.org/abs/1803.09010) — accessed 2026-07-22.
- [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1) — accessed 2026-07-22.
