---
title: "Image-Generation Cost, Reproducibility, and Troubleshooting"
tags:
  - image-generation
  - cost
  - reproducibility
  - troubleshooting
aliases:
  - Image-generation production checks
source_checked: 2026-07-22
lang: en
translation_key: 图像生成/02-工程与质量/08-成本复现与故障排查.md
translation_source_hash: fdc561e32d36098e685b865c22413a5d240d5cacaf2157cee0528a9c841bfc60
translation_route: zh-CN/图像生成/02-工程与质量/08-成本复现与故障排查
translation_default_route: zh-CN/图像生成/02-工程与质量/08-成本复现与故障排查
---

# Cost, Reproducibility, and Troubleshooting

## Goal of this lesson

Treat every attempt as a budgeted, recorded experiment. Distinguish requirement, policy, provider, transport, and quality problems.

## Cost is more than the price of one image

Total cost includes at least request count, candidates per request, size/quality tier, edit rounds, failed retries, storage and transport, human review, and post-production. Provider pricing changes, so this course does not hard-code prices. At runtime, read unit cost from official pricing pages or billing data, and set `max_attempts`, `max_outputs`, and budget thresholds requiring human confirmation at the task layer.

Validate layout and subject at low cost first; raise resolution or quality only after confirming direction. Separate “creative exploration” from “production rendering” queues so every draft does not use the highest specification. Report total attempts required to deliver a successful image, not only the final request.

## Reproduction record

Retain: original structured requirement and `source_revision`; normalized prompt; negative/prohibited items; input `asset_id` and hash; summary of object-level authorization/ACL decision; adapter version; provider and model response identifier; every explicit parameter; seed if supported; request time; `transform_id`; output hash; post-production steps; human selection rationale; `release_id`; revocation/deletion propagation status; and documentation-check date. Keys, complete face input, and sensitive prompts never enter ordinary logs.

Normalize the request object as JSON and compute SHA-256 to determine whether the same task was actually sent. Even with the same request hash, cloud output can differ because of a model update or nondeterministic implementation. The aim of a reproduction record is to **explain differences**, not promise byte-for-byte identity.

## Layered diagnosis

1. **Requirement error**: contradictory constraints, unclear use, or unclear ratio; return to task layer.
2. **Policy refusal**: object-level authorization/ACL, rights, safety, or person rules; record refusal category and do not retry around it. Failed revocation/deletion propagation belongs here too, not under network failure.
3. **Parameter error**: adapter capability is stale; refresh official documentation and capability probe.
4. **Transient failure**: timeout, 429, or 5xx; retry with bounded backoff and check whether the job already exists.
5. **Damaged output**: MIME, length, hash, or decode failure; quarantine the file and download it once again.
6. **Unacceptable quality**: use failure tags to change prompt, split task, or move to post-production; do not confuse this with network retry.

## Stop rules

For example: pause after the same failure tag appears three times in succession; hand off to a person at maximum attempts or budget; stop immediately on safety/rights/ACL failure; pause all processing associated with `transform_id` and `release_id` after revocation; and begin a new experiment only after changing exactly one variable. Stop rules prevent an Agent from entering a “maybe one more sample will be better” loop.

## Exercise and self-check

Design a table for six image experiments with a unique task hash, one-variable change, failure tag, candidate count, and human decision. Why should you query job state before retrying after a request timeout?

Finally complete [[image-generation/03-project-and-self-assessment/09-project-image-generation-task-audit|the Offline Task Audit Project]].

## References

- [OpenAI Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) (interface and output options change over time; checked 2026-07-22)
- [[runtime-monitoring/00-index|Runtime Monitoring]]
