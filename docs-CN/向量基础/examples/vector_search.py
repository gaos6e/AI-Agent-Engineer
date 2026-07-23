"""标准库实现的精确向量检索与 Recall@k 教学示例。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite, sqrt
from numbers import Real
from typing import Literal


Vector = tuple[float, ...]
MetricName = Literal["cosine", "dot", "euclidean"]


def _as_vector(vector: Sequence[float], *, name: str) -> Vector:
    """返回有限且非空的浮点向量，否则给出明确错误。"""

    if isinstance(vector, (str, bytes)):
        raise ValueError(f"{name} 必须是数值序列")
    try:
        values = tuple(vector)
    except TypeError:
        raise ValueError(f"{name} 必须是数值序列") from None
    if not values:
        raise ValueError(f"{name} 不能为空")

    normalized: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name}[{index}] 必须是实数")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{name}[{index}] 必须是有限值")
        normalized.append(number)
    return tuple(normalized)


def _validated_pair(
    left: Sequence[float],
    right: Sequence[float],
) -> tuple[Vector, Vector]:
    left_vector = _as_vector(left, name="left")
    right_vector = _as_vector(right, name="right")
    if len(left_vector) != len(right_vector):
        raise ValueError("向量维度不一致")
    return left_vector, right_vector


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    """计算两个同维向量的点积。"""

    left_vector, right_vector = _validated_pair(left, right)
    return sum(a * b for a, b in zip(left_vector, right_vector))


def norm(vector: Sequence[float]) -> float:
    """计算向量的欧氏（L2）范数。"""

    values = _as_vector(vector, name="vector")
    return sqrt(sum(value * value for value in values))


def normalize(vector: Sequence[float]) -> Vector:
    """返回 L2 单位向量，并拒绝没有定义的零向量情况。"""

    values = _as_vector(vector, name="vector")
    length = norm(values)
    if length == 0.0:
        raise ValueError("零向量不能单位化")
    return tuple(value / length for value in values)


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """计算两个非零向量的余弦相似度。"""

    left_vector, right_vector = _validated_pair(left, right)
    denominator = norm(left_vector) * norm(right_vector)
    if denominator == 0.0:
        raise ValueError("零向量没有定义好的 cosine")
    return dot(left_vector, right_vector) / denominator


def euclidean(left: Sequence[float], right: Sequence[float]) -> float:
    """计算两个同维向量的欧氏距离。"""

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
    """执行精确 top-k 检索，同分时按文档 ID 确定性排序。"""

    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k 必须是至少为 1 的整数")
    if metric not in {"cosine", "dot", "euclidean"}:
        raise ValueError(f"不支持的度量：{metric}")
    if not documents:
        raise ValueError("documents 不能为空")

    query_vector = _as_vector(query, name="query")
    scores: list[tuple[str, float]] = []
    for document_id, vector in documents.items():
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id 必须是非空字符串")
        document_vector = _as_vector(
            vector,
            name=f"document[{document_id!r}]",
        )
        if len(document_vector) != len(query_vector):
            raise ValueError(f"文档 {document_id!r} 与 query 维度不一致")
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
    """根据前 k 个排序结果和外部相关集合计算 Recall@k。"""

    if not relevant:
        raise ValueError("相关集合不能为空")
    if any(not isinstance(item, str) or not item for item in relevant):
        raise ValueError("相关文档 ID 必须是非空字符串")

    retrieved: set[str] = set()
    for document_id, score in results:
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("结果中的文档 ID 必须是非空字符串")
        if document_id in retrieved:
            raise ValueError(f"结果中出现重复文档：{document_id}")
        if isinstance(score, bool) or not isinstance(score, Real):
            raise ValueError("结果分数必须是实数")
        if not isfinite(float(score)):
            raise ValueError("结果分数必须是有限值")
        retrieved.add(document_id)
    return len(retrieved & relevant) / len(relevant)


def _require(condition: bool, message: str) -> None:
    """让教学验收在 Python 使用 -O 时仍然生效。"""

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
        "cosine top-2 与教学预期不一致",
    )
    _require(
        [document_id for document_id, _ in euclidean_results] == expected,
        "Euclidean top-2 与教学预期不一致",
    )
    _require(abs(recall - 1.0) < 1e-12, "Recall@2 应为 1.0")
    _require(
        abs(euclidean((0.0, 0.0), (3.0, 4.0)) - 5.0) < 1e-12,
        "3-4-5 距离检查失败",
    )
    _require(
        abs(norm(normalize((3.0, 4.0))) - 1.0) < 1e-12,
        "单位化检查失败",
    )
    try:
        cosine((0.0, 0.0), (1.0, 0.0))
    except ValueError:
        pass
    else:
        raise RuntimeError("零向量应触发 ValueError")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
