---
title: "Representation Learning and Vector Intuition"
tags:
  - ai-agent-engineer
  - embedding
  - representation-learning
aliases:
  - Embedding vector intuition
  - Representation-learning fundamentals
source_checked: 2026-07-14
source_baseline: Google MLCC and the original word2vec, Sentence-BERT, and CLIP
  papers, checked through 2026-07-14
lang: en
translation_key: Embedding/01-表示学习与向量直觉.md
translation_source_hash: 3bc6841a08819fef6f22f17d057e8d8e6abfa3b0f58414761f4101478ea2b46d
translation_route: zh-CN/Embedding/01-表示学习与向量直觉
translation_default_route: zh-CN/Embedding/01-表示学习与向量直觉
---

# Representation Learning and Vector Intuition

## Objective

Starting with the limits of one-hot vectors, you will learn that a training objective shapes a vector space. You will distinguish static word vectors, contextual token representations, sentence/document vectors, and multimodal vectors. Finally, you will make the boundary explicit: embeddings can retrieve candidates, but cannot independently prove facts or authorization.

## Why one-hot vectors are insufficient

Suppose a vocabulary contains $V$ words. A one-hot representation assigns each word a vector of length $V$ with a single entry equal to 1. The dot product of two different words is always 0:

$$
e_i\cdot e_j=0,\qquad i\ne j
$$

Consequently, a cat is no more similar to a dog than to a database under this representation. The vectors are also sparse, and a larger vocabulary increases both storage and the number of parameters in the first layer.

An embedding learns a mapping:

$$
f(x)\in\mathbb{R}^d
$$

Here, $d$ is usually much smaller than the one-hot dimension, and each component is typically a nonzero floating-point value. More importantly, training makes some relationship usable geometrically: shared context, paired text, classes, user behavior, or image-text correspondence.

What “nearby” actually means is:

> Under a particular training dataset, training objective, encoding instruction, and similarity rule, the model tends to place these two inputs near one another.

It is not a probability of objective synonymy, factual agreement, or answer support.

## How training objectives shape a space

### Context prediction

The central intuition behind word2vec is that words appearing in similar contexts may receive similar representations. Training can predict neighboring words from a center word, or predict the center word from its context. The result is a static vector for each word type.

### Contrastive learning

Give a model positive and negative pairs, then train it to bring positives closer and negatives farther apart. A positive might be a query and relevant passage, paraphrases, or an image and its description. Negative selection matters: easy negatives do not teach fine-grained boundaries, while false negatives push truly relevant items apart.

### Distillation, classification, and multitask learning

A model can also distill scores from a stronger model or jointly optimize classification, clustering, retrieval, and other tasks. Multitask coverage may be broader, but does not guarantee that your domain terminology, language, and query distribution are adequately represented.

Do not ask only how large an embedding model is. Also ask which relationships it was trained to capture and how its model card requires inputs to be supplied.

## Four common representation levels

### Static word vectors

One word type receives one vector. A word such as “apple” has the same representation whether it refers to the fruit or the company, so it cannot be disambiguated by context. word2vec is useful for building intuition, but modern retrieval commonly uses contextual models.

### Contextual token representations

In a Transformer, the same token receives different hidden states in different surrounding text. This resolves some ambiguity, but a sequence produces many token vectors; it does not automatically yield a high-quality sentence vector.

### Sentence or document vectors

A variable-length sequence must be pooled into one fixed-size vector, perhaps through a special token, mean pooling, or pooling trained for the task. The original Sentence-BERT paper trained efficiently comparable sentence representations with siamese/triplet networks. It shows why taking an arbitrary hidden state from a generative model should not be assumed to produce a valid retrieval vector.

### Multimodal vectors

Models such as CLIP train a shared space from image-text pairs, allowing text to retrieve images. Cross-modal comparison is meaningful only when a model has been explicitly trained and documented for the relevant modalities. Equal output dimensions, or a model accepting two input kinds, do not prove that its outputs occupy a compatible shared space.

## Bi-encoders and rerankers

### Bi-encoder

Queries and documents are encoded separately:

$$
q=f_q(\text{query}),\qquad d_i=f_d(\text{document}_i)
$$

Document vectors can be precomputed. At query time, encode the query once and make many fast dot-product or distance comparisons. This is the main pattern for semantic candidate retrieval.

### Cross-encoder / reranker

Feed a query together with one candidate document so that the model can directly model their interaction. This is normally slower and cannot precompute document-interaction results for every query, but it is well suited to precisely reranking the top-*N* bi-encoder candidates.

The two are not mutually exclusive competitors. A common two-stage system is:

