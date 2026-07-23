---
title: "Machine Learning, RAG, and Agent Evaluation Charts"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - AI Evaluation Visualization
source_checked: 2026-07-14
source_baseline:
  - scikit-learn 1.9.0 official model-evaluation and visualization documentation
  - Matplotlib 3.11.0 official documentation
lang: en
translation_key: 数据可视化/05-机器学习RAG与Agent评测图.md
translation_source_hash: 2c4ee5f9266aa114ba3580ad363a35d4cbef6fb5183e4c530e3bc093db66d27b
translation_route: zh-CN/数据可视化/05-机器学习RAG与Agent评测图
translation_default_route: zh-CN/数据可视化/05-机器学习RAG与Agent评测图
---

# Machine Learning, RAG, and Agent Evaluation Charts

## Objectives

Choose charts that locate failure sources for classifiers, retrieval pipelines, and Agent systems. Present quality, cost, tail latency, timeouts, and safety risk separately instead of compressing them into one overall score.

## Classifiers

- **Confusion matrix:** rows and columns are true/predicted labels; state the direction and whether it is row-normalized.
- **PR curve:** for class imbalance or focus on the positive class, show how precision–recall changes with a threshold.
- **ROC curve:** shows the TPR–FPR tradeoff, but with a very rare positive class also inspect PR and actual counts.
- **Calibration plot:** compare predicted and actual frequency after binning predicted probabilities.
- **Learning curve:** training sample count against training/validation scores, helping decide whether more data collection is worthwhile.

A confusion matrix must state whether “rows are truth and columns are prediction” or the reverse. Absolute counts answer incident scale; row-normalized values answer the recall pattern of each true class. Ideally, show both in each cell as `count / row %`. Normalization does not replace the denominator: a 50% cell may be 1/2 or 500/1000.

PR/ROC are both threshold scans; they do not represent the real cost at a chosen production threshold. A final report should also mark the deployment threshold, precision/recall at that point, positive base rate, and absolute error counts. A calibration plot's bins can also change its appearance, so report the binning method and sample count per bin.

## RAG

At minimum, separate retrieval and generation:

- Retrieval: Recall@k, MRR/nDCG, and similar metrics as `k` changes, split by query type.
- Generation: evidence support, answer correctness, citation accuracy, and appropriate refusal.
- System: end-to-end success rate, latency, tokens, cost, and no-result rate.

If you plot only an overall answer score, you cannot determine whether failure comes from parsing, chunking, retrieval, reranking, or generation.

Use a query as the observational unit and retain slices: head/long-tail query, language, document age, and whether an answer exists. Higher `Recall@k` is not free: context length, latency, and noise can also grow. Interpret quality curves together with cost/latency under the same experimental version.

## Agents

Use a combined “outcome–cost–risk” view:

1. Success rate by task category with sample count/interval.
2. p50/p95 latency and timeout proportion.
3. A stacked view or small multiples for tool-call error types.
4. Scatter plot of per-task cost and success rate, labeling Pareto candidates.
5. Report safety failures separately by severity; do not dilute them with the overall success rate.

In a cost–success scatter plot, a “Pareto candidate” is a point for which no other version has both no greater cost and no lower success rate, with at least one strictly better. It means only that the candidate is not dominated on the current two metrics and current evaluation set; it does not automatically become the best version. Review safety thresholds, p95 latency, and confidence intervals separately.

## Ablation and version comparison

An ablation chart removes one component per run and compares under the same evaluation set, configuration, and randomness design. If multiple factors change at once, call it a version comparison rather than attributing the effect to one component.

## Exercise

For the RAG finding “citation error rate increased,” design three diagnostic charts that inspect data source, retrieval rank, and generated citations. State denominator and slices for each.

One acceptable answer: (1) plot citation-error count and query count by data-source version/document age; (2) plot an ECDF or Recall@k curve by gold-document rank, stratified by query type; (3) plot stacked counts of “supporting evidence was retrieved but citation was wrong” and “supporting evidence was not retrieved.” Use the same frozen query snapshot in all three, retain no-answer and timeout cases, and report absolute counts.

## Mastery check

- [ ] I can explain a confusion matrix's absolute counts, row percentages, and axis direction together.
- [ ] I know PR/ROC curves do not replace actual error counts at the deployment threshold.
- [ ] I plot RAG parsing, retrieval, reranking, generation, and end-to-end failures separately.
- [ ] I can explain the definition and limitation of a Pareto candidate without treating it as an automatic decision.
- [ ] I expose safety failures, timeouts, and critical subgroups separately from the overall mean.

Next: [[data-visualization/06-misleading-risk-and-accessibility|Misleading Risk and Accessibility]].

## References

Sources were checked on 2026-07-14. scikit-learn `stable` was 1.9.0 at the time; recheck visualization APIs in later releases.

- [scikit-learn: Visualizations](https://scikit-learn.org/stable/visualizations.html)
- [scikit-learn: Model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn: Confusion matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)
- [scikit-learn: Precision-Recall](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html)
- [scikit-learn: Calibration curves](https://scikit-learn.org/stable/modules/calibration.html)
