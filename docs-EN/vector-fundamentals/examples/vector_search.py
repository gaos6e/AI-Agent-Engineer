"""A standard-library teaching example of exact vector retrieval and Recall@k."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite, sqrt
from numbers import Real
from typing import Literal


Vector = tuple[float, ...]
MetricName = Literal["cosine", "dot", "euclidean"]


def _as_vector(vector: Sequence[float], *, name: str) -> Vector:
    """Return a finite, nonempty floating-point vector or raise a clear error."""

    if isinstance(vector, (str, bytes)):
        raise ValueError(f"{name} must be a numeric sequence")
    try:
        values = tuple(vector)
    except TypeError:
        raise ValueError(f"{name} must be a numeric sequence") from None
    if not values:
        raise ValueError(f"{name} must not be empty")

    normalized: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name}[{index}] must be a real number")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{name}[{index}] must be finite")
        normalized.append(number)
    return tuple(normalized)


def _validated_pair(
    left: Sequence[float],
    right: Sequence[float],
) -> tuple[Vector, Vector]:
    left_vector = _as_vector(left, name="left")
    right_vector = _as_vector(right, name="right")
    if len(left_vector) != len(right_vector):
        raise ValueError("vector dimensions do not match")
    return left_vector, right_vector


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate the dot product of two equal-dimensional vectors."""

    left_vector, right_vector = _validated_pair(left, right)
    return sum(a * b for a, b in zip(left_vector, right_vector))


def norm(vector: Sequence[float]) -> float:
    """Calculate a vector's Euclidean (L2) norm."""

    values = _as_vector(vector, name="vector")
    return sqrt(sum(value * value for value in values))


def normalize(vector: Sequence[float]) -> Vector:
    """Return an L2 unit vector and reject the undefined zero-vector case."""

    values = _as_vector(vector, name="vector")
    length = norm(values)
    if length == 0.0:
        raise ValueError("a zero vector cannot be normalized")
    return tuple(value / length for value in values)


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate cosine similarity for two nonzero vectors."""

    left_vector, right_vector = _validated_pair(left, right)
    denominator = norm(left_vector) * norm(right_vector)
    if denominator == 0.0:
        raise ValueError("cosine is undefined for a zero vector")
    return dot(left_vector, right_vector) / denominator


def euclidean(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate Euclidean distance between two equal-dimensional vectors."""

    left_vector, right_vector = _validated_pair(left, right)
    return sqrt(
        sum((a - b) ** 2 for a, b in zip(left_vector, right_vector))
    )


def top_k(
    query: Sequence[float],
    documents: Mapping[str, Sequence[float]],
    *,
    k: int,
    metric: MetricName = "cosine",
) -> list[tuple[str, float]]:
    """Run exact top-k retrieval, breaking equal scores deterministically by ID."""

    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be an integer of at least 1")
    if metric not in {"cosine", "dot", "euclidean"}:
        raise ValueError(f"unsupported metric: {metric}")
    if not documents:
        raise ValueError("documents must not be empty")

    query_vector = _as_vector(query, name="query")
    scores: list[tuple[str, float]] = []
    for document_id, vector in documents.items():
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be a nonempty string")
        document_vector = _as_vector(
            vector,
            name=f"document[{document_id!r}]",
        )
        if len(document_vector) != len(query_vector):
            raise ValueError(
                f"document {document_id!r} and query dimensions do not match"
            )
        if metric == "cosine":
            score = cosine(query_vector, document_vector)
        elif metric == "dot":
            score = dot(query_vector, document_vector)
        else:
            score = euclidean(query_vector, document_vector)
        scores.append((document_id, score))

    if metric == "euclidean":
        ranked = sorted(scores, key=lambda item: (item[1], item[0]))
    else:
        ranked = sorted(scores, key=lambda item: (-item[1], item[0]))
    return ranked[:k]


def recall_at_k(
    results: Sequence[tuple[str, float]],
    relevant: set[str],
) -> float:
    """Calculate Recall@k from ranked results and an external relevance set."""

    if not relevant:
        raise ValueError("the relevant set must not be empty")
    if any(not isinstance(item, str) or not item for item in relevant):
        raise ValueError("relevant document IDs must be nonempty strings")

    retrieved: set[str] = set()
    for document_id, score in results:
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("result document IDs must be nonempty strings")
        if document_id in retrieved:
            raise ValueError(f"duplicate document in results: {document_id}")
        if isinstance(score, bool) or not isinstance(score, Real):
            raise ValueError("result scores must be real numbers")
        if not isfinite(float(score)):
            raise ValueError("result scores must be finite")
        retrieved.add(document_id)
    return len(retrieved & relevant) / len(relevant)


def _require(condition: bool, message: str) -> None:
    """Keep teaching checks active when Python runs with -O."""

    if not condition:
        raise RuntimeError(message)


def main() -> int:
    documents: dict[str, Vector] = {
        "python-api": (1.0, 0.9, 0.0),
        "http-retry": (0.9, 0.8, 0.1),
        "cat-care": (0.0, 0.0, 1.0),
    }
    query: Vector = (1.0, 1.0, 0.0)

    cosine_results = top_k(
        query,
        documents,
        k=2,
        metric="cosine",
    )
    euclidean_results = top_k(
        query,
        documents,
        k=2,
        metric="euclidean",
    )
    recall = recall_at_k(
        cosine_results,
        {"python-api", "http-retry"},
    )

    print("cosine top-2:", cosine_results)
    print("euclidean top-2:", euclidean_results)
    print(f"Recall@2={recall:.3f}")

    expected = ["python-api", "http-retry"]
    _require(
        [document_id for document_id, _ in cosine_results] == expected,
        "cosine top-2 does not match the teaching expectation",
    )
    _require(
        [document_id for document_id, _ in euclidean_results] == expected,
        "Euclidean top-2 does not match the teaching expectation",
    )
    _require(abs(recall - 1.0) < 1e-12, "Recall@2 must be 1.0")
    _require(
        abs(euclidean((0.0, 0.0), (3.0, 4.0)) - 5.0) < 1e-12,
        "the 3-4-5 distance check failed",
    )
    _require(
        abs(norm(normalize((3.0, 4.0))) - 1.0) < 1e-12,
        "the normalization check failed",
    )
    try:
        cosine((0.0, 0.0), (1.0, 0.0))
    except ValueError:
        pass
    else:
        raise RuntimeError("a zero vector should raise ValueError")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
