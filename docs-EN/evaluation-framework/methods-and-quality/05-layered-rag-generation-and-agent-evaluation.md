---
title: "Layered RAG, Generation, and Agent Evaluation"
aliases:
  - Layered RAG and Agent Evaluation
tags:
  - evaluation
  - rag
  - agent
source_checked: 2026-07-14
content_origin: original
content_status: dynamic
lang: en
translation_key: 评测体系/02-方法与质量/05-RAG生成与Agent分层评测.md
translation_source_hash: d10c30851515213333d0f58661ec7d975750117459d63838764290287eb9b440
translation_route: zh-CN/评测体系/02-方法与质量/05-RAG生成与Agent分层评测
translation_default_route: zh-CN/评测体系/02-方法与质量/05-RAG生成与Agent分层评测
---

# Layered RAG, Generation, and Agent Evaluation

## Goal

Decompose end-to-end failures into retrieval, generation, decision, tool, trace, and outcome layers to shorten the path to diagnosis.

## Intuition

A wrong final answer is only a symptom. Layered evaluation checks each station along the data flow: first whether the right evidence was found, then whether it was used. For an Agent, also inspect selection, parameters, trace, and the real final state.

## Start RAG with two layers

### Retrieval layer

- Does the query correctly represent user intent?
- Did gold evidence enter top-`k`, measurable with Recall@k?
- What proportion of returned content is relevant, measurable with Precision@k?
- Are permissions, version, freshness, and deduplication correct?
- Are ordering, metadata, and context budget appropriate?

### Generation layer

- Are critical conclusions supported by retrieved evidence?
- Can citations locate real passages?
- Does the answer omit necessary information or add claims outside evidence?
- Does it correctly abstain or clarify when evidence is insufficient?
- Does it meet the requested format, language, and user task?

The final answer alone cannot distinguish “the evidence was not retrieved” from “it was retrieved but not used.” The original RAGAS paper proposed automated reference-free dimensions, but model metrics still require calibration against domain human judgment and cannot be treated as absolute truth.

Also separate “the answer is correct” from “the citation is faithful.” An answer may happen to be correct while citing the wrong source; a claims/citations structure may also be valid while the user-visible answer adds unsupported facts. The `evaluate` subcommand in [[rag/08-project-offline-cited-qa|the RAG offline project]] actually emits retrieval/context/citation fact recall, status accuracy, critical slices, and non-disclosure gates. It renders the answer from verified claims and separates public response and protected audit trace into different schemas.

## Additional Agent layers

| Layer | Typical checks |
| --- | --- |
| Intent / planning | Recognizes objectives and constraints; asks for clarification when needed |
| Tool selection | Correct tool choice; no prohibited tool |
| Parameters | Correct ID, path, scope, and idempotency key |
| Trace | No repetition, loop, or skipped critical validation; avoid overconstraining one unique sequence |
| Outcome | External state achieves the goal without side effects |
| Operations | Turns, tokens, latency, retries, and recovery from failure |

Official guidance recommends evaluating artifacts and state before forcing an Agent to follow one unique tool sequence. Traces still matter for diagnosing unauthorized behavior and futile loops.

## Trace grading is not “the more similar the path, the better”

**Trace grading** assigns structured labels to decisions, tools, parameters, or steps in one end-to-end invocation trace. It is appropriate for checking prohibited tools, parameter scope, evidence use, loops, and missing policy steps. It is not appropriate for making one correct tool order the only answer, nor can an Agent's textual statement of intent prove final state by itself.

A trace grader must define:

- required and forbidden behavior, and multiple permitted paths;
- how sampling, missing spans, concurrency, and retries are scored;
- access and retention boundaries for sensitive prompts, tool results, and reasoning material;
- grader version, human calibration, and treatment of `Unknown`;
- how trace judgments cross-check outcomes, structured logs, and environment state.

OpenAI's current Trace grading page defines a trace as an end-to-end record of decisions, tool calls, and reasoning steps and emphasizes its diagnostic value, but it still points to the announced-deprecated Evals dashboard. This course retains the method and does not teach that legacy dashboard workflow. MLflow documentation currently labeled `latest` likewise treats traces as an offline or automated-evaluation vehicle; verify concrete APIs against the installed version.

## Component tests and end-to-end tests

- Component tests can fix retrieval results and evaluate only generation, or fix tool responses and evaluate only parameters and decisions.
- End-to-end tests use a realistic environment and evaluate the complete system and recovery behavior.
- Contract tests validate JSON, schema, and permission boundaries.
- Security tests attempt prompt injection, unauthorized access, and data disclosure.

Component tests localize failures quickly but can miss interaction problems; end-to-end tests are more realistic but noisier. Both are needed.

## A diagnostic example

If an answer cites the wrong policy, first check whether the gold document appeared in top-`k`. If not, inspect query, index, and filtering. If it did, inspect context truncation and generation grounding. If text is correct but users remain dissatisfied, inspect the task definition and presentation. At every step retain case ID, configuration, document version, and trace.

## Failure classification and evidence chain

For each failure, label the layer first and write down evidence rather than declaring root cause immediately:

1. **Data / task:** incorrect gold data, stale document, impossible task, or ambiguous definition.
2. **Retrieval:** gold not recalled, incorrect permission filter, ranking or truncation problem.
3. **Generation:** evidence was present but unused, unsupported expansion, or format failure.
4. **Tool / trace:** wrong choice, wrong parameters, repetition or loop, or skipped critical safety check.
5. **Outcome:** text is correct but external state is incomplete, or hidden side effects occurred.
6. **Grader / harness:** scoring bug, residual environment state, unequal budget, or missing trace.

A root-cause conclusion must link at least to the case, grader result, trace or outcome evidence, and configuration difference. A correlated timestamp or one failed span is only a hypothesis to validate.

## Common mistakes and diagnostics

- Only inspect final text: also inspect retrieval IDs, tool parameters, trace, and environment state.
- Force a unique tool sequence: constrain only required safety steps and allow multiple correct paths.
- Treat automated RAG metrics as ground truth: calibrate with domain-human samples and retain failure cases.

## Exercises

1. For “look up the refund policy from a knowledge base and create a ticket,” write one assertion per layer.
2. Design one unit test with a fixed tool response and one end-to-end test in a real sandbox.

## Self-check

Can a correct final answer justify ignoring the trace? No. It may still have performed unauthorized reads, futile loops, or hidden side effects.

## Summary and next step

Continue to [[evaluation-framework/methods-and-quality/06-offline-online-statistics-and-regression|Offline, Online, Statistics, and Regression]].

## References

- [OpenAI Evaluation best practices: architecture layers](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-14.
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading) — checked 2026-07-14; methodological reference, not a new Evals API tutorial.
- [MLflow LLM Judges and Scorers](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/index.html) — documentation labeled `latest`, checked 2026-07-14.
- [Anthropic: Agent eval structure and graders](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; checked 2026-07-14.
- [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://aclanthology.org/2024.eacl-demo.16/) — original paper, checked 2026-07-14.
