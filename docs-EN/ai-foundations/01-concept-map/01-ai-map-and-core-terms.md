---
title: "AI Map and Core Terms"
tags:
  - ai-agent-engineer
  - ai-foundations
  - core-terms
aliases:
  - Differences among AI, ML, DL, LLMs, and Agents
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/01-AI地图与核心术语.md
translation_source_hash: de7d186d5410a9c0725827f0e26fad758c8922b5aa129ef0ae2e4c0540ac6f4e
translation_route: zh-CN/AI基础认知/01-概念地图/01-AI地图与核心术语
translation_default_route: zh-CN/AI基础认知/01-概念地图/01-AI地图与核心术语
---

# AI Map and Core Terms

## Learning objective

After this lesson, you can place common AI terms on one map and decide whether a requirement calls for rule-based automation, machine learning, an LLM application, or an Agent system.

## Understand AI through what a system does

**Stable fact:** The OECD definition of an AI system emphasizes that a machine-based system infers, for explicit or implicit objectives, how to generate predictions, content, recommendations, or decisions from inputs, and that its outputs may affect physical or virtual environments. Systems can differ in autonomy and post-deployment adaptiveness. The important ideas are not “being human-like,” but these four points:

1. It has inputs, such as text, images, or sensor readings.
2. It uses a model or knowledge rules to make an inference.
3. It produces outputs used by people or other systems.
4. It creates effects and risks in a defined context of use.

AI is therefore not one algorithm. A product also usually contains databases, interfaces, permissions, user interfaces, logs, and human processes. A model is only one part of an AI system.

## Six easily confused concepts

| Concept | A useful beginner intuition | Typical artifact | Example |
| --- | --- | --- | --- |
| Artificial intelligence (AI) | The umbrella term for getting machines to perform tasks that usually need inference, perception, or decision-making | AI system | Optical character recognition (OCR), recommendations, voice assistants |
| Machine learning (ML) | Learning patterns from data instead of hard-coding every rule | Predictive model | Spam classification, sales forecasting |
| Deep learning (DL) | A machine-learning approach that uses multilayer neural networks | Neural-network model | Image recognition, speech recognition |
| Generative AI | Generating text, images, audio, video, or code | New content | Text summaries, image generation |
| Large language model (LLM) | A language model trained on extensive text or code that processes token sequences | Text or structured output | Question answering, rewriting, code assistance |
| Agent | A system that repeatedly observes, decides, acts, and reads feedback around a goal | Task trace and result | Checking inventory, then drafting an order |

The relationships can be sketched roughly as follows:

```text
AI
├─ Knowledge/rule-based and other approaches
└─ Machine learning (ML)
   └─ Deep learning (DL)
      └─ Many modern generative models and LLMs

Agent system = model (possibly an LLM, but not necessarily)
             + goal + state + tools + control policy + feedback
```

This is not a strict set diagram for products. For example, an Agent can call a rules engine, a search model, and an LLM; generative AI is not limited to language either.

## AI is not automation, and an Agent is not a chat box

A script that copies files to a backup folder at 9:00 every day is **deterministic automation**: under the same conditions, it normally follows the same steps and does not need model inference. It can be highly valuable, but does not need to be called AI.

A chat model answering one question is one **LLM call**. It becomes closer to an Agent in the engineering sense only when the system maintains task state, selects or calls tools, reads execution feedback, and continues pursuing a goal based on that feedback.

> **Engineering recommendation:** Choose the simplest solution that meets the goal. Use rules when rules are sufficient; use a workflow when the steps are fixed; add Agent autonomy only when the path genuinely must be selected from intermediate feedback and the risk can be controlled.

## Identify the system type with four questions

For a requirement such as “process customer email automatically,” ask in order:

1. **Can stable rules produce the output?** If the task is only filing messages by sender domain, rules are enough.
2. **Must the system learn classification boundaries from historical samples?** If it must recognize several intents, an ML classifier may help.
3. **Must it understand or generate open-ended text?** If it must summarize a request and draft a response, an LLM may help.
4. **Must it choose actions from results and operate external systems?** If it must look up an order, decide the next step, create a ticket, and verify the state, consider an Agent or controlled workflow.

“Uses AI” is never an acceptance criterion. Acceptance should instead be an observable outcome such as “the missed-routing rate for high-priority mail stays below the agreed threshold” or “every refund action requires human approval.”

## Exercise: classify the requirements

Label the following tasks “rules / ML / LLM / workflow / Agent.” Multiple labels are allowed, but explain why.

1. Normalize dates in file names to `YYYY-MM-DD`.
2. Identify anomalous payments from historical transactions.
3. Rewrite a long explanation into three bullet points.
4. Extract invoice fields, then check the total and notify a human when fields are missing.
5. Read an incident description, query monitoring and the knowledge base, choose diagnostic commands from the results, and request approval before restarting a service.

Suggested reasoning: 1 fits rules; 2 is usually ML; 3 is an LLM task; 4 is a fixed workflow, although field extraction can use OCR, ML, or an LLM; 5 has dynamic tool selection and a feedback loop, so it is closer to a controlled Agent. Classification is not the goal—the goal is explaining why a model or autonomy is needed.

## Self-check

1. Are ML and DL peers, or does one contain the other?
2. Why is a “model” not the same as an “AI system”?
3. Is a chat application that calls one search API necessarily an Agent?
4. Why can deterministic rules sometimes be better than an LLM?

Suggested answers:

1. DL is usually treated as a family of ML methods.
2. A system also includes data, interfaces, permissions, people, processes, and its operating environment; risk comes from those interactions as well.
3. Not necessarily. Without goal-driven state, decisions, and a feedback loop, it may only be an enhanced one-shot call.
4. Rules are easier to explain, reproduce, and test; when requirements are stable and explicit, model nondeterminism only adds cost and risk.

## Related concepts

- [[machine-learning/00-index|Machine Learning]] explains how models learn from samples; [[deep-learning/00-index|Deep Learning]] goes further into neural networks.
- [[multimodal-ai/00-index|Multimodal AI]] extends inputs from text to images, audio, and video. It remains a system capability, not proof that a system is human-like.
- [[workflow-automation/00-index|Workflow Automation]] and [[agent-core/00-index|Agent Core]] respectively deepen deterministic orchestration and the boundary of dynamic decision-making.

## Summary and next step

First decide what kind of capability a task needs, then choose the technology. Next, continue with [[ai-foundations/01-concept-map/02-data-model-training-and-inference|Data, Models, Training, and Inference]] to understand how capability forms and why a model is not a complete system.

## References

Accessed **2026-07-22**.

- [OECD: What is AI?](https://oecd.ai/en/wonk/definition)
- [OECD: Explanatory memorandum on the updated definition of an AI system](https://oecd.ai/en/ai-publications/explanatory-memorandum-on-the-updated-oecd-definition-of-an-ai-system)
- [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
