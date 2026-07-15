"""Deterministic offline hybrid-search lab for teaching, never production.

The lab combines a small BM25 implementation, hand-authored unit vectors,
fail-closed metadata filtering, reciprocal rank fusion and graded metrics.  The
vectors are fixtures, not learned embeddings; all search is exact and local.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isclose, isfinite, log, log2, sqrt
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
import unicodedata


MAX_FIXTURE_BYTES = 2 * 1024 * 1024
MAX_DOCUMENTS = 10_000
MAX_QUERIES = 10_000
MAX_TEXT_LENGTH = 20_000
ALLOWED_METRICS = {"cosine", "dot", "euclidean"}
ALLOWED_STATUSES = {"draft", "published", "archived"}
ALLOWED_FILTERS = {"language", "product"}
NORMALIZED_ABS_TOLERANCE = 1e-6
SCHEMA_VERSION = 1
DEFAULT_FIXTURE = Path(__file__).with_name("semantic-search-fixture.json")
SEGMENT_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+")


class SemanticSearchError(ValueError):
    """Invalid fixture, retrieval setting or evaluation input."""


@dataclass(frozen=True)
class RepresentationContract:
    name: str
    revision: str
    dimension: int
    metric: str
    normalized: bool
    notice: str

    def validate(self) -> None:
        _clean_token("representation.name", self.name)
        _clean_token("representation.revision", self.revision)
        _clean_text("representation.notice", self.notice, maximum=1_000)
        if (
            not isinstance(self.dimension, int)
            or isinstance(self.dimension, bool)
            or not 1 <= self.dimension <= 100_000
        ):
            raise SemanticSearchError("representation.dimension 必须是 1..100000 的整数")
        if self.metric not in ALLOWED_METRICS:
            raise SemanticSearchError(f"不支持的 metric：{self.metric}")
        if not isinstance(self.normalized, bool):
            raise SemanticSearchError("representation.normalized 必须是 boolean")

    def signature(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    text: str
    tenant_id: str
    acl: tuple[str, ...]
    status: str
    language: str
    product: str
    source_revision: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class Query:
    query_id: str
    text: str
    tenant_id: str
    subject_groups: tuple[str, ...]
    filters: tuple[tuple[str, str], ...]
    vector: tuple[float, ...]
    qrels: tuple[tuple[str, int], ...]
    must_not_return: tuple[str, ...]

    def filter_map(self) -> dict[str, str]:
        return dict(self.filters)

    def qrels_map(self) -> dict[str, int]:
        return dict(self.qrels)


@dataclass(frozen=True)
class Fixture:
    representation: RepresentationContract
    documents: tuple[Document, ...]
    queries: tuple[Query, ...]


@dataclass(frozen=True)
class ScoredHit:
    document_id: str
    score: float


def _clean_token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SemanticSearchError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise SemanticSearchError(f"{name} 长度或控制字符不合法")
    return value


def _clean_text(name: str, value: Any, maximum: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SemanticSearchError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(
        ord(character) < 32 and character not in "\n\t" for character in value
    ):
        raise SemanticSearchError(f"{name} 长度或控制字符不合法")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticSearchError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise SemanticSearchError(f"JSON 不允许非有限数值：{value}")


def _require_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise SemanticSearchError(
            f"{label} 字段必须精确为 {sorted(expected)}，实际为 {sorted(actual)}"
        )


def _read_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise SemanticSearchError(f"无法读取 fixture：{path}") from exc
    if size > MAX_FIXTURE_BYTES:
        raise SemanticSearchError("fixture 超过 2 MiB 教学上限")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise SemanticSearchError("fixture 必须是 UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise SemanticSearchError(
            f"{path.name} JSON 错误：{exc.lineno}:{exc.colno}"
        ) from exc


def _parse_string_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "数组" if allow_empty else "非空数组"
        raise SemanticSearchError(f"{label} 必须是{qualifier}")
    parsed = tuple(_clean_token(label, item) for item in value)
    if len(set(parsed)) != len(parsed) or parsed != tuple(sorted(parsed)):
        raise SemanticSearchError(f"{label} 必须去重并按字典序排列")
    return parsed


def _parse_vector(
    value: Any,
    contract: RepresentationContract,
    label: str,
) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != contract.dimension:
        actual = len(value) if isinstance(value, list) else "非数组"
        raise SemanticSearchError(
            f"{label} 维度必须是 {contract.dimension}，实际为 {actual}"
        )
    parsed: list[float] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not isfinite(float(item))
        ):
            raise SemanticSearchError(f"{label}[{index}] 必须是有限数值")
        parsed.append(float(item))
    norm = sqrt(sum(item * item for item in parsed))
    if norm == 0.0 or not isfinite(norm):
        raise SemanticSearchError(f"{label} 不得是零向量")
    if contract.normalized and not isclose(
        norm,
        1.0,
        rel_tol=0.0,
        abs_tol=NORMALIZED_ABS_TOLERANCE,
    ):
        raise SemanticSearchError(
            f"{label} 声明 normalized=true，但 L2 norm={norm:.9f}"
        )
    return tuple(parsed)


def _parse_representation(value: Any) -> RepresentationContract:
    if not isinstance(value, dict):
        raise SemanticSearchError("representation 必须是 object")
    _require_fields(
        value,
        {"name", "revision", "dimension", "metric", "normalized", "notice"},
        "representation",
    )
    contract = RepresentationContract(
        name=value["name"],
        revision=value["revision"],
        dimension=value["dimension"],
        metric=value["metric"],
        normalized=value["normalized"],
        notice=value["notice"],
    )
    contract.validate()
    return contract


def _parse_document(
    value: Any,
    contract: RepresentationContract,
    index: int,
) -> Document:
    label = f"documents[{index}]"
    if not isinstance(value, dict):
        raise SemanticSearchError(f"{label} 必须是 object")
    _require_fields(
        value,
        {
            "id",
            "title",
            "text",
            "tenant_id",
            "acl",
            "status",
            "language",
            "product",
            "source_revision",
            "vector",
        },
        label,
    )
    status = _clean_token(f"{label}.status", value["status"])
    if status not in ALLOWED_STATUSES:
        raise SemanticSearchError(f"{label}.status 不受支持：{status}")
    return Document(
        document_id=_clean_token(f"{label}.id", value["id"]),
        title=_clean_text(f"{label}.title", value["title"], maximum=500),
        text=_clean_text(f"{label}.text", value["text"]),
        tenant_id=_clean_token(f"{label}.tenant_id", value["tenant_id"]),
        acl=_parse_string_list(value["acl"], f"{label}.acl", allow_empty=False),
        status=status,
        language=_clean_token(f"{label}.language", value["language"]),
        product=_clean_token(f"{label}.product", value["product"]),
        source_revision=_clean_token(
            f"{label}.source_revision", value["source_revision"]
        ),
        vector=_parse_vector(value["vector"], contract, f"{label}.vector"),
    )


def _parse_filters(value: Any, label: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise SemanticSearchError(f"{label} 必须是 object")
    parsed: list[tuple[str, str]] = []
    for key, item in value.items():
        if key not in ALLOWED_FILTERS:
            raise SemanticSearchError(f"{label} 不允许字段：{key}")
        parsed.append((key, _clean_token(f"{label}.{key}", item)))
    return tuple(sorted(parsed))


def _parse_qrels(value: Any, label: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict):
        raise SemanticSearchError(f"{label} 必须是 object")
    parsed: list[tuple[str, int]] = []
    for document_id, relevance in value.items():
        document_id = _clean_token(f"{label}.document_id", document_id)
        if (
            not isinstance(relevance, int)
            or isinstance(relevance, bool)
            or not 1 <= relevance <= 3
        ):
            raise SemanticSearchError(f"{label}.{document_id} 必须是 1..3 的整数")
        parsed.append((document_id, relevance))
    return tuple(sorted(parsed))


def _parse_query(
    value: Any,
    contract: RepresentationContract,
    index: int,
) -> Query:
    label = f"queries[{index}]"
    if not isinstance(value, dict):
        raise SemanticSearchError(f"{label} 必须是 object")
    _require_fields(
        value,
        {
            "id",
            "text",
            "tenant_id",
            "subject_groups",
            "filters",
            "vector",
            "qrels",
            "must_not_return",
        },
        label,
    )
    return Query(
        query_id=_clean_token(f"{label}.id", value["id"]),
        text=_clean_text(f"{label}.text", value["text"], maximum=2_000),
        tenant_id=_clean_token(f"{label}.tenant_id", value["tenant_id"]),
        subject_groups=_parse_string_list(
            value["subject_groups"],
            f"{label}.subject_groups",
            allow_empty=True,
        ),
        filters=_parse_filters(value["filters"], f"{label}.filters"),
        vector=_parse_vector(value["vector"], contract, f"{label}.vector"),
        qrels=_parse_qrels(value["qrels"], f"{label}.qrels"),
        must_not_return=_parse_string_list(
            value["must_not_return"],
            f"{label}.must_not_return",
            allow_empty=True,
        ),
    )


def _is_eligible(document: Document, query: Query) -> bool:
    if document.tenant_id != query.tenant_id:
        return False
    if document.status != "published":
        return False
    if not set(document.acl).intersection(query.subject_groups):
        return False
    for key, expected in query.filters:
        if getattr(document, key) != expected:
            return False
    return True


def load_fixture(path: Path) -> Fixture:
    value = _read_json(path)
    if not isinstance(value, dict):
        raise SemanticSearchError("fixture 顶层必须是 object")
    _require_fields(
        value,
        {"schema_version", "representation", "documents", "queries"},
        "fixture",
    )
    if value["schema_version"] != SCHEMA_VERSION:
        raise SemanticSearchError(
            f"不支持 schema_version：{value['schema_version']}"
        )
    contract = _parse_representation(value["representation"])
    if not isinstance(value["documents"], list) or not value["documents"]:
        raise SemanticSearchError("documents 必须是非空数组")
    if len(value["documents"]) > MAX_DOCUMENTS:
        raise SemanticSearchError("documents 超过教学上限")
    documents = tuple(
        _parse_document(item, contract, index)
        for index, item in enumerate(value["documents"])
    )
    document_map: dict[str, Document] = {}
    for document in documents:
        if document.document_id in document_map:
            raise SemanticSearchError(f"document id 重复：{document.document_id}")
        document_map[document.document_id] = document
    if not isinstance(value["queries"], list) or not value["queries"]:
        raise SemanticSearchError("queries 必须是非空数组")
    if len(value["queries"]) > MAX_QUERIES:
        raise SemanticSearchError("queries 超过教学上限")
    queries = tuple(
        _parse_query(item, contract, index)
        for index, item in enumerate(value["queries"])
    )
    query_ids: set[str] = set()
    for query in queries:
        if query.query_id in query_ids:
            raise SemanticSearchError(f"query id 重复：{query.query_id}")
        query_ids.add(query.query_id)
        qrel_ids = set(query.qrels_map())
        denied_ids = set(query.must_not_return)
        if qrel_ids.intersection(denied_ids):
            raise SemanticSearchError(
                f"{query.query_id} 的 qrels 与 must_not_return 重叠"
            )
        for document_id in qrel_ids:
            document = document_map.get(document_id)
            if document is None:
                raise SemanticSearchError(
                    f"{query.query_id} qrels 引用未知文档：{document_id}"
                )
            if not _is_eligible(document, query):
                raise SemanticSearchError(
                    f"{query.query_id} qrels 文档不满足权限/过滤：{document_id}"
                )
        for document_id in denied_ids:
            document = document_map.get(document_id)
            if document is None:
                raise SemanticSearchError(
                    f"{query.query_id} must_not_return 引用未知文档：{document_id}"
                )
            if _is_eligible(document, query):
                raise SemanticSearchError(
                    f"{query.query_id} must_not_return 文档仍满足过滤：{document_id}"
                )
    return Fixture(contract, documents, queries)


def analyze(text: str) -> tuple[str, ...]:
    """Return deterministic ASCII tokens and overlapping CJK bigrams."""

    normalised = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    for match in SEGMENT_PATTERN.finditer(normalised):
        segment = match.group(0)
        if segment.isascii():
            tokens.append(segment)
        elif len(segment) == 1:
            tokens.append(segment)
        else:
            tokens.extend(
                segment[index : index + 2]
                for index in range(len(segment) - 1)
            )
    return tuple(tokens)


def eligible_documents(fixture: Fixture, query: Query) -> tuple[Document, ...]:
    return tuple(
        document
        for document in fixture.documents
        if _is_eligible(document, query)
    )


def _validate_limit(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SemanticSearchError(f"{name} 必须是正整数")
    return value


def rank_bm25(
    query: Query,
    documents: Sequence[Document],
    *,
    limit: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> list[ScoredHit]:
    """Rank eligible documents with a compact BM25 teaching implementation."""

    _validate_limit("limit", limit)
    if not isfinite(k1) or k1 <= 0:
        raise SemanticSearchError("k1 必须是有限正数")
    if not isfinite(b) or not 0 <= b <= 1:
        raise SemanticSearchError("b 必须在 0..1")
    if not documents:
        return []
    tokenised = {
        document.document_id: analyze(f"{document.title} {document.text}")
        for document in documents
    }
    lengths = {key: len(tokens) for key, tokens in tokenised.items()}
    average_length = sum(lengths.values()) / len(lengths)
    if average_length <= 0:
        return []
    query_terms = set(analyze(query.text))
    document_frequency: Counter[str] = Counter()
    for tokens in tokenised.values():
        document_frequency.update(set(tokens))
    total = len(documents)
    scored: list[ScoredHit] = []
    for document in documents:
        tokens = tokenised[document.document_id]
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue
            frequency_in_documents = document_frequency[term]
            inverse_document_frequency = log(
                1.0
                + (total - frequency_in_documents + 0.5)
                / (frequency_in_documents + 0.5)
            )
            denominator = frequency + k1 * (
                1.0 - b + b * lengths[document.document_id] / average_length
            )
            score += inverse_document_frequency * (
                frequency * (k1 + 1.0) / denominator
            )
        if score > 0.0:
            scored.append(ScoredHit(document.document_id, score))
    scored.sort(key=lambda hit: (-hit.score, hit.document_id))
    return scored[:limit]


def vector_score(
    left: Sequence[float],
    right: Sequence[float],
    *,
    metric: str,
) -> float:
    if metric not in ALLOWED_METRICS:
        raise SemanticSearchError(f"不支持的 metric：{metric}")
    if not left or len(left) != len(right):
        raise SemanticSearchError("向量必须非空且维度相同")
    if not all(isfinite(float(value)) for value in (*left, *right)):
        raise SemanticSearchError("向量包含 NaN/Inf")
    if metric == "dot":
        return sum(a * b for a, b in zip(left, right))
    if metric == "euclidean":
        return -sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise SemanticSearchError("零向量没有 cosine 方向")
    return sum(a * b for a, b in zip(left, right)) / (
        left_norm * right_norm
    )


def rank_dense(
    query: Query,
    documents: Sequence[Document],
    contract: RepresentationContract,
    *,
    limit: int,
) -> list[ScoredHit]:
    _validate_limit("limit", limit)
    scored = [
        ScoredHit(
            document.document_id,
            vector_score(query.vector, document.vector, metric=contract.metric),
        )
        for document in documents
    ]
    scored.sort(key=lambda hit: (-hit.score, hit.document_id))
    return scored[:limit]


def reciprocal_rank_fusion(
    channels: Mapping[str, Sequence[ScoredHit]],
    *,
    rank_window: int,
    constant: int,
) -> list[ScoredHit]:
    _validate_limit("rank_window", rank_window)
    _validate_limit("constant", constant)
    if len(channels) < 2:
        raise SemanticSearchError("RRF 至少需要两个通道")
    scores: dict[str, float] = {}
    for name, ranking in channels.items():
        _clean_token("channel", name)
        identifiers = [hit.document_id for hit in ranking[:rank_window]]
        if len(identifiers) != len(set(identifiers)):
            raise SemanticSearchError(f"通道 {name} 含重复 document_id")
        for rank, document_id in enumerate(identifiers, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (
                constant + rank
            )
    fused = [ScoredHit(document_id, score) for document_id, score in scores.items()]
    fused.sort(key=lambda hit: (-hit.score, hit.document_id))
    return fused


def ranking_metrics(
    ranking: Sequence[str],
    qrels: Mapping[str, int],
    *,
    top_k: int,
) -> dict[str, float | None]:
    _validate_limit("top_k", top_k)
    if not qrels:
        return {"recall": None, "mrr": None, "ndcg": None}
    top = list(ranking[:top_k])
    relevant = set(qrels)
    recall = len(relevant.intersection(top)) / len(relevant)
    reciprocal_rank = 0.0
    for rank, document_id in enumerate(top, start=1):
        if document_id in relevant:
            reciprocal_rank = 1.0 / rank
            break
    dcg = sum(
        (2 ** qrels.get(document_id, 0) - 1) / log2(rank + 1)
        for rank, document_id in enumerate(top, start=1)
    )
    ideal_grades = sorted(qrels.values(), reverse=True)[:top_k]
    ideal_dcg = sum(
        (2**grade - 1) / log2(rank + 1)
        for rank, grade in enumerate(ideal_grades, start=1)
    )
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0
    return {
        "recall": round(recall, 6),
        "mrr": round(reciprocal_rank, 6),
        "ndcg": round(ndcg, 6),
    }


def _rank_map(ranking: Sequence[ScoredHit]) -> dict[str, int]:
    return {
        hit.document_id: rank
        for rank, hit in enumerate(ranking, start=1)
    }


def _serialise_hits(
    ranking: Sequence[ScoredHit],
    *,
    top_k: int,
    source_ranks: Mapping[str, Mapping[str, int]] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for rank, hit in enumerate(ranking[:top_k], start=1):
        item: dict[str, Any] = {
            "rank": rank,
            "document_id": hit.document_id,
            "score": round(hit.score, 9),
        }
        if source_ranks is not None:
            item["source_ranks"] = {
                name: ranks.get(hit.document_id)
                for name, ranks in source_ranks.items()
            }
        result.append(item)
    return result


def evaluate(
    fixture: Fixture,
    *,
    top_k: int,
    rank_window: int,
    rrf_constant: int,
) -> dict[str, Any]:
    _validate_limit("top_k", top_k)
    _validate_limit("rank_window", rank_window)
    _validate_limit("rrf_constant", rrf_constant)
    if rank_window < top_k:
        raise SemanticSearchError("rank_window 必须大于或等于 top_k")
    channel_metrics: dict[str, list[dict[str, float | None]]] = {
        "bm25": [],
        "dense": [],
        "hybrid_rrf": [],
    }
    query_reports: list[dict[str, Any]] = []
    security_violations: list[dict[str, str]] = []
    for query in fixture.queries:
        eligible = eligible_documents(fixture, query)
        bm25 = rank_bm25(query, eligible, limit=rank_window)
        dense = rank_dense(
            query,
            eligible,
            fixture.representation,
            limit=rank_window,
        )
        source_channels = {"bm25": bm25, "dense": dense}
        hybrid = reciprocal_rank_fusion(
            source_channels,
            rank_window=rank_window,
            constant=rrf_constant,
        )
        rankings = {
            "bm25": bm25,
            "dense": dense,
            "hybrid_rrf": hybrid,
        }
        qrels = query.qrels_map()
        metrics: dict[str, dict[str, float | None]] = {}
        for channel, ranking in rankings.items():
            identifiers = [hit.document_id for hit in ranking]
            metrics[channel] = ranking_metrics(identifiers, qrels, top_k=top_k)
            channel_metrics[channel].append(metrics[channel])
            for forbidden in query.must_not_return:
                if forbidden in identifiers[:top_k]:
                    security_violations.append(
                        {
                            "query_id": query.query_id,
                            "channel": channel,
                            "document_id": forbidden,
                        }
                    )
        source_ranks = {name: _rank_map(hits) for name, hits in source_channels.items()}
        query_reports.append(
            {
                "query_id": query.query_id,
                "text": query.text,
                "eligible_document_ids": sorted(
                    document.document_id for document in eligible
                ),
                "qrels": qrels,
                "must_not_return": list(query.must_not_return),
                "metrics": metrics,
                "rankings": {
                    "bm25": _serialise_hits(bm25, top_k=top_k),
                    "dense": _serialise_hits(dense, top_k=top_k),
                    "hybrid_rrf": _serialise_hits(
                        hybrid,
                        top_k=top_k,
                        source_ranks=source_ranks,
                    ),
                },
            }
        )

    macro: dict[str, dict[str, float | None]] = {}
    for channel, per_query in channel_metrics.items():
        macro[channel] = {}
        for metric in ("recall", "mrr", "ndcg"):
            values = [
                row[metric]
                for row in per_query
                if row[metric] is not None
            ]
            macro[channel][metric] = (
                round(sum(values) / len(values), 6) if values else None
            )
    return {
        "notice": fixture.representation.notice,
        "fixture": {
            "schema_version": SCHEMA_VERSION,
            "representation_signature": fixture.representation.signature(),
            "document_count": len(fixture.documents),
            "query_count": len(fixture.queries),
        },
        "settings": {
            "top_k": top_k,
            "rank_window": rank_window,
            "rrf_constant": rrf_constant,
        },
        "macro_metrics": macro,
        "security_violations": security_violations,
        "queries": query_reports,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="离线 BM25 + toy dense + RRF 语义搜索教学实验"
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--rank-window", type=int, default=5)
    parser.add_argument("--rrf-constant", type=int, default=60)
    return parser.parse_args(argv)


def cli(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", newline="\n")
    args = parse_args(argv)
    try:
        fixture = load_fixture(args.fixture.resolve())
        report = evaluate(
            fixture,
            top_k=args.top_k,
            rank_window=args.rank_window,
            rrf_constant=args.rrf_constant,
        )
    except SemanticSearchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
