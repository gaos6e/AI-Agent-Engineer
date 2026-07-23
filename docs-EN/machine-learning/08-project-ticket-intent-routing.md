---
title: "Project: Ticket Intent Routing"
tags:
  - ai-agent-engineer
  - machine-learning
  - project
aliases:
  - Ticket Router Project
source_checked: 2026-07-22
source_baseline:
  - scikit-learn 1.9.0 official documentation
  - Python 3.11.9 isolated runtime validation (2026-07-20 historical snapshot)
  - scikit-learn 1.7.1 local compatibility check with warnings promoted to
    errors (2026-07-22)
lang: en
translation_key: 机器学习/08-项目-工单意图路由.md
translation_source_hash: 5613ff974e381c0a54833c7aab616b392180d3c84a6e912c46f131be97a918d6
translation_route: zh-CN/机器学习/08-项目-工单意图路由
translation_default_route: zh-CN/机器学习/08-项目-工单意图路由
---

# Project: Ticket Intent Routing

## Project goal

Train a completely offline, small classifier that routes English teaching tickets into three classes: `account`, `refund`, and `technical`. The project runs both a majority-class baseline and a character TF-IDF plus logistic-regression Pipeline, outputting macro F1, a confusion matrix, and error examples with confidence. The point is not to chase a high score, but to complete the loop of data validation, stratified splitting, preprocessing boundaries, evaluation, and tests.

Implementation: [[machine-learning/examples/ticket_router.py|ticket_router.py]] | Tests: [[machine-learning/examples/test_ticket_router.py|test_ticket_router.py]] | Dependencies: [[machine-learning/examples/requirements.txt|requirements.txt]].

## Data and decision boundary

- The 24 teaching examples are hand-authored, not real user data; each of the three classes has eight examples.
- A fixed `random_state=42` produces a stratified split: 18 training examples, 6 test examples, and 2 test examples per class.
- Identical text is explicitly rejected to prevent obvious duplicates across sets. Semantic near duplicates still need human review.
- The project evaluates one fixed offline split only. It has no independent validation set, so test results must not drive further tuning.
- Routing results are for instructional display only. A real system also needs a low-confidence human fallback, privacy review, and drift monitoring.

## Environment and execution

In Windows 11 PowerShell 7, run from the project root. Put the virtual environment in a temporary directory outside the vault, and always call that environment's interpreter explicitly:

```powershell
$exampleDir = (Resolve-Path '.\docs-EN\machine-learning\examples').Path
$practice = Join-Path $env:TEMP ("ticket-router-{0}" -f [guid]::NewGuid())
$python = Join-Path $practice 'Scripts\python.exe'

py -3.11 -m venv $practice
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $exampleDir 'requirements.txt')
& $python -m pip check
& $python -B (Join-Path $exampleDir 'ticket_router.py')
& $python -B -O (Join-Path $exampleDir 'ticket_router.py')
& $python -B -W error (Join-Path $exampleDir 'ticket_router.py')
& $python -B -O -W error (Join-Path $exampleDir 'ticket_router.py')
& $python -B -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
```

`$practice` is in the system temporary directory, so the virtual environment is not written into the knowledge base. It can be removed after validation once its exact resolved path has been checked. Script execution makes no network calls and uses no real user data or secrets; only dependency installation accesses a package index. `requirements.txt` pins the direct dependency verified for this course, `scikit-learn==1.9.0`, but does not lock transitive dependencies such as NumPy and SciPy, so it is not a complete reproducible production lockfile. After upgrading direct or transitive dependencies, rerun all tests and inspect release notes.

## Seven things to notice while reading the code

1. **Validate data first**: `validate_samples` rejects nulls, blank text, exact duplicate text, one-class data, and classes with too few examples. It can detect only literal duplicates; semantic near duplicates still need human review.
2. **Stratify by index**: `split_dataset` uses `stratify=labels`, giving two test examples for each of three classes. A fixed random seed makes this split reproducible; it does not create multiple independent experiments.
3. **Build a weak baseline first**: `DummyClassifier(strategy="most_frequent")` always predicts the training set's majority class. If a model cannot reliably beat it, complex features have no engineering value.
4. **Seal fitting inside a Pipeline**: character TF-IDF `fit`s only on training text and transforms test text with the same vocabulary. Calling `fit_transform` on all text first leaks test information.
5. **Use a fixed reproducible model configuration**: character 2–4 grams capture short fragments and logistic regression classifies. Pinned scikit-learn 1.9.0 uses L2 regularization by default. The example does not explicitly pass `penalty`, whose old use is under deprecation, or `l1_ratio=0.0`, which produces invalid warnings in older versions. Consult the matching documentation and rerun tests when changing versions.
6. **Read metrics together**: accuracy answers overall correctness; macro F1 weights every class equally; the confusion matrix shows error direction; and `support` in the classification report reminds you that every class has only two test examples.
7. **Review errors one by one**: the script prints misclassified text, true label, predicted label, and maximum prediction probability. That probability is not calibrated; it is a ranking/debugging clue, not a literal “chance of correctness” or automatic deployment threshold.

## Actual output and interpretation

The English-localized teaching data and fixed split produced the following summary in scikit-learn 1.9.0:

```text
train=18 test=6 random_state=42
labels=account,refund,technical
baseline-accuracy=0.333
accuracy=0.667 macro-f1=0.667
confusion-matrix rows=true columns=predicted
- account: (1, 1, 0)
- refund: (0, 2, 0)
- technical: (0, 1, 1)
```

The model improves on the 0.333 majority-class baseline, but the test set has only six examples: 0.667 means only four predictions are correct and is not evidence of generalization. The two errors are:

