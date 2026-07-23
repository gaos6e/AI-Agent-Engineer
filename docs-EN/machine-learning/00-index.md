---
title: "Machine Learning"
tags:
  - ai-agent-engineer
  - machine-learning
  - learning-path
aliases:
  - Machine Learning Index
  - Machine Learning Learning Path
source_checked: 2026-07-22
source_baseline:
  - scikit-learn 1.9.0 official documentation
  - scikit-learn common pitfalls and model evaluation guides
  - NIST AI RMF 1.0 (risk-management reference, not legal advice)
ai_learning_stage: "2. Mathematics and Data Foundations"
ai_learning_order: 13
ai_learning_schema: 2
ai_learning_id: machine-learning
ai_learning_domain: foundations
ai_learning_catalog_order: 1300
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 90
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 90
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 90
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 90
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 机器学习/00-目录.md
translation_source_hash: 38a23e33b96c21c8147d9177ae9f1aea41d73718a22ca534c834521e451393bc
translation_route: zh-CN/机器学习/00-目录
translation_default_route: zh-CN/机器学习/00-目录
---

# Machine Learning

## Course overview

Machine learning lets a program derive reusable prediction rules from examples instead of encoding every case with `if/else`. For an AI Agent Engineer, it is chiefly useful for intent routing, risk classification, retrieval and ranking, anomaly detection, and evaluation-data analysis. This course first establishes a main path that can actually complete training and evaluation, then provides loss functions, optimizers, Transformer, and Mamba as deep-learning bridge references. Those four pages do not replace the data boundaries, baselines, and evaluation in the main path.

## Place in the overall learning path

This is recommended engineering background in the “Mathematics and Data Foundations” stage, not a complete hard prerequisite course for Embeddings, Reranking, RAG, or evaluation systems. Before starting, you should know basic Python and JSON/CSV. Probability/statistics and linear algebra can be learned as needed. You may begin concrete Agent/RAG work first and return to this course when data splitting, baselines, ranking metrics, or error analysis become relevant; completing this short main path first will make later judgment more reliable.

## Learning goals

- Distinguish supervised and unsupervised learning, and classification, regression, and clustering tasks.
- Split data correctly and recognize data leakage and distribution shift.
- Put cleaning, feature transformations, and a model into one reproducible Pipeline.
- Evaluate a model with metrics aligned to business cost rather than accuracy alone.
- Independently complete a small text intent-routing project and explain its error examples.

## Prerequisites

- Be able to create a `venv`, install packages with `pip`, and run Python 3 scripts in PowerShell 7. Completing [[python-fundamentals/00-index|Python Fundamentals]] first is recommended.
- Understand that table rows are examples and columns are fields.
- A rough understanding of means, proportions, and vectors is sufficient; when needed, review [[probability-and-statistics/00-index|Probability and Statistics]] and [[linear-algebra/00-index|Linear Algebra]].

## Recommended order

1. [[machine-learning/01-task-types-and-the-complete-workflow|Task Types and the Complete Workflow]]: put the problem, data, model, and deliverable on one map.
2. [[machine-learning/02-data-splitting-and-data-leakage|Data Splitting and Data Leakage]]: establish an evaluation boundary that no experiment may skip.
3. [[machine-learning/03-features-and-preprocessing-pipelines|Features and Preprocessing Pipelines]]: turn raw fields into features a model can consume.
4. [[machine-learning/04-training-validation-and-hyperparameter-tuning|Training, Validation, and Hyperparameter Tuning]]: understand the responsibilities of training, cross-validation, and hyperparameter search.
5. [[machine-learning/05-overfitting-and-generalization|Overfitting and Generalization]]: learn to tell whether a model learns a pattern or memorizes training data.
6. [[machine-learning/06-metrics-baselines-and-error-analysis|Metrics, Baselines, and Error Analysis]]: make metrics serve actual risk and cost.
7. [[machine-learning/07-introduction-to-unsupervised-learning|Introduction to Unsupervised Learning]]: explore unlabeled data with clustering and dimensionality reduction.
8. [[machine-learning/08-project-ticket-intent-routing|Project: Ticket Intent Routing]]: connect data, Pipeline, evaluation, and error analysis.

