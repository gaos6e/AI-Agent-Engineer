---
title: "Privacy, Memorization, Bias, and Copyright"
aliases:
  - Synthetic Data Risks
  - Privacy, Memorization, Bias, and Copyright
tags:
  - synthetic-data
  - privacy
  - bias
  - copyright
source_checked: 2026-07-22
lang: en
translation_key: "数据合成/02-方法与质量/06-隐私记忆偏差与版权.md"
translation_source_hash: 12cf4f325399b6351fdd2532f9210a544773c3f9e94535969482f4ce7fa8ada4
translation_route: zh-CN/数据合成/02-方法与质量/06-隐私记忆偏差与版权
translation_default_route: zh-CN/数据合成/02-方法与质量/06-隐私记忆偏差与版权
---

# Privacy, Memorization, Bias, and Copyright

## Objective

Recognize risks synthetic data introduces for privacy, training memorization, group bias, intellectual property, and content source, then choose controls and human approval that match the claim.

## Intuition

A newly generated sentence is not necessarily created from nothing. A model can reproduce a training fragment, a statistical generator can retain a rare individual combination, and a prompt can contain real information directly. Generators can also inherit or amplify bias in source distributions and safety filters.

## Core concepts

- **Memorization** — a model retains and, in some conditions, reproduces a training instance or long fragment.
- **Re-identification / linkage** — combine apparently de-identified data with other information to link it to a person.
- **Differential privacy (DP)** — a formal framework quantifying the effect of adding/removing one record on an output distribution. A guarantee depends on definition, parameters, implementation, and composition accounting.
- **Privacy attack** — empirical risk test such as membership inference, attribute inference, record linkage, or similarity inspection.
- **Bias amplification** — a generated distribution worsens existing group differences, stereotyped patterns, or omissions.
- **Provenance and license** — source, authorization to use, derivative restrictions, and release conditions.
- **Synthetic-content transparency** — record origin, processing, and marking of generated content.

## Write the threat model before choosing a privacy metric

At minimum, state whom you protect, what an attacker can see in synthetic data/generator/statistical query, what auxiliary data the attacker may have, and the harm of failure. Membership inference, attribute inference, rare-combination linkage, and verbatim-memory probes answer different questions; one distance metric or PII regex cannot cover all. An empirical attack that finds no leak only says none was observed for that attack and sample—it is not a formal guarantee.

Differential privacy compares output distributions on adjacent datasets. Its guarantee depends on the adjacency definition, $(\varepsilon,\delta)$, privacy accountant, sampling assumptions, and implementation. DP synthetic data can still have poor utility, bias, or improper release; ordinary noise, sampling, or rewriting is not automatically DP. NIST SP 800-226 is a current authoritative guide for assessing these claims and implementation pitfalls, but a deployment still needs specialist review.

## Method

1. List every real dataset, prompt, retrieval corpus, and human example the generator touches, grouped by sensitivity.
2. Minimize input before generation; use fictional identifiers and never put real credentials or personal information into prompts.
3. Check output against exact/near training matches, rare combinations, and sensitive patterns.
4. If claiming differential privacy, record adjacency definition, privacy parameters, accounting, implementation version, and independent review; do not equate “add noise” with DP.
5. Check coverage, error, and refusal rate by group, language, and intersectional slice. Bias review needs relevant domain and affected-party participation.
6. Verify license, contract, and policy for every input, model service, and output; do not assume generation erases copyright.
7. For high-risk or public release, apply access control, Data Card, approval, deletion/response process, and continuous monitoring.

Copyright and contractual issues cannot be settled by a similarity threshold. Engineering should retain source class, authorization basis, model/service-term version, derivative/republication status, filtering, and human decision; qualified personnel make the legal conclusion. Where rights are unclear, restrict access, pause release, and record the pending question rather than treating “model generated” as the end of source inquiry.

## Source-to-derived-artifact graph and withdrawal readiness

Risk review must reach concrete artifacts. Give each input source or controlled prompt a stable `source_lineage_id`, version, access scope, processing purpose, evidence reference, and retention class; give each generation a `generation_run_id`; connect these to candidates, filter decisions, family/split, release package, index/cache, and downstream evaluation report. This graph shows which versions a source correction, permission change, or deletion request affects. It does not decide whether rights are valid.

“No real data has currently been observed” and “source, rights, and privacy were reviewed” are different states. The first can be a factual declaration for a fictional teaching fixture. The second needs controlled evidence matching release scope. Missing lineage, untraceable source, or pending review requires candidate quarantine or a block on wider release; hashes, deduplication, and PII regex cannot upgrade it to public data.

`source_lineage_id` is an abstract cross-data-engineering reference. It does not replace RAG's precise identity contract for tenant, document, source sequence, revision, generation, ACL, and tombstone. A synthetic case that cites real knowledge must map verifiably to that concrete identity, not a free-text URL; see [[rag/09-project-offline-provenance-from-source-to-citation|RAG's Offline Evidence Chain from Source to Citation]].

## Example

A risk statement must be specific:

```text
Confirmed: candidates are author-designed fictional templates; no real customer records were used.
Checked: normalized exact duplication, common personal-information patterns, and condition-slice coverage.
Not proved: absence of semantic similarity to every external corpus; no claim of differential privacy.
Engineering recommendation: if real logs are connected later, repeat authorization, minimization, privacy, and release review.
```

NIST notes that many ordinary synthetic techniques do not meet differential privacy or other formal privacy properties. NIST SP 800-226 guides assessment of DP guarantees and common implementation hazards; it does not replace professional audit for a specific system.

## Common mistakes and diagnosis

- **Synthetic means anonymous.** Trace real inputs and memorization/linkage risks first.
- **Removing names completes privacy work.** Quasi-identifier combinations can still link a person.
- **A model refuses sensitive content, so the system is safe.** Inspect prompts, output, cache, and downstream access.
- **Only average bias is checked.** Inspect small and intersecting groups and state uncertainty.
- **Open-source downloadable means unrestricted training/republication.** Check the specific license, source terms, and organization policy.
- **Deleting final JSON completes withdrawal.** Use the source-to-derived graph to locate packages, indexes, caches, training/evaluation inputs, and historic reports, then follow release policy.

## Exercises

1. Draw the privacy data flow: real log → prompt → generator → filter → release.
2. State separately what ordinary template synthesis and DP synthesis may and may not claim.
3. Design three group/language-slice risk checks for bilingual customer-support data.

## Self-check

1. Does output with no name prove it lacks personal information? No.
2. Does an unsuccessful empirical attack equal a formal privacy guarantee? No.
3. If a generator's terms allow API use, does that automatically allow publishing its output dataset? No. Review complete terms, input rights, and purpose.

## Summary and next step

Synthesis is part of a data-processing chain; it does not erase upstream rights and risks. Continue with [[data-synthesis/methods-and-quality/07-versioning-evaluation-and-release|Versioning, Evaluation, and Release]] to turn evidence and limits into maintainable artifacts.

## References

- [NIST SP 800-226: Guidelines for Evaluating Differential Privacy Guarantees](https://doi.org/10.6028/NIST.SP.800-226) — final 2025-03; accessed 2026-07-22.
- [NIST: Differentially Private Synthetic Data](https://www.nist.gov/blogs/cybersecurity-insights/differentially-private-synthetic-data) — accessed 2026-07-22.
- [NIST SP 800-188: De-Identifying Government Datasets](https://csrc.nist.gov/pubs/sp/800/188/final) — accessed 2026-07-22.
- [NIST AI 600-1: privacy, bias, and intellectual-property risk](https://doi.org/10.6028/NIST.AI.600-1) — accessed 2026-07-22.
