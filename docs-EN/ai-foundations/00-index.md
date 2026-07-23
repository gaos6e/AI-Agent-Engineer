---
title: "AI Foundations Learning Path"
tags:
  - ai-agent-engineer
  - learning-path
  - ai-foundations
aliases:
  - AI Foundations index
  - AI beginner map
content_origin: original
content_status: dynamic
source_checked: 2026-07-22
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 1
ai_learning_schema: 2
ai_learning_id: ai-foundations
ai_learning_domain: foundations
ai_learning_catalog_order: 100
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 5
ai_learning_track_agent_app_kind: core
ai_learning_track_rag_order: 5
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 5
ai_learning_track_agent_platform_kind: core
ai_learning_track_multimodal_realtime_order: 5
ai_learning_track_multimodal_realtime_kind: core
lang: en
translation_key: AI基础认知/00-目录.md
translation_source_hash: 7060e67a84eb95087eea487e61b5a5756781462c113e56a8829108e8b6cc34dd
translation_route: zh-CN/AI基础认知/00-目录
translation_default_route: zh-CN/AI基础认知/00-目录
---

# AI Foundations

## About this knowledge base

This course is not about memorizing AI vocabulary. It builds a map that can guide engineering decisions: where Artificial Intelligence (AI), machine learning, deep learning, large language models, and Agents sit relative to one another; what they can do and how they fail; when a requirement is worth solving with AI; and how to carry risk controls through the full system lifecycle.

No mathematics or programming background is required. After completing it, you should be able to explain key terms in your own words, decompose an LLM/Agent system, and write a verifiable, reversible minimum plan for a low-risk use case.

> [!abstract] Source and evidence boundary
> The explanations, exercises, project template, and diagrams in this course are original syntheses for this project. External standards, papers, and annual reports support factual boundaries only and are listed under “References” on each page; the course does not reproduce third-party prose or code. AI definitions, risk frameworks, and annual trends change. When implementing a concrete system, recheck primary sources as of the page’s `source_checked` date.

> This knowledge base uses these fact labels: **stable facts** are supported by standards, papers, or enduring engineering consensus; **engineering recommendations** require tradeoffs in context; **changeable facts**—such as models, products, interfaces, prices, regulations, or framework status—must be checked again during implementation.

## Where this course fits in the overall route

This is the first stop in the [[all-of-ai|AI Agent Engineer main route]]. It builds a “requirement → system → risk → validation” framework before Python, APIs, machine learning, LLMs, RAG, tool calling, and Agent frameworks. Do not skip it because it contains no complex code: unclear conceptual boundaries make it easy to call ordinary automation an Agent or mistake a compelling demo for engineering acceptance.

## Learning objectives

- Distinguish AI, machine learning (ML), deep learning (DL), generative AI, LLMs, and Agents.
- Explain an LLM with “input → model → context → output,” and an Agent with “goal → state → decision → tools → feedback.”
- Recognize common failure modes such as hallucination, prompt injection, tool misuse, distribution change, and automation bias.
- Decide from the business goal whether no AI, an LLM alone, a fixed workflow, or an Agent is the right system shape.
- Define data boundaries, an evaluation set, human approval, monitoring, rollback, and shutdown conditions for a minimum viable system.
- Make recorded risk tradeoffs among privacy, fairness, transparency, safety, and accountability.

## Prerequisites

- You only need to be able to create and read Markdown files in Windows 11.
- No Python, linear algebra, or machine-learning experience is required.
- When formulas appear, understand their inputs and outputs before learning derivations.

## Knowledge taxonomy

The course follows “concept map → engineering decisions → project validation.” The three directories have separate responsibilities so conceptual explanation, risk lists, release gates, and final checks do not collapse into one long page:

| Category | Core question | Lesson scope |
| --- | --- | --- |
| `01-concept-map` | What is an AI system made of, where do capabilities come from, and how is it validated? | AI/ML/DL/LLM/Agent boundaries; training and inference; generalization and leakage; evaluation evidence; LLM generation; Agent loops |
| `02-engineering-decisions` | When should it be used, how should it be constrained, and how should it launch or exit? | Failure diagnosis, system-shape selection, lifecycle gates, responsibility, and risk control |
| `03-project-and-self-assessment` | Can the learned judgment become an acceptable deliverable and transfer to a new context? | An independent integrated project, a partially completed template, and course-wide self-checks |

> [!note] Scope boundary
> This course builds engineering intuition only. Algorithm derivations belong in [[machine-learning/00-index|Machine Learning]] and [[deep-learning/00-index|Deep Learning]]. Specific LLM calls, retrieval, tools, and Agent control belong in their later knowledge bases. Downstream courses should link to the definitions here rather than maintain a second competing basic vocabulary.

## Recommended order

