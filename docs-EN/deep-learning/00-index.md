---
title: "Deep Learning"
tags:
  - ai-agent-engineer
  - deep-learning
  - D2L
aliases:
  - Deep Learning Learning Path
  - D2L Agent Engineering Path
source_checked: 2026-07-22
source_snapshot_created: 2026-05-07
source_baseline:
  - D2L Chinese 2.0.0 documentation and d2l-zh repository
  - PyTorch official installation, AMP, reproducibility, and distributed
    documentation
  - Attention Is All You Need, BERT, and Decoupled Weight Decay Regularization
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: Apache-2.0
ai_learning_stage: "2. Mathematics and Data Foundations"
ai_learning_order: 14
ai_learning_schema: 2
ai_learning_id: deep-learning
ai_learning_domain: foundations
ai_learning_catalog_order: 1400
ai_learning_hard_prerequisites: []
ai_learning_track_multimodal_realtime_order: 95
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 深度学习/00-目录.md
translation_source_hash: 6175a713d78ae3d56d6d58eb6ca497267aefdd153c5e3f80f7b561e8b640e13d
translation_route: zh-CN/深度学习/00-目录
translation_default_route: zh-CN/深度学习/00-目录
---

# Deep Learning

## About this knowledge base

This directory retains the complete Chinese *Dive into Deep Learning* (D2L) course text and adds a selective path for AI Agent Engineers. A typical Agent or RAG application does not require learning convolutional networks, distributed training, and every derivation first. Build intuition for tensors, gradients, training/generalization, attention, and Transformers when a project needs to understand model internals, embeddings, multimodality, or the boundary around training and evaluation.

> [!info] Navigation
> [[deep-learning/sources-and-full-index|Sources and Full Index]] preserves provenance and the structure of all 140 course pages. This page provides the selective Agent-engineering path. On 2026-07-22, explicitly labeled modern engineering guidance was added for high-risk entry points including installation, automatic differentiation, evaluation, numerical behavior, Transformer, optimization, distributed training, and BERT; the historical D2L text remains preserved and traceable.

## Place in the overall path

Deep learning sits in “Mathematics and Data Foundations.” It is recommended background for multimodal and model-research directions, not a complete hard prerequisite for general Agents, embeddings, LLM APIs, or RAG. Before entering this path, build introductory intuition for probability and statistics, linear algebra, calculus, and machine learning—but do not wait until every mathematical topic feels effortless. [[vector-fundamentals/00-index|Vector Fundamentals]] supports embeddings and retrieval; it can be studied alongside this course or separately when RAG becomes relevant, and it is not a hard prerequisite for training neural networks.

Before applying course concepts to a real experiment or project, read [[deep-learning/engineering-practice-and-modern-workflow|Engineering Practice and a Modern Workflow]]. It connects D2L's training intuition to data lineage, evaluation, release, execution modes, and Agent/RAG system boundaries. It is not a second textbook replacing the 140 source pages; it helps you select necessary chapters and avoid treating historical code or one curve as production evidence.

## Learning objectives

- Describe one training iteration with tensors, parameters, loss, gradients, and an optimizer.
- Distinguish training, validation, and test sets; explain underfitting, overfitting, and distribution shift.
- Understand the roles of forward propagation, backpropagation, automatic differentiation, and parameter updates.
- Explain attention and self-attention with queries, keys, and values.
- Explain how Transformers, word embeddings, and pretrained models connect to LLM/RAG work.
- Run a small experiment, read loss/metrics, and record environment and randomness limits.

## Prerequisites

- Python functions, lists/dictionaries, virtual environments, and exception handling. Complete [[python-fundamentals/00-index|Python Fundamentals]] first if needed.
- Intuition for vectors, matrix multiplication, derivatives, and probability. If a derivation is unclear, first check shapes and data flow; revisit [[linear-algebra/00-index|Linear Algebra]], [[calculus/00-index|Calculus]], and [[probability-and-statistics/00-index|Probability and Statistics]] as needed.
- First understand the data-split, baseline, metric, and generalization boundaries in [[machine-learning/00-index|Machine Learning]], then replace a model with a neural network.
- D2L examples may use different frameworks and hardware. Start with a small CPU example to understand the flow; you do not need to buy a GPU to begin.

