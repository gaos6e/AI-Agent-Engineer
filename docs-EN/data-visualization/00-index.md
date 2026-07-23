---
title: "Data Visualization"
tags:
  - ai-agent-engineer
  - data-visualization
  - learning-path
aliases:
  - Data Visualization Index
  - Data Visualization Learning Path
source_checked: 2026-07-18
source_baseline:
  - Matplotlib 3.11.0 official documentation and release notes
  - scikit-learn 1.9.0 official model-evaluation documentation
  - NIST SEMATECH e-Handbook of Statistical Methods
  - W3C WCAG 2.2 use-of-color guidance
ai_learning_stage: 2. Mathematics and Data Foundations
ai_learning_order: 18
ai_learning_schema: 2
ai_learning_id: data-visualization
ai_learning_domain: evaluation-reliability
ai_learning_catalog_order: 1800
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 900
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 1250
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 900
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 675
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 数据可视化/00-目录.md
translation_source_hash: 6a879f94dc94a1b5de3cc08d7338af13f7c3e58335a7a382a3feae4f788e6dc2
translation_route: zh-CN/数据可视化/00-目录
translation_default_route: zh-CN/数据可视化/00-目录
---

# Data Visualization

## About this knowledge base

Data visualization turns data structures, model errors, and system tradeoffs into evidence that people can inspect. It is not “adding a pretty chart to a report.” First identify the argument and unit of data, then choose visual encodings that expose distributions, uncertainty, and failure modes. Agent Engineers use it to inspect data distributions, classification errors, RAG metrics, cost, latency, and version regressions.

## Place in the overall path

This course appears late in “Mathematics and Data Foundations.” It connects probability and statistics, machine learning, data cleaning, evaluation frameworks, and runtime monitoring. Basic Python lists/dictionaries and statistics are sufficient to begin.

## Learning objectives

- Choose charts from the question and the reader's intended action, rather than from a plotting-library function.
- Present distributions, relationships, change over time, error, and uncertainty correctly.
- Design combined charts for classification, retrieval, Agent operation, and cost evaluation.
- Detect truncated axes, incorrect aggregation, filtering bias, and misleading use of color.
- Produce reproducible static charts with labels and sources using Matplotlib.

## Prerequisites

Be able to create a `venv`, install packages, and run Python 3 in PowerShell 7. Understand means, medians, quantiles, and sample size. If needed, first study [[python-fundamentals/00-index|Python Fundamentals]], [[probability-and-statistics/00-index|Probability and Statistics]], and [[data-cleaning/00-index|Data Cleaning]]. Course examples use fictional aggregate data and require neither a network nor an API key.

## Recommended learning order

1. [[data-visualization/01-from-question-to-chart|From Question to Chart]]: build a “question → data → encoding → action” decision framework.
2. [[data-visualization/02-distributions-and-group-comparisons|Distributions and Group Comparisons]]: prevent averages from hiding long tails and subgroups.
3. [[data-visualization/03-relationships-trends-and-time-series|Relationships, Trends, and Time Series]]: distinguish correlation, change, and aggregation-driven illusions.
4. [[data-visualization/04-error-and-uncertainty|Error and Uncertainty]]: make error bars, confidence intervals, and repeated runs interpretable.
5. [[data-visualization/05-machine-learning-rag-and-agent-evaluation-charts|Machine Learning, RAG, and Agent Evaluation Charts]]: place component metrics alongside system tradeoffs.
6. [[data-visualization/06-misleading-risk-and-accessibility|Misleading Risk and Accessibility]]: audit axes, color, filtering, labels, and sources.
7. [[data-visualization/07-project-agent-evaluation-dashboard|Project: Agent Evaluation Dashboard]]: generate a four-panel offline evaluation chart and interpret it.

## Hands-on practice or project entry point

[[data-visualization/examples/agent_eval_dashboard.py|agent_eval_dashboard.py]] reads strictly validated [[data-visualization/examples/sample_agent_eval.json|fictional evaluation data]], plots success-rate Wilson 95% intervals, tail latency and timeouts, a routing confusion matrix, and cost–success-rate Pareto candidates, then exports PNG, SVG, and text alternative descriptions. The course embeds the [[data-visualization/07-project-agent-evaluation-dashboard#generated-result|generated evaluation dashboard]]. [[data-visualization/examples/test_agent_eval_dashboard.py|Automated tests]] cover the data contract, statistics, exact output dimensions, both export types, and the CLI; dependency versions are recorded in [[data-visualization/examples/requirements.txt|requirements.txt]].

## Mastery criteria

- [ ] Given an analytical question, explain why you chose a particular chart and encoding.
- [ ] When presenting a mean, also consider distribution, sample size, and uncertainty.
- [ ] Read the major errors in a confusion matrix instead of reporting accuracy alone.
- [ ] Audit axis range, binning, aggregation, color, and treatment of missing data.
- [ ] Generate charts with title, axis labels, units, legend, source, and reproducible code.
- [ ] At final size, check missing glyphs, clipping, overlap, grayscale distinguishability, and alternative text.
- [ ] Run normal and `-O` tests and explain Wilson intervals, row-normalized confusion matrices, and Pareto candidates.

## Relationship to the other knowledge-base courses

- [[data-cleaning/00-index|Data Cleaning]] makes the units, missing values, duplicates, and grouping fields shown in a chart trustworthy.
- [[machine-learning/00-index|Machine Learning]] provides classification/regression metrics, training–validation differences, and error-analysis questions.
- [[data-annotation/00-index|Data Annotation]] uses charts to inspect class distributions, annotator bias, and disagreement patterns.
- [[rag/00-index|RAG]], [[evaluation-framework/00-index|Evaluation Framework]], and [[runtime-monitoring/00-index|Runtime Monitoring]] must examine retrieval quality, answer quality, cost, latency, and safety subgroups together rather than compressing them into one overall score.

## Main references

Sources were checked on 2026-07-18. Matplotlib `stable` was 3.11.0 at the time (release notes date 2026-06-11), and scikit-learn `stable` was 1.9.0. Both will continue to change. This knowledge base relies on `requirements.txt` and actual verification records rather than treating a `stable` URL as a permanent version.

- [Matplotlib documentation](https://matplotlib.org/stable/)
- [Matplotlib 3.11 release notes](https://matplotlib.org/stable/users/release_notes)
- [Matplotlib installation and non-interactive backends](https://matplotlib.org/stable/install/index.html)
- [Matplotlib Quick start guide](https://matplotlib.org/stable/users/explain/quick_start.html)
- [Matplotlib Plot types](https://matplotlib.org/stable/plot_types/index.html)
- [Matplotlib: Statistical distributions](https://matplotlib.org/stable/plot_types/stats/index.html)
- [scikit-learn: Visualizations](https://scikit-learn.org/stable/visualizations.html)
- [NIST: Confidence intervals for a binomial proportion](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
- [W3C WCAG 2.2: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
