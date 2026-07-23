---
title: "Template and Programmatic Generation"
aliases:
  - Template Synthetic Data
  - Programmatic Generation
tags:
  - synthetic-data
  - templates
  - Python
source_checked: 2026-07-14
lang: en
translation_key: "数据合成/01-基础与设计/02-模板与程序化生成.md"
translation_source_hash: b500f79dfc3aeb2f8a53e977f513b06432ba8fd4a3b0bc5ac62fa3f4d0577089
translation_route: zh-CN/数据合成/01-基础与设计/02-模板与程序化生成
translation_default_route: zh-CN/数据合成/01-基础与设计/02-模板与程序化生成
---

# Template and Programmatic Generation

## Objective

Use factor matrices, templates, simulators, and fixed random seeds to create explainable candidate samples while retaining family and provenance correctly.

## Intuition

Templates are less natural than a generative model, but act like transparent test fixtures: the source condition of every variation, why the answer holds, and how to reproduce it are clear. For JSON, tool parameters, authorization boundaries, and state-machine tasks, programmatic generation is often the first choice.

## Core concepts

- **Factorial design** — systematically combine discrete factors and explicitly inspect coverage.
- **Template** — fill a fixed linguistic or structural form with controlled variables.
- **Simulator** — generate inputs, trajectory, and outcome from state/action rules.
- **Seed** — makes random sampling and permutation reproducible; it does not repair faulty logic.
- **Family ID** — marks variants of the same template/original event for group-level splitting.
- **Oracle** — expected answer/state from a rule or simulator.
- **Provenance record** — template version, variables, seed, code version, and generation time.

## Full combinations, constrained combinations, and sampling

Six factors with five values each already yield $5^6=15,625$ Cartesian cells before paraphrases. Remove impossible combinations through business rules first, then make high-risk interactions such as safety/authorization mandatory coverage. With limited resources, pairwise-style combinatorial testing can allocate budget inside a defined task space, but list uncovered higher-order interactions as gaps. Random sampling distributes budget within the stated task space; it does not design that space.

Templates, simulators, and property-based testing have distinct jobs. Templates control wording; simulators determine state transitions; properties verify invariants such as no unauthorized action, no duplicate payment, and reproducible terminal state. For Agent data, `input + expected_text` is often insufficient: retain initial state, permitted tools, expected terminal state, prohibited side effects, and reset method.

## Method

1. Select two to four critical factors from the data contract to avoid immediate combinatorial explosion.
2. Write a programmatically verifiable oracle for every combination.
3. Give every semantic family a few expression templates. Guarantee label correctness before expanding language variation.
4. Generate stable IDs and retain family, template ID, variables, and generator version.
5. Use a fixed seed only for ordering, sampling, or numeric perturbation, and record it in the manifest.
6. Run Schema, logical-invariant, and prohibited-value checks.
7. Review at least one sample in every condition cell, not a random overall sample alone.

Do not make random ordering identity. A stable ID should derive from normalized family, template, and variables; seed only determines sampling/split. Then a reordering still identifies the same candidate and makes content changes clearly require a new version.

## Example

Three factors for order lookup:

```text
language = {zh-CN, en}
scenario = {status, missing-id, write-request}
tool_state = {ok, timeout}
```

The complete Cartesian product has $2\times3\times2=12$ cells. If `write-request` under `timeout` has no business meaning, exclude it explicitly in the contract rather than generating it and quietly deleting it later.

One sample retains:

```json
{
  "id": "syn-zh-status-ok-001",
  "family_id": "zh-status-ok",
  "template_id": "status-ask-v2",
  "variables": {"order_id": "SYN-001"},
  "synthetic": true,
  "generator_version": "template-pipeline-1.0.0"
}
```

Use visibly fictional identifiers so tutorials or shared data cannot be mistaken for real identifiers.

## Common mistakes and diagnosis

- **Many surface forms but identical semantics.** Count family and condition coverage, not only rows.
- **Variable combinations contradict.** Write invariants, such as a delivered state never being in transit.
- **Randomly split every variant.** The same family crosses train/test; split by family.
- **Claim complete reproducibility from a fixed seed.** Freeze code, templates, and dependencies too.
- **Template language is rigid.** Use it as a verifiable baseline, then add human/model rewrites and reaccept them.

## Exercises

1. Design an intent × time-expression × permission matrix for a calendar Agent.
2. Write three invariants and two explicitly excluded combinations.
3. Design a variable pool and ID rules that do not leak real identities.

## Self-check

1. Are programmatically generated labels always correct? No: oracle and template code can contain bugs too.
2. Is full-factorial combination always necessary? No: choose from business meaning, risk, and budget.
3. Why retain a family ID? For deduplication, slice diagnosis, and preventing variants from crossing splits.

## Summary and next step

Templates and simulators provide a transparent reproducible skeleton, but open-task and linguistic coverage remain limited. Next, use [[data-synthesis/foundations-and-design/03-model-generation-and-condition-coverage|Model Generation and Condition Coverage]] to expand the candidate pool without losing contract or provenance.

## References

- [NIST AI 600-1: documenting GAI data provenance, TEVV, and synthetic-data risk](https://doi.org/10.6028/NIST.AI.600-1) — accessed 2026-07-14.
- [Google Data Cards Playbook](https://sites.research.google/datacardsplaybook/) — accessed 2026-07-14.
