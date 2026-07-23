---
title: "Misleading Risk and Accessibility"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - Visualization Integrity
source_checked: 2026-07-14
source_baseline:
  - Matplotlib 3.11.0 official colormap and export documentation
  - W3C WCAG 2.2 use-of-color and non-text-content guidance
lang: en
translation_key: 数据可视化/06-误导风险与可访问性.md
translation_source_hash: 97c57c8225996427483923ace3ed99d0d906ff2f57719499d3cefd48ad83f3c9
translation_route: zh-CN/数据可视化/06-误导风险与可访问性
translation_default_route: zh-CN/数据可视化/06-误导风险与可访问性
---

# Misleading Risk and Accessibility

## Objectives

Audit charts across six dimensions—axes, denominators, filtering, color, text, and exported files—and establish a loop of “render → programmatic checks → human reading → revision.”

## Common ways charts mislead

- A truncated y-axis makes a small bar-chart difference appear enormous.
- Histogram bins are changed to show only a shape that supports the conclusion.
- Latency is compared only after successful runs are filtered in.
- Cumulative values hide recent regressions, or percentages hide absolute counts.
- 3D perspective occludes back bars and makes areas difficult to compare.
- Dual y-axes create correlation through arbitrary range adjustment.
- A smoothed trend appears without raw variation and anomalies.

During review, ask: how was data filtered? What is the denominator? Where did missing values go? Are axes comparable? Does aggregation hide a subgroup? Does the conclusion remain under a different reasonable parameter choice?

## Color and accessibility

Color must not be the only encoding. Pair safety/failure with shape, line style, text, or direct labels. Use perceptually uniform, color-vision-deficiency-friendly colormaps; use continuous ramps for ordered data, discrete colors for categories, and diverging ramps with a clear center for positive/negative deviations.

W3C WCAG 2.2 “Use of Color” requires that information not be conveyed by color alone. Data charts can use redundant encoding with “color + marker/line style/texture/direct label.” For one-directional continuous values, start with perceptually more uniform maps such as `viridis`, `magma`, or `cividis`. Use a diverging map with a locked symmetric range only when values are positive and negative and zero is a meaningful business center. Do not use `jet/rainbow` to create uneven lightness boundaries.

Ensure sufficient text/background contrast, readable font size, and a legend close to the data. For external publication, provide brief alternative text: what the chart shows, the main trend, the key anomaly, and the data range.

## Annotation and sources

Every deliverable chart needs at least a title, axis labels, units, legend/direct labels, time window, sample count or denominator, error-bar meaning, and data/code version. A title may state an observation; it should not overstate causality.

Alternative text is not a spoken inventory of colors and decoration. It describes chart type and data range, primary comparison, key anomaly, denominator/interval, and limits on interpretation. Complex charts should also provide the underlying table or downloadable data. Text conclusions must be generated from the same frozen data as the chart so alternative text does not preserve old numbers after a chart update.

## Reproducible export and visual self-check

1. Create the `Figure` at final delivery size, with consistent fonts, units, color semantics, and panel order.
2. Render a high-resolution PNG preview first while retaining vector SVG/PDF versions; do not use JPEG for data charts.
3. Have code check missing-glyph warnings, canvas boundaries, tick overlap, panel count, pixel dimensions, and output signatures.
4. Open the PNG and inspect whether the legend obscures data, text/color blocks have contrast, subplots align, and the chart remains distinguishable in grayscale.
5. Render again after revisions. The final file must be rebuildable from locked dependencies, an input snapshot, and the script.

`bbox_inches="tight"` or constrained layout is a fallback, not a substitute for human reading. In particular, heatmap cell text can lose contrast on dark/light backgrounds; a program that does not understand semantics can still “pass formally while being unreadable.”

## Pre-publication checklist

- [ ] Bar lengths start from a reasonable common baseline.
- [ ] Colors remain distinguishable in grayscale or for differing color vision.
- [ ] Failures, timeouts, missing values, and small samples are not hidden.
- [ ] Uncertainty, filtering, and aggregation methods appear in the caption.
- [ ] Numbers on the chart can be recomputed from underlying data.
- [ ] The export is free from clipping, overlap, and garbled glyphs at delivery size.

## Exercise

Find an internal evaluation chart and audit it from the perspectives of axes, denominator, missingness, color, and provenance. Rewrite its conclusion so it contains only what evidence in the chart supports.

## Mastery check

- [ ] I can identify misleading paths from truncated axes, selective binning, successful-sample filtering, and dual y-axes.
- [ ] I do not distinguish categories by color alone and check grayscale plus direct labels.
- [ ] I can select an appropriate colormap for continuous, diverging, and categorical data and provide a colorbar/units.
- [ ] I export both a previewable raster and vector chart, then read the chart at final size.
- [ ] I can write alternative text containing the main trend, key anomaly, denominator, and limitations.

Next: [[data-visualization/07-project-agent-evaluation-dashboard|Project: Agent Evaluation Dashboard]].

## References

Sources were checked on 2026-07-14. Matplotlib colormap pages were checked against 3.11.0; web-accessibility principles were checked against W3C WCAG 2.2.

- [Matplotlib: Choosing Colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html)
- [Matplotlib: Customizing with style sheets](https://matplotlib.org/stable/users/explain/customizing.html)
- [Matplotlib `Figure.savefig`](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html)
- [W3C WCAG 2.2: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
- [W3C WCAG 2.2: Non-text Content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)