1. [[ai-foundations/01-concept-map/01-ai-map-and-core-terms|AI map and core terms]] — establish boundaries among AI, ML, DL, LLMs, and Agents.
2. [[ai-foundations/01-concept-map/02-data-model-training-and-inference|Data, models, training, and inference]] — understand how capability arises from data and parameters and where context adaptation stops.
3. [[ai-foundations/01-concept-map/03-generalization-data-splits-and-leakage|Generalization, data splits, and leakage]] — understand new inputs, independent tests, and evaluation contamination.
4. [[ai-foundations/01-concept-map/04-evaluation-evidence-and-feedback-loops|Evaluation evidence and feedback loops]] — combine baselines, offline sets, human review, trial operation, and online feedback.
5. [[ai-foundations/01-concept-map/05-how-llms-generate-answers|How LLMs generate answers]] — understand language models through tokens, context, and probabilistic prediction.
6. [[ai-foundations/01-concept-map/06-how-agents-complete-tasks|How Agents complete tasks]] — recognize decision loops, tools, state, and human takeover.
7. [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability boundaries and failure modes]] — turn “looks smart” into localizable failures and responses.
8. [[ai-foundations/02-engineering-decisions/08-when-to-use-ai-and-system-shape-selection|When to use AI and choose a system shape]] — compare rules, ML, LLMs, workflows, and Agents.
9. [[ai-foundations/02-engineering-decisions/09-from-prototype-to-launch-and-exit|From prototype to launch and exit]] — establish pilots, launch gates, dependency control, rollback, and shutdown.
10. [[ai-foundations/02-engineering-decisions/10-responsible-use-and-risk-controls|Responsible use and risk controls]] — address affected people, privacy, safety, fairness, resources, and accountability.
11. [[ai-foundations/03-project-and-self-assessment/11-integrated-project-meeting-action-item-assistant|Integrated project: Meeting Action-Item Assistant]] — complete requirement, boundary, evidence, test, and risk deliverables.
12. [[ai-foundations/03-project-and-self-assessment/12-course-wide-self-check-and-mastery|Course-wide self-check and mastery]] — use transfer questions to confirm that concepts work in new scenarios.

## Hands-on work and project entry

- Every lesson has a no-secret exercise. Write your own answer before viewing the reference approach.
- See [[ai-foundations/03-project-and-self-assessment/11-integrated-project-meeting-action-item-assistant|Integrated Project: Meeting Action-Item Assistant]] for the integrated task. You will produce a requirement card, system-boundary diagram, test samples, risk register, and launch criteria—not just one prompt.
- Afterward, use [[ai-foundations/03-project-and-self-assessment/12-course-wide-self-check-and-mastery|Course-Wide Self-Check and Mastery]] for closed-book transfer. Return via links to lessons for questions not yet passed.
- The project can be completed completely offline. If you independently use an online model, replace real meeting notes with fictional ones; do not upload real names, accounts, trade secrets, or other sensitive data.

## Mastery checklist

After completing the course, you should be able to check all of these independently:

- [ ] Explain the relationship among AI, ML, DL, LLMs, and Agents with one example without looking at notes.
- [ ] Distinguish data, model, parameters, training, inference, context, and feedback, and identify obvious data leakage.
- [ ] Draw an Agent’s input, state, model, tools, policy, output, and feedback paths.
- [ ] Compare rule-based code, one LLM call, a fixed workflow, and an Agent for the same requirement.
- [ ] Define at least five decidable tests for generated output, including exceptional and adversarial cases.
- [ ] Explain why model output cannot automatically be treated as fact, authorization, or a business commitment.
- [ ] Define when human approval, rollback, and system shutdown are needed.
- [ ] Record data sources, expected users, known limitations, accountable owners, and review date.

## Relationship to other knowledge bases

| Next knowledge base | Connection this course provides |
| --- | --- |
| [[machine-learning/00-index\|Machine Learning]], [[deep-learning/00-index\|Deep Learning]] | Moves from the concept map into training, generalization, overfitting, and neural-network details |
| [[prompt-engineering/00-index\|Prompt Engineering]], [[context-engineering/00-index\|Context Engineering]], [[llm-api-integration/00-index\|LLM API Integration]] | Turns LLM intuition into controlled input, interface calls, and structured output |
| [[rag/00-index\|RAG]], [[semantic-search/00-index\|Semantic Search]] | Handles knowledge updates, evidence citation, and external retrieval, but cannot automatically eliminate error |
| [[tool-calling-function-calling/00-index\|Tool Calling]], [[agent-core/00-index\|Agent Core]] | Constrains model outputs as tool parameters and designs loops, state, permissions, and stop conditions |
| [[evaluation-framework/00-index\|Evaluation Framework]], [[runtime-monitoring/00-index\|Runtime Monitoring]], [[llmops/00-index\|LLMOps]] | Extends this course’s tests, launch criteria, and event records into production systems |
| [[ai-safety/00-index\|AI Safety]], [[ai-governance/00-index\|AI Governance]], [[privacy-computing/00-index\|Privacy Computing]] | Deepens threats, organizational accountability, compliance, and data protection |

## Primary references

All sources below were checked on **2026-07-22**. Their content and framework-revision status may change further.

- [OECD: Explanatory memorandum on the updated OECD definition of an AI system](https://oecd.ai/en/ai-publications/explanatory-memorandum-on-the-updated-oecd-definition-of-an-ai-system): supports the conceptual boundary that a system infers from inputs and produces outputs that affect environments.
- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1): supports trustworthy-AI characteristics and the risk-management framework. **Changeable:** the NIST page marked AI RMF 1.0 as under revision on the access date.
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/): supports the iterative relationship among Govern, Map, Measure, and Manage.
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1): supports generative-AI risks and controls.
- [Stanford HAI: 2026 AI Index Report](https://hai.stanford.edu/ai-index/2026-ai-index-report): tracks annual changes in model capability, evaluation, industry, responsible AI, and governance; trend data are not a guarantee of any one product’s capability.
- [Vaswani et al.: Attention Is All You Need](https://arxiv.org/abs/1706.03762): original Transformer paper.
- [Yao et al.: ReAct](https://arxiv.org/abs/2210.03629): representative Agent research on alternating language-model reasoning and action.
- [Mitchell et al.: Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596): supports recording model uses, evaluation, and limitations.