- “My account was locked unexpectedly”: `account -> refund`, maximum prediction probability about 0.358;
- “The API request returns a server error”: `technical -> refund`, maximum prediction probability about 0.375.

Both values are close to uniform three-class probability `1/3`, which looks more like uncertainty than a reliable decision. The original Chinese-language source fixture has a different lexical snapshot; because this English counterpart localizes reader-facing training text, character features and error examples differ. In both cases, the next step is to expand and review data, create a validation split or cross-validation inside training data, then select features, thresholds, or models. Do not repeatedly tune after seeing these six test outcomes.

## Test coverage and reproducibility boundary

[[machine-learning/examples/test_ticket_router.py|The test file]] contains ten regression checks covering class balance and deduplication, reproducible/exclusive splitting, stratified result, Pipeline structure, metric boundaries, confusion-matrix shape, error records, invalid input, CLI output, and evaluation with all warnings promoted to errors. Invalid-input tests also cover `random_state` outside scikit-learn's supported non-negative 32-bit range.

- The historical isolated environment (2026-07-20) recorded the source page's numerical snapshot and nine tests under Python 3.11.9 and scikit-learn 1.9.0; that environment has been removed.
- The source course's review environment (2026-07-22) already had scikit-learn 1.7.1 and did not install or replace dependencies; its corrected ten tests and script passed normal, `-O`, `-W error`, and `-O -W error`. That checks warning handling across versions but does not replace revalidation in the pinned 1.9.0 environment.
- Direct dependency is pinned as `scikit-learn==1.9.0` in [[machine-learning/examples/requirements.txt|requirements.txt]]. Transitive dependencies resolve at installation time; this project does not yet provide a full lockfile.

These checks prove the example is reproducible in verified environments. They do not prove teaching data represents real tickets or that every scikit-learn version is compatible.

> [!note] Historical pinned-environment snapshot (2026-07-20)
> In a Python 3.11.9 isolated environment outside the vault, nine source-fixture tests passed once each in normal, `-O`, `-W error`, and `-O -W error` modes under scikit-learn 1.9.0 (then resolved to NumPy 2.4.6 and SciPy 1.17.1). This record explains the source page's numerical snapshot; the temporary environment was removed, and transitive versions were not a complete lock.

## Acceptance tasks

- [ ] Run normal, `-O`, `-W error`, `-O -W error`, and the ten tests in sequence, and explain what each mode can reveal.
- [ ] Compute accuracy from output: four correct predictions out of six gives `4 / 6 ≈ 0.667`.
- [ ] Explain every confusion-matrix row, identifying one `account -> refund` and one `technical -> refund`.
- [ ] Explain why the current test set cannot choose 2–4 grams versus 2–5 grams, and draw training/validation/test boundaries.
- [ ] Change one clearly refund-oriented sentence into an ambiguous **new input** and observe prediction; do not modify the model then report the same test score again.
- [ ] Design a data plan for a new `invoice` class: define label boundaries, collect and deduplicate, then resplit stratified data; do not append only one or two examples.
- [ ] Propose one data-level improvement and one system-level fallback for each existing error, and explain why maximum prediction probability is not calibrated confidence.

## Advanced but still controlled

- Move embedded examples to UTF-8 CSV and record a data version.
- Select a human-review threshold with independent validation data. If probability must express reliability, compare reliability diagrams or Brier score before/after calibration.
- Build test sets by source or time to inspect distribution change.

## Common mistakes and investigation

| Mistake | Why it is a problem | Repair |
| --- | --- | --- |
| Treat a result as stable after fixing one random seed | it only makes one split reproducible | add data and assess variation through cross-validation or multiple predefined splits |
| Change n-gram after viewing test results | the test set becomes a hidden validation set | tune inside training data; use test data only for final evaluation |
| Treat maximum `predict_proba` as true confidence | classification probability may be uncalibrated, especially with little data | first validate calibration quality, then use validation data to choose a human-review threshold |
| Remove only exact duplicate text | paraphrases can still leak across sets | group by session, user, source, or time, and review semantic near duplicates |
| Substitute real tickets directly | they may contain names, account numbers, phone numbers, and business secrets | first design authorization, minimization, redaction, retention, and access control |
| After dependency upgrade, only see whether script starts | defaults, deprecated parameters, and metric behavior can change | read official release notes and rerun normal, `-O`, warnings-as-errors, and unit tests |

## Self-check

1. Why cannot you run `fit_transform` over all text before splitting?
2. Why is one high score on a small sample insufficient deployment evidence?
3. What do macro F1 and sample-weighted F1 respectively tend to reveal or hide?
4. If the model treats “money” as a refund shortcut, how can error analysis repair it?

Completion standard: independently reproduce the project, explain its data boundaries, show error examples, and propose at least one data-level and one model-level improvement.

Return to [[machine-learning/00-index|Machine Learning Index]].

## References

Material acquisition and runtime review date: 2026-07-22. The project API explanation follows official scikit-learn 1.9.0 documentation. Numerical output above was reproduced in an isolated 1.9.0 environment after English-localized fixture data; source-language numbers remain historical snapshot evidence only. When installing another version, follow that version's documentation and actual test results.

- [scikit-learn: Working with text data](https://scikit-learn.org/stable/tutorial/text_analytics/working_with_text_data.html)
- [scikit-learn: Pipeline](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html)
- [scikit-learn: Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [scikit-learn: LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)
- [scikit-learn: Classification metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics)
- [scikit-learn: CalibratedClassifierCV](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html)
- [scikit-learn 1.9 release history](https://scikit-learn.org/stable/whats_new.html)