1. use a bi-encoder to expand recall quickly;
2. combine metadata, keyword, and vector candidates;
3. rerank with a cross-encoder or LLM; and
4. select evidence within the context budget.

## Symmetric and asymmetric tasks

- **Symmetric similarity** compares two items of the same kind, such as duplicate-question detection.
- **Asymmetric retrieval** uses a short query to find a longer document; their forms and goals differ.
- **Classification or clustering** organizes examples relative to one another and need not use retrieval roles.
- **Cross-modal retrieval** can use different modalities for queries and documents.

Some models have distinct encoders; some use one encoder with a query/document prompt or task type; and some return the same result for both calls. Follow the official model card. Sentence Transformers currently recommends `encode_query()` and `encode_document()` for retrieval, while also documenting that models without a dedicated prompt or route can return the same result.

## Geometric intuition and its limits

### Individual dimensions are usually not interpretable

Apply a distance-preserving rotation to an entire space and retrieval order can stay unchanged while every coordinate changes. Therefore, claims such as “dimension 42 represents legal content” usually have no evidence. Explaining a direction requires a dedicated probe or a known training structure.

### Two-dimensional plots distort

PCA, t-SNE, UMAP, and similar methods compress high dimensions into two, inevitably discarding some distance relationships. A plot can help find candidate clusters and outliers, but it cannot replace Recall/MRR/nDCG in the original space.

### High similarity is not a high-confidence probability

Cosine 0.8 does not mean “80% relevant.” Score distributions vary with model, domain, role, and normalization. Calibrate thresholds on a development set, and redo that work after migrating to a new model.

### Semantic proximity is not sufficient evidence

“Authentication failed” and “Do not retry when authentication fails” may be close, but the former does not contain the action conclusion. Embeddings retrieve candidates; reranking, rules, or answer evaluation must still establish citation support and complete conditions.

## Typical RAG failures

| Symptom | Likely cause | First action |
| --- | --- | --- |
| Proper names, identifiers, or error codes are not found | Training favors semantic similarity and rare-token signals are weak | Add keyword or hybrid retrieval and field filters. |
| Negative statements rank beside positive ones | The topic is similar but polarity is not sufficiently distinguished | Add hard negatives, reranking, and evidence checks. |
| A short query retrieves a broad generic passage | The query/document role is wrong or chunks are too large | Verify roles and prefixes, then review [[chunking-strategies/00-index\|Chunking Strategies]]. |
| Chinese is substantially weaker than English | Training-language coverage or corpus fit is poor | Evaluate language subgroups, then replace a candidate or adapt it to the domain. |
| Results fluctuate sharply between old and new data | Spaces are mixed or the revision drifted | Check the complete space signature and index version. |
| Unauthorized content appears among candidates | ACL filtering happens after retrieval | Apply fail-closed filtering in the retrieval layer. |

## Exercises

1. Draw one-hot vectors for “cat,” “dog,” and “database” in a vocabulary of five. Explain why one-hot distance cannot express the similarity of cat and dog.
2. For “find API timeout configuration,” write one query, two positives, one easy negative, and one hard negative. Explain what the hard negative teaches.
3. Classify the following as symmetric or asymmetric: duplicate questions, a short question finding a long document, a product finding similar products, and text finding an image.
4. Find a pair of sentences that are topically similar but cannot serve as answer evidence. Explain why an embedding match does not constitute factual support.
5. Explain why vectors from two 768-dimensional models cannot be placed into the same index and compared directly.

## Mastery check

- [ ] I can explain the motivation for embeddings from the sparsity and orthogonality of one-hot vectors.
- [ ] I know that a space's meaning is jointly determined by training data, objective, input role, and metric.
- [ ] I distinguish static word, contextual token, sentence/document, and multimodal vectors.
- [ ] I can explain why bi-encoders suit retrieval and rerankers are slower.
- [ ] I do not overinterpret a single dimension, a two-dimensional plot, or a cosine score.
- [ ] I treat an embedding as a candidate signal, not as fact, authorization, or a confidence probability.

## Summary and next step

Once you understand the meaning of a representation, do not immediately select the top leaderboard model. First turn the task, roles, dimension, metric, limits, and cost into a candidate contract: [[embeddings/02-model-dimension-and-normalization|Model, Dimension, and Normalization Selection]].

## References

- [Google ML Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [Mikolov et al., word2vec](https://arxiv.org/abs/1301.3781)
- [Reimers & Gurevych, Sentence-BERT](https://arxiv.org/abs/1908.10084)
- [Radford et al., CLIP](https://arxiv.org/abs/2103.00020)
- [Sentence Transformers Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)

Sources were obtained on 2026-07-14. Return to [[embeddings/00-index|Embeddings]].
