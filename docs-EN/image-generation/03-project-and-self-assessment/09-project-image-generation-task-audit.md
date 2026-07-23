---
title: "Project: Image Generation Task Audit"
tags:
  - image-generation
  - project
  - python
aliases:
  - Image task-manifest project
source_checked: 2026-07-22
lang: en
translation_key: 图像生成/03-项目与自测/09-项目：图像生成任务审计.md
translation_source_hash: c2c39760a8cabd9bfe2077a8ce700b066042533b4f36cf9af69a6d847afae384
translation_route: zh-CN/图像生成/03-项目与自测/09-项目：图像生成任务审计
translation_default_route: zh-CN/图像生成/03-项目与自测/09-项目：图像生成任务审计
---

# Project: Image Generation Task Audit

## Project goal

Before calling any generation model, audit a task manifest with the Python standard library. The project validates task type, canvas ratio, prompt elements, risk gates, acceptance dimensions, budget, reproduction plan, and source/release governance. It does not access the network, require a key, generate images, or read images.

## Files

- [[image-generation/03-project-and-self-assessment/examples/image_task_plan.json|image_task_plan.json]]: a teaching cover-task fixture explicitly declared offline, provider-free, and without model execution.
- [[image-generation/03-project-and-self-assessment/examples/audit_image_plan.py|audit_image_plan.py]]: the command-line auditor.
- [[image-generation/03-project-and-self-assessment/examples/test_audit_image_plan.py|test_audit_image_plan.py]]: basic tests for a valid plan, invalid ratio, and missing rights.
- [[image-generation/03-project-and-self-assessment/examples/test_contract_and_cli.py|test_contract_and_cli.py]]: regression tests for strict JSON, closed fields, asset revisions, object-level ACL, revocation/deletion propagation, evidence boundary, policy, hashes, and CLI.

## Run it

In PowerShell 7, enter the examples directory from the project root that contains both `docs-EN/` and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\image-generation\03-project-and-self-assessment\examples'
python -B .\audit_image_plan.py .\image_task_plan.json
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
```

On success, the auditor prints a task summary and returns exit code `0`. When the structural contract is valid but rights, ratio, asset role, ACL, deletion propagation, evidence boundary, budget, or acceptance gates fail, it returns `1`. File, UTF-8, strict-JSON, or closed-field contract errors return `2`. `-B` prevents Python from creating `.pyc` caches. The current suite has **90 tests**, all of which should pass in three modes.

Strict JSON rejects duplicate keys and `NaN`/`Infinity`. If a reference asset exists, record its `asset_id`, `source_revision`, role, source reference, SHA-256, rights reference, and `acl_reference`. `image_to_image`, `variation`, and `outpainting` need `source_image`; `inpainting` also needs `mask`. Top-level `lineage` fixes the requirement version, execution `transform_id`, and candidate `release_id`. `governance` requires object-level authorization/ACL before scoring, a revocation/deletion propagation plan, and limits factual publication to `evidence_supported`. This is a teaching business contract, not a provider API mirror.

## Experiments to modify

1. Change `rights_confirmed` to `false` and observe the hard-gate error.
2. Change width to `1000` while retaining `4:5` and observe ratio-consistency validation.
3. Remove the `safety` dimension from `acceptance` to see why a total score cannot replace a safety threshold.
4. Copy the fixture and design an inpainting task. Add two anonymous asset records, `source_image` and `mask`, with `asset_id`, `source_revision`, `acl_reference`, hash, and rights reference. State the protected area in prompt composition/prohibitions; do not pretend the generic schema covers every provider edit parameter.
5. Set `object_acl_required` to `false` and observe why the auditor rejects the task before any scoring.
6. Change `evidence_policy` to another value and explain why a generated image, hash, or Content Credential cannot independently support factual publication.

## Project acceptance

- [ ] A purpose, audience, task type, and structured prompt exist.
- [ ] Output specifications agree internally and candidates/attempts are bounded.
- [ ] Reference-asset rights, human review, and provenance plan are explicit fields.
- [ ] `source_revision`, `transform_id`, and `release_id` distinguish requirement, transform, and publication candidate; object-level ACL and revocation/deletion propagation have explicit plans.
- [ ] The factual-publication boundary is `evidence_supported`, not generated output treated as external factual evidence.
- [ ] Acceptance covers prompt adherence, composition, text, visual quality, safety, and rights.
- [ ] No API key, real-person asset, specific price, or model weight occurs.
- [ ] A valid fixture returns `0`, policy failure returns `1`, and contract failure returns `2`.
- [ ] All 90 tests pass in normal, `-O`, and warnings-as-errors modes.

## Comprehensive self-check

1. Why does the auditor validate only “plan completeness,” not output safety or quality?
2. Which fields are stable business semantics, and which should remain in a provider adapter?
3. How would an Agent use the audit result: continue, ask for information, or refuse?
4. If a provider does not support a seed, what should a reproduction record still retain?

## References

- [[image-generation/02-engineering-and-quality/05-workflows-and-api-boundaries|Workflows and API Boundaries]]
- [[image-generation/02-engineering-and-quality/07-safety-copyright-and-content-credentials|Safety, Copyright, and Content Credentials]]
