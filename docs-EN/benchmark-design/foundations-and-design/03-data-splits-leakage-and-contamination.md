---
title: "Data Splits, Leakage, and Contamination"
aliases:
  - Benchmark Leakage and Contamination
  - Data-Contamination Protection
tags:
  - benchmark
  - data-leakage
  - contamination
source_checked: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "NIST and OpenAI primary material plus original work on
  Datasheets and test contamination through 2026-07-21"
lang: en
translation_key: Benchmark设计/01-基础与设计/03-数据划分泄漏与污染.md
translation_source_hash: eebb56d4b0a48dfb4b7ce222ccfec99e33114aae4decb78bf837e04848d7518c
translation_route: zh-CN/Benchmark设计/01-基础与设计/03-数据划分泄漏与污染
translation_default_route: zh-CN/Benchmark设计/01-基础与设计/03-数据划分泄漏与污染
---

# Data Splits, Leakage, and Contamination

## Goal

Split development, validation, and test data by their real generating unit; identify direct, near-duplicate, semantic, and process leakage; and maintain a contamination-risk register for a public Benchmark.

## Intuition

If the first half of one customer session enters development and the second half enters test, a model can recognize a context template instead of learning the task. Once public test questions are used in training or repeated tuning, a score may measure memorization and adaptation instead of generalization to new tasks.

## Core concepts

- **split leakage:** source-related or derivable information crosses into different splits.
- **test contamination:** test samples, answers, or close variants enter training, prompt libraries, retrieval corpora, or the tuning process.
- **evaluation overfitting:** repeatedly observing test results and changing a system overfits the test even without training a model.
- **group split:** assign whole users, documents, templates, events, or question families together.
- **temporal split:** use a time boundary to simulate generalization to future data.
- **hidden test:** inputs or answers are undisclosed and run by a controlled service; this lowers risk while sacrificing some transparency and independent reproduction.

## Step-by-step method

1. Find the true “generating unit” for each sample: a user, document, session, template, code repository, or original event.
2. Preserve source and group ID before deduplication; split by group, not random row.
3. Freeze test first, then derive development and validation from remaining data; fit all transformations only on permitted splits.
4. Check exact duplicates, normalized duplicates, and near duplicates; manually sample translations, paraphrases, and templates with the same answer.
5. Record test exposure surfaces: public repositories, web pages, paper appendices, prompts, retrieval corpora, and model providers.
6. Declare known training-data boundaries and ability to exclude training data before a run; label contamination `unknown` when it cannot be confirmed.
7. Limit test-query count and retain submission history; after material tuning, use a new holdout or version.
8. Report contamination risk and detection method, but never rewrite `not-detected` as `certainly uncontaminated`.

## Build an exposure and contamination register

Different risks require different evidence; one string-deduplication pass cannot be called “no contamination”:

| Risk surface | Question to record | Possible control or evidence |
| --- | --- | --- |
| Training / post-training contamination | Did questions, answers, or close variants enter pretraining, fine-tuning, distillation, or prompt optimization? | Vendor disclosure, training cutoff, auditable exclusion, membership/order-style detection, and its limits |
| Runtime discoverability | Can an Agent find questions or answers through browser, search, RAG, or tools during evaluation? | Network/index snapshot, allowed domains, query trace, isolated track |
| Developer adaptation | Did developers view test content, fine-grained feedback, or results from repeated submissions? | Access records, submission budget, feedback granularity, independent final holdout |
| Maintenance-chain leakage | Did private cases, graders, logs, or answers escape through repository, service, or report? | Least privilege, audit, rotation, retention, and deletion records |

Label every system separately as `confirmed`, `evidence-of-risk`, `not-detected`, or `unknown`, while recording detection version, coverage, and false-positive/false-negative boundaries. `not-detected` means only that the specified method did not find evidence; `unknown` must not be filled in as no. For browser-capable Agents, pretraining contamination and finding an answer directly during evaluation are independent risk chains.

