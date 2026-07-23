"""Train and evaluate a tiny offline English ticket-intent classifier."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from sklearn import __version__ as sklearn_version
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


Sample = tuple[str, str]

SAMPLES: tuple[Sample, ...] = (
    ("I keep seeing an incorrect password message when I sign in", "account"),
    ("I changed my phone and no longer receive verification codes", "account"),
    ("How do I change the email linked to my account", "account"),
    ("My account was locked unexpectedly", "account"),
    ("How can I reset a forgotten password", "account"),
    ("I cannot complete two-factor authentication", "account"),
    ("Please close my old account", "account"),
    ("Can I change my username", "account"),
    ("I was charged twice and need a refund", "refund"),
    ("I changed my mind after purchase and want a refund", "refund"),
    ("My membership was canceled but the money has not arrived", "refund"),
    ("I paid for an order by mistake", "refund"),
    ("The order was canceled, please refund it", "refund"),
    ("My refund request is still under review", "refund"),
    ("I was charged during the trial and want it refunded", "refund"),
    ("The invoice amount is wrong and I want to reverse payment", "refund"),
    ("The page stays blank after it opens", "technical"),
    ("File uploads keep failing", "technical"),
    ("The API request returns a server error", "technical"),
    ("The application crashes immediately after launch", "technical"),
    ("Search results never finish loading", "technical"),
    ("A button stopped working after the update", "technical"),
    ("My network works but the application will not sync", "technical"),
    ("Exported files contain garbled text", "technical"),
)


@dataclass(frozen=True)
class DatasetSplit:
    train_texts: tuple[str, ...]
    test_texts: tuple[str, ...]
    train_labels: tuple[str, ...]
    test_labels: tuple[str, ...]
    random_state: int


@dataclass(frozen=True)
class PredictionError:
    text: str
    expected: str
    predicted: str
    confidence: float


@dataclass(frozen=True)
class EvaluationResult:
    split: DatasetSplit
    labels: tuple[str, ...]
    baseline_accuracy: float
    accuracy: float
    macro_f1: float
    confusion: tuple[tuple[int, ...], ...]
    report_text: str
    errors: tuple[PredictionError, ...]


def validate_samples(samples: Sequence[Sample]) -> tuple[Sample, ...]:
    """Validate the teaching dataset and return normalized immutable rows."""

    try:
        rows = list(samples)
    except TypeError:
        raise ValueError("samples must be a sequence of (text, label) rows") from None
    if not rows:
        raise ValueError("samples must not be empty")

    normalized: list[Sample] = []
    seen_texts: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise ValueError(f"sample {index} must contain text and label")
        text, label = row
        if not isinstance(text, str) or not isinstance(label, str):
            raise ValueError(f"sample {index} text and label must be strings")
        clean_text = text.strip()
        clean_label = label.strip()
        if not clean_text or not clean_label:
            raise ValueError(f"sample {index} text and label must not be empty")
        if clean_text in seen_texts:
            raise ValueError(f"duplicate text detected: {clean_text!r}")
        seen_texts.add(clean_text)
        normalized.append((clean_text, clean_label))

    counts = Counter(label for _, label in normalized)
    if len(counts) < 2:
        raise ValueError("classification requires at least two labels")
    if min(counts.values()) < 4:
        raise ValueError("each label needs at least 4 samples for a stratified split")
    return tuple(normalized)


def split_dataset(
    samples: Sequence[Sample],
    *,
    test_size: float | int = 0.25,
    random_state: int = 42,
) -> DatasetSplit:
    """Create a deterministic stratified split over unique teaching rows."""

    rows = validate_samples(samples)
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise ValueError("random_state must be an integer")
    if not 0 <= random_state <= 2**32 - 1:
        raise ValueError("random_state must be in [0, 2**32 - 1]")
    if isinstance(test_size, bool) or not isinstance(test_size, (int, float)):
        raise ValueError("test_size must be a fraction or a positive integer")
    if isinstance(test_size, float) and not 0.0 < test_size < 1.0:
        raise ValueError("a float test_size must be in (0, 1)")
    if isinstance(test_size, int) and not 0 < test_size < len(rows):
        raise ValueError("an integer test_size must be between 1 and the sample count")

    indices = list(range(len(rows)))
    labels = [label for _, label in rows]
    try:
        train_indices, test_indices = train_test_split(
            indices,
            test_size=test_size,
            stratify=labels,
            random_state=random_state,
        )
    except ValueError as exc:
        raise ValueError(f"class counts cannot support a stratified split: {exc}") from exc

    return DatasetSplit(
        train_texts=tuple(rows[index][0] for index in train_indices),
        test_texts=tuple(rows[index][0] for index in test_indices),
        train_labels=tuple(rows[index][1] for index in train_indices),
        test_labels=tuple(rows[index][1] for index in test_indices),
        random_state=random_state,
    )


def build_model() -> Pipeline:
    """Build a leakage-resistant text preprocessing and classifier pipeline."""

    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(analyzer="char", ngram_range=(2, 4)),
            ),
            (
                "classifier",
                LogisticRegression(
                    solver="lbfgs",
                    max_iter=1_000,
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate(
    samples: Sequence[Sample] = SAMPLES,
    *,
    test_size: float | int = 0.25,
    random_state: int = 42,
) -> EvaluationResult:
    """Fit the baseline and pipeline, then return auditable test metrics."""

    split = split_dataset(
        samples,
        test_size=test_size,
        random_state=random_state,
    )
    labels = tuple(sorted(set(split.train_labels) | set(split.test_labels)))

    baseline = DummyClassifier(strategy="most_frequent")
    baseline_features = [[0.0] for _ in split.train_labels]
    baseline.fit(baseline_features, split.train_labels)
    baseline_predictions = baseline.predict(
        [[0.0] for _ in split.test_labels]
    )

    model = build_model()
    model.fit(split.train_texts, split.train_labels)
    predictions = model.predict(split.test_texts)
    probabilities = model.predict_proba(split.test_texts)

    errors: list[PredictionError] = []
    for text, expected, predicted, row_probabilities in zip(
        split.test_texts,
        split.test_labels,
        predictions,
        probabilities,
    ):
        if expected != predicted:
            errors.append(
                PredictionError(
                    text=text,
                    expected=expected,
                    predicted=str(predicted),
                    confidence=float(max(row_probabilities)),
                )
            )

    matrix = confusion_matrix(split.test_labels, predictions, labels=labels)
    return EvaluationResult(
        split=split,
        labels=labels,
        baseline_accuracy=float(
            accuracy_score(split.test_labels, baseline_predictions)
        ),
        accuracy=float(accuracy_score(split.test_labels, predictions)),
        macro_f1=float(
            f1_score(
                split.test_labels,
                predictions,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        ),
        confusion=tuple(tuple(int(value) for value in row) for row in matrix),
        report_text=classification_report(
            split.test_labels,
            predictions,
            labels=labels,
            zero_division=0,
        ),
        errors=tuple(errors),
    )


def main() -> int:
    result = evaluate()
    print(f"scikit-learn={sklearn_version}")
    print(
        f"train={len(result.split.train_texts)} "
        f"test={len(result.split.test_texts)} "
        f"random_state={result.split.random_state}"
    )
    print(f"labels={','.join(result.labels)}")
    print(f"baseline-accuracy={result.baseline_accuracy:.3f}")
    print(
        f"accuracy={result.accuracy:.3f} "
        f"macro-f1={result.macro_f1:.3f}"
    )
    print("confusion-matrix rows=true columns=predicted")
    for label, row in zip(result.labels, result.confusion):
        print(f"- {label}: {row}")
    print(result.report_text.rstrip())
    print("errors:")
    if not result.errors:
        print("- This split has no misclassifications; do not infer production readiness.")
    for error in result.errors:
        print(
            f"- text={error.text!r} expected={error.expected} "
            f"predicted={error.predicted} confidence={error.confidence:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
