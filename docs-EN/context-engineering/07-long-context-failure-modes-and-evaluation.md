---
title: "Long-Context Failure Modes and Evaluation"
tags:
  - context-engineering
  - long-context
  - evaluation
aliases:
  - Long-Context Evaluation
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - Lost in the Middle original paper
  - LongBench original paper
  - Google Gemini Long Context documentation
  - Anthropic Context Windows documentation
lang: en
translation_key: 上下文工程/07-长上下文失效模式与评测.md
translation_source_hash: bcffb6d6416653672b79d8b861c05d901a00c6d80d8e91cc1a2395388aa7a6b7
translation_route: zh-CN/上下文工程/07-长上下文失效模式与评测
translation_default_route: zh-CN/上下文工程/07-长上下文失效模式与评测
---

# Long-Context Failure Modes and Evaluation

## Objective

Turn “the model supports a long window” into evidence on concrete tasks. Test degradation in position, conflict, interference, citation, and budget.

## Fitting is not the same as finding or using correctly

Research shows that a model can be sensitive to the position of relevant information in a long context, with performance potentially declining when the information is in the middle. As effective context grows, recall and accuracy can also show context rot. There is no fixed degradation curve that applies to every model and task. Papers, single-needle retrieval demonstrations, and provider benchmarks are clues only; reproduce them with your own model snapshot, document length, language, number of evidence items, and question type.

Common failure modes include:

- **Position omission**: The system answers when a key fact is at the beginning but misses it in the middle.
- **Interference**: Many similar but irrelevant chunks overwhelm the true evidence.
- **Conflict-handling failure**: Old and new policies appear together, but the system chooses the old one.
- **Citation drift**: The answer is correct but cites another passage, or the cited ID does not exist.
- **Instruction contamination**: A command inside a document is treated as an application instruction.
- **Truncation and budget degradation**: Output or tool descriptions are crowded out of the budget.
- **Incomplete multi-evidence reasoning**: The system finds one needle but misses other evidence needed to complete a comparison.
- **Tool-history expansion**: Old tool results and failed retries remain for too long and obscure current state.

## A minimal evaluation matrix

Construct the same question with:

| Variable | Example values |
| --- | --- |
| Evidence position | Beginning / middle / end |
| Amount of interference | None / little / much |
| Number of required evidence items | One / several complementary / several distributed |
| Source relationship | Consistent / old-versus-new conflict / authoritative-versus-nonauthoritative conflict |
| Representation | Original text / table / summary |
| Injection text | None / direct / indirect |
| History type | Documents only / multi-turn messages / tool calls and results |

Check answer correctness, required-evidence coverage, citation validity, conflict explanation, whether refusal is appropriate, input/output/cache usage, and latency. Repeat nondeterministic outputs and record the model and context-strategy version. Run the same matrix after changing selection, ordering, summarization, compaction, or cache strategy; a cache hit must not change the quality bar.

## When to split a task

If a question contains several independent subtasks, retrieve and answer each subquestion first, then merge them in a final step. If it requires a global comparison, preserve consistent fields across documents. Splitting adds calls and opportunities for error propagation, so validate it through task metrics rather than assuming it is better.

## Exercise and self-check

Using three simulated documents with twenty sections each, place the sole answer in sections 1, 10, and 20 respectively, and add one stale conflict. Define a passing standard in which the answer, source ID, and effective date are all correct. Self-check: what errors would be missed by testing only whether the answer contains a keyword?

## Mastery check

- [ ] I test evidence position, length, interference, conflict, multiple evidence, injection, and tool history rather than only the maximum window.
- [ ] Every experiment fixes the model and context-strategy version and repeats critical cases.
- [ ] Passing criteria cover answer, completeness, provenance, freshness, permission, safety, usage, and latency together.
- [ ] I do not treat single-needle retrieval success or provider showcase numbers as quality evidence for my own task.
- [ ] The choice among task splitting, long context, RAG, and compaction is compared by the same task-level evaluation.

## Next

Continue to [[context-engineering/08-context-pack-project-and-self-test|Context Pack Project and Self-Test]].

## References

- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (original paper)
- Bai et al., [LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding](https://arxiv.org/abs/2308.14508) (original paper)
- [Anthropic: Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) (accessed 2026-07-21)
- [Google: Long context](https://ai.google.dev/gemini-api/docs/long-context) (accessed 2026-07-21)

