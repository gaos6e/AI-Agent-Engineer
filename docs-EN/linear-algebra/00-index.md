---
title: "Linear Algebra"
tags:
  - ai-agent-engineer
  - linear-algebra
aliases:
  - Linear algebra learning path
  - Linear algebra for AI engineering
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - NumPy stable linear algebra documentation
  - PyTorch official Linear documentation
ai_learning_stage: "2. Mathematics and data foundations"
ai_learning_order: 11
ai_learning_schema: 2
ai_learning_id: linear-algebra
ai_learning_domain: foundations
ai_learning_catalog_order: 1100
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 85
ai_learning_track_rag_kind: recommended
ai_learning_track_multimodal_realtime_order: 85
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 线性代数/00-目录.md
translation_source_hash: b77b7917a751c9aa9e74e027294f306a51d916d5ffe29e26c90bda4ae73f81f2
translation_route: zh-CN/线性代数/00-目录
translation_default_route: zh-CN/线性代数/00-目录
---

# Linear Algebra

## Course overview

Linear algebra is the language for representing directions, organizing data, and transforming batches of numbers. Features, model parameters, embeddings, retrieval scores, and batched computations can all be represented as vectors, matrices, or higher-dimensional tensors. This path is designed for genuine beginners: it builds intuition for dot products and distance first, then covers shapes, spaces, linear layers, projection, and numerical stability, and finally verifies least-squares geometry with a tested standard-library project.

## Where this fits in the overall path

Linear Algebra sits in the Mathematics and data foundations stage. It is a shared prerequisite for vector fundamentals, machine learning, deep learning, and embeddings. It explains how data and parameters are organized, which directions are independent, and how matrices transform information in batches.

## Learning objectives

- Calculate dot products, norms, distances, and cosine similarity by hand, and explain their semantic limits.
- Read vectors, matrices, shapes, and matrix multiplication.
- Use linear combinations, column spaces, and rank to explain whether a system is solvable.
- Understand $Wx+b$ in neural networks as a spatial transformation.
- Understand least squares through projection, while distinguishing algebraic fitting from statistical conclusions.
- Use condition numbers and singular values to recognize ill-posed problems, and understand the limits of eigenvalues, SVD, and dimensionality reduction.

## Prerequisites

Basic arithmetic, square roots, and one-variable linear equations are enough. The code exercises require lists, functions, and exceptions from [[python-fundamentals/00-index|Python Fundamentals]]. You do not need calculus first. Vector-retrieval indexes, thresholds, and evaluation are covered next in [[vector-fundamentals/00-index|Vector Fundamentals]].

## Recommended order

1. [[linear-algebra/00a-coordinates-dot-products-norms-and-similarity|Coordinates, dot products, norms, and similarity]]: begin with coordinate semantics and vector geometry.
2. [[linear-algebra/01-vectors-matrices-and-shapes|Vectors, matrices, and shapes]]: build a shape ledger and distinguish matrix multiplication from elementwise operations.
3. [[linear-algebra/02-linear-combinations-systems-and-rank|Linear combinations, systems, and rank]]: use column spaces, null spaces, bases, and rank to reason about information and solutions.
4. [[linear-algebra/03-linear-transformations-and-neural-networks|Linear transformations and neural networks]]: understand $Wx+b$, batch-direction conventions, and the role of nonlinearity.
5. [[linear-algebra/04-orthogonality-projection-and-least-squares|Orthogonality, projection, and least squares]]: understand fitting, residuals, and normal equations geometrically.
6. [[linear-algebra/04a-numerical-stability-and-condition-numbers|Numerical stability and condition numbers]]: distinguish singularity, ill-conditioning, and algorithmic instability.
7. [[linear-algebra/05-eigenvalues-svd-and-least-squares-project|Eigenvalues, SVD, and the least-squares project]]: understand principal directions and dimensionality reduction, then complete a tested least-squares project.

## Hands-on entry points

- Implement and test dot products, norms, and cosine similarity in [[linear-algebra/00a-coordinates-dot-products-norms-and-similarity|Coordinates, dot products, norms, and similarity]].
- Keep a shape ledger for every formula: decide first whether an operation is valid, then what it means.
- Continue to [[linear-algebra/05-eigenvalues-svd-and-least-squares-project|Eigenvalues, SVD, and the least-squares project]], run the standard-library least-squares program and its eight tests, verify residual orthogonality, and experiment with rank deficiency, ill-conditioning, and outliers.

## Mastery criteria

- [ ] I can write vector and matrix shapes and check that inner dimensions agree before computing.
- [ ] I can explain matrix multiplication as linear combinations rather than elementwise multiplication.
- [ ] I can use rank to identify redundant features or a non-unique solution.
- [ ] I can explain why least-squares residuals are orthogonal to the feature space through projection.
- [ ] I can distinguish singularity, ill-conditioning, and algorithmic instability, and explain why explicitly inverting a matrix is not the default.
- [ ] I can explain the use and limits of eigenvalues, singular values, and SVD in dimensionality reduction.
- [ ] I can fit a one-variable linear model with the standard library, explain its input contract, and verify it in normal mode, with `-O`, and with unit tests.

## Connections to other knowledge bases

| Knowledge base | Connection |
| --- | --- |
| [[vector-fundamentals/00-index\|Vector Fundamentals]], [[embeddings/00-index\|Embeddings]] | Apply dot products, norms, normalization, and batched matrix operations to semantic vectors. |
| [[semantic-search/00-index\|Semantic Search]] | Similarity, dimensionality reduction, and index thresholds depend on vector geometry and evaluation with real data. |
| [[calculus/00-index\|Calculus Fundamentals]] | Gradients determine how matrix parameters are updated; the chain rule runs through composed transformations. |
| [[machine-learning/00-index\|Machine Learning]] | Least squares, rank, condition numbers, regularization, and PCA are foundational tools. |
| [[deep-learning/00-index\|Deep Learning]] | Linear layers, embedding tables, and attention all rely on matrix and tensor operations. |

## Primary references

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [MIT 18.06SC Syllabus](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/syllabus/)
- [NumPy: Linear algebra routines](https://numpy.org/doc/stable/reference/routines.linalg.html)
- [NumPy: `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)
- [PyTorch: `torch.nn.Linear`](https://docs.pytorch.org/docs/main/generated/torch.nn.Linear.html)

Verified on **2026-07-14**. The MIT course covers stable mathematical concepts. NumPy and PyTorch are changing engineering interfaces; this path records only the semantics verified on that date. Consult current official documentation and record versions before use. The local project requires only the Python 3.11.9 standard library; it does not require NumPy or PyTorch.
