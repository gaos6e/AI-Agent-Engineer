---
title: "Inter-Annotator Agreement Metrics"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Inter-Annotator Agreement
  - Cohen's Kappa
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Cohen 1960 original kappa paper
  - Artstein and Poesio 2008 agreement survey
lang: en
translation_key: 数据标注/05-一致性指标.md
translation_source_hash: 2cbba6811f5207476e544b3bd5cfe7bc8b6a904bfcbb379f89c2096d5a09e3cb
translation_route: zh-CN/数据标注/05-一致性指标
translation_default_route: zh-CN/数据标注/05-一致性指标
---

# Inter-Annotator Agreement Metrics

## Objective

Calculate observed and expected agreement and Cohen’s kappa by hand. Identify class imbalance, constant labels, and version breaks. Reduce a total score back to its confusion matrix, strata, conflicts, and sampling uncertainty rather than calling one coefficient label correctness.

## First distinguish reliability, validity, and representativeness

- **Agreement or reliability:** under the same protocol and visible evidence, do annotators make similar judgments?
- **Validity:** do those judgments actually measure the construct declared in the task card? This needs expert evidence, guideline review, outcome analysis, or external criteria.
- **Representativeness:** can the doubly annotated samples describe the target population? This depends on sampling, time, coverage, and missingness, not on the kappa value.

High agreement can represent a shared misunderstanding. High scores on gold items can represent familiarity with leaked items. Agreement from one random subsample cannot automatically generalize online. Metrics are diagnostic signals, not a single certificate that data are ready.

## Percent agreement

For two annotators labeling $N$ samples with the **same input snapshot and version**, with $A$ matching labels:

$$Agreement=\frac{A}{N}$$

This is easy to interpret, but it ignores class marginal distributions. If 95% of samples are helpful and both annotators favor the majority class, agreement can still be very high. Report $N$, class counts, sampling strata, and the content of conflicts alongside it.

## Cohen’s kappa: formula and boundary

For two annotators, complete pairs, and nominal classes:

$$\kappa=\frac{p_o-p_e}{1-p_e}$$

$p_o$ is observed agreement. $p_e$ is expected agreement if the two annotators’ **observed marginal label distributions are paired independently**. It is a stated marginal baseline, not an observable “true chance rate.” When the denominator is nonzero, $\kappa=1$ means complete agreement, 0 means agreement at that baseline, and a negative value means agreement below it.

If both annotators give every sample the same label, $p_o=p_e=1$ and the formula is $0/0$: kappa is **undefined**. Report 100% agreement and “no class variation,” rather than forcing a value of 1. Extreme class imbalance can likewise yield high percent agreement with low or unstable kappa. This is not a problem solved by “fixing” the metric; it is a prompt to inspect the samples, label space, and coverage of risk classes.

Do not mechanically apply a fixed grade such as “0.8 is excellent.” Interpret kappa with, at minimum, the label definition and version, sample size, per-class counts, percent agreement, $p_e$, confusion counts, conflict samples, sampling method, and known limitations.

## Metrics must match the object and sampling design

| Annotation object or design | Usable evidence | Assumptions that still need stating |
| --- | --- | --- |
| Two fixed annotators, complete nominal pairs | Percent agreement, Cohen’s kappa, confusion matrix | Input, guideline, and label space are identical; correctness cannot be inferred |
| More annotators or incomplete coverage | Record the coverage graph; select a metric that supports the number of annotators, missingness, and scale, such as Krippendorff’s alpha | Missingness is not agreement; implementation and distance function must be versioned |
| Ordinal ratings | Raw confusion plus weighted kappa with predeclared weights, or ordinal analysis | Weights represent business distance and cannot be chosen after seeing results |
| Text spans, boxes, or segmentation | Exact match plus boundary or area overlap, such as IoU | Unitization rules, partial overlap, and category match must be defined first |
| Free-text rationales or generative review | Rubric dimensions, sampled expert review, and error taxonomy | Matching strings do not make a rationale reliable or correct |

If the guideline, label space, or input snapshot has changed materially, do not combine old and new batches in one kappa. First use [[data-annotation/04-quality-control-review-and-adjudication#bridging-and-relabeling-after-guideline-changes|bridge samples and relabeling]] to determine the comparable scope, or report the version break side by side.

## Uncertainty and stratified diagnosis

A coefficient from a small double-annotation sample varies. When the sample design supports inference, resample or build a confidence interval over the **complete annotation pair for each sample unit**, retaining strata and pairing. Do not treat two labels from one sample as independent observations. An interval quantifies random uncertainty under that sample design; it cannot repair selection bias, leakage, an incorrect guideline, or uncovered populations.

Prioritize denominators and conflicts by risk stratum, class, source, language, time, difficulty, old or new version, and annotator role. For example, helpful ↔ not_helpful concentration can mean the completion standard is unclear; unsafe ↔ not_helpful concentration can mean priority or escalation conditions are unclear. The next step is guideline repair, pilot annotation, and relabeling, not merely raising an overall score.

## Hand-calculation exercise

Two annotators label 20 samples and agree on 16. Annotator A selects helpful 12 times, and B selects it 10 times; all other labels are not_helpful. Calculate $p_o$, $p_e$, and kappa, then explain why the conflict content still matters.

Check: $p_o=16/20=0.8$. The helpful proportions for A and B are 0.6 and 0.5, so $p_e=0.6\times0.5+0.4\times0.5=0.5$ and $\kappa=(0.8-0.5)/(1-0.5)=0.6$. The value still does not reveal which rule caused a conflict, whether gold cases are correct, whether samples represent online traffic, or whether a new version is comparable.

## Mastery check

- [ ] I can compute $p_e$ from the two annotators’ marginal proportions and explain its baseline.
- [ ] I know how to report the limits of undefined kappa, extreme imbalance, small samples, and version changes.
- [ ] I report sample size, label distribution, agreement, kappa, confusion counts, conflicts, and stratified denominators together.
- [ ] I do not use a fixed threshold, a confidence interval, or one overall score as a substitute for validity and representativeness review within this task.

Next: [[data-annotation/06-active-learning-and-human-in-the-loop|Active Learning, Weak Supervision, and Human-in-the-Loop Work]].

## References

Sources checked on 2026-07-22.

- Cohen, J. (1960). [A coefficient of agreement for nominal scales](https://doi.org/10.1177/001316446002000104)
- Artstein, R., & Poesio, M. (2008). [Survey Article: Inter-Coder Agreement for Computational Linguistics](https://aclanthology.org/J08-4004/)
- Krippendorff, K. (2011). [Computing Krippendorff's Alpha-Reliability](https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf)
