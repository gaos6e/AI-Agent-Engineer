---
title: "Probability and Statistics: Evaluation Design, Effect Sizes, and
  Statistical Pitfalls"
tags:
  - ai-agent-engineer
  - probability-and-statistics
  - agent-evaluation
aliases:
  - Statistical design for Agent A/B evaluation
  - Evaluation experiment design
source_checked: 2026-07-14
source_baseline:
  - NIST Randomized Block Designs
  - ASA Statement on Statistical Significance and P-Values
related: "[[probability-and-statistics/00-index]]"
lang: en
translation_key: 概率统计/04A-评测设计、效应量与统计陷阱.md
translation_source_hash: fa069b9c05570ae6a0d54d6ee93c08df42aa1b043dbc283240100568e3c20df8
translation_route: zh-CN/概率统计/04A-评测设计、效应量与统计陷阱
translation_default_route: zh-CN/概率统计/04A-评测设计、效应量与统计陷阱
---

# Probability and Statistics: Evaluation Design, Effect Sizes, and Statistical Pitfalls

## Objective

Statistical methods should serve a question defined in advance. By the end of this lesson, you should be able to document the target population, treatment, unit of analysis, primary metric, pairing or randomization method, minimum practically important difference, and stopping rule before running an Agent A/B evaluation. You should also be able to recognize false certainty caused by repeated samples, data leakage, multiple comparisons, and interim peeking.

## Define the estimand first: what exactly will you estimate?

An **estimand** is the precise quantity you want to estimate from data. An executable question should include at least:

```text
Target population: Which users, tasks, languages, times, and environments?
Treatment: How exactly do A and B differ—model, prompt, tool, retrieval, or the whole pipeline?
Unit of analysis: A unique task, user, session, or one generation?
Outcome: Success, quality score, latency, cost, or safety failure?
Aggregation: Macro average, traffic-weighted average, or worst critical subgroup?
Comparison: Absolute B–A difference, relative difference, or non-inferiority to a threshold?
Time horizon: Immediate outcome, seven-day retention, or a full incident cycle?
```

“Is B better?” is not an estimand. A more operational statement is: “On a pre-frozen population of Chinese tool-use tasks, estimate the absolute difference in strict task-level success between B and A; score timeouts as failures; require at least a 3-percentage-point improvement while P95 latency increases by no more than 200 ms.”

## Offline pairing and online randomization answer different questions

### Offline pairing

Give the same task to A and B, yielding $(A_i,B_i)$, and analyze $d_i=B_i-A_i$. Task difficulty affects both versions, so pairing lets each task serve as its own control. If you scramble the correspondence or give the versions different task sets, you lose that advantage.

For stochastic generative models, a common structure is:

```text
Task i
├─ multiple generations from A
└─ multiple generations from B
```

Repeated generations are nested within a task; they are not all mutually independent tasks. You can aggregate at the task level and bootstrap tasks. More complex estimands may require stratified or hierarchical models.

### Online randomization

Randomly assign eligible users or sessions to A or B. This can reduce observed and unobserved confounding, but randomization does not automatically solve:

- enrollment traffic that does not represent future users or other regions;
- cross-group user interference;
- lost logs, failed exposure, or selective attrition;
- correlated requests from the same user; or
- changes in product, traffic, or an external service during the experiment.

The randomization unit must match the intervention and interference boundary. If a user can encounter different versions across sessions, request-level randomization can contaminate the comparison. If assignment is by user, the analysis must respect user clustering too.

## Pairing, blocking, and stratification

NIST describes blocking as controlling an important nuisance factor: compare the main treatments within relatively homogeneous blocks, then randomize factors that cannot be controlled. For Agent evaluation:

- **Pairing**: evaluate both A and B on the same task.
- **Blocking**: compare within blocks such as language, task type, difficulty, or data source.
- **Stratified reporting**: predefine critical subgroups and report the sample size and interval for each.
- **Weighting**: if the evaluation-set composition differs from target traffic, use weights that are justified and defined in advance.

More strata mean fewer observations per stratum and a greater multiple-comparison burden. Do not keep slicing after seeing the results until one subgroup appears “significantly improved.”

## Primary metrics, guardrails, and the minimum practically important difference

Before seeing the data, distinguish:

- **Primary metric**: the main question the experiment is designed to answer; keep these few.
- **Guardrail metric**: a safety, latency, cost, or refusal metric that must not materially worsen.
- **Diagnostic metric**: helps explain a mechanism but does not all carry the primary decision.

The **minimum practically important difference** is a difference too small to justify release, or too small to offset cost. It is not derived from a *p*-value. For example: improve success by at least 3 percentage points, or reduce cost by 15% while quality falls by no more than 1 percentage point.

Interpret intervals alongside that threshold:

| B–A interval | Relation to the +3 pp threshold | Example conclusion |
| --- | --- | --- |
| `[+5,+9]` | Entirely above the threshold | Under the current design, the evidence is compatible with a practically valuable improvement. |
| `[+1,+5]` | Crosses the threshold but not zero | The direction looks positive, but practical value remains uncertain. |
| `[-2,+2]` | Crosses zero and stays below the threshold | Both a small regression and a small improvement remain plausible; evidence is insufficient. |
| `[-1,+1]` | If the equivalence margin was pre-specified as ±2 pp, entirely inside the margin | May support “small enough difference,” but requires a predesigned equivalence framework. |