## A minimum mental model of one training iteration

Deep learning is still machine learning; its models simply have many learnable layers, more parameters, and stronger representation capacity. One training iteration can be compressed into four steps:

1. **Forward propagation:** with parameters $\theta$, the model transforms input $x$ into a prediction $\hat{y}=f_\theta(x)$.
2. **Loss computation:** loss $L(\hat{y}, y)$ measures the gap between prediction and target $y$. It is an optimization signal, not necessarily a business metric.
3. **Backpropagation:** automatic differentiation follows the computation graph to calculate $\nabla_\theta L$, answering “which direction should each parameter move to reduce the current loss?”
4. **Parameter update:** the simplest gradient-descent update is $\theta \leftarrow \theta-\eta\nabla_\theta L$, where learning rate $\eta$ controls the step size.

You can compute one update by hand to verify the direction. Let $\hat{y}=wx$, $x=2$, $y=6$, initial $w=1$, and loss $L=(\hat{y}-y)^2/2$. Then $\hat{y}=2$, $L=8$, and $\partial L/\partial w=(\hat{y}-y)x=-8$. With $\eta=0.1$, $w$ updates to $1-0.1\times(-8)=1.8$, giving a new prediction of $3.6$ and new loss of $2.88$: one update did reduce loss on the current sample. It still does not prove performance on new data.

A **batch** is the small group of samples read by one iteration, and an **epoch** is one pass through the training set. Falling training loss says only that the model fits training data better. Whether it learned a generalizable pattern still depends on validation/test data that did not participate in fitting. Common mistakes include treating “a gradient exists” as “the gradient is numerically stable,” or treating “more parameters” as “better results by necessity.”

For an Agent Engineer, this model helps explain embeddings, Transformers, and fine-tuning. Calling a pretrained LLM API, building RAG, or orchestrating tools does not require training a large model first.

## Versions, environment, and reproducibility boundary

The local course is a snapshot organized from the D2L Chinese 2.0.0 site on 2026-05-07. Its installation page still illustrates Python 3.9, PyTorch 1.12.0, torchvision 0.13.0, and `d2l==0.17.6`. That is a **historical environment for reproducing the book's code**, not a current PyTorch recommendation. PyTorch's official installer command is generated dynamically for a Windows/Python/CPU-or-CUDA combination, so this page does not hard-code a command that could become stale quickly.

