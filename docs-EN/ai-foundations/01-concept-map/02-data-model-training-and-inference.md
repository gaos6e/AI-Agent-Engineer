---
title: "Data, Models, Training, and Inference"
tags:
  - ai-agent-engineer
  - ai-foundations
  - model-lifecycle
aliases:
  - How AI capabilities form
  - Introduction to training and inference
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/02-数据模型训练与推理.md
translation_source_hash: 645b0769948e8612c9cb9aa223d2c6812c7388266268fa5416c2771175c9bd4a
translation_route: zh-CN/AI基础认知/01-概念地图/02-数据模型训练与推理
translation_default_route: zh-CN/AI基础认知/01-概念地图/02-数据模型训练与推理
---

# Data, Models, Training, and Inference

## Learning objective

After this lesson, you should be able to distinguish data, algorithms, models, parameters, training, and inference; explain the difference among pre-training, fine-tuning, prompting, and RAG; and read the minimum data flow from examples to output in an AI feature.

## A minimum map

```text
Task and examples
  ↓ Data processing and representation
Training algorithm repeatedly adjusts parameters
  ↓
Trained model (architecture + parameters + input/output contract)
  ↓ New input enters inference
Prediction, content, or decision signal
  ↓ Rules, tools, people, and product process
Real system outcome
```

The map establishes two boundaries: a model is not a complete system, and learning patterns for a training objective does not mean the model already satisfies a business objective.

## What the six concepts are

| Concept | A beginner-friendly interpretation | Example |
| --- | --- | --- |
| Data | Records that describe reality, provide examples, or validate outcomes | Text, images, labels, sensor readings |
| Algorithm | A sequence of steps for processing input or updating parameters | Gradient descent, nearest-neighbor search, rule matching |
| Model | A parameterized mapping that produces predictions or generated results from inputs | Classifier, neural network, LLM |
| Parameters | Values adjusted during training and usually fixed during inference | Neural-network weights |
| Training | The process of adjusting parameters with data and an objective function | Gradually reducing classification error |
| Inference | The computation that applies a trained model to one new input | Assigning a category to a new email |

“Model” is sometimes used broadly to mean a callable service. In engineering discussions, clarify whether you mean a parameter file, a service version, or a complete application that includes prompts, retrieval, and tools.

## Data is not only “more is better”

Data must answer at least these questions:

1. **Where did it come from?** Real operations, public material, human-authored content, or synthetic generation; and was its use authorized?
2. **What does it represent?** Which users, languages, devices, times, and exceptions does it cover, and which does it not cover?
3. **What is its quality?** Is it duplicated, erroneous, stale, label-conflicted, or sensitive?
4. **How does it change?** What are its version, retention period, deletion method, and update owner?

Without examples for “decline to answer” or “insufficient information,” a system may learn to force a conclusion. If only successful records are collected, it cannot see failure. The selection of data already expresses task boundaries and value judgments.

A Datasheet can record a dataset’s motivation, composition, collection process, recommended uses, and limitations. It improves traceability, but does not automatically prove that the data is lawful, representative enough, or error-free.

## What training actually optimizes

Training needs a computable objective. A classifier might minimize label-prediction error; language-model pre-training commonly learns to predict a token from its context. A training algorithm repeatedly computes error and adjusts parameters so the training objective improves.

Keep three objectives separate:

- **Training objective:** how parameters are optimized.
- **Task objective:** whether classification, extraction, retrieval, or generation succeeds on representative examples.
- **System objective:** whether users complete the real task with acceptable cost, latency, and risk.

An improving proxy metric can still coincide with a worse system outcome. For example, a higher JSON-format pass rate does not mean the tool object and amount are correct; a shorter summary does not mean it retained a crucial negation.

## Pre-training, fine-tuning, prompting, and RAG

