---
title: "Multimodal, Embedding, and Specialized Models"
tags:
  - llm
  - multimodal
  - embedding
aliases:
  - Multimodal model selection
  - Embedding and specialized model selection
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/04-多模态、Embedding与专用模型.md
translation_source_hash: a93e55b778a88616805ebfb6723e2a694be032acc236c9a74a18dd28ffe84166
translation_route: zh-CN/现代LLM能力与模型选择/04-多模态、Embedding与专用模型
translation_default_route: zh-CN/现代LLM能力与模型选择/04-多模态、Embedding与专用模型
---

# Multimodal, Embedding, and Specialized Models

## Goal

Select generative, perception, or embedding models by their role in a pipeline. Do not replace end-to-end task evidence with one generic overall score.

## Core concepts

A multimodal system is not a Boolean “supports images” flag. It can be a pipeline containing OCR/ASR, visual understanding, generation, embeddings, reranking, and business validation. Evaluate each model by the interface it changes:

- Images/documents: resolution, page count, layout, tables, rotation, text language, and citation coordinates;
- Audio: noise, accents, overlap, timestamps, streaming latency, and interruption;
- Video: sampling, temporal order, long clips, audio-video relationships, and cost;
- Embeddings: query/document conventions, language, domain, vector dimension, normalization, maximum input, and version migration.

An embedding is a retrieval or clustering component and should not be evaluated with a generative model’s fluency metrics. MTEB covers multiple embedding tasks, and its original study found no method that dominates every task. That is evidence for selecting by task.

## Why this matters

A single screenshot demo cannot prove reliability for multi-page PDFs, low-resolution scans, and tables. High semantic-similarity scores also cannot prove that your retrieval top-*k* finds evidence that is authorized for the requester. Upstream pipeline errors can be concealed as fluent answers by downstream language models, so layered metrics must be retained.

## How to implement it

1. Draw the stages and intermediate contracts from input to outcome.
2. Prepare the real distribution, difficult slices, and rejection examples for every layer.
3. Measure perception correctness, retrieval quality, citation/location fidelity, and end-to-end success separately.
4. Record preprocessing, compression, sampling, embedding prefixes, dimensions, and the similarity function.
5. For a version upgrade, dual-write or backfill the index first; never mix different embedding spaces directly.

For an embedding candidate, report at least Recall@*k*, MRR/nDCG, no-result cases, latency, throughput, index size, and rebuild cost on a private query–corpus–relevance set. Public MTEB/VHELM can support candidate discovery and slice design, but cannot replace private evaluation.

## Common failures

- Assuming “multimodal input” means that all file types, sizes, and languages are equivalent.
- Looking only at the final answer and not retaining intermediate OCR/ASR/retrieval evidence.
- Selecting a RAG embedding directly from an STS score.
- Reusing old vectors after changing the embedding, which creates inexplicable distances.
- Ignoring image tokens, audio duration, and video sampling costs and tail latency.

## How to validate

Run layered ablations: fix the downstream component while replacing the upstream one, then fix the upstream component while replacing the downstream one. If a final-quality change cannot be explained by intermediate metrics, inspect data alignment, caches, and the harness before attributing it to the model.

## Practice task

Draw 30 queries from a real knowledge base, label relevant documents and unanswerable cases, and compare two embedding candidates on Recall@5, nDCG@10, p95 latency, and index size. Then inspect whether top-*k* results are affected by chunking, language, or permission filtering.

## References

- Muennighoff et al., [MTEB](https://aclanthology.org/2023.eacl-main.148/)
- Stanford CRFM, [VHELM](https://crfm.stanford.edu/helm/vhelm/v2.0.0/)
- [[embeddings/00-index|This knowledge base: Embeddings]]
- [[multimodal-ai/00-index|This knowledge base: Multimodal AI]]
