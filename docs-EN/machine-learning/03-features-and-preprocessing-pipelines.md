---
title: "Features and Preprocessing Pipelines"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Feature Engineering
  - Machine Learning Pipeline
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/03-特征与预处理管线.md
translation_source_hash: d015dee362a2c50e3a105ba258667f6219dc549d26cb0c965279eaeaa3df357c
translation_route: zh-CN/机器学习/03-特征与预处理管线
translation_default_route: zh-CN/机器学习/03-特征与预处理管线
---

# Features and Preprocessing Pipelines

## Features are not “the more the better”

Features are the numeric representations a model actually receives. Raw data needs transformation, but every transformation must be reproducible at prediction time and must not peek into the future.

| Raw field | Common transformation | Risk |
| --- | --- | --- |
| numeric | missing-value imputation, scaling, log transform | outliers, mixed units |
| categorical | one-hot encoding | unknown categories, high cardinality |
| text | bag of words, TF-IDF, embeddings | near duplicates, private information, length bias |
| time | hour, day of week, time since event | time zone, post-prediction information |

**Feature engineering** is not decorating data. It expresses information relevant to the decision and available at prediction time in a form the model can learn.

## `fit` and `transform`

- `fit`: learn state from data, such as a mean, vocabulary, or category set.
- `transform`: transform new data with learned state.
- `fit_transform`: learn and transform in sequence; use it only in the training region.

If the test set participates in `fit`, leakage occurs. A scikit-learn `Pipeline` binds preprocessing and model together so cross-validation can preserve the boundary.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

model = Pipeline(
    steps=[
        ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 4))),
        ("classifier", LogisticRegression(max_iter=1000)),
    ]
)
model.fit(train_texts, train_labels)
predictions = model.predict(test_texts)
```

Here the TF-IDF vocabulary is learned only from `train_texts`; test text is only transformed.

`Pipeline` can place “fit on each training fold, transform the matching validation fold/test set” in one reproducible object. It cannot determine whether a field is available at prediction time, whether a time window is correct, whether a server schema agrees, or whether text contains personal information or secrets that must not enter the model. Validate those boundaries separately in a data contract and deployment review.

## Intuition for text features

A bag of words counts whether terms occur. TF-IDF further lowers the weight of terms that appear everywhere. It does not truly understand semantics, but is often a strong baseline for short-text classification. An embedding maps text to a dense vector that can represent semantic similarity, but depends on an external model, version, and inference cost.

Build a simple, interpretable, reproducible baseline first, then decide whether embeddings provide stable gains.

## Common mistakes

- Encode labels into text, such as prefixing training documents with their true category.
- Clean training data manually but forget to apply the same rule on the server.
- Apply the same scaling indiscriminately to tree and linear models.
- Treat an ID as a continuous number; the model invents an ordering relationship.
- Save only model weights, not preprocessors and class order.

## Exercise

Design five candidate features for “whether an Agent run needs human review.” For each, state: whether it is available at prediction time, whether it contains sensitive information, how it transforms, and how it could leak.

## Mastery checklist

- [ ] I can distinguish `fit` and `transform` in one sentence.
- [ ] I can explain why a Pipeline reduces leakage risk.
- [ ] I can choose one reasonable representation each for numeric, categorical, and text fields.

Next: [[machine-learning/04-training-validation-and-hyperparameter-tuning|Training, Validation, and Hyperparameter Tuning]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Pipelines and composite estimators](https://scikit-learn.org/stable/modules/compose.html)
- [scikit-learn: Feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html)
- [scikit-learn: Preprocessing data](https://scikit-learn.org/stable/modules/preprocessing.html)
