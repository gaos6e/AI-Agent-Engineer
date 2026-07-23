---
title: "Generalization, Data Splits, and Leakage"
tags:
  - ai-agent-engineer
  - ai-foundations
  - generalization
aliases:
  - Introduction to training, validation, and test sets
  - Introduction to data leakage
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/03-泛化数据划分与泄漏.md
translation_source_hash: 41fac8084216c8f76ebcd99b463895a81789da5cb5531cff925ddef6fb006f0d
translation_route: zh-CN/AI基础认知/01-概念地图/03-泛化数据划分与泄漏
translation_default_route: zh-CN/AI基础认知/01-概念地图/03-泛化数据划分与泄漏
---

# Generalization, Data Splits, and Leakage

## Learning objective

After this lesson, you should be able to explain generalization, overfitting, training sets, validation sets, test sets, and data leakage; design an independent test for a simple scenario; and recognize leakage through time, users, documents, and prompts.

## Knowing practiced questions is not enough

Good performance on seen data may only mean that a model memorized examples or used clues that should not have been present. Engineering instead cares about **generalization**: whether a system can still perform acceptably on new inputs from its intended context of use that did not participate in development.

**Overfitting** occurs when a system adapts too much to development data and performs worse on new inputs. It does not happen only while training parameters: repeatedly changing a prompt, rule, or RAG system against a fixed evaluation set can overfit that set as well.

## Training, validation, and test sets

| Dataset | Primary purpose | May you modify the solution from it? |
| --- | --- | --- |
| Training set | Learn model parameters or build retrieval/rule assets | Yes |
| Validation/development set | Choose features, prompts, thresholds, hyperparameters, and candidate solutions | Yes, but record the number of uses and versions |
| Test set | Independently estimate final performance after the solution is substantially frozen | It should not be repeatedly used for tuning |

If you change the solution immediately after inspecting test errors and then announce improvement on the same test set, it is gradually becoming a development set. Keep a new independent test set, or clearly report that the test set was used for development.

## A random split is not always correct

The unit of splitting must match real independence:

- Multiple emails from the same user can have highly similar language, so group by user.
- Adjacent chunks from one document cannot be split between training and testing.
- When predicting future events, split by time; do not leak future records into the past.
- Synthetic examples from one template should be grouped by template or generation seed.
- Multi-turn conversations should be split as whole sessions rather than separating earlier and later turns.

Randomly splitting by row is convenient, but can put near-duplicates in different sets and produce overly optimistic results.

## What data leakage is

**Data leakage** occurs when development or evaluation uses information that would be unavailable during real prediction, or that should have remained independent, and therefore inflates results. Common types include:

| Type | Example | How to check |
| --- | --- | --- |
| Target leakage | A feature directly includes the final label or a post-event field | Ask of each field: “Would it be available at prediction time?” |
| Temporal leakage | Using post-completion state to predict whether something will complete | Draw the data flow by event time |
| Duplicate leakage | The same document, user, or paraphrased copy crosses sets | Hashing, near-duplicate checks, and grouping |
| Preprocessing leakage | Computing normalization or a vocabulary from all data | Fit preprocessing only on the training portion |
| Evaluation contamination | Test questions enter training data, few-shot examples, or a retrieval collection | Record data lineage and check overlap |
| Human leakage | Annotators see answers or future information they should not receive | Review the annotation interface and guidelines |

LLM applications make it especially easy to overlook **system-level leakage**: test answers might not appear in model training data, yet could enter prompt examples, a knowledge base, a cache, or debugging traces. The evaluated object includes the model, prompt, retrieval, tools, and post-processing, so the full system must be isolated.

## Distribution shifts and slices

A test set represents a particular time, channel, and population. After launch, input distributions can change: a new product, language, attack technique, or policy can appear. Even if the overall average does not change, one critical group may degrade substantially.

Alongside aggregate results, report slices based on risk-relevant dimensions:

- Common and long-tail tasks.
- Different languages, regions, devices, or input formats.
- Answerable, unanswerable, conflicting, and adversarial inputs.
- High-impact versus read-only actions.
- New versus returning users.
- Healthy dependencies, timeouts, and degraded states.

More slices are not automatically better. Each slice should correspond to a real failure hypothesis and use a reasonable sample size and privacy treatment.

## A minimum split example

Task: extract action items from meeting records. There are 1,000 records, and each project repeatedly uses its own templates.

An unreliable approach is to split by paragraph at random. Near-duplicate text from the same meeting or template can then appear in both training and test data.

A more reasonable design is:

1. Group first by project and complete meeting.
2. Use earlier meetings for training/development and newer meetings for a temporal test.
3. Hold out project templates never seen before as a transfer slice.
4. Check exact and near duplicates in the text.
5. Isolate test meetings from prompt examples, RAG documents, and human debugging records.
6. Report results separately for no-action-item cases, conflicting dates, missing owners, and injection text.

There is no fixed ratio here. Small-data, high-risk, and time-series tasks need a design based on available samples and consequences, not a mechanical `80/10/10` split.

## Common misconceptions

| Misconception | Why it fails | Improvement |
| --- | --- | --- |
| “The test set never trained the model, so it is absolutely independent.” | People may repeatedly inspect it to tune prompts or rules. | Isolate test access and record evaluation uses. |
| “A random split is fairest.” | Related samples can cross sets. | Group by user, time, document, or entity. |
| “A high average score means it generalizes.” | Long-tail and high-risk slices may fail. | Report slices and the worst plausible cases. |
| “Online feedback is ground truth.” | Likes, acceptance, and edits have selection bias. | Form labels only after review. |
| “A new version needs only a few smoke tests.” | Format, latency, and boundary behavior can change. | Run a frozen regression set and critical risk slices. |

## Exercise

For “customer-service email escalation classification,” design three splits: random rows, grouped users, and time. Explain what each estimates, what each can leak, and which best matches the launch context. Then list five critical slices and one sensitive field that must not enter logs.

## Self-check

1. Why can overfitting happen to prompts and rules as well?
2. Why is it dangerous for adjacent chunks of one document to cross training and test sets?
3. What is the difference between target leakage and temporal leakage?
4. How should you report a test set that has been inspected many times?
5. Why does distribution shift require online monitoring instead of offline tests alone?

## Related concepts and next step

- Formal definitions of supervised learning, overfitting, and metrics appear in [[machine-learning/00-index|Machine Learning]].
- Near duplicates, missing values, and outlier handling appear in [[data-cleaning/00-index|Data Cleaning]].
- Next, [[ai-foundations/01-concept-map/04-evaluation-evidence-and-feedback-loops|Evaluation Evidence and Feedback Loops]] turns independent data into release gates and evidence for continuous improvement.

## References

Accessed **2026-07-22**.

- Kaufman et al., [Leakage in Data Mining: Formulation, Detection, and Avoidance](https://doi.org/10.1145/2382577.2382579)
- Koh et al., [WILDS: A Benchmark of in-the-Wild Distribution Shifts](https://arxiv.org/abs/2012.07421)
- Gebru et al., [Datasheets for Datasets](https://doi.org/10.1145/3458723)
- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1)
