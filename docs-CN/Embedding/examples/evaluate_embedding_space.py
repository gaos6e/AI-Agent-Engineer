"""离线 Embedding 空间契约、精确检索、评测与迁移审计。

所有向量均来自本地教学 fixture，不下载或运行真实模型。这个脚本验证
数据流和指标实现，不能代表任何生产 embedding 模型的效果。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isclose, isfinite, log2, sqrt
from pathlib import Path
import statistics
import sys
from typing import Any, Sequence
import unicodedata


Vector = tuple[float, ...]
ALLOWED_METRICS = {"cosine", "dot", "euclidean"}
ALLOWED_DTYPES = {"float32", "float64"}
MAX_FIXTURE_BYTES = 5 * 1024 * 1024
NORMALIZED_ABS_TOLERANCE = 1e-6


class EmbeddingError(ValueError):
    """空间契约、fixture 或评测输入不合法。"""


@dataclass(frozen=True)
class EmbeddingContract:
    space_id: str
    provider: str
    model: str
    revision: str
    dimension: int
    metric: str
    normalized: bool
    query_role: str
    document_role: str
    dtype: str

    def validate(self) -> None:
        for name in (
            "space_id",
            "provider",
            "model",
            "revision",
            "query_role",
            "document_role",
            "dtype",
        ):
            _clean_token(name, getattr(self, name))
        if (
            not isinstance(self.dimension, int)
            or isinstance(self.dimension, bool)
            or not 1 <= self.dimension <= 100_000
        ):
            raise EmbeddingError("dimension 必须是 1..100000 的整数")
        if self.metric not in ALLOWED_METRICS:
            raise EmbeddingError(f"不支持的 metric：{self.metric}")
        if not isinstance(self.normalized, bool):
            raise EmbeddingError("normalized 必须是 boolean")
        if self.query_role == self.document_role:
            raise EmbeddingError("query_role 与 document_role 必须不同")
        if self.dtype not in ALLOWED_DTYPES:
            raise EmbeddingError(f"不支持的 dtype：{self.dtype}")

    def signature(self) -> str:
        """Return a fingerprint for the mathematical/encoding space contract."""
        payload = {
            "dimension": self.dimension,
            "document_role": self.document_role,
            "dtype": self.dtype,
            "metric": self.metric,
            "model": self.model,
            "normalized": self.normalized,
            "provider": self.provider,
            "query_role": self.query_role,
            "revision": self.revision,
        }
        return _digest(_canonical_json(payload))


@dataclass(frozen=True)
class EmbeddedItem:
    item_id: str
    space_id: str
    role: str
    text: str
    vector: Vector
    acl: tuple[str, ...]
    source_revision: str
    content_sha256: str


@dataclass(frozen=True)
class QueryCase:
    case_id: str
    query_item_id: str
    subject_groups: tuple[str, ...]
    relevance: tuple[tuple[str, int], ...]
    subgroups: tuple[str, ...]

    def relevance_map(self) -> dict[str, int]:
        return dict(self.relevance)


@dataclass(frozen=True)
class Fixture:
    contracts: tuple[EmbeddingContract, ...]
    items: tuple[EmbeddedItem, ...]
    queries: tuple[QueryCase, ...]


@dataclass(frozen=True)
class RankedItem:
    rank: int
    item_id: str
    score: float


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalise_text(value: str) -> str:
    return unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )


def _clean_token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise EmbeddingError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise EmbeddingError(f"{name} 长度或控制字符不合法")
    return value


def _clean_text(name: str, value: Any, maximum: int = 100_000) -> str:
    if not isinstance(value, str):
        raise EmbeddingError(f"{name} 必须是字符串")
    text = _normalise_text(value)
    if not text.strip() or len(text) > maximum:
        raise EmbeddingError(f"{name} 必须是长度受限的非空文本")
    return text


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EmbeddingError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise EmbeddingError(f"JSON 不允许非有限数值：{value}")


def _load_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise EmbeddingError(f"无法读取 fixture：{path}") from exc
    if size > MAX_FIXTURE_BYTES:
        raise EmbeddingError("fixture 超过 5 MiB 上限")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise EmbeddingError("fixture 必须是 UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise EmbeddingError(
            f"{path.name} JSON 错误：{exc.lineno}:{exc.colno}"
        ) from exc


def _require_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise EmbeddingError(
            f"{label} 字段必须精确为 {sorted(expected)}，实际为 {sorted(actual)}"
        )


def _clean_string_list(
    name: str,
    value: Any,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        requirement = "数组" if allow_empty else "非空数组"
        raise EmbeddingError(f"{name} 必须是{requirement}")
    cleaned = tuple(_clean_token(name, item) for item in value)
    if len(set(cleaned)) != len(cleaned):
        raise EmbeddingError(f"{name} 不得重复")
    return tuple(sorted(cleaned))


def _vector_norm(vector: Sequence[float]) -> float:
    return sqrt(sum(value * value for value in vector))


def _finite_float(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise EmbeddingError(f"{label} 必须是有限数值")
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise EmbeddingError(f"{label} 必须是有限数值") from exc
    if not isfinite(parsed):
        raise EmbeddingError(f"{label} 必须是有限数值")
    return parsed


def _parse_vector(
    value: Any,
    *,
    contract: EmbeddingContract,
    label: str,
) -> Vector:
    if not isinstance(value, list) or len(value) != contract.dimension:
        raise EmbeddingError(
            f"{label} 维度必须是 {contract.dimension}，实际为 "
            f"{len(value) if isinstance(value, list) else '非数组'}"
        )
    parsed: list[float] = []
    for index, item in enumerate(value):
        parsed.append(_finite_float(item, f"{label}[{index}]"))
    vector = tuple(parsed)
    norm = _vector_norm(vector)
    if norm == 0.0 or not isfinite(norm):
        raise EmbeddingError(f"{label} 不得是零向量")
    if contract.normalized and not isclose(
        norm,
        1.0,
        rel_tol=0.0,
        abs_tol=NORMALIZED_ABS_TOLERANCE,
    ):
        raise EmbeddingError(
            f"{label} 声明 normalized=True，但 L2 norm={norm:.9f}"
        )
    return vector


def _parse_contracts(value: Any) -> tuple[EmbeddingContract, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("contracts 必须是非空数组")
    expected = {
        "space_id",
        "provider",
        "model",
        "revision",
        "dimension",
        "metric",
        "normalized",
        "query_role",
        "document_role",
        "dtype",
    }
    result: list[EmbeddingContract] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EmbeddingError(f"contracts[{index}] 必须是 object")
        _require_fields(item, expected, f"contracts[{index}]")
        contract = EmbeddingContract(
            space_id=item["space_id"],
            provider=item["provider"],
            model=item["model"],
            revision=item["revision"],
            dimension=item["dimension"],
            metric=item["metric"],
            normalized=item["normalized"],
            query_role=item["query_role"],
            document_role=item["document_role"],
            dtype=item["dtype"],
        )
        contract.validate()
        if contract.space_id in seen:
            raise EmbeddingError(f"space_id 重复：{contract.space_id}")
        seen.add(contract.space_id)
        result.append(contract)
    return tuple(sorted(result, key=lambda contract: contract.space_id))


def _parse_items(
    value: Any,
    contracts: dict[str, EmbeddingContract],
) -> tuple[EmbeddedItem, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("items 必须是非空数组")
    expected = {
        "item_id",
        "space_id",
        "role",
        "text",
        "vector",
        "acl",
        "source_revision",
    }
    result: list[EmbeddedItem] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EmbeddingError(f"items[{index}] 必须是 object")
        _require_fields(item, expected, f"items[{index}]")
        item_id = _clean_token("item_id", item["item_id"])
        space_id = _clean_token("space_id", item["space_id"])
        if space_id not in contracts:
            raise EmbeddingError(f"item 指向不存在空间：{space_id}")
        key = (space_id, item_id)
        if key in seen:
            raise EmbeddingError(f"item 重复：{space_id}/{item_id}")
        seen.add(key)
        contract = contracts[space_id]
        role = _clean_token("role", item["role"])
        if role not in {contract.query_role, contract.document_role}:
            raise EmbeddingError(
                f"{space_id}/{item_id} role 不符合空间契约：{role}"
            )
        text = _clean_text("text", item["text"])
        vector = _parse_vector(
            item["vector"],
            contract=contract,
            label=f"{space_id}/{item_id}.vector",
        )
        acl = _clean_string_list("acl", item["acl"])
        source_revision = _clean_token(
            "source_revision", item["source_revision"]
        )
        result.append(
            EmbeddedItem(
                item_id=item_id,
                space_id=space_id,
                role=role,
                text=text,
                vector=vector,
                acl=acl,
                source_revision=source_revision,
                content_sha256=_digest(text),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.space_id, item.item_id)))


def _parse_queries(
    value: Any,
    *,
    contracts: Sequence[EmbeddingContract],
    items: Sequence[EmbeddedItem],
) -> tuple[QueryCase, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("queries 必须是非空数组")
    by_key = {(item.space_id, item.item_id): item for item in items}
    expected = {
        "case_id",
        "query_item_id",
        "subject_groups",
        "relevance",
        "subgroups",
    }
    result: list[QueryCase] = []
    seen: set[str] = set()
    for index, value_item in enumerate(value):
        if not isinstance(value_item, dict):
            raise EmbeddingError(f"queries[{index}] 必须是 object")
        _require_fields(value_item, expected, f"queries[{index}]")
        case_id = _clean_token("case_id", value_item["case_id"])
        if case_id in seen:
            raise EmbeddingError(f"case_id 重复：{case_id}")
        seen.add(case_id)
        query_item_id = _clean_token(
            "query_item_id", value_item["query_item_id"]
        )
        subject_groups = _clean_string_list(
            "subject_groups", value_item["subject_groups"]
        )
        subgroups = _clean_string_list("subgroups", value_item["subgroups"])
        relevance_value = value_item["relevance"]
        if not isinstance(relevance_value, dict) or not relevance_value:
            raise EmbeddingError("relevance 必须是非空 object")
        relevance: list[tuple[str, int]] = []
        for document_id, grade in relevance_value.items():
            _clean_token("relevant document_id", document_id)
            if (
                not isinstance(grade, int)
                or isinstance(grade, bool)
                or not 1 <= grade <= 3
            ):
                raise EmbeddingError("relevance grade 必须是 1..3 的整数")
            relevance.append((document_id, grade))

        for contract in contracts:
            query_key = (contract.space_id, query_item_id)
            if query_key not in by_key:
                raise EmbeddingError(
                    f"{case_id} 在 {contract.space_id} 缺少 query item"
                )
            query_item = by_key[query_key]
            if query_item.role != contract.query_role:
                raise EmbeddingError(
                    f"{contract.space_id}/{query_item_id} 不是 query role"
                )
            for document_id, _ in relevance:
                document_key = (contract.space_id, document_id)
                if document_key not in by_key:
                    raise EmbeddingError(
                        f"{case_id} 在 {contract.space_id} 缺少 relevant document："
                        f"{document_id}"
                    )
                document = by_key[document_key]
                if document.role != contract.document_role:
                    raise EmbeddingError(
                        f"{contract.space_id}/{document_id} 不是 document role"
                    )
                if not set(subject_groups).intersection(document.acl):
                    raise EmbeddingError(
                        f"{case_id} 的 gold 包含主体无权读取的文档：{document_id}"
                    )
        result.append(
            QueryCase(
                case_id=case_id,
                query_item_id=query_item_id,
                subject_groups=subject_groups,
                relevance=tuple(sorted(relevance)),
                subgroups=subgroups,
            )
        )
    return tuple(sorted(result, key=lambda case: case.case_id))


def load_fixture(path: Path) -> Fixture:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise EmbeddingError("fixture 顶层必须是 object")
    _require_fields(payload, {"contracts", "items", "queries"}, "fixture")
    contracts = _parse_contracts(payload["contracts"])
    by_space = {contract.space_id: contract for contract in contracts}
    items = _parse_items(payload["items"], by_space)
    queries = _parse_queries(
        payload["queries"],
        contracts=contracts,
        items=items,
    )
    for contract in contracts:
        roles = {
            item.role for item in items if item.space_id == contract.space_id
        }
        if contract.query_role not in roles or contract.document_role not in roles:
            raise EmbeddingError(
                f"{contract.space_id} 必须同时包含 query 与 document items"
            )
    return Fixture(contracts=contracts, items=items, queries=queries)


def normalize(vector: Vector) -> Vector:
    if not vector:  # 空向量没有方向，不能参与 cosine 或归一化。
        raise EmbeddingError("向量必须非空且全部有限")  # 在数学计算前拒绝无意义输入。
    parsed = tuple(  # 逐维转成有限浮点数，防止 bool、NaN 和 Inf 进入后续运算。
        _finite_float(value, f"vector[{index}]") for index, value in enumerate(vector)  # 给错误附上具体维度位置。
    )
    norm = _vector_norm(parsed)  # 计算 L2 范数，即向量长度。
    if norm == 0.0 or not isfinite(norm):  # 零向量无法除以范数，非有限范数会污染分数。
        raise EmbeddingError("向量范数必须为有限正数")  # fail closed，不返回伪归一化结果。
    return tuple(value / norm for value in parsed)  # 每一维除以相同长度，得到长度为 1 的单位向量。


def similarity(
    left: Vector,
    right: Vector,
    *,
    metric: str,
) -> float:
    if metric not in ALLOWED_METRICS:  # 只允许本实验明确实现和测试过的三种度量。
        raise EmbeddingError(f"不支持的 metric：{metric}")  # 不让拼写错误静默退化为其他算法。
    if not left or len(left) != len(right):  # 点积、cosine 与距离都要求非空且维度一致。
        raise EmbeddingError("向量必须非空且维度相同")  # 错维向量绝不能通过截断或 zip 被悄悄比较。
    left_values = tuple(  # 校验左向量的每个维度。
        _finite_float(value, f"left[{index}]") for index, value in enumerate(left)  # 保留出错维度便于排查 fixture。
    )
    right_values = tuple(  # 校验右向量的每个维度。
        _finite_float(value, f"right[{index}]") for index, value in enumerate(right)  # 同样拒绝非有限数值。
    )
    if metric == "cosine":  # cosine 比较方向，因此先把两边转换为单位向量。
        left_unit = normalize(left_values)  # 将左向量除以自身 L2 范数。
        right_unit = normalize(right_values)  # 将右向量除以自身 L2 范数。
        return sum(a * b for a, b in zip(left_unit, right_unit))  # 单位向量的点积就是 cosine similarity。
    if metric == "dot":  # dot 保留原始长度信息，只适用于契约允许的空间。
        return sum(a * b for a, b in zip(left_values, right_values))  # 按维相乘再求和。
    squared = sum((a - b) ** 2 for a, b in zip(left_values, right_values))  # 先计算 Euclidean 距离的平方。
    return -sqrt(squared)  # 搜索统一按“分数越大越好”排序，因此返回负距离。


def _contract_for(fixture: Fixture, space_id: str) -> EmbeddingContract:
    for contract in fixture.contracts:
        if contract.space_id == space_id:
            return contract
    raise EmbeddingError(f"不存在 embedding space：{space_id}")


def _item_map(fixture: Fixture, space_id: str) -> dict[str, EmbeddedItem]:
    return {
        item.item_id: item
        for item in fixture.items
        if item.space_id == space_id
    }


def search(
    fixture: Fixture,
    *,
    space_id: str,
    query_item_id: str,
    subject_groups: Sequence[str],
    k: int,
) -> list[RankedItem]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:  # k 是 API 边界，不能接受 0、负数或布尔值。
        raise EmbeddingError("k 必须是正整数")  # 非法 k 必须显式失败，不能偷偷改成默认值。
    contract = _contract_for(fixture, space_id)  # 读取目标空间的度量、角色和维度契约。
    items = _item_map(fixture, space_id)  # 只建立同一 space_id 内的候选映射，防止跨空间比较。
    if query_item_id not in items:  # 查询 ID 必须属于目标空间。
        raise EmbeddingError(f"query item 不存在：{space_id}/{query_item_id}")  # 缺失 ID 不是“没有结果”。
    query = items[query_item_id]  # 取出 query 向量和其角色元数据。
    if query.role != contract.query_role:  # document 不能被误当作 query 传入。
        raise EmbeddingError(f"{query_item_id} 不是 query role")  # 角色错误虽可能维度正确，仍需拒绝。
    groups = {  # 规范化主体所属组，后面用于 ACL 的 OR 语义判断。
        _clean_token("subject_group", group) for group in subject_groups  # 逐项拒绝空白或控制字符组名。
    }
    if not groups:  # 无身份上下文时不能默认看见所有文档。
        return []  # fail closed，返回空候选而不是执行开放检索。

    scored: list[tuple[float, str]] = []  # 保存“分数、ID”对，直到完成所有授权过滤。
    for item in items.values():  # 遍历该空间中的所有教学 item。
        if item.role != contract.document_role:  # query 自身和其他角色都不是可检索文档。
            continue  # 跳过非 document，避免 query-query 比较混入结果。
        if not groups.intersection(item.acl):  # 必须至少有一个主体组被文档 ACL 授权。
            continue  # 在算相似度前过滤，防止未授权文档影响排序或日志。
        score = similarity(query.vector, item.vector, metric=contract.metric)  # 用目标空间声明的度量计算 exact 分数。
        scored.append((score, item.item_id))  # 暂存已授权 document 的可排序结果。
    scored.sort(key=lambda row: (-row[0], row[1]))  # 分数降序；同分时按 ID 升序，确保结果可重放。
    return [  # 把前 k 项转换为带从 1 开始排名的不可变输出记录。
        RankedItem(rank=index, item_id=item_id, score=score)  # 保留原始数值，展示层再决定如何 round。
        for index, (score, item_id) in enumerate(scored[:k], start=1)  # 先截取 top-k，再连续编号。
    ]


def _validate_metric_inputs(
    results: Sequence[str], relevance: dict[str, int]
) -> tuple[str, ...]:
    if isinstance(results, (str, bytes)):
        raise EmbeddingError("results 必须是按排名排列的 ID 序列")
    identifiers = tuple(
        _clean_token(f"results[{index}]", item_id)
        for index, item_id in enumerate(results)
    )
    if len(identifiers) != len(set(identifiers)):
        raise EmbeddingError("results 含重复 item_id")
    if not isinstance(relevance, dict) or not relevance:
        raise EmbeddingError("relevance 必须是非空 object")
    for item_id, grade in relevance.items():
        _clean_token("relevance item_id", item_id)
        if (
            not isinstance(grade, int)
            or isinstance(grade, bool)
            or not 1 <= grade <= 3
        ):
            raise EmbeddingError("relevance grade 必须是 1..3 的整数")
    return identifiers


def recall_at_k(results: Sequence[str], relevance: dict[str, int]) -> float:
    identifiers = _validate_metric_inputs(results, relevance)
    return len(set(identifiers).intersection(relevance)) / len(relevance)


def reciprocal_rank(results: Sequence[str], relevance: dict[str, int]) -> float:
    identifiers = _validate_metric_inputs(results, relevance)
    for rank, item_id in enumerate(identifiers, start=1):
        if item_id in relevance:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(results: Sequence[str], relevance: dict[str, int], k: int) -> float:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise EmbeddingError("k 必须是正整数")
    identifiers = _validate_metric_inputs(results, relevance)

    def dcg(grades: Sequence[int]) -> float:
        return sum(
            (2**grade - 1) / log2(rank + 1)
            for rank, grade in enumerate(grades, start=1)
        )

    observed = [relevance.get(item_id, 0) for item_id in identifiers[:k]]
    ideal = sorted(relevance.values(), reverse=True)[:k]
    ideal_score = dcg(ideal)
    score = 0.0 if ideal_score == 0.0 else dcg(observed) / ideal_score
    if not isfinite(score) or not 0.0 <= score <= 1.0 + 1e-12:
        raise EmbeddingError("nDCG 超出 0..1，排名或 qrels 合同不合法")
    return min(1.0, score)


def _mean(values: Sequence[float | int]) -> float:
    return 0.0 if not values else round(float(statistics.fmean(values)), 4)


def evaluate_space(
    fixture: Fixture,
    *,
    space_id: str,
    k: int,
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    subgroup_values: dict[str, dict[str, list[float]]] = {}

    for case in fixture.queries:
        ranked = search(
            fixture,
            space_id=space_id,
            query_item_id=case.query_item_id,
            subject_groups=case.subject_groups,
            k=k,
        )
        result_ids = [item.item_id for item in ranked]
        relevance = case.relevance_map()
        recall = recall_at_k(result_ids, relevance)
        rr = reciprocal_rank(result_ids, relevance)
        ndcg = ndcg_at_k(result_ids, relevance, k)
        recalls.append(recall)
        reciprocal_ranks.append(rr)
        ndcgs.append(ndcg)
        for subgroup in case.subgroups:
            metrics = subgroup_values.setdefault(
                subgroup,
                {"recall_at_k": [], "reciprocal_rank": [], "ndcg_at_k": []},
            )
            metrics["recall_at_k"].append(recall)
            metrics["reciprocal_rank"].append(rr)
            metrics["ndcg_at_k"].append(ndcg)
        details.append(
            {
                "case_id": case.case_id,
                "query_item_id": case.query_item_id,
                "result_ids": result_ids,
                "scores": [round(item.score, 6) for item in ranked],
                "recall_at_k": round(recall, 4),
                "reciprocal_rank": round(rr, 4),
                "ndcg_at_k": round(ndcg, 4),
                "subgroups": list(case.subgroups),
            }
        )

    subgroup_report = {
        subgroup: {
            metric: _mean(values)
            for metric, values in metrics.items()
        }
        for subgroup, metrics in sorted(subgroup_values.items())
    }
    return {
        "space_id": space_id,
        "k": k,
        "query_count": len(fixture.queries),
        "mean_recall_at_k": _mean(recalls),
        "mrr": _mean(reciprocal_ranks),
        "mean_ndcg_at_k": _mean(ndcgs),
        "subgroups": subgroup_report,
        "details": details,
    }


def inventory_report(
    fixture: Fixture,
    *,
    space_id: str,
) -> dict[str, Any]:
    contract = _contract_for(fixture, space_id)
    items = [
        item for item in fixture.items if item.space_id == space_id
    ]
    documents = [
        item for item in items if item.role == contract.document_role
    ]
    queries = [item for item in items if item.role == contract.query_role]
    norms = [_vector_norm(item.vector) for item in items]
    bytes_per_value = 4 if contract.dtype == "float32" else 8
    return {
        "space_id": space_id,
        "contract_signature": contract.signature(),
        "item_count": len(items),
        "document_count": len(documents),
        "query_item_count": len(queries),
        "dimension": contract.dimension,
        "metric": contract.metric,
        "normalized": contract.normalized,
        "dtype": contract.dtype,
        "estimated_raw_vector_bytes": (
            len(items) * contract.dimension * bytes_per_value
        ),
        "norm_min": round(min(norms), 6),
        "norm_median": round(float(statistics.median(norms)), 6),
        "norm_max": round(max(norms), 6),
    }


def migration_audit(
    fixture: Fixture,
    *,
    old_space_id: str,
    new_space_id: str,
    k: int,
) -> dict[str, Any]:
    if old_space_id == new_space_id:
        raise EmbeddingError("迁移审计要求两个不同 space_id")
    old_contract = _contract_for(fixture, old_space_id)
    new_contract = _contract_for(fixture, new_space_id)
    old_items = _item_map(fixture, old_space_id)
    new_items = _item_map(fixture, new_space_id)
    old_ids = set(old_items)
    new_ids = set(new_items)
    only_old = sorted(old_ids - new_ids)
    only_new = sorted(new_ids - old_ids)
    canonical_mismatches: list[str] = []
    for item_id in sorted(old_ids.intersection(new_ids)):
        old = old_items[item_id]
        new = new_items[item_id]
        old_canonical = (
            old.role,
            old.text,
            old.acl,
            old.source_revision,
            old.content_sha256,
        )
        new_canonical = (
            new.role,
            new.text,
            new.acl,
            new.source_revision,
            new.content_sha256,
        )
        if old_canonical != new_canonical:
            canonical_mismatches.append(item_id)

    old_evaluation = evaluate_space(
        fixture, space_id=old_space_id, k=k
    )
    new_evaluation = evaluate_space(
        fixture, space_id=new_space_id, k=k
    )
    old_details = {
        detail["case_id"]: detail for detail in old_evaluation["details"]
    }
    new_details = {
        detail["case_id"]: detail for detail in new_evaluation["details"]
    }
    agreements: list[dict[str, Any]] = []
    jaccards: list[float] = []
    for case_id in sorted(set(old_details).intersection(new_details)):
        old_results = set(old_details[case_id]["result_ids"])
        new_results = set(new_details[case_id]["result_ids"])
        union = old_results.union(new_results)
        jaccard = 1.0 if not union else len(old_results.intersection(new_results)) / len(union)
        jaccards.append(jaccard)
        agreements.append(
            {
                "case_id": case_id,
                "top_k_jaccard": round(jaccard, 4),
            }
        )

    quality_keys = ("mean_recall_at_k", "mrr", "mean_ndcg_at_k")
    quality_delta = {
        key: round(new_evaluation[key] - old_evaluation[key], 4)
        for key in quality_keys
    }
    inventory_match = not only_old and not only_new
    canonical_match = not canonical_mismatches
    return {
        "old_space_id": old_space_id,
        "new_space_id": new_space_id,
        "vectors_directly_comparable": (
            old_contract.signature() == new_contract.signature()
        ),
        "inventory_match": inventory_match,
        "canonical_match": canonical_match,
        "only_old": only_old,
        "only_new": only_new,
        "canonical_mismatches": canonical_mismatches,
        "mechanical_gates_pass": inventory_match and canonical_match,
        "quality_delta_new_minus_old": quality_delta,
        "mean_top_k_jaccard": _mean(jaccards),
        "per_query_agreement": agreements,
        "quality_decision_required": True,
    }


def run_experiment(fixture: Fixture, *, k: int = 3) -> dict[str, Any]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise EmbeddingError("k 必须是正整数")
    space_ids = [contract.space_id for contract in fixture.contracts]
    evaluations = {
        space_id: evaluate_space(fixture, space_id=space_id, k=k)
        for space_id in space_ids
    }
    inventories = {
        space_id: inventory_report(fixture, space_id=space_id)
        for space_id in space_ids
    }
    migrations = [
        migration_audit(
            fixture,
            old_space_id=space_ids[0],
            new_space_id=space_id,
            k=k,
        )
        for space_id in space_ids[1:]
    ]
    return {
        "fixture_notice": (
            "hand-authored vectors; validates contracts and metrics, "
            "not real model quality"
        ),
        "k": k,
        "spaces": {
            contract.space_id: {
                "contract": asdict(contract),
                "inventory": inventories[contract.space_id],
                "evaluation": evaluations[contract.space_id],
            }
            for contract in fixture.contracts
        },
        "migrations": migrations,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="离线 Embedding 空间评测与迁移审计"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=base / "embedding-fixture.json",
        help="严格 JSON fixture 路径",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="精确检索返回数量（正整数）",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", newline="\n")
    args = parse_args(argv)
    try:
        fixture = load_fixture(args.fixture.resolve())
        report = run_experiment(fixture, k=args.k)
    except EmbeddingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