At minimum, results must include sensitivity analyses by exposure-risk stratum and results on a post-cutoff, controlled-new-question, or other lower-exposure subset. If contamination detection changes the exclusion set, report original and adjusted scores, exclusion rules, and case counts together, so after-the-fact cleanup cannot become selective improvement.

## Data versions and Datasheets

Every data version records at least source, license/authorization, collection window, generating unit, deduplication method, split rule, known contamination, sensitive-data treatment, labeling process, and appropriate/inappropriate uses. A content hash can detect whether a file changed; it cannot prove lawful source or correct labels. A label repair that does not change the task population can be a patch version. A change to task distribution, test exposure, or scoring meaning requires a major version and stops cross-version ranking.

## Example

Incorrect random-row split:

~~~text
doc-17/chunk-1 -> train
doc-17/chunk-2 -> test
~~~

Correct group split:

~~~text
doc-17/* -> train
doc-29/* -> test
~~~

Agent data follows the same rule: surface rewrites generated by one workflow template should share a family ID. For time-sensitive knowledge, a rolling test can use events after a cutoff, but must still check whether the event is public and could enter model or retrieval data.

## Common mistakes and diagnostics

- **Check only exact strings:** translations, option reorderings, and synonym rewrites can still leak; combine provenance, normalization, similarity retrieval, and spot checks.
- **Augment before splitting:** variants from one original sample can cross sets; group by family first, then augment inside permitted splits.
- **Publish answers and never update:** publication supports audit, but contamination risk rises over time; plan version rotation or controlled testing.
- **Treat hidden testing as absolute security:** repeated submissions can probe it, and service logs can leak; limit rate and audit anomalies.
- **Treat contamination detection as conviction:** closed training data are often unavailable and detection has error; report evidence strength and alternatives.

## Exercises

1. Choose one group key each for RAG chunks, customer-service sessions, and code-repository tasks.
2. Draw the exposure surface from collection to submission and mark nodes that can leak answers.
3. Create a test-rotation, query-limit, and contamination-declaration template for a public Benchmark.

## Self-check

1. Why are random-row splits often optimistic? Related samples cross sets and break independence.
2. Does no exact duplicate prove no contamination? No. Near-duplicate, translated, semantic, or process contamination can remain.
3. If a team views test scores weekly and tunes its prompt, has training-data contamination occurred? Not necessarily, but evaluation overfitting has.

## Summary and next step

Independent test evidence comes from source isolation, group splits, exposure records, and controlled use; no single similarity algorithm can guarantee it. Continue to [[benchmark-design/methods-and-quality/04-baselines-metrics-and-comparable-runs|Baselines, Metrics, and Comparable Runs]] to freeze truly comparable execution conditions.

## References

- [NIST AI 600-1: document training/test cross-contamination](https://doi.org/10.6028/NIST.AI.600-1) — retrieved 2026-07-21.
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) — published 2026-05-29; contamination and runtime-validity checks.
- [Datasheets for Datasets](https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/) — original paper page, retrieved 2026-07-21.
- [NLP Evaluation in Trouble](https://aclanthology.org/2023.findings-emnlp.722/) — original paper, retrieved 2026-07-21.
- [Stop Uploading Test Data in Plain Text](https://aclanthology.org/2023.emnlp-main.308/) — original paper, retrieved 2026-07-21.
- [Investigating Data Contamination in Modern Benchmarks](https://aclanthology.org/2024.naacl-long.482/) — original paper, retrieved 2026-07-21.
- [An Open-Source Data Contamination Report for Large Language Models](https://aclanthology.org/2024.findings-emnlp.30/) — original paper; a detection-coverage and stratified-reporting example.
- [Proving Test Set Contamination in Black-Box Language Models](https://proceedings.iclr.cc/paper_files/paper/2024/hash/46e624c244cff669223d488defd4e835-Abstract-Conference.html) — ICLR 2024 original paper; black-box-detection example.
