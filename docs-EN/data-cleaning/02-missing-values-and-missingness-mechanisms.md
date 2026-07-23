---
title: "Missing Values and Missingness Mechanisms"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - Missing data
source_checked: 2026-07-14
source_baseline:
  - pandas 3.0 missing-data guide
  - scikit-learn 1.9.0 imputation guide
lang: en
translation_key: 数据清洗/02-缺失值与缺失机制.md
translation_source_hash: 9f1df9b99c7b9d5c02d028dff2c6e4bea73e3c23ce794c85f41ecdb576240e86
translation_route: zh-CN/数据清洗/02-缺失值与缺失机制
translation_default_route: zh-CN/数据清洗/02-缺失值与缺失机制
---

# Missing Values and Missingness Mechanisms

## Objective

Separate missing-data representation, reason, and treatment so that “fill every value with zero” does not hide collection failures, create bias, or leak the test distribution.

## Missingness is not one value

An empty string, **null**, **NaN**, **N/A**, **-1**, and an absent field can all represent missingness, but their semantics differ. Standardize the convention before calculating missingness. Do not use **== np.nan** for a direct comparison; pandas provides **isna()** and **notna()**.

## Why data is missing

- **Missing completely at random (MCAR), approximately**: no material relationship to observed or unobserved information, such as an occasional transmission failure.
- **Missing at random (MAR)**: missingness is related to observed fields, such as a client version that does not upload latency.
- **Missing not at random (MNAR)**: missingness itself is related to the unrecorded value, such as failed calls being more likely to lack cost data.

These are analysis assumptions, not labels that a table alone can prove. They require collection-process knowledge, logs, and domain context.

## Treatment strategies

1. **Repair collection at the source**: for critical fields, fix the upstream producer before relying on imputation.
2. **Retain a missingness indicator**: missingness can be informative, so add a field such as **latency_missing**.
3. **Delete**: use only when missingness is rare, deletion does not create systematic bias, and the field is not critical.
4. **Impute**: a numeric field can use training-set statistics and a categorical field can use explicit **unknown**; validate the impact.
5. **Quarantine**: unexplained missing critical fields enter an issue queue.

In machine learning, mean, median, and similar imputers must be fit only on the training split. Computing statistics on the full dataset before splitting leaks the test distribution.

## Agent and RAG examples

- A tool call's **response** is empty: it might be a timeout, cancellation, parse failure, or a genuine empty result. Use status codes to distinguish them.
- A document title is empty: a filename can yield a candidate, but mark it with **title_source=filename**.
- An evaluation score is empty: do not default it to zero; “not executed” and “execution failed” are different states.

## Exercises and self-check

Choose three fields and write, for each, whether it may be null, possible reasons for missingness, whether it may be imputed, and which bias imputation can introduce. If the reason cannot be explained, preserve the missingness and report it first.

- [ ] I can distinguish an absent field, explicit **null**, an empty string, and a business-level “unknown.”
- [ ] I do not claim MCAR, MAR, or MNAR is proven from the current table alone.
- [ ] I fit training statistics on the training split only, and place missingness indicators and imputation strategy in the Pipeline.
- [ ] I can explain why “not executed,” “execution failed,” and “the real value is zero” cannot be collapsed.

Next: [[data-cleaning/03-duplicates-and-entity-identity|Duplicates and entity identity]].

## References

Sources were checked on 2026-07-14.

- [pandas: Working with missing data](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [scikit-learn: Imputation of missing values](https://scikit-learn.org/stable/modules/impute.html)
- [Little and Rubin: Statistical Analysis with Missing Data](https://doi.org/10.1002/9781119482260)