`pp` means percentage points: 50% to 53% is +3 pp and a 6% relative improvement. Do not confuse the two in a report.

## Intuition for sample size and power

Plan sample size before the experiment around:

- the smallest practically important difference you want to detect;
- the metric's baseline and variability;
- paired correlation or within-user correlation;
- acceptable Type I and Type II error;
- the number of primary comparisons, strata, and expected missingness; and
- generation stochasticity and grader noise.

More samples usually narrow intervals, but repeated, correlated, or biased samples do not add effective information in proportion to their row count. “Low statistical power” is not a universal explanation to invoke after a non-significant result. Instead, specify hypotheses before the study, simulate plausible data structures, and report which effects the interval still permits.

## Multiple comparisons and interim peeking

If you independently test 20 completely null metrics at a 0.05 threshold, the probability of at least one chance-significant result is:

$$1-(1-0.05)^{20}\approx64.2\%$$

Real metrics are often correlated, but this calculation shows why “try enough things and a highlight will appear.” Defenses include:

1. Pre-specify the primary metric, primary comparisons, and key strata.
2. Clearly label exploratory analyses rather than presenting them as confirmatory.
3. When necessary, use a correction aligned with the goal, such as Bonferroni, Holm, or FDR.
4. Keep the record of every attempt, failure, and analysis version.

Repeatedly inspecting results and stopping on the first threshold crossing changes the error rate. When the business needs continual monitoring, use a sequential method or pre-specified looks during design; a fixed-sample test is not a dashboard that can be watched indefinitely.

## Leakage, contamination, and adaptive overfitting

- If prompts, retrieval parameters, or grading rules are repeatedly tuned against a test set, that set has become a development set.
- Near-duplicate variants of the same question spanning development and test sets leak the task template.
- A model may have encountered a public benchmark during training.
- A grading model can share systematic preferences with the model under evaluation.
- Keeping only successfully parsed outputs selectively removes difficult failures.

A confidence interval describes random uncertainty conditional on the data and model; it cannot repair these systematic biases. Freeze an independent holdout, record every decision that touches the test set, and periodically introduce fresh representative tasks.

## Score missingness and failures in advance

Suppose B triggers timeouts more often, but timeout rows never enter the scoring table. Comparing only outputs that returned successfully and were graded may make B look better. Define in advance:

- whether timeouts, refusals, tool exceptions, and parsing failures count as failures, missing values, or separate outcomes;
- whether missingness depends on version or task difficulty;
- how attrition and lost logs are tracked; and
- whether to run a sensitivity analysis, such as scoring unknown outcomes under both best- and worst-case assumptions.

Exclusion rules change the estimand. Every post hoc exclusion must report its count, reason, and effect on the conclusion.

## Evaluation design card

```text
Decision question:
Target population and time window:
Treatment A / B:
Randomization or pairing unit:
Unit of analysis and clustering structure:
Primary metric / guardrail metrics:
Numerator, denominator, and failure scoring:
Minimum practically important difference / non-inferiority margin:
Pre-specified strata and weights:
Sample-size rationale:
Stopping rule and analysis times:
Multiple-comparison strategy:
Holdout and contamination safeguards:
Missing-data and exclusion rules:
Versions, random seeds, and audit record:
```

## Exercises and self-check

1. Rewrite “compare two Agents” as an estimand containing a population, unit, outcome, aggregation, and direction of difference.
2. Draw the hierarchy for an offline evaluation that generates five outputs per Agent for the same task; explain at which level to resample.
3. Design one primary quality metric, two guardrail metrics, and a +3 pp minimum practically important difference.
4. Explain why randomization reduces confounding but does not guarantee the sample represents future traffic.
5. You inspect 12 prompts × 8 metrics and report only the best combination. Name at least three corrective actions.
6. The interval `[+1,+5]` does not cross zero but does cross a +3 pp decision threshold. How should the conclusion be written?

- [ ] I fix the estimand, primary metric, threshold, and stopping rule before seeing results.
- [ ] I distinguish the correlation structure of tasks, generations, users, sessions, and graders.
- [ ] I preserve pairing and block or stratify important nuisance factors.
- [ ] I do not treat statistical significance as effect size or release value.
- [ ] I can identify multiple comparisons, peeking, leakage, missingness, and selective reporting.

Previous: [[probability-and-statistics/estimation-confidence-intervals-and-hypothesis-testing|Estimation, confidence intervals, and hypothesis testing]] | Next: [[probability-and-statistics/project-agent-evaluation-uncertainty|Project: Agent evaluation uncertainty]].

## References

Sources checked on **2026-07-14**.

- [NIST: Randomized Block Designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)
- [NIST: Choosing an Experimental Design](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3.htm)
- [NIST: Confidence Intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm)
- [ASA Statement on Statistical Significance and P-Values](https://www.amstat.org/asa/files/pdfs/P-ValueStatement.pdf)
