"""Deterministic, contract-checked reranker adapter for teaching only.

The rule score is transparent and deliberately non-neural.  The useful lesson
is the safe orchestration boundary: hard-filter candidates, cap the window,
validate model output, and fall back to the safe first-stage order on failure.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from math import isfinite, log2
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
import unicodedata


SCHEMA_VERSION = 2
MAX_FIXTURE_BYTES = 2 * 1024 * 1024
MAX_CANDIDATES = 10_000
ALLOWED_STATUSES = {"draft", "published", "archived"}
FAILURE_MODES = {"none", "timeout", "error", "empty", "malformed"}
DEFAULT_FIXTURE = Path(__file__).with_name("reranker-fixture.json")
SEGMENT_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+")
MODEL_REVISION = "transparent-rule-r1"
AUDIT_VISIBILITY = "protected_audit"
EVIDENCE_SCHEMA_VERSION = "reranker-evidence-v1"


class RerankerError(ValueError):
    """Invalid fixture, parameters, provider response or model failure."""


class RerankerTimeout(RerankerError):
    """Simulated provider timeout."""


class RerankerProviderError(RerankerError):
    """Simulated provider/server failure."""


class OutputContractError(RerankerError):
    """Provider output is incomplete, duplicated, unknown or non-finite."""


@dataclass(frozen=True)
class Query:
    query_id: str
    text: str
    tenant_id: str
    subject_groups: tuple[str, ...]
    authorization_revision: str
    as_of: date


@dataclass(frozen=True)
class Settings:
    candidate_window: int
    output_top_n: int
    max_per_canonical: int


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    canonical_document_id: str
    title: str
    text: str
    tenant_id: str
    acl: tuple[str, ...]
    status: str
    effective_from: date
    effective_to: date | None
    source_revision: str
    first_rank: int
    first_score: float


@dataclass(frozen=True)
class Fixture:
    query: Query
    settings: Settings
    candidates: tuple[Candidate, ...]
    qrels: tuple[tuple[str, int], ...]
    must_not_return: tuple[str, ...]

    def qrels_map(self) -> dict[str, int]:
        return dict(self.qrels)


@dataclass(frozen=True)
class ModelResult:
    candidate_id: str
    score: float
    features: tuple[tuple[str, float], ...]

    def feature_map(self) -> dict[str, float]:
        return dict(self.features)


def _clean_token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RerankerError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise RerankerError(f"{name} 长度或控制字符不合法")
    return value


def _clean_text(name: str, value: Any, maximum: int = 20_000) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RerankerError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(
        ord(character) < 32 and character not in "\n\t" for character in value
    ):
        raise RerankerError(f"{name} 长度或控制字符不合法")
    return value


def _positive_integer(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RerankerError(f"{name} 必须是正整数")
    return value


def _finite_float(
    value: Any,
    message: str,
    *,
    error_type: type[RerankerError] = RerankerError,
) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise error_type(message)
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise error_type(message) from exc
    if not isfinite(parsed):
        raise error_type(message)
    return parsed


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RerankerError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise RerankerError(f"JSON 不允许非有限数值：{value}")


def _require_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise RerankerError(
            f"{label} 字段必须精确为 {sorted(expected)}，实际为 {sorted(actual)}"
        )


def _parse_date(name: str, value: Any, *, allow_null: bool = False) -> date | None:
    if value is None and allow_null:
        return None
    value = _clean_token(name, value)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise RerankerError(f"{name} 必须是 YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise RerankerError(f"{name} 必须使用规范 ISO 日期")
    return parsed


def _parse_string_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "数组" if allow_empty else "非空数组"
        raise RerankerError(f"{label} 必须是{qualifier}")
    parsed = tuple(_clean_token(label, item) for item in value)
    if len(parsed) != len(set(parsed)) or parsed != tuple(sorted(parsed)):
        raise RerankerError(f"{label} 必须去重并按字典序排列")
    return parsed


def _read_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise RerankerError(f"无法读取 fixture：{path}") from exc
    if size > MAX_FIXTURE_BYTES:
        raise RerankerError("fixture 超过 2 MiB 教学上限")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise RerankerError("fixture 必须是 UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise RerankerError(
            f"{path.name} JSON 错误：{exc.lineno}:{exc.colno}"
        ) from exc


def _parse_query(value: Any) -> Query:
    if not isinstance(value, dict):
        raise RerankerError("query 必须是 object")
    _require_fields(
        value,
        {
            "id",
            "text",
            "tenant_id",
            "subject_groups",
            "authorization_revision",
            "as_of",
        },
        "query",
    )
    as_of = _parse_date("query.as_of", value["as_of"])
    if as_of is None:
        raise RerankerError("query.as_of 不得为空")
    return Query(
        query_id=_clean_token("query.id", value["id"]),
        text=_clean_text("query.text", value["text"], maximum=2_000),
        tenant_id=_clean_token("query.tenant_id", value["tenant_id"]),
        subject_groups=_parse_string_list(
            value["subject_groups"],
            "query.subject_groups",
            allow_empty=True,
        ),
        authorization_revision=_clean_token(
            "query.authorization_revision", value["authorization_revision"]
        ),
        as_of=as_of,
    )


def _parse_settings(value: Any) -> Settings:
    if not isinstance(value, dict):
        raise RerankerError("settings 必须是 object")
    _require_fields(
        value,
        {"candidate_window", "output_top_n", "max_per_canonical"},
        "settings",
    )
    settings = Settings(
        candidate_window=_positive_integer(
            "settings.candidate_window", value["candidate_window"]
        ),
        output_top_n=_positive_integer(
            "settings.output_top_n", value["output_top_n"]
        ),
        max_per_canonical=_positive_integer(
            "settings.max_per_canonical", value["max_per_canonical"]
        ),
    )
    if settings.output_top_n > settings.candidate_window:
        raise RerankerError("output_top_n 不得大于 candidate_window")
    return settings


def _parse_candidate(value: Any, index: int) -> Candidate:
    label = f"candidates[{index}]"
    if not isinstance(value, dict):
        raise RerankerError(f"{label} 必须是 object")
    _require_fields(
        value,
        {
            "id",
            "canonical_document_id",
            "title",
            "text",
            "tenant_id",
            "acl",
            "status",
            "effective_from",
            "effective_to",
            "source_revision",
            "first_rank",
            "first_score",
        },
        label,
    )
    status = _clean_token(f"{label}.status", value["status"])
    if status not in ALLOWED_STATUSES:
        raise RerankerError(f"{label}.status 不受支持：{status}")
    effective_from = _parse_date(
        f"{label}.effective_from", value["effective_from"]
    )
    effective_to = _parse_date(
        f"{label}.effective_to",
        value["effective_to"],
        allow_null=True,
    )
    if effective_from is None:
        raise RerankerError(f"{label}.effective_from 不得为空")
    if effective_to is not None and effective_to <= effective_from:
        raise RerankerError(f"{label} 的有效期必须满足 from < to")
    first_score = _finite_float(
        value["first_score"], f"{label}.first_score 必须是有限数值"
    )
    return Candidate(
        candidate_id=_clean_token(f"{label}.id", value["id"]),
        canonical_document_id=_clean_token(
            f"{label}.canonical_document_id", value["canonical_document_id"]
        ),
        title=_clean_text(f"{label}.title", value["title"], maximum=500),
        text=_clean_text(f"{label}.text", value["text"]),
        tenant_id=_clean_token(f"{label}.tenant_id", value["tenant_id"]),
        acl=_parse_string_list(value["acl"], f"{label}.acl", allow_empty=False),
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
        source_revision=_clean_token(
            f"{label}.source_revision", value["source_revision"]
        ),
        first_rank=_positive_integer(f"{label}.first_rank", value["first_rank"]),
        first_score=first_score,
    )


def _parse_qrels(value: Any) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict) or not value:
        raise RerankerError("qrels 必须是非空 object")
    parsed: list[tuple[str, int]] = []
    for candidate_id, relevance in value.items():
        candidate_id = _clean_token("qrels.candidate_id", candidate_id)
        if (
            not isinstance(relevance, int)
            or isinstance(relevance, bool)
            or not 1 <= relevance <= 3
        ):
            raise RerankerError(f"qrels.{candidate_id} 必须是 1..3 的整数")
        parsed.append((candidate_id, relevance))
    return tuple(sorted(parsed))


def eligibility_reason(candidate: Candidate, query: Query) -> str | None:
    if candidate.tenant_id != query.tenant_id:
        return "wrong_tenant"
    if candidate.status != "published":
        return "not_published"
    if not set(candidate.acl).intersection(query.subject_groups):
        return "acl_denied"
    if query.as_of < candidate.effective_from:
        return "not_yet_effective"
    if candidate.effective_to is not None and query.as_of >= candidate.effective_to:
        return "expired"
    return None


def load_fixture(path: Path) -> Fixture:
    value = _read_json(path)
    if not isinstance(value, dict):
        raise RerankerError("fixture 顶层必须是 object")
    _require_fields(
        value,
        {
            "schema_version",
            "query",
            "settings",
            "candidates",
            "qrels",
            "must_not_return",
        },
        "fixture",
    )
    if value["schema_version"] != SCHEMA_VERSION:
        raise RerankerError(f"不支持 schema_version：{value['schema_version']}")
    query = _parse_query(value["query"])
    settings = _parse_settings(value["settings"])
    if not isinstance(value["candidates"], list) or not value["candidates"]:
        raise RerankerError("candidates 必须是非空数组")
    if len(value["candidates"]) > MAX_CANDIDATES:
        raise RerankerError("candidates 超过教学上限")
    candidates = tuple(
        _parse_candidate(item, index)
        for index, item in enumerate(value["candidates"])
    )
    candidate_map: dict[str, Candidate] = {}
    ranks: set[int] = set()
    for candidate in candidates:
        if candidate.candidate_id in candidate_map:
            raise RerankerError(f"candidate id 重复：{candidate.candidate_id}")
        if candidate.first_rank in ranks:
            raise RerankerError(f"first_rank 重复：{candidate.first_rank}")
        candidate_map[candidate.candidate_id] = candidate
        ranks.add(candidate.first_rank)
    if ranks != set(range(1, len(candidates) + 1)):
        raise RerankerError("first_rank 必须从 1 连续排列")
    qrels = _parse_qrels(value["qrels"])
    denied = _parse_string_list(
        value["must_not_return"],
        "must_not_return",
        allow_empty=True,
    )
    qrel_ids = {candidate_id for candidate_id, _ in qrels}
    if qrel_ids.intersection(denied):
        raise RerankerError("qrels 与 must_not_return 不得重叠")
    for candidate_id in qrel_ids:
        candidate = candidate_map.get(candidate_id)
        if candidate is None:
            raise RerankerError(f"qrels 引用未知 candidate：{candidate_id}")
        if eligibility_reason(candidate, query) is not None:
            raise RerankerError(f"qrels candidate 不满足硬过滤：{candidate_id}")
    for candidate_id in denied:
        candidate = candidate_map.get(candidate_id)
        if candidate is None:
            raise RerankerError(f"must_not_return 引用未知 candidate：{candidate_id}")
        if eligibility_reason(candidate, query) is None:
            raise RerankerError(f"must_not_return candidate 仍可访问：{candidate_id}")
    return Fixture(query, settings, candidates, qrels, denied)


def analyze(text: str) -> tuple[str, ...]:
    normalised = unicodedata.normalize("NFKC", text).casefold()  # 统一全角/兼容字符并忽略大小写，减少表面写法差异。
    tokens: list[str] = []  # 保存透明规则要比较的词项或中文二字符片段。
    for match in SEGMENT_PATTERN.finditer(normalised):  # 依次读取 ASCII 词或连续中文片段。
        segment = match.group(0)  # 取出当前正则匹配到的原始片段。
        if segment.isascii():  # 英文、数字等 ASCII 片段可作为一个完整词项。
            tokens.append(segment)  # 保留完整 ASCII token，方便精确词面重叠。
        elif len(segment) == 1:  # 单个汉字无法再切出长度为 2 的 n-gram。
            tokens.append(segment)  # 直接把它作为一个可检索词项。
        else:  # 连续中文片段使用相邻二字符来获得最小的词序上下文。
            tokens.extend(  # 把每个二字符片段追加进 token 列表。
                segment[index : index + 2]  # 取 index 与下一字符组成的滑动窗口。
                for index in range(len(segment) - 1)  # 最后一个起点是倒数第二个字符。
            )
    return tuple(tokens)  # 返回不可变 token 序列，确保相同输入的评分可重放。


def transparent_rule_score(query: Query, candidate: Candidate) -> ModelResult:
    query_terms = set(analyze(query.text))  # 把 query 变成去重后的透明词项集合。
    title_terms = set(analyze(candidate.title))  # 单独分析标题，因为标题匹配在本教学规则中权重更高。
    body_terms = set(analyze(candidate.text))  # 单独分析正文，避免和标题特征混在一起。
    denominator = max(1, len(query_terms))  # 空 query 也不会出现除以 0；上游已负责更严格的文本校验。
    title_coverage = len(query_terms.intersection(title_terms)) / denominator  # 计算 query 词项有多少出现在标题中。
    body_coverage = len(query_terms.intersection(body_terms)) / denominator  # 计算 query 词项有多少出现在正文中。
    exact_query = unicodedata.normalize("NFKC", query.text).casefold()  # 为短语匹配准备同样规范化的 query。
    combined = unicodedata.normalize(  # 把标题和正文合成一个只用于短语判断的字符串。
        "NFKC", f"{candidate.title} {candidate.text}"  # 用空格分隔，避免两个字段首尾无意粘连。
    ).casefold()  # 再忽略大小写，使比较与上面的 token 化一致。
    exact_phrase = 1.0 if exact_query in combined else 0.0  # 完整 query 出现时给予一个可解释的 bonus。
    score = 2.0 * title_coverage + body_coverage + exact_phrase  # 这是教学权重，不是可迁移的模型分数。
    features = (  # 将每个组成特征随结果输出，便于审计为何候选升降。
        ("body_coverage", round(body_coverage, 9)),  # 记录正文词项覆盖率并固定展示精度。
        ("exact_phrase", exact_phrase),  # 记录是否命中了完整 query 短语。
        ("title_coverage", round(title_coverage, 9)),  # 记录标题词项覆盖率。
    )
    return ModelResult(candidate.candidate_id, score, features)  # 返回 ID、总分与可审计特征，而不修改候选对象。


def simulate_provider(
    query: Query,
    candidates: Sequence[Candidate],
    *,
    failure_mode: str,
) -> list[ModelResult]:
    if failure_mode not in FAILURE_MODES:  # CLI 以外的调用也必须遵守允许的故障枚举。
        raise RerankerError(f"未知 failure_mode：{failure_mode}")  # 不把未知字符串当成正常 provider 状态。
    if failure_mode == "timeout":  # 模拟服务在截止时间内没有返回。
        raise RerankerTimeout("simulated_timeout")  # 外层捕获后切换到安全 fallback。
    if failure_mode == "error":  # 模拟可识别的 provider/server 失败。
        raise RerankerProviderError("simulated_provider_error")  # 外层同样应给出受控报告。
    if failure_mode == "empty":  # 模拟模型返回了语法合法但没有任何候选的响应。
        return []  # 由输出契约层判为无效，不能解释为“都不相关”。
    results = [transparent_rule_score(query, candidate) for candidate in candidates]  # 正常路径为窗口中每个候选生成一个透明结果。
    if failure_mode == "malformed" and results:  # 构造重复 ID 的畸形输出，测试 exact-set 校验。
        return [results[0], results[0]]  # 故意漏掉其余候选，验证 fallback 不信任半截结果。
    return results  # 只有完整正常的列表才会进入后续模型输出校验。


def validate_model_output(
    results: Any,
    candidates: Sequence[Candidate],
) -> dict[str, ModelResult]:
    expected = {candidate.candidate_id for candidate in candidates}
    if not isinstance(results, list) or not results:
        raise OutputContractError("模型输出必须是非空 list")
    parsed: dict[str, ModelResult] = {}
    for index, item in enumerate(results):
        if not isinstance(item, ModelResult):
            raise OutputContractError(f"results[{index}] 类型错误")
        if item.candidate_id not in expected:
            raise OutputContractError(f"模型返回未知 candidate：{item.candidate_id}")
        if item.candidate_id in parsed:
            raise OutputContractError(f"模型重复返回 candidate：{item.candidate_id}")
        _finite_float(
            item.score,
            f"模型分数非有限：{item.candidate_id}",
            error_type=OutputContractError,
        )
        feature_names: set[str] = set()
        for name, value in item.features:
            _clean_token("feature.name", name)
            if name in feature_names:
                raise OutputContractError(f"feature 非法：{item.candidate_id}/{name}")
            _finite_float(
                value,
                f"feature 非法：{item.candidate_id}/{name}",
                error_type=OutputContractError,
            )
            feature_names.add(name)
        parsed[item.candidate_id] = item
    missing = expected.difference(parsed)
    if missing:
        raise OutputContractError(f"模型漏返回 candidate：{sorted(missing)}")
    return parsed


def ranking_metrics(
    ranking: Sequence[str],
    qrels: Mapping[str, int],
    *,
    top_n: int,
) -> dict[str, float]:
    _positive_integer("top_n", top_n)
    top = list(ranking[:top_n])
    reciprocal_rank = 0.0
    for rank, candidate_id in enumerate(top, start=1):
        if candidate_id in qrels:
            reciprocal_rank = 1.0 / rank
            break
    precision = sum(candidate_id in qrels for candidate_id in top) / top_n
    dcg = sum(
        (2 ** qrels.get(candidate_id, 0) - 1) / log2(rank + 1)
        for rank, candidate_id in enumerate(top, start=1)
    )
    ideal = sorted(qrels.values(), reverse=True)[:top_n]
    ideal_dcg = sum(
        (2**grade - 1) / log2(rank + 1)
        for rank, grade in enumerate(ideal, start=1)
    )
    return {
        "mrr": round(reciprocal_rank, 6),
        "ndcg": round(dcg / ideal_dcg if ideal_dcg else 0.0, 6),
        "precision": round(precision, 6),
    }


def select_with_canonical_cap(
    ordered_ids: Sequence[str],
    candidate_map: Mapping[str, Candidate],
    *,
    top_n: int,
    max_per_canonical: int,
) -> list[str]:
    _positive_integer("top_n", top_n)
    _positive_integer("max_per_canonical", max_per_canonical)
    selected: list[str] = []
    counts: Counter[str] = Counter()
    for candidate_id in ordered_ids:
        candidate = candidate_map[candidate_id]
        canonical = candidate.canonical_document_id
        if counts[canonical] >= max_per_canonical:
            continue
        selected.append(candidate_id)
        counts[canonical] += 1
        if len(selected) == top_n:
            break
    return selected


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _fixture_payload(fixture: Fixture) -> dict[str, Any]:
    """Return every normalized field that can affect scoring or authorization."""

    candidates = sorted(
        fixture.candidates,
        key=lambda candidate: (candidate.first_rank, candidate.candidate_id),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "id": fixture.query.query_id,
            "text": fixture.query.text,
            "tenant_id": fixture.query.tenant_id,
            "subject_groups": list(fixture.query.subject_groups),
            "authorization_revision": fixture.query.authorization_revision,
            "as_of": fixture.query.as_of.isoformat(),
        },
        "settings": {
            "candidate_window": fixture.settings.candidate_window,
            "output_top_n": fixture.settings.output_top_n,
            "max_per_canonical": fixture.settings.max_per_canonical,
        },
        "candidates": [
            {
                "id": candidate.candidate_id,
                "canonical_document_id": candidate.canonical_document_id,
                "title": candidate.title,
                "text": candidate.text,
                "tenant_id": candidate.tenant_id,
                "acl": list(candidate.acl),
                "status": candidate.status,
                "effective_from": candidate.effective_from.isoformat(),
                "effective_to": (
                    candidate.effective_to.isoformat()
                    if candidate.effective_to is not None
                    else None
                ),
                "source_revision": candidate.source_revision,
                "first_rank": candidate.first_rank,
                "first_score": candidate.first_score,
            }
            for candidate in candidates
        ],
        "qrels": fixture.qrels_map(),
        "must_not_return": list(fixture.must_not_return),
    }


def _fixture_signature(fixture: Fixture) -> str:
    return _canonical_sha256(_fixture_payload(fixture))


def _evidence_signature(
    fixture: Fixture,
    *,
    execution: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> str:
    return _canonical_sha256(
        {
            "envelope": {
                "visibility": AUDIT_VISIBILITY,
                "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
            },
            "normalized_input": _fixture_payload(fixture),
            "execution": dict(execution),
            "decision": dict(decision),
        }
    )


def _serialise_ranking(
    identifiers: Sequence[str],
    candidate_map: Mapping[str, Candidate],
    model_results: Mapping[str, ModelResult] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, candidate_id in enumerate(identifiers, start=1):
        candidate = candidate_map[candidate_id]
        model = model_results.get(candidate_id) if model_results else None
        rows.append(
            {
                "rank": rank,
                "candidate_id": candidate_id,
                "canonical_document_id": candidate.canonical_document_id,
                "first_rank": candidate.first_rank,
                "first_score": candidate.first_score,
                "model_score": round(model.score, 9) if model else None,
                "features": model.feature_map() if model else {},
            }
        )
    return rows


def run_pipeline(
    fixture: Fixture,
    *,
    failure_mode: str,
    candidate_window: int | None = None,
    output_top_n: int | None = None,
    max_per_canonical: int | None = None,
) -> dict[str, Any]:
    _clean_token(
        "query.authorization_revision", fixture.query.authorization_revision
    )
    window_size = _positive_integer(
        "candidate_window",
        (
            fixture.settings.candidate_window
            if candidate_window is None
            else candidate_window
        ),
    )
    top_n = _positive_integer(
        "output_top_n",
        fixture.settings.output_top_n if output_top_n is None else output_top_n,
    )
    canonical_cap = _positive_integer(
        "max_per_canonical",
        (
            fixture.settings.max_per_canonical
            if max_per_canonical is None
            else max_per_canonical
        ),
    )
    if top_n > window_size:
        raise RerankerError("output_top_n 不得大于 candidate_window")
    if failure_mode not in FAILURE_MODES:
        raise RerankerError(f"未知 failure_mode：{failure_mode}")

    ordered = sorted(fixture.candidates, key=lambda item: item.first_rank)
    eligible: list[Candidate] = []
    filtered_out: list[dict[str, str]] = []
    for candidate in ordered:
        reason = eligibility_reason(candidate, fixture.query)
        if reason is None:
            eligible.append(candidate)
        else:
            filtered_out.append(
                {"candidate_id": candidate.candidate_id, "reason": reason}
            )
    window = eligible[:window_size]
    candidate_map = {candidate.candidate_id: candidate for candidate in eligible}
    window_ids = [candidate.candidate_id for candidate in window]
    qrels = fixture.qrels_map()
    candidate_recall = len(set(window_ids).intersection(qrels)) / len(qrels)
    first_output = select_with_canonical_cap(
        window_ids,
        candidate_map,
        top_n=top_n,
        max_per_canonical=canonical_cap,
    )

    applied = False
    fallback_reason: str | None = None
    model_results: dict[str, ModelResult] | None = None
    ordered_after_model = window_ids
    if not window:
        fallback_reason = "empty_candidate_window"
    else:
        try:
            raw_results = simulate_provider(
                fixture.query,
                window,
                failure_mode=failure_mode,
            )
            model_results = validate_model_output(raw_results, window)
            ordered_after_model = sorted(
                window_ids,
                key=lambda candidate_id: (
                    -model_results[candidate_id].score,
                    candidate_map[candidate_id].first_rank,
                    candidate_id,
                ),
            )
            applied = True
        except RerankerTimeout:
            fallback_reason = "timeout"
        except RerankerProviderError:
            fallback_reason = "provider_error"
        except OutputContractError:
            fallback_reason = "invalid_output"

    final_output = select_with_canonical_cap(
        ordered_after_model,
        candidate_map,
        top_n=top_n,
        max_per_canonical=canonical_cap,
    )
    forbidden = set(fixture.must_not_return)
    security_violations = sorted(
        forbidden.intersection(window_ids).union(forbidden.intersection(final_output))
    )
    execution = {
        "candidate_window": window_size,
        "output_top_n": top_n,
        "max_per_canonical": canonical_cap,
        "failure_mode": failure_mode,
        "model_revision": MODEL_REVISION,
    }
    first_stage = {
        "ranking": _serialise_ranking(first_output, candidate_map, None),
        "metrics": ranking_metrics(first_output, qrels, top_n=top_n),
    }
    final = {
        "ranking": _serialise_ranking(
            final_output,
            candidate_map,
            model_results if applied else None,
        ),
        "metrics": ranking_metrics(final_output, qrels, top_n=top_n),
    }
    decision = {
        "candidate_recall_at_window": round(candidate_recall, 6),
        "filtered_out": filtered_out,
        "window_candidate_ids": window_ids,
        "rerank_applied": applied,
        "fallback_reason": fallback_reason,
        "first_stage": first_stage,
        "final": final,
        "security_violations": security_violations,
    }
    fixture_sha256 = _fixture_signature(fixture)
    return {
        "visibility": AUDIT_VISIBILITY,
        "notice": (
            "protected teaching/audit envelope, not a public response; "
            "transparent rule reranker is not a cross-encoder or LLM quality claim"
        ),
        "evidence": {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "authorization_revision": fixture.query.authorization_revision,
            "fixture_sha256": fixture_sha256,
            "evidence_sha256": _evidence_signature(
                fixture,
                execution=execution,
                decision=decision,
            ),
        },
        "fixture": {
            "schema_version": SCHEMA_VERSION,
            "signature": fixture_sha256,
            "candidate_count": len(fixture.candidates),
            "eligible_count": len(eligible),
        },
        "settings": execution,
        **decision,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="严格输出契约与安全回退的离线教学 reranker"
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--failure", choices=sorted(FAILURE_MODES), default="none")
    parser.add_argument("--candidate-window", type=int)
    parser.add_argument("--output-top-n", type=int)
    parser.add_argument("--max-per-canonical", type=int)
    return parser.parse_args(argv)


def cli(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", newline="\n")
    args = parse_args(argv)
    try:
        fixture = load_fixture(args.fixture.resolve())
        report = run_pipeline(
            fixture,
            failure_mode=args.failure,
            candidate_window=args.candidate_window,
            output_top_n=args.output_top_n,
            max_per_canonical=args.max_per_canonical,
        )
    except RerankerError as exc:
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