## Deep-learning bridge references

- [[machine-learning/loss-functions|Loss Functions]]: understand common losses from logits, labels, and training objectives; distinguish single-label, multi-label, and regression first.
- [[machine-learning/optimizers|Optimizers]]: understand parameter updates, learning rate, and weight decay; use current framework API documentation for concrete parameters.
- [[machine-learning/transformer-models|Transformer Models]]: the key sequence architecture of modern LLMs. First complete the training loop and attention path in [[deep-learning/00-index|Deep Learning]].
- [[machine-learning/mamba-models|Mamba Models]]: the selective state-space path for long sequences. Use it to understand architecture tradeoffs, not as a prerequisite for ordinary Agent applications.

## Hands-on project

The main project uses [[machine-learning/examples/ticket_router.py|ticket_router.py]] and [[machine-learning/examples/test_ticket_router.py|test_ticket_router.py]]. Its data is embedded in the script, with no download and no API key. It compares a majority-class baseline with a character-level TF-IDF plus logistic-regression Pipeline, and prints macro F1, a confusion matrix, and confidence-bearing error examples. Dependencies are pinned in [[machine-learning/examples/requirements.txt|requirements.txt]]; full commands and acceptance criteria are in [[machine-learning/08-project-ticket-intent-routing|Project: Ticket Intent Routing]].

## Mastery standard

- [ ] Explain feature, label, parameter, hyperparameter, and prediction with your own example.
- [ ] Explain what the training, validation, and test sets may each be used for.
- [ ] Identify why “standardize the full dataset before splitting” leaks information.
- [ ] Choose precision, recall, or F1 for an imbalanced task and explain the cost tradeoff.
- [ ] Train with `Pipeline`, save configuration, and reproduce an experiment result.
- [ ] Inspect error examples and propose a data-, feature-, or threshold-level improvement rather than only changing models.
- [ ] Run normal mode, `python -O`, `-W error`, and the ten tests, and explain why 0.667 accuracy is not deployment evidence.

## Relationship to other knowledge bases

- Data cleaning determines whether inputs are trustworthy: [[data-cleaning/00-index|Data Cleaning]].
- Data annotation determines whether supervision is consistent: [[data-annotation/00-index|Data Annotation]].
- Charts help discover distributions, overfitting, and error patterns: [[data-visualization/00-index|Data Visualization]].
- [[embeddings/00-index|Embeddings]] and [[reranking/00-index|Reranking]] reuse similarity, train/test boundaries, and ranking metrics.
- [[deep-learning/00-index|Deep Learning]] builds on training/validation/testing, loss, and optimization concepts here to discuss neural networks, attention, and Transformers. Neither course may treat training loss as deployment evidence.
- An Agent router, safety classifier, and offline evaluator can all be viewed as machine-learning components, but a generative LLM is not identical to a traditional supervised classifier.

## Primary references

Review date: **2026-07-22**. This course uses scikit-learn **1.9.0** official documentation as its API baseline. `stable` pages and APIs change with releases; the project pins direct dependency versions in `requirements.txt`, so rerun tests and read release notes before upgrades. Fairness, privacy, and deployment risk are discussed here only as engineering-risk boundaries. Applicable law, domain rules, and organizational policy require separate confirmation.

- [scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html)
- [Supervised learning](https://scikit-learn.org/stable/supervised_learning.html)
- [Unsupervised learning](https://scikit-learn.org/stable/unsupervised_learning.html)
- [Model selection and evaluation](https://scikit-learn.org/stable/model_selection.html)
- [Pipelines and composite estimators](https://scikit-learn.org/stable/modules/compose.html)
- [Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn Release History](https://scikit-learn.org/stable/whats_new.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