| Method | Does it usually change model parameters? | What it primarily changes | Best suited to |
| --- | --- | --- | --- |
| Pre-training | Yes | Base parameters over large-scale data | Acquiring general representation and generation capability |
| Fine-tuning | Yes | Continued parameter updates for a particular dataset or objective | Behavioral, stylistic, or task adaptation |
| Prompting and context | No | Instructions, examples, and material visible to this request | Explaining the task, constraints, and current information |
| RAG | Usually no | Material retrieved from an external collection and injected into this request’s context | Current, private, and citable knowledge |
| Tool calling | No | Reading or changing external systems through controlled interfaces | Real-time state, computation, and actions |

“Usually” matters. Some research systems jointly train retrievers and generators, but an ordinary application does not alter language-model parameters simply by calling RAG. Regardless of the adaptation method, independent evaluation is necessary: training a model, retrieving a passage, or writing an instruction does not make a conclusion correct.

## Inference is still a system

A production request commonly includes:

```text
Identity and authorization checks
  → Input validation or de-identification
  → Prompts, retrieval, tools, and model inference
  → Output-structure and business-rule validation
  → Human approval or a safety action
  → Logs, metrics, and event handling
```

The same model forms different systems under different contexts, tool permissions, decoding parameters, and post-processing. A Model Card can record a model’s intended use, evaluation conditions, and limitations; an application must also record its prompts, data sources, tools, dependencies, and deployment configuration.

> [!warning] Inference does not mean “the model permanently remembers this input”
> This request’s context affects this computation, but normally does not write directly to model parameters. Whether a provider stores requests or uses them to improve a model is a product-setting, contract, and data-policy question. Check the current official terms; do not infer it from the word “inference.”

## A verifiable example

Task: decide whether a customer-service email needs human escalation.

```text
Data: authorized, de-identified historical email plus dual human annotation
Training/selection: keyword rules as a baseline; a classifier or LLM as a candidate
Inference: enter a new email and output a category, rationale, and available confidence signals
Post-processing: high-risk rules take priority; insufficient or conflicting information goes to a human
System outcome: false negatives, false positives, human workload, latency, and incidents
```

The example does not specify a threshold, because the threshold depends on the real consequences of false negatives and false positives. First define who bears each error, then choose the threshold.

## Common misconceptions

| Misconception | Why it fails | Better wording |
| --- | --- | --- |
| “The model is the code.” | A model also includes learned parameters and an input contract. | Record code, parameters, data, and configuration separately. |
| “Putting documents in a prompt is training.” | Parameters usually have not changed. | This is adaptation through the current request’s context. |
| “Fine-tuning automatically adds the latest facts.” | Facts can become stale and are difficult to trace individually. | For up-to-date knowledge, prefer governed data sources or RAG. |
| “A high training metric means it can launch.” | It may be overfit, leaked, or misaligned with the goal. | Use independent tests, real slices, and operational evidence. |
| “Model output is the decision.” | Output is only one signal in the system. | Use rules, permissions, people, and accountability processes to determine consequences. |

## Exercise

Choose either “meeting action-item extraction” or “customer-service email classification.” Draw the data, training/selection, model, inference, validation, people, and system outcome. Mark which parts change parameters, which affect only the current request, and which deterministic logic outside the model owns.

## Self-check

1. What is the difference among an algorithm, a model, and parameters?
2. Why are both pre-training and fine-tuning forms of training?
3. Why do prompting, RAG, and tool calling usually not change model parameters?
4. How can a training objective and a system objective become misaligned?
5. Where should you confirm whether a provider retains an inference request?

## Related concepts and next step

- Data quality, labeling specifications, and cleaning continue in [[data-cleaning/00-index|Data Cleaning]] and [[data-annotation/00-index|Data Annotation]].
- Parameter optimization and neural-network details continue in [[machine-learning/00-index|Machine Learning]] and [[deep-learning/00-index|Deep Learning]].
- Next, [[ai-foundations/01-concept-map/03-generalization-data-splits-and-leakage|Generalization, Data Splits, and Leakage]] explains why success on seen examples cannot be directly generalized to future inputs.

## References

Accessed **2026-07-22**.

- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
- Gebru et al., [Datasheets for Datasets](https://doi.org/10.1145/3458723)
- Sculley et al., [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)
