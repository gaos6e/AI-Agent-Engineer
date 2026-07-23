---
title: "Diffusion and Autoregressive Intuition"
tags:
  - image-generation
  - diffusion-models
  - autoregressive
aliases:
  - Image-generation intuition
source_checked: 2026-07-14
lang: en
translation_key: 图像生成/01-基础与生成原理/02-扩散与自回归直觉.md
translation_source_hash: 54ade3aabe6e65c8b3ce313621b8a18085f8d6a72b5c704190770abd7522c72a
translation_route: zh-CN/图像生成/01-基础与生成原理/02-扩散与自回归直觉
translation_default_route: zh-CN/图像生成/01-基础与生成原理/02-扩散与自回归直觉
---

# Diffusion and Autoregressive Intuition

## Goal of this lesson

Do not train a model. Build only the mental model needed to explain sampling, randomness, conditioning, and cost.

## Diffusion: progressively denoise noise

During training, researchers add noise to a real image step by step so a network learns how, at a given noise level, to predict the added noise or direction toward a clean image. Generation reverses this: it begins with random noise $x_T$ and repeatedly updates toward a clearer $x_0$. One forward noising step can be written in simplified form as:

$$
x_t = \sqrt{\bar{\alpha}_t}x_0 + \sqrt{1-\bar{\alpha}_t}\epsilon,
$$

where $\epsilon$ is random noise and $\bar{\alpha}_t$ controls how much original-image signal remains. Real implementations include a noise schedule, network prediction target, and sampler; beginners only need the idea of “multi-step correction.” Latent diffusion performs the process in a compressed representation to reduce high-resolution computation.

**Conditioning** is the steering wheel for denoising. Text embeddings, reference images, depth maps, and masks can all be conditions. Classifier-free guidance intuitively compares a prediction that follows the condition with one that does not, then pushes the result toward the condition. Pushing too hard can sacrifice naturalness or diversity.

## Autoregression: predict the next visual unit in sequence

An autoregressive model turns an image into discrete visual tokens and predicts the next image token in sequence just as a language model predicts the next word:

$$
p(x)=\prod_i p(x_i\mid x_{<i}, c),
$$

where $c$ is a condition such as text. Its advantage is clear probabilistic modeling and reuse of Transformers; its cost is that sequential generation can be slow and early errors affect later tokens. Modern systems also use parallel and masked-prediction compromises, so do not force every product into two categories.

## Why the same prompt can produce different images

Sampling needs a random starting point or choice. A **random seed** is only an integer initializing pseudorandom numbers. The same seed may reproduce an output only when model version, parameters, implementation, hardware path, and other conditions are also stable. If a cloud product does not promise determinism, a seed is not an absolute reproducibility guarantee.

Sampling steps and guidance strength are common parameters, not cross-provider standards. More steps often increase latency but do not guarantee continuous improvement. Obtain parameter names, ranges, and defaults only from the official documentation of the version in use.

## Common misconceptions

- “The model looks up the most similar image in a database”: generative models learn a distribution and sample from it; this does not prove absence of training-data memorization or rights risk.
- “Diffusion is always better than autoregression”: quality depends on data, model, conditions, and evaluation, not only paradigm.
- “Locking the seed fully reproduces output”: also record model snapshot, request, input hash, and provider behavior.
- “More steps are always better”: measure the quality-latency curve on your task set.

## Exercise and self-check

1. Use “repair a photograph gradually covered by snowflakes” to describe denoising, then identify where the analogy is inaccurate.
2. What visual issue can overly strong conditioning cause?
3. List at least five items needed to reproduce one cloud-generated image.

Next, turn conditions into a checkable task description: [[image-generation/01-foundations-and-generation-principles/03-conditioning-and-prompt-design|Conditioning and Prompt Design]].

## References

- [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
- [High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Zero-Shot Text-to-Image Generation](https://arxiv.org/abs/2102.12092)