On Windows 11 / PowerShell 7, create an isolated `venv`, then select Windows, Pip, Python, and the actual compute platform at [PyTorch Start Locally](https://docs.pytorch.org/get-started/locally/). Rewrite the page-generated installation command so that the environment's Python executes it:

```powershell
$course = (Resolve-Path '.\docs-EN\deep-learning').Path
$venv = Join-Path $course '.venv'
$python = Join-Path $venv 'Scripts\python.exe'

py -3.11 -m venv $venv
& $python -m pip install --upgrade pip
& $python -c "import sys; print(sys.executable); print(sys.version)"
```

Then rewrite the selector's `pip install ...` command as `& $python -m pip install ...` to avoid installing into system Python. After installation, record `python --version`, `pip freeze`, CPU/GPU, and driver information. To reproduce the book's historical code line by line, create a separate historical environment using the book's versions; do not mix “current PyTorch” and “historical D2L dependencies” in one environment. Once you understand `venv + pip`, you can use `uv` to create environments faster, but isolation and version-recording principles remain the same.

> [!warning] Verification boundary for this update
> This update verified local files, the complete index, and the selective path. It did not download frameworks, create a `.venv`, or claim that all 140 historical pages run unchanged on current Python/PyTorch. When you run an experiment, treat that experiment's actual output and locked environment as evidence.

## Recommended learning order

### Read first: engineering boundaries and evidence

1. [[deep-learning/engineering-practice-and-modern-workflow|Engineering Practice and a Modern Workflow]]: distinguish the course snapshot, current framework, training/validation/test, and release responsibilities before running historical code or creating cloud resources.

### 0. Tensors and mathematical preparation

1. [[deep-learning/upstream-references/chapter-05-02/reference-01-02|Preliminaries]]: understand the course tools and learning sequence.
2. [[deep-learning/upstream-references/chapter-05-02/reference-02-02-1|Data Manipulation]]: focus on tensor shapes, indexing, and broadcasting.
3. [[deep-learning/upstream-references/chapter-05-02/reference-03-02-2|Data Preprocessing]]: understand how tabular data enters tensors.
4. [[deep-learning/upstream-references/chapter-05-02/reference-04-02-3|Linear Algebra]], [[deep-learning/upstream-references/chapter-05-02/reference-05-02-4|Calculus]], and [[deep-learning/upstream-references/chapter-05-02/reference-07-02-6|Probability]]: learn only the minimum concepts needed by later material first.
5. [[deep-learning/upstream-references/chapter-05-02/reference-06-02-5|Automatic Differentiation]]: observe how a framework calculates gradients.

### 1. From linear models to neural networks

1. [[deep-learning/upstream-references/chapter-06-03/reference-02-03-1|Linear Regression]]: connect model, loss, and optimization into one loop.
2. [[deep-learning/upstream-references/chapter-06-03/reference-04-03-3|Concise Implementation of Linear Regression]]: learn the framework interfaces for data, models, losses, and optimizers.
3. [[deep-learning/upstream-references/chapter-07-04/reference-02-04-1|Multilayer Perceptrons]]: understand layers, nonlinearities, and representation capacity.
4. [[deep-learning/upstream-references/chapter-07-04/reference-05-04-4|Model Selection, Underfitting, and Overfitting]]: required concepts for evaluation and production work.
5. [[deep-learning/upstream-references/chapter-07-04/reference-08-04-7|Forward Propagation, Backpropagation, and Computational Graphs]]: understand gradients along the data flow.
6. [[deep-learning/upstream-references/chapter-07-04/reference-09-04-8|Numerical Stability and Initialization]]: recognize failure modes such as vanishing/exploding gradients.

### 2. The sequence-and-attention path to LLMs

1. [[deep-learning/upstream-references/chapter-11-08/reference-03-08-2|Text Preprocessing]] and [[deep-learning/upstream-references/chapter-11-08/reference-04-08-3|Language Models and Datasets]]: understand token sequences and next-token prediction.
2. [[deep-learning/upstream-references/chapter-12-09/reference-07-09-6|Encoder–Decoder]] and [[deep-learning/upstream-references/chapter-12-09/seq2seq|seq2seq]]: understand input-to-output sequences.
3. [[deep-learning/upstream-references/chapter-13-10/reference-01-10|Attention Mechanisms]] and [[deep-learning/upstream-references/chapter-13-10/reference-06-10-5|Multi-Head Attention]]: build Q/K/V and multiple-subspace intuition.
4. [[deep-learning/upstream-references/chapter-13-10/reference-07-10-6|Self-Attention and Positional Encoding]]: understand information mixing and positional signals within one sequence.
5. [[deep-learning/upstream-references/chapter-13-10/transformer|Transformer]]: combine attention, feed-forward layers, residual connections, and normalization into a model.
6. [[deep-learning/upstream-references/chapter-17-14/word2vec|Word Embeddings]] and [[deep-learning/upstream-references/chapter-17-14/bert|BERT]]: connect vector representations, pretraining, and downstream tasks.

### 3. Application-driven electives

- Multimodality/OCR: return to computer-vision chapters on convolution, transfer learning, detection, and segmentation.
- Model training and performance: return to optimization, computational performance, and multi-GPU material. They are not prerequisites for calling an LLM API.
- NLP tasks: study sentiment analysis, natural-language inference, and BERT fine-tuning as needed.

## Hands-on practice and project entry points

### Minimum experiment

Choose either [[deep-learning/upstream-references/chapter-06-03/reference-04-03-3|Concise Implementation of Linear Regression]] or [[deep-learning/upstream-references/chapter-07-04/reference-04-04-3|Concise Implementation of Multilayer Perceptrons]]. Run it once in an isolated environment after reducing the data size and number of rounds, then record:

1. Python, framework, and device versions;
2. input/label shapes;
3. how loss changes;
4. whether the random seed is fixed;
5. which result proves that code ran and which result still does not prove generalization.

### Integrated project

[[deep-learning/upstream-references/chapter-07-04/kaggle|House Price Prediction]] provides a complete modeling workflow. While learning, you may complete preprocessing, a training/validation split, model, loss, and pre-submission checks on small local data; participating in an online competition is not required. Afterwards, write a one-page experiment card: objective, data, baseline, metrics, overfitting evidence, reproduction command, and known limits.

At a minimum, the experiment card answers:

| Area | Required evidence |
| --- | --- |
| Environment | Python, framework, dependencies, device, and random seed |
| Data | Source, license, sample count, shapes, and train/validation/test boundary |
| Model | Input/output shapes, layers, activations, loss, optimizer, and learning rate |
| Baseline | Comparable result from a simple model or rule |
| Results | Training curve, validation metrics, best epoch, and at least three error samples |
| Limits | Small samples, randomness, distribution differences, steps not run, and reproducibility risk |

## Beginner self-check

1. Who creates parameters, hyperparameters, activations, and gradients, and when does each change?
2. Why can loss decline while accuracy, F1, or business value does not rise in lockstep?
3. Do `model.eval()` and “do not compute gradients” solve the same problem? If unsure, use the official documentation for your framework to check which layers change behavior.
4. What calculation does each of Q, K, and V participate in for self-attention? Why cannot positional encoding be naturally replaced by word embeddings?
5. If training loss keeps decreasing while validation loss rises, what data, model, and training checks would you make?
6. Why does “I can call a large-model API” neither mean “I can train models” nor prevent me from becoming an Agent application engineer first?

When completing this self-check, do not only memorize terms. Draw a training-loop diagram, calculate one single-parameter gradient update by hand, and support your judgment with one experiment log.

## Mastery criteria

- [ ] Given a batch tensor, explain what each dimension represents.
- [ ] Draw the data → model → prediction → loss → gradient → update loop.
- [ ] Explain why low training loss does not equal good performance on new data.
- [ ] Distinguish parameters, activations, gradients, hyperparameters, and evaluation metrics.
- [ ] Explain Q/K/V, self-attention, multi-head attention, and positional encoding in your own words.
- [ ] Identify how Transformers relate to embeddings/RAG without treating embeddings as a knowledge base.
- [ ] Run and record a minimum experiment; when it fails, investigate shapes, device, dependencies, and data first.

## Relationship to the other knowledge-base courses

- [[linear-algebra/00-index|Linear Algebra]], [[calculus/00-index|Calculus]], [[probability-and-statistics/00-index|Probability and Statistics]], and [[vector-fundamentals/00-index|Vector Fundamentals]] explain this course's formulas.
- [[machine-learning/00-index|Machine Learning]] provides the general workflow for data splits, baselines, metrics, and generalization.
- [[embeddings/00-index|Embeddings]] and [[semantic-search/00-index|Semantic Search]] use vector representations produced by deep models, but require separate evaluation.
- [[prompt-engineering/00-index|Prompt Engineering]], [[llm-api-integration/00-index|LLM API Integration]], and [[rag/00-index|RAG]] mainly use pretrained models; they do not require you to train a large model first.
- [[mlops/00-index|MLOps]], [[llmops/00-index|LLMOps]], and [[evaluation-framework/00-index|Evaluation Framework]] extend experiment records, versioning, monitoring, and regression testing into production.

## Main references

Checked on **2026-07-22**. The local D2L bodies are teaching snapshots; consult the official documentation on the day of installation for dynamic installation commands, framework APIs, and hardware support.

- [D2L Chinese 2.0.0 site](https://zh-v2.d2l.ai/)
- [D2L installation instructions](https://zh-v2.d2l.ai/chapter_installation/)
- [D2L Chinese GitHub repository](https://github.com/d2l-ai/d2l-zh)
- [D2L Apache-2.0 License](https://github.com/d2l-ai/d2l-zh/blob/master/LICENSE)
- [PyTorch: Start Locally](https://docs.pytorch.org/get-started/locally/)
- [PyTorch: Automatic differentiation package](https://docs.pytorch.org/docs/stable/autograd.html)
- [PyTorch: Automatic Mixed Precision](https://docs.pytorch.org/docs/stable/amp.html)
- [PyTorch: Reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)
- [PyTorch: DistributedDataParallel](https://docs.pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html)
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
