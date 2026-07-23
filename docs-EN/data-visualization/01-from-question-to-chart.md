---
title: "From Question to Chart"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - Chart Selection
  - Chart-Selection Method
source_checked: 2026-07-14
source_baseline:
  - Matplotlib 3.11.0 official quick-start and plot-type documentation
  - W3C WCAG 2.2 use-of-color guidance
lang: en
translation_key: 数据可视化/01-从问题到图表.md
translation_source_hash: 9ee3177a5fb70c7d6dc87e7887deb224de9690520ca69afd85a88808be713005
translation_route: zh-CN/数据可视化/01-从问题到图表
translation_default_route: zh-CN/数据可视化/01-从问题到图表
---

# From Question to Chart

## Objectives

Turn the vague request “plot the data” into a testable question. Identify the observational unit, variable type, sample size, and reader action, then choose a chart type rather than choosing a library function first.

## Write the question and action first

“Plot the Agent data” has no acceptance criterion. Rewrite it as: “Compare the success rates of v1 and v2 on refund, technical, and account tasks, then decide whether to release v2 to everyone.” The question determines the required version, task category, success indicator, sample count, and uncertainty.

First write a falsifiable chart claim, such as “v2 has higher overall success on the same frozen task set, but technical tasks did not improve.” Then record what each point/count represents, whether observations are independent, whether denominators match, and whether failures and missing values remain. If you cannot answer those questions, return to data cleaning and experiment design rather than adjusting colors.

## A four-step selection framework

1. **Question:** distribution, comparison, relationship, change over time, composition, or process?
2. **Data unit:** is each point one run, one daily aggregate, or one model version?
3. **Visual encoding:** position and length are normally easier to compare precisely than area, angle, or 3D volume.
4. **Action:** after reading, should someone choose a version, investigate an anomaly, or adjust a threshold?

| Question | Preferred starting point | Watch for |
| --- | --- | --- |
| Distribution of one variable | histogram / ECDF / boxplot | Binning and long tails |
| Numeric comparison across categories | dot plot or bar chart | Category order and zero baseline |
| Relationship between two numbers | scatter plot | Overplotting and common causes |
| Change over time | line chart | Time granularity and missing intervals |
| Classification errors | confusion matrix | Absolute counts and normalization denominator |
| Tradeoff between two metrics | scatter plot + labels | A hidden third variable |

A table is often better for a small number of exact values; charts suit patterns, differences, and anomalies.

Sample size also changes the choice. For fewer than 10 observations per group, prefer showing every point directly. With 10–30 observations, use a box/violin plot only with overlaid raw points. For many points, use transparency, hexbin, or stratified sampling. When there are more than about six categories, a legend is hard to remember, or one chart must carry several claims, split it into small multiples or multiple charts.

## Figure, Axes, and data

In Matplotlib, a `Figure` is the complete canvas and an `Axes` is one panel with a coordinate system. Prefer the explicit form:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot([1, 2, 3], [120, 150, 210], marker="o")
ax.set(title="Agent latency", xlabel="Run", ylabel="Latency (ms)")
fig.tight_layout()
```

An explicit `ax` suits multi-panel and testable code better than relying on the current global plot.

`figsize` uses inches and font size uses points (pt). Decide the final display size before plotting so text remains readable after use in Word, PowerPoint, or a web page. Scripted exports should use a non-interactive backend such as `Agg`. Prefer retaining vector SVG/PDF versions for lines, text, and point plots, while generating PNG for quick preview.

## Exercise

Choose one chart for each question and state its denominator: error rate for different tools; p95 latency over one week; and the tradeoff between cost and task success.

Then perform a reverse check: if you replace the chart with a table, change a reasonable binning choice, or stratify by task type, does the conclusion still hold? If it holds only under one set of visual parameters, do not treat it as robust evidence.

## Mastery check

- [ ] I can state in one sentence the question a chart answers and the action a reader should take afterward.
- [ ] I can explain the observational unit and denominator for every point, line, or matrix cell.
- [ ] I can propose a preferred chart and at least one alternative based on variable type, sample size, and argument.
- [ ] I know when to use a table, when to split a chart, and why I avoid pie charts, 3D charts, and dual y-axes.
- [ ] I set a `Figure` at final size and use the explicit `Axes` API.

Next: [[data-visualization/02-distributions-and-group-comparisons|Distributions and Group Comparisons]].

## References

Sources were checked on 2026-07-14; API examples were checked against Matplotlib 3.11.0 official documentation.

- [Matplotlib Quick start guide](https://matplotlib.org/stable/users/explain/quick_start.html)
- [Matplotlib Plot types](https://matplotlib.org/stable/plot_types/index.html)
- [Matplotlib `pyplot.figure`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.figure.html)
- [W3C WCAG 2.2: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
