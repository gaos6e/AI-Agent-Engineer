---
title: "Differential Privacy Intuition and Budget"
aliases:
  - Differential Privacy Budget
  - DP privacy budget
tags:
  - privacy
  - differential-privacy
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 隐私计算/01-基础与风险/02-差分隐私直觉与预算.md
translation_source_hash: 94a6004ec7452c4918dc2a8f5cd4ec588b2af7b0ad5c67959cdc6c46179c637b
translation_route: zh-CN/隐私计算/01-基础与风险/02-差分隐私直觉与预算
translation_default_route: zh-CN/隐私计算/01-基础与风险/02-差分隐私直觉与预算
---

# Differential Privacy Intuition and Budget

## Goal of this lesson

Explain $(ε, δ)$-differential privacy with neighboring datasets, understand contribution bounds, sensitivity, noise, and composition; maintain a cross-release budget ledger; and distinguish mathematical definition, mechanism implementation, system configuration, and evidence from a real release.

## Intuition: output should look similar with or without one person

Let `D` and `D'` be neighboring datasets that differ in only one subject. For every output set `S`, a randomized mechanism `M` satisfies:

$$
\Pr[M(D)\in S] \le e^{\varepsilon}\Pr[M(D')\in S] + \delta
$$

Intuitively, after observing the output, an attacker should not be able to easily determine whether that subject participated. `ε` controls the multiplicative difference between output distributions; `δ` permits additive relaxation relative to a pure `ε` guarantee. `δ=0` is a valid case of pure differential privacy. A smaller ε generally means a stronger guarantee and more noise, but neither ε nor δ is an “anonymity percentage” or a compliance score independent of subject scope, adjacency, mechanism, and composition.

## The first step is not choosing ε; it is defining adjacency

“One-row difference” can treat an event as the subject. If one person contributes a thousand rows, the protection is misdescribed. Common semantics add or remove all records for one person, or replace one person's records. State the subject scope, time window, and contribution bound: how many events each person can contribute and the range to which each value is clipped.

Query sensitivity describes the maximum result change between neighboring datasets. A count has sensitivity 1 when each person contributes at most 1; if a person can contribute 20 times, unbounded sensitivity is at least larger. Real mechanisms, sampling, accounting, and proofs can be more complex. This lesson does not replace expert review.

## Mechanisms, post-processing, and bypasses

Mechanisms such as Laplace and Gaussian add randomness according to sensitivity and parameters. Post-process output already produced by a DP mechanism without accessing raw data and you do not add privacy loss. But re-querying raw data, correcting output with a non-DP small-group statistic, leaking a random seed or intermediate value, and similar actions bypass the guarantee.

“We added noise” is not enough to demonstrate DP. Confirm adjacency, contribution clipping, mechanism formula, randomness implementation, parameters, numerical stability, accounting, concurrency, failed retries, caches, and every release channel.

## Privacy budget and composition

Multiple releases compose. The most conservative basic composition can add ε and δ separately. More advanced accounting can give tighter bounds, but must record the theorem or implementation used and its conditions. A minimum budget ledger includes:

- subject scope, adjacency definition, and contribution bound;
- data, query, mechanism, and software version;
- release ID, ε, δ, accounting method, and approval for every release;
- spent, reserved, canceled, and remaining budget;
- operator, time, output location, and whether a failure or retry consumed budget; and
- responsible owner, frozen cap, and action on overrun.

Reserve budget atomically so two concurrent requests cannot both see a remaining balance. Whether tuning, dashboard refreshes, grouped queries, A/B output, or experimental reruns consume budget depends on whether they access private data again and on mechanism design; do not assume they are free.

## Utility and fairness

Strong noise increases error, often disproportionately for small groups, long-tail categories, and high-dimensional slices. Do not report average accuracy alone. Report bias, variance, confidence intervals or stability across repeated runs, subgroup utility, and changes in ranking or decisions. When a group has few samples, noise can reduce service quality for that group; privacy guarantees and fairness outcomes are different dimensions.

## Four layers of evidence

1. **Definition layer**: what are subject and adjacency, and for whom does the protection claim hold?
2. **Mechanism layer**: are sensitivity, clipping, randomized mechanism, ε/δ, and accounting correct?
3. **Implementation layer**: do code, randomness, numerics, concurrency, errors, and tests follow the design?
4. **System layer**: are every bypass output, cache, log, access path, and budget gate controlled?

NIST SP 800-226 uses a multi-layer “DP pyramid” and privacy harms to assess the gap from mathematics to software. It is not a checklist for choosing one universal production parameter.

## Common misconceptions

- Claiming safety because ε is small without defining adjacency or contribution bounds.
- Letting each team view its own budget and ignoring composition across products for the same subject or dataset.
- Conflating training-time DP with every privacy issue in inference prompts, RAG, logs, and model output.
- Slicing DP output without limit or “correcting” it with raw data while claiming free post-processing.
- Reporting only average utility, not small groups, random variation, or budget use.

## Exercise and self-check

For “total monthly usage, regional groups, and quarterly trend” on one monthly dataset, write a budget ledger. Define add/remove-one-person adjacency and each person's contribution bound, use basic composition to calculate total ε/δ, then cancel one release and explain whether it was already consumed. Do not choose a production threshold yourself.

- [ ] Can explain adjacency, ε, δ, sensitivity, and contribution clipping with both formula and intuition.
- [ ] Can explain when post-processing is free and when it secretly accesses private data again.
- [ ] Can maintain one coherent budget ledger across releases, concurrency, failures, and retries.
- [ ] Can distinguish a mathematical claim, implementation evidence, system bypasses, and utility results.

## Next step

When data are held by several parties, continue with [[privacy-computing/01-foundations-and-risks/03-federated-learning-and-secure-aggregation|Federated Learning and Secure Aggregation]].

## References

- [NIST SP 800-226: Guidelines for Evaluating Differential Privacy Guarantees](https://csrc.nist.gov/pubs/sp/800/226/final) (final, March 2025; accessed 2026-07-21)
- [NIST SP 800-226 DOI](https://doi.org/10.6028/NIST.SP.800-226)
