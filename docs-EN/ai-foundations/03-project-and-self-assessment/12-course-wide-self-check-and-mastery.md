---
title: "Course-Wide Self-Check and Mastery"
tags:
  - ai-agent-engineer
  - ai-foundations
  - self-check
aliases:
  - AI foundations final self-check
  - AI foundations mastery check
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/03-项目与自测/12-全库自测与掌握检查.md
translation_source_hash: 0833447a985bdbcf505f10b24d87721db49a91dea2093d362d514cfc9f866de3
translation_route: zh-CN/AI基础认知/03-项目与自测/12-全库自测与掌握检查
translation_default_route: zh-CN/AI基础认知/03-项目与自测/12-全库自测与掌握检查
---

# Course-Wide Self-Check and Mastery

## How to use this page

Close the course notes first and answer with your own examples. Each answer must contain three parts: definition or judgment, a concrete example, and an engineering consequence. Repeating terms alone does not pass. Then use the links in each section to check your answer and record concepts that remain confused.

Suggested scoring:

- `0`: cannot answer, or makes a key judgment error.
- `1`: the definition is roughly correct, but no example or engineering consequence is given.
- `2`: definition, example, and boundary are complete, including when the idea does not apply.

Proceed to the following main route only with a total score of at least 32 and no zero on a question marked **Key**. The score is for learning diagnosis, not a capability certification.

## I. Concept map

1. What is the difference between an AI system and a model? Why cannot responsibility be assigned to “the model itself”?
2. What are the usual relationships among ML, DL, generative AI, LLMs, and Agents? Give one AI system that does not use an LLM.
3. How do rule automation, one LLM call, a fixed workflow, and an Agent differ?

Check: [[ai-foundations/01-concept-map/01-ai-map-and-core-terms|AI Map and Core Terms]].

## II. Data, training, and generalization

4. What are algorithms, models, parameters, training, and inference respectively?
5. Among pre-training, fine-tuning, prompting, RAG, and tool calling, which usually change model parameters?
6. How can a training objective, task metric, and system outcome become misaligned? Give an example with valid JSON but a business error.
7. **Key:** Why is a test set no longer independent after repeated prompt tuning against it? What should be done?
8. Give one example each of target leakage, temporal leakage, duplicate leakage, and evaluation contamination.
9. Why is a random row split not always reasonable? Give a case that groups by user, document, or time.

Check: [[ai-foundations/01-concept-map/02-data-model-training-and-inference|Data, Models, Training, and Inference]] and [[ai-foundations/01-concept-map/03-generalization-data-splits-and-leakage|Generalization, Data Splits, and Leakage]].

## III. Evaluation and LLMs

10. What can a baseline, frozen offline set, human review, shadow mode, and online monitoring each find?
11. **Key:** Why can user likes, human acceptance, or scores from another LLM not directly become ground truth?
12. How does an LLM generate output step by step from input text? What do tokens, parameters, context, and decoding each do?
13. Why can lower temperature or more context not guarantee factual correctness?
14. How do internal model token representations relate to, and differ from, text embeddings used for retrieval?

Check: [[ai-foundations/01-concept-map/04-evaluation-evidence-and-feedback-loops|Evaluation Evidence and Feedback Loops]] and [[ai-foundations/01-concept-map/05-how-llms-generate-answers|How LLMs Generate Answers]].

## IV. Agent and failure boundaries

15. Which system parts does an Agent add beyond one LLM call? Why are state, memory, and context not the same concept?
16. **Key:** Why can a tool call not execute directly after its parameters pass JSON Schema?
17. Why cannot prompt injection be solved only by “writing one more sentence saying do not be attacked”?
18. What risks do idempotency, stop conditions, read/write separation, an identity-and-authorization chain, and human approval each control?
19. When an answer is wrong, how do you distinguish failures in data, retrieval, context, generation, tools, and third-party dependencies?

Check: [[ai-foundations/01-concept-map/06-how-agents-complete-tasks|How Agents Complete Tasks]] and [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability Boundaries and Failure Modes]].

## V. Solution, launch, and responsibility

20. **Key:** Given “let AI automatically choose the best candidates,” which questions would you ask first, and how would you narrow the scope?
21. Why should the autonomy ladder begin with read-only information or drafts rather than direct automatic execution?
22. What kinds of releases can a value gate, quality gate, and risk gate each block?
23. How do shadow mode, degradation, rollback, and retirement differ?
24. Why should a third-party model or tool service be re-evaluated after an update that causes no explicit error?
25. **Key:** Under which conditions is human review an effective control?
26. Why cannot trustworthy AI be compressed into one overall score? How can privacy, transparency, explainability, and fairness trade off?
27. Why do high-impact contexts require professional review, access to evidence, and appeal paths?

Check: [[ai-foundations/02-engineering-decisions/08-when-to-use-ai-and-system-shape-selection|When to Use AI and Select a System Shape]], [[ai-foundations/02-engineering-decisions/09-from-prototype-to-launch-and-exit|From Prototype to Launch and Exit]], and [[ai-foundations/02-engineering-decisions/10-responsible-use-and-risk-controls|Responsible Use and Risk Controls]].

## VI. Integrated transfer questions

28. For “internal policy question answering,” draw input, permissions, retrieval, model, citation validation, people, and logs, and mark trust boundaries.
29. For that system, write a rules or search baseline, six test slices, one quality gate, and one retirement condition.
30. For the same requirement, when should you use a fixed workflow, and when should you consider an Agent?
31. If model performance improves but user completion rate falls, in what order would you investigate?
32. If one high-consequence risk cannot be measured reliably, how should a team record and decide on it rather than assuming it is low risk?

These questions have no single technical answer, but every answer must have a clear goal, evidence, ownership, and safe exit. If an answer contains only “optimize the prompt,” “use a stronger model,” or “let people check it,” return to the relevant lesson and redo its exercise.

## Mastery check

- [ ] Can explain AI, ML, DL, LLMs, workflows, and Agents with personal examples.
- [ ] Can distinguish data, parameters, training, inference, context, and feedback.
- [ ] Can design development/test boundaries and critical slices with no obvious leakage.
- [ ] Can attribute a failure to a system layer instead of vaguely saying “the model is not strong enough.”
- [ ] Can compare rules, ML, LLMs, workflows, and Agents and select the minimum viable shape.
- [ ] Can define a baseline, offline threshold, pilot, monitoring, rollback, and retirement.
- [ ] Can explain when human oversight is effective and who is accountable.
- [ ] Can design deterministic validation for output contracts, evidence, permissions, and external actions.
- [ ] Completed [[ai-foundations/03-project-and-self-assessment/11-integrated-project-meeting-action-item-assistant|Integrated Project: Meeting Action-Item Assistant]] and met the project rubric.

## Next route

- Begin engineering capability with [[python-fundamentals/00-index|Python Fundamentals]], [[api/00-index|API]], and [[json/00-index|JSON]].
- Continue model principles in [[machine-learning/00-index|Machine Learning]] and [[deep-learning/00-index|Deep Learning]].
- Continue LLM systems in [[prompt-engineering/00-index|Prompt Engineering]], [[rag/00-index|RAG]], [[tool-calling-function-calling/00-index|Tool Calling]], and [[agent-core/00-index|Agent Core]].
- After recording completion, return to [[ai-foundations/00-index|AI Foundations]] to check the mastery standard.

## References

Accessed **2026-07-22**.

- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- [OECD: Explanatory memorandum on the updated definition of an AI system](https://oecd.ai/en/ai-publications/explanatory-memorandum-on-the-updated-oecd-definition-of-an-ai-system)
