"""Strict offline RAG teaching pipeline with safe filters and extractive citations.

This module deliberately uses no embedding model, vector index, LLM, network, or key.
Its purpose is to make orchestration contracts observable and testable before real
components are connected.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


ROOT_FIELDS = {
    "schema_version",
    "pipeline",
    "evaluation_policy",
    "documents",
    "queries",
}
PIPELINE_FIELDS = {
    "pipeline_revision",
    "retrieval_revision",
    "rerank_revision",
    "context_policy_revision",
    "answer_policy_revision",
    "retrieval_limit",
    "context_limit",
    "max_context_chars",
}
DOCUMENT_FIELDS = {
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
    "authority",
    "facts",
}
FACT_FIELDS = {"fact_id", "topic", "statement", "value", "unit"}
QUERY_FIELDS = {
    "id",
    "text",
    "tenant_id",
    "subject_groups",
    "authorization_revision",
    "as_of",
    "route",
    "topic",
    "slice",
    "critical",
    "expected_status",
    "expected_fact_ids",
    "forbidden_document_ids",
    "forbidden_output_substrings",
}
RUNTIME_QUERY_FIELDS = {
    "id",
    "text",
    "tenant_id",
    "subject_groups",
    "authorization_revision",
    "as_of",
    "route",
    "topic",
}
EVALUATION_POLICY_FIELDS = {
    "suite_revision",
    "harness_revision",
    "min_case_pass_rate",
    "min_critical_case_pass_rate",
    "min_status_accuracy",
    "min_retrieval_fact_recall",
    "min_context_fact_recall",
    "min_citation_fact_recall",
    "max_non_disclosure_violations",
}
RESPONSE_FIELDS = {"trace_id", "status", "answer", "claims", "citations"}
EXECUTION_FIELDS = {"response", "audit_trace"}
TRACE_FIELDS = {
    "visibility",
    "trace_id",
    "pipeline_revision",
    "retrieval_revision",
    "rerank_revision",
    "context_policy_revision",
    "answer_policy_revision",
    "query_id",
    "route",
    "topic",
    "authorization_revision",
    "as_of",
    "failure",
    "degraded",
    "filter_summary",
    "retrieved",
    "reranked",
    "selected",
    "dropped",
    "context_chars",
    "fallback",
}
VALID_STATUSES = {
    "answered",
    "conflict",
    "insufficient_evidence",
    "tool_required",
    "dependency_unavailable",
    "generation_unavailable",
}
VALID_FAILURES = {"none", "retrieval_error", "reranker_error", "generation_error"}
TOPIC_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ASCII_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
CJK_RUN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
MAX_FIXTURE_BYTES = 2_000_000
MAX_JSON_DEPTH = 64
MAX_DOCUMENTS = 256
MAX_QUERIES = 512
MAX_FACTS_PER_DOCUMENT = 128
MAX_LIST_ITEMS = 512
MAX_STAGE_LIMIT = 1_000
MAX_CONTEXT_CHARS = 1_000_000
MAX_STRING_CHARS = 100_000


class FixtureError(ValueError):
    """Raised when the teaching fixture violates its explicit contract."""


def _reject_constant(value: str) -> None:
    raise FixtureError(f"JSON 不允许非有限常量：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # Do not reflect an untrusted member name into a CLI error.  Besides
            # needless disclosure, a JSON-escaped lone surrogate cannot be
            # written to a strict UTF-8 terminal.
            raise FixtureError("JSON 出现重复字段")
        result[key] = value
    return result


def _reject_invalid_unicode(value: Any) -> None:
    """Reject JSON strings/keys that cannot become strict UTF-8 evidence bytes."""

    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise FixtureError("fixture 含非法 Unicode") from exc
        return
    if isinstance(value, list):
        for item in value:
            _reject_invalid_unicode(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_invalid_unicode(key)
            _reject_invalid_unicode(item)


def _reject_excessive_json_nesting(text: str) -> None:
    """Bound container nesting before the recursive JSON decoder runs."""

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise FixtureError(f"JSON 容器嵌套不得超过 {MAX_JSON_DEPTH} 层")
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        raise FixtureError("fixture 必须是 JSON 文本")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise FixtureError("fixture 含非法 Unicode") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise FixtureError(f"fixture 不得超过 {MAX_FIXTURE_BYTES} UTF-8 bytes")
    _reject_excessive_json_nesting(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(f"fixture JSON 无法解析：{exc.msg}") from exc
    except RecursionError as exc:
        raise FixtureError("fixture JSON 嵌套超过解析器上限") from exc
    _reject_invalid_unicode(parsed)
    return parsed


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} 必须是对象")
        return False
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        errors.append(f"{label} 字段不匹配：missing={missing}, extra={extra}")
        return False
    return True


def _nonempty_string(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_STRING_CHARS:
        return False
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return False
    return True


def _parse_iso_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} 必须是 ISO 日期字符串")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} 不是有效 ISO 日期：{value!r}")
        return None


def _sorted_unique_strings(value: Any, label: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not all(_nonempty_string(item) for item in value):
        errors.append(f"{label} 必须是非空字符串组成的列表")
        return None
    if len(value) > MAX_LIST_ITEMS:
        errors.append(f"{label} 不得超过 {MAX_LIST_ITEMS} 项")
        return None
    strings = list(value)
    if strings != sorted(set(strings)):
        errors.append(f"{label} 必须已排序且无重复")
    return strings


def _unit_interval(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} 必须是 0..1 的有限数值")
        return
    try:
        number = float(value)
    except OverflowError:
        errors.append(f"{label} 必须是 0..1 的有限数值")
        return
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        errors.append(f"{label} 必须是 0..1 的有限数值")


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _runtime_query(query_case: dict[str, Any]) -> dict[str, Any]:
    """Project only trusted runtime fields into the answer pipeline, excluding oracle data."""

    return {field: query_case[field] for field in RUNTIME_QUERY_FIELDS}


def validate_fixture(fixture: Any) -> list[str]:
    """Return every detectable fixture-contract violation without using assert."""

    errors: list[str] = []
    if not _exact_fields(fixture, ROOT_FIELDS, "root", errors):
        return errors
    if fixture["schema_version"] != "2.0":
        errors.append("schema_version 必须为 '2.0'")

    pipeline = fixture["pipeline"]
    if _exact_fields(pipeline, PIPELINE_FIELDS, "pipeline", errors):
        for field in (
            "pipeline_revision",
            "retrieval_revision",
            "rerank_revision",
            "context_policy_revision",
            "answer_policy_revision",
        ):
            if not _nonempty_string(pipeline[field]):
                errors.append(f"pipeline.{field} 必须是非空字符串")
        for field in ("retrieval_limit", "context_limit"):
            if type(pipeline[field]) is not int or pipeline[field] <= 0:
                errors.append(f"pipeline.{field} 必须是正整数")
            elif pipeline[field] > MAX_STAGE_LIMIT:
                errors.append(
                    f"pipeline.{field} 不得超过 {MAX_STAGE_LIMIT}"
                )
        if (
            type(pipeline["max_context_chars"]) is not int
            or not 1 <= pipeline["max_context_chars"] <= MAX_CONTEXT_CHARS
        ):
            errors.append(
                f"pipeline.max_context_chars 必须是 1..{MAX_CONTEXT_CHARS} 的整数"
            )

    evaluation_policy = fixture["evaluation_policy"]
    if _exact_fields(
        evaluation_policy,
        EVALUATION_POLICY_FIELDS,
        "evaluation_policy",
        errors,
    ):
        for field in ("suite_revision", "harness_revision"):
            if not _nonempty_string(evaluation_policy[field]):
                errors.append(f"evaluation_policy.{field} 必须是非空字符串")
        for field in (
            "min_case_pass_rate",
            "min_critical_case_pass_rate",
            "min_status_accuracy",
            "min_retrieval_fact_recall",
            "min_context_fact_recall",
            "min_citation_fact_recall",
        ):
            _unit_interval(
                evaluation_policy[field],
                f"evaluation_policy.{field}",
                errors,
            )
        if (
            type(evaluation_policy["max_non_disclosure_violations"]) is not int
            or evaluation_policy["max_non_disclosure_violations"] < 0
        ):
            errors.append(
                "evaluation_policy.max_non_disclosure_violations 必须是非负整数"
            )

    documents = fixture["documents"]
    if (
        not isinstance(documents, list)
        or not documents
        or len(documents) > MAX_DOCUMENTS
    ):
        errors.append(f"documents 必须是 1..{MAX_DOCUMENTS} 项的列表")
        documents = []
    document_ids: set[str] = set()
    fact_ids: set[str] = set()
    for index, document in enumerate(documents):
        label = f"documents[{index}]"
        if not _exact_fields(document, DOCUMENT_FIELDS, label, errors):
            continue
        for field in (
            "id",
            "canonical_document_id",
            "title",
            "text",
            "tenant_id",
            "source_revision",
        ):
            if not _nonempty_string(document[field]):
                errors.append(f"{label}.{field} 必须是非空字符串")
        document_id = document["id"]
        if isinstance(document_id, str):
            if document_id in document_ids:
                errors.append(f"document id 重复：{document_id}")
            document_ids.add(document_id)
        acl = _sorted_unique_strings(document["acl"], f"{label}.acl", errors)
        if acl == []:
            errors.append(f"{label}.acl 不得为空")
        if not isinstance(document["status"], str) or document["status"] not in {
            "published",
            "draft",
            "archived",
        }:
            errors.append(f"{label}.status 非法")
        start = _parse_iso_date(document["effective_from"], f"{label}.effective_from", errors)
        end_value = document["effective_to"]
        end = None
        if end_value is not None:
            end = _parse_iso_date(end_value, f"{label}.effective_to", errors)
        if start is not None and end is not None and end <= start:
            errors.append(f"{label} 的有效期必须满足 [effective_from, effective_to)")
        if type(document["authority"]) is not int or not 0 <= document["authority"] <= 100:
            errors.append(f"{label}.authority 必须是 0..100 的整数")

        facts = document["facts"]
        if (
            not isinstance(facts, list)
            or not facts
            or len(facts) > MAX_FACTS_PER_DOCUMENT
        ):
            errors.append(
                f"{label}.facts 必须是 1..{MAX_FACTS_PER_DOCUMENT} 项的列表"
            )
            continue
        for fact_index, fact in enumerate(facts):
            fact_label = f"{label}.facts[{fact_index}]"
            if not _exact_fields(fact, FACT_FIELDS, fact_label, errors):
                continue
            for field in FACT_FIELDS:
                if not _nonempty_string(fact[field]):
                    errors.append(f"{fact_label}.{field} 必须是非空字符串")
            fact_id = fact["fact_id"]
            if isinstance(fact_id, str):
                if fact_id in fact_ids:
                    errors.append(f"fact id 重复：{fact_id}")
                fact_ids.add(fact_id)
            topic = fact["topic"]
            if isinstance(topic, str) and TOPIC_PATTERN.fullmatch(topic) is None:
                errors.append(f"{fact_label}.topic 必须是稳定的 snake_case 标识")
            if isinstance(fact["statement"], str) and isinstance(document["text"], str):
                if fact["statement"] not in document["text"]:
                    errors.append(f"{fact_label}.statement 必须逐字存在于 document.text")

    queries = fixture["queries"]
    if (
        not isinstance(queries, list)
        or not queries
        or len(queries) > MAX_QUERIES
    ):
        errors.append(f"queries 必须是 1..{MAX_QUERIES} 项的列表")
        queries = []
    query_ids: set[str] = set()
    for index, query in enumerate(queries):
        label = f"queries[{index}]"
        if not _exact_fields(query, QUERY_FIELDS, label, errors):
            continue
        for field in (
            "id",
            "text",
            "tenant_id",
            "authorization_revision",
            "topic",
            "slice",
        ):
            if not _nonempty_string(query[field]):
                errors.append(f"{label}.{field} 必须是非空字符串")
        query_id = query["id"]
        if isinstance(query_id, str):
            if query_id in query_ids:
                errors.append(f"query id 重复：{query_id}")
            query_ids.add(query_id)
        subject_groups = _sorted_unique_strings(
            query["subject_groups"], f"{label}.subject_groups", errors
        )
        if subject_groups == []:
            errors.append(f"{label}.subject_groups 不得为空；公共访问也应由可信组解析")
        _parse_iso_date(query["as_of"], f"{label}.as_of", errors)
        if not isinstance(query["route"], str) or query["route"] not in {
            "knowledge",
            "tool_required",
        }:
            errors.append(f"{label}.route 非法")
        topic = query["topic"]
        if isinstance(topic, str) and TOPIC_PATTERN.fullmatch(topic) is None:
            errors.append(f"{label}.topic 必须是稳定的 snake_case 标识")
        slice_name = query["slice"]
        if isinstance(slice_name, str) and TOPIC_PATTERN.fullmatch(slice_name) is None:
            errors.append(f"{label}.slice 必须是稳定的 snake_case 标识")
        if type(query["critical"]) is not bool:
            errors.append(f"{label}.critical 必须是布尔值")
        if (
            not isinstance(query["expected_status"], str)
            or query["expected_status"] not in VALID_STATUSES
        ):
            errors.append(f"{label}.expected_status 非法")
        expected_fact_ids = _sorted_unique_strings(
            query["expected_fact_ids"], f"{label}.expected_fact_ids", errors
        )
        forbidden_ids = _sorted_unique_strings(
            query["forbidden_document_ids"], f"{label}.forbidden_document_ids", errors
        )
        forbidden_substrings = _sorted_unique_strings(
            query["forbidden_output_substrings"],
            f"{label}.forbidden_output_substrings",
            errors,
        )
        if expected_fact_ids is not None:
            unknown_facts = sorted(set(expected_fact_ids) - fact_ids)
            if unknown_facts:
                errors.append(f"{label} 引用了未知 fact：{unknown_facts}")
        if forbidden_ids is not None:
            unknown_documents = sorted(set(forbidden_ids) - document_ids)
            if unknown_documents:
                errors.append(f"{label} 引用了未知 forbidden document：{unknown_documents}")
        if forbidden_substrings is not None:
            if any(len(item) < 4 for item in forbidden_substrings):
                errors.append(f"{label}.forbidden_output_substrings 每项至少 4 个字符")
            forbidden_documents = [
                document
                for document in documents
                if isinstance(document, dict)
                and isinstance(document.get("id"), str)
                and document["id"] in set(forbidden_ids or [])
            ]
            forbidden_source = json.dumps(
                forbidden_documents,
                ensure_ascii=False,
                sort_keys=True,
            )
            for index, item in enumerate(forbidden_substrings):
                if item not in forbidden_source:
                    errors.append(
                        f"{label}.forbidden_output_substrings[{index}] "
                        "必须来自 forbidden document 的测试 canary"
                    )
        if query["route"] == "tool_required" and query["expected_status"] != "tool_required":
            errors.append(f"{label} 的 tool_required 路由必须期望 tool_required 状态")
    if queries and not any(
        isinstance(query, dict) and query.get("critical") is True for query in queries
    ):
        errors.append("queries 至少需要一个 critical case 才能计算关键切片门")
    if queries and not any(
        isinstance(query, dict) and query.get("expected_fact_ids") for query in queries
    ):
        errors.append("queries 至少需要一个 expected fact 才能计算分层 fact recall")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    """Load strict JSON and reject duplicate keys, NaN, Infinity, and bad schemas."""

    try:
        with path.open("rb") as handle:
            raw_bytes = handle.read(MAX_FIXTURE_BYTES + 1)
        if len(raw_bytes) > MAX_FIXTURE_BYTES:
            raise FixtureError(
                f"fixture 不得超过 {MAX_FIXTURE_BYTES} UTF-8 bytes"
            )
        raw = raw_bytes.decode("utf-8", errors="strict")
        fixture = strict_json_loads(raw)
    except FixtureError:
        raise
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"无法读取 fixture：{type(exc).__name__}") from exc
    errors = validate_fixture(fixture)
    if errors:
        raise FixtureError("fixture 校验失败：\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root 必须是对象")
    return fixture


def text_features(text: str) -> set[str]:
    """Create transparent ASCII tokens plus CJK unigrams/bigrams for the toy retriever."""

    lowered = text.lower()  # 统一英文大小写；这只是透明词法基线，不是 tokenizer。
    features = {f"a:{token}" for token in ASCII_TOKEN_PATTERN.findall(lowered)}  # 为每个 ASCII 词加类型前缀，避免和中文片段混淆。
    for run in CJK_RUN_PATTERN.findall(lowered):  # 逐段处理连续中文字符。
        features.update(f"c1:{character}" for character in run)  # 加入单字特征，保证短词仍可命中。
        features.update(f"c2:{run[index:index + 2]}" for index in range(len(run) - 1))  # 加入相邻二字特征，保留最小局部语序。
    return features  # 返回去重集合，后续只比较重叠数量。


def filter_documents(
    documents: list[dict[str, Any]], query: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, list[str]]]:
    """Apply tenant, lifecycle, time, and ACL constraints before any scoring."""

    as_of = date.fromisoformat(query["as_of"])  # 把可信运行时间解析为日期，供有效期判断使用。
    groups = set(query["subject_groups"])  # 取可信主体的组集合，后续与每篇文档 ACL 求交。
    visible: list[dict[str, Any]] = []  # 只有通过所有强制约束的文档才会加入此列表。
    decisions: dict[str, list[str]] = {}  # 受保护 trace 保存每篇文档的过滤原因。
    reason_counts: dict[str, int] = {}  # 聚合原因计数，公共响应不能看到它。
    for document in documents:  # 在计算任何检索分数前逐篇执行安全过滤。
        reasons: list[str] = []  # 同一文档可同时触发多个过滤原因。
        if document["tenant_id"] != query["tenant_id"]:  # 租户必须完全一致，不能仅靠语义相近。
            reasons.append("tenant_mismatch")  # 记录内部原因，便于审计和测试。
        if document["status"] != "published":  # draft/archived 文档不参与在线检索。
            reasons.append("not_published")  # 先过滤生命周期状态，避免后续评分泄露。
        effective_from = date.fromisoformat(document["effective_from"])
        effective_to = (
            date.fromisoformat(document["effective_to"])
            if document["effective_to"] is not None
            else None
        )
        if as_of < effective_from or (effective_to is not None and as_of >= effective_to):  # 有效期使用半开区间 [from,to)。
            reasons.append("outside_effective_window")  # 到 effective_to 当天即不再可用。
        acl = set(document["acl"])  # 文档 ACL 是允许读取的组集合。
        if not (acl & groups):  # 当前主体必须至少命中一个被授权组。
            reasons.append("acl_denied")  # 无组交集时 fail closed。
        decisions[document["id"]] = reasons  # 即使不可见也保留内部决定，供 protected audit 使用。
        if reasons:  # 有任一强制条件失败就绝不进入候选集合。
            for reason in reasons:  # 每种失败都计数，帮助排查策略漂移。
                reason_counts[reason] = reason_counts.get(reason, 0) + 1  # 增加该原因的聚合数。
        else:  # 只有所有条件通过时才可被检索器打分。
            visible.append(document)  # 保存可见文档的完整教学记录。
    summary = {  # 形成不应进入公共响应的内部过滤摘要。
        "visible": len(visible),
        "filtered": len(documents) - len(visible),
        "reasons": dict(sorted(reason_counts.items())),
    }
    return visible, summary, decisions  # 同时返回安全候选、汇总和逐文档决定给受保护执行链。


def retrieve(
    query: dict[str, Any], documents: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Return positive lexical candidates; scores are comparable only within this query."""

    query_features = text_features(query["text"])  # 将 query 转成透明词法特征集合。
    candidates: list[dict[str, Any]] = []  # 这里接收的 documents 已完成 tenant/ACL/生命周期过滤。
    for document in documents:  # 仅在可见集合中计算教学检索分数。
        document_features = text_features(f"{document['title']} {document['text']}")  # 标题和正文共同参与召回。
        overlap = len(query_features & document_features)  # 计算两集合共享特征数。
        denominator = math.sqrt(max(1, len(query_features)) * max(1, len(document_features)))  # 用长度几何平均做简单归一化。
        score = overlap / denominator  # 得到仅可在本 query 内比较的非负词法分数。
        if score > 0.0:  # 0 分候选没有共同词项，不浪费后续 rerank 窗口。
            candidates.append({"document_id": document["id"], "score": round(score, 6)})  # 固定展示精度，保留文档身份。
    candidates.sort(key=lambda item: (-item["score"], item["document_id"]))  # 分数降序，ID 升序稳定打破平局。
    limited = candidates[:limit]  # 强制第一阶段候选上限，避免下游无限增长。
    return [  # 生成连续 rank 的轻量候选投影。
        {"document_id": item["document_id"], "rank": index, "score": item["score"]}  # 不携带正文，正文仍由受控映射读取。
        for index, item in enumerate(limited, start=1)  # 从 1 开始编号，符合用户可读排名习惯。
    ]


def rerank(
    query: dict[str, Any],
    candidates: list[dict[str, Any]],
    document_by_id: dict[str, dict[str, Any]],
    use_fallback: bool,
) -> list[dict[str, Any]]:
    """Apply a deterministic topic rule or preserve retrieval order as fallback."""

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        document = document_by_id[candidate["document_id"]]
        topic_match = any(fact["topic"] == query["topic"] for fact in document["facts"])
        score = candidate["score"]
        if not use_fallback:
            score += (2.0 if topic_match else 0.0) + document["authority"] / 10_000
        scored.append(
            {
                "document_id": candidate["document_id"],
                "retrieval_rank": candidate["rank"],
                "retrieval_score": candidate["score"],
                "score": round(score, 6),
                "topic_match": topic_match,
            }
        )
    if not use_fallback:
        scored.sort(key=lambda item: (-item["score"], item["retrieval_rank"], item["document_id"]))
    return [dict(item, rank=index) for index, item in enumerate(scored, start=1)]


def select_context(
    ranked: list[dict[str, Any]],
    document_by_id: dict[str, dict[str, Any]],
    context_limit: int,
    max_context_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """Select a bounded context while deduplicating canonical documents."""

    selected: list[dict[str, Any]] = []
    dropped: list[dict[str, str]] = []
    canonical_seen: set[str] = set()
    context_chars = 0
    for candidate in ranked:
        document = document_by_id[candidate["document_id"]]
        canonical_id = document["canonical_document_id"]
        chars = len(document["title"]) + len(document["text"])
        if canonical_id in canonical_seen:
            dropped.append({"document_id": document["id"], "reason": "canonical_duplicate"})
            continue
        if len(selected) >= context_limit:
            dropped.append({"document_id": document["id"], "reason": "context_limit"})
            continue
        if context_chars + chars > max_context_chars:
            dropped.append({"document_id": document["id"], "reason": "character_budget"})
            continue
        canonical_seen.add(canonical_id)
        context_chars += chars
        selected.append(
            {
                "document_id": document["id"],
                "rank": candidate["rank"],
                "score": candidate["score"],
                "chars": chars,
            }
        )
    return selected, dropped, context_chars


def _fingerprint(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        encoded = payload.encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise FixtureError("fixture 不能序列化为严格 UTF-8 指纹") from exc
    return hashlib.sha256(encoded).hexdigest()


def _trace_id(fixture: dict[str, Any], query: dict[str, Any]) -> str:
    """Create a stable teaching ID; production should generate an opaque random request ID."""

    seed = f"{fixture['pipeline']['pipeline_revision']}:{query['id']}"
    return f"trace-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _base_trace(fixture: dict[str, Any], query: dict[str, Any], failure: str) -> dict[str, Any]:
    pipeline = fixture["pipeline"]
    return {
        "visibility": "privileged_audit",
        "trace_id": _trace_id(fixture, query),
        "pipeline_revision": pipeline["pipeline_revision"],
        "retrieval_revision": pipeline["retrieval_revision"],
        "rerank_revision": pipeline["rerank_revision"],
        "context_policy_revision": pipeline["context_policy_revision"],
        "answer_policy_revision": pipeline["answer_policy_revision"],
        "query_id": query["id"],
        "route": query["route"],
        "topic": query["topic"],
        "authorization_revision": query["authorization_revision"],
        "as_of": query["as_of"],
        "failure": failure,
        "degraded": False,
        "filter_summary": {"visible": 0, "filtered": 0, "reasons": {}},
        "retrieved": [],
        "reranked": [],
        "selected": [],
        "dropped": [],
        "context_chars": 0,
        "fallback": None,
    }


def _citation(document: dict[str, Any], fact: dict[str, Any]) -> dict[str, str]:
    return {
        "document_id": document["id"],
        "fact_id": fact["fact_id"],
        "source_revision": document["source_revision"],
    }


def _claim(index: int, fact: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": f"C{index}",
        "text": fact["statement"],
        "citations": [{"document_id": document["id"], "fact_id": fact["fact_id"]}],
    }


def generate_extractively(
    query: dict[str, Any],
    selected: list[dict[str, Any]],
    document_by_id: dict[str, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[dict[str, str]]]:
    """Generate only exact fixture statements and surface active-source conflicts."""

    matching: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for selected_item in selected:
        document = document_by_id[selected_item["document_id"]]
        for fact in document["facts"]:
            if fact["topic"] == query["topic"]:
                matching.append((document, fact))
    if not matching:
        return "insufficient_evidence", [], []

    value_groups = {(fact["value"], fact["unit"]) for _, fact in matching}
    if len(value_groups) > 1:
        claims = [_claim(index, fact, document) for index, (document, fact) in enumerate(matching, 1)]
        citations = [_citation(document, fact) for document, fact in matching]
        return "conflict", claims, citations

    document, fact = matching[0]
    return "answered", [_claim(1, fact, document)], [_citation(document, fact)]


def _find_query(fixture: dict[str, Any], query_id: str) -> dict[str, Any]:
    for query in fixture["queries"]:
        if query["id"] == query_id:
            return query
    raise KeyError(f"未知 query id：{query_id}")


NON_EVIDENCE_ANSWERS = {
    "insufficient_evidence": "当前可访问且有效的资料不足以回答；请补充问题或转人工核验。",
    "tool_required": "这是实时状态问题，应调用经过鉴权的受控工具；离线知识快照不回答当前状态。",
    "dependency_unavailable": "检索依赖当前不可用；为避免脱离证据回答，本次请求已停止。",
    "generation_unavailable": "回答组件当前不可用；已保留内部审计轨迹，但不会用未验证文本代替答案。",
}


def render_answer(status: str, claims: list[dict[str, Any]]) -> str:
    """Render the public answer only from a validated status and claim set."""

    if status == "answered":
        if len(claims) != 1:
            raise ValueError("answered 必须恰好包含一个 claim")
        return str(claims[0]["text"])
    if status == "conflict":
        if len(claims) < 2:
            raise ValueError("conflict 必须包含至少两个 claim")
        statements = "；".join(str(claim["text"]) for claim in claims)
        return f"现有有效资料互相冲突，暂不选择其一：{statements}"
    if status in NON_EVIDENCE_ANSWERS:
        if claims:
            raise ValueError("非证据状态不得渲染 claims")
        return NON_EVIDENCE_ANSWERS[status]
    raise ValueError(f"未知 status：{status}")


def _response(
    trace_id: str,
    status: str,
    claims: list[dict[str, Any]],
    citations: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "status": status,
        "answer": render_answer(status, claims),
        "claims": claims,
        "citations": citations,
    }


def _fact_lookup(
    fixture: dict[str, Any],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        fact["fact_id"]: (document, fact)
        for document in fixture["documents"]
        for fact in document["facts"]
    }


def validate_public_response(fixture: dict[str, Any], response: Any) -> list[str]:
    """Validate the user-visible schema, grounded claims, citations, and answer coverage."""

    errors: list[str] = []
    if not _exact_fields(response, RESPONSE_FIELDS, "response", errors):
        return errors
    if not _nonempty_string(response["trace_id"]):
        errors.append("response.trace_id 必须是非空字符串")
    status_is_valid = (
        isinstance(response["status"], str) and response["status"] in VALID_STATUSES
    )
    if not status_is_valid:
        errors.append("response.status 非法")
    if not _nonempty_string(response["answer"]):
        errors.append("response.answer 必须是非空字符串")
    if not isinstance(response["claims"], list):
        errors.append("response.claims 必须是列表")
        return errors
    if not isinstance(response["citations"], list):
        errors.append("response.citations 必须是列表")
        return errors

    fact_lookup = _fact_lookup(fixture)
    top_citations: set[tuple[str, str]] = set()
    for citation in response["citations"]:
        if not isinstance(citation, dict) or set(citation) != {
            "document_id",
            "fact_id",
            "source_revision",
        }:
            errors.append("citation 字段不匹配")
            continue
        if not _nonempty_string(citation["document_id"]):
            errors.append("citation.document_id 必须是非空字符串")
            continue
        if not _nonempty_string(citation["fact_id"]):
            errors.append("citation.fact_id 必须是非空字符串")
            continue
        if not _nonempty_string(citation["source_revision"]):
            errors.append("citation.source_revision 必须是非空字符串")
            continue
        key = (citation["document_id"], citation["fact_id"])
        if key in top_citations:
            errors.append(f"citation 重复：{key}")
        top_citations.add(key)
        fact_entry = fact_lookup.get(citation["fact_id"])
        if fact_entry is None:
            errors.append(f"citation 引用了未知 fact：{citation['fact_id']}")
            continue
        document, _ = fact_entry
        if document["id"] != citation["document_id"]:
            errors.append(f"citation 的 document/fact 不匹配：{key}")
        if document["source_revision"] != citation["source_revision"]:
            errors.append(f"citation 的 source_revision 不匹配：{key}")

    claim_citations: set[tuple[str, str]] = set()
    claim_ids: set[str] = set()
    structurally_valid_claims = True
    for claim in response["claims"]:
        if not isinstance(claim, dict) or set(claim) != {"claim_id", "text", "citations"}:
            errors.append("claim 字段不匹配")
            structurally_valid_claims = False
            continue
        claim_id = claim["claim_id"]
        if not _nonempty_string(claim_id):
            errors.append("claim.claim_id 必须是非空字符串")
            structurally_valid_claims = False
        else:
            if claim_id in claim_ids:
                errors.append(f"claim id 重复：{claim_id}")
            claim_ids.add(claim_id)
        if not _nonempty_string(claim["text"]):
            errors.append("claim.text 必须是非空字符串")
            structurally_valid_claims = False
        if not isinstance(claim["citations"], list) or not claim["citations"]:
            errors.append(f"claim {claim_id!r} 必须有引用")
            structurally_valid_claims = False
            continue
        references_seen: set[tuple[str, str]] = set()
        for reference in claim["citations"]:
            if not isinstance(reference, dict) or set(reference) != {"document_id", "fact_id"}:
                errors.append("claim citation 字段不匹配")
                structurally_valid_claims = False
                continue
            if not _nonempty_string(reference["document_id"]):
                errors.append("claim citation.document_id 必须是非空字符串")
                structurally_valid_claims = False
                continue
            if not _nonempty_string(reference["fact_id"]):
                errors.append("claim citation.fact_id 必须是非空字符串")
                structurally_valid_claims = False
                continue
            key = (reference["document_id"], reference["fact_id"])
            if key in references_seen:
                errors.append(f"claim citation 重复：{claim_id!r} {key}")
                structurally_valid_claims = False
                continue
            references_seen.add(key)
            claim_citations.add(key)
            if key not in top_citations:
                errors.append(f"claim citation 不在顶层 citations：{key}")
            fact_entry = fact_lookup.get(reference["fact_id"])
            if fact_entry is None:
                errors.append(f"claim citation 引用了未知 fact：{reference['fact_id']}")
                continue
            document, fact = fact_entry
            if (
                document["id"] != reference["document_id"]
                or claim["text"] != fact["statement"]
            ):
                errors.append(
                    f"claim 的每条 citation 都必须逐字支持 claim：{claim_id!r} {key}"
                )
    if claim_citations != top_citations:
        errors.append("claims 与顶层 citations 的集合不一致")

    evidence_statuses = {"answered", "conflict"}
    if status_is_valid and response["status"] in evidence_statuses and not response["claims"]:
        errors.append("answered/conflict 必须包含有引用的 claims")
    if status_is_valid and response["status"] not in evidence_statuses and (
        response["claims"] or response["citations"]
    ):
        errors.append("非证据回答不得携带 claims/citations")
    if status_is_valid and structurally_valid_claims:
        try:
            expected_answer = render_answer(response["status"], response["claims"])
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if response["answer"] != expected_answer:
                errors.append("response.answer 未由已验证的 status/claims 确定性渲染")
    return errors


def _validated_stage_items(
    trace: dict[str, Any], errors: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Validate trace-stage scalar types before any hashing, ordering, or joins."""

    stage_shapes = {
        "retrieved": {"document_id", "rank", "score"},
        "reranked": {
            "document_id",
            "retrieval_rank",
            "retrieval_score",
            "score",
            "topic_match",
            "rank",
        },
        "selected": {"document_id", "rank", "score", "chars"},
        "dropped": {"document_id", "reason"},
    }
    stage_items: dict[str, list[dict[str, Any]]] = {}
    for stage, shape in stage_shapes.items():
        items = trace[stage]
        if not isinstance(items, list):
            errors.append(f"audit_trace.{stage} 必须是列表")
            stage_items[stage] = []
            continue
        valid_items: list[dict[str, Any]] = []
        ids: list[str] = []
        for index, item in enumerate(items):
            label = f"audit_trace.{stage}[{index}]"
            if not isinstance(item, dict) or set(item) != shape:
                errors.append(f"{label} 字段不匹配")
                continue
            item_is_valid = True
            if not _nonempty_string(item["document_id"]):
                errors.append(f"{label}.document_id 必须是非空字符串")
                item_is_valid = False
            else:
                ids.append(item["document_id"])
            if stage in {"retrieved", "reranked", "selected"}:
                if type(item["rank"]) is not int or item["rank"] <= 0:
                    errors.append(f"{label}.rank 必须是正整数")
                    item_is_valid = False
                if not _finite_number(item["score"]):
                    errors.append(f"{label}.score 必须是有限数值")
                    item_is_valid = False
            if stage == "retrieved" and _finite_number(item["score"]):
                if not 0.0 <= float(item["score"]) <= 1.0:
                    errors.append(f"{label}.score 必须位于 0..1")
                    item_is_valid = False
            if stage == "reranked":
                if type(item["retrieval_rank"]) is not int or item["retrieval_rank"] <= 0:
                    errors.append(f"{label}.retrieval_rank 必须是正整数")
                    item_is_valid = False
                if not _finite_number(item["retrieval_score"]):
                    errors.append(f"{label}.retrieval_score 必须是有限数值")
                    item_is_valid = False
                if type(item["topic_match"]) is not bool:
                    errors.append(f"{label}.topic_match 必须是布尔值")
                    item_is_valid = False
            if stage == "selected":
                if type(item["chars"]) is not int or item["chars"] <= 0:
                    errors.append(f"{label}.chars 必须是正整数")
                    item_is_valid = False
            if stage == "dropped":
                if not isinstance(item["reason"], str) or item["reason"] not in {
                    "canonical_duplicate",
                    "context_limit",
                    "character_budget",
                }:
                    errors.append(f"{label}.reason 非法")
                    item_is_valid = False
            if item_is_valid:
                valid_items.append(item)
        if len(ids) != len(set(ids)):
            errors.append(f"audit_trace.{stage} document_id 重复")
        if stage in {"retrieved", "reranked"} and len(valid_items) == len(items):
            ranks = [item["rank"] for item in valid_items]
            if ranks != list(range(1, len(valid_items) + 1)):
                errors.append(f"audit_trace.{stage}.rank 必须从 1 连续递增")
        stage_items[stage] = valid_items
    return stage_items


def validate_execution(
    fixture: dict[str, Any], query: dict[str, Any], execution: Any
) -> list[str]:
    """Validate runtime invariants without reading offline expected/oracle fields."""

    errors: list[str] = []
    if not _exact_fields(execution, EXECUTION_FIELDS, "execution", errors):
        return errors
    response = execution["response"]
    trace = execution["audit_trace"]
    errors.extend(validate_public_response(fixture, response))
    if not _exact_fields(trace, TRACE_FIELDS, "audit_trace", errors):
        return errors
    query_errors: list[str] = []
    if not _exact_fields(query, RUNTIME_QUERY_FIELDS, "runtime_query", query_errors):
        errors.extend(query_errors)
        return errors
    for field in (
        "id",
        "text",
        "tenant_id",
        "authorization_revision",
        "as_of",
        "route",
        "topic",
    ):
        if not _nonempty_string(query[field]):
            query_errors.append(f"runtime_query.{field} 必须是非空字符串")
    _sorted_unique_strings(
        query["subject_groups"], "runtime_query.subject_groups", query_errors
    )
    _parse_iso_date(query["as_of"], "runtime_query.as_of", query_errors)
    if not isinstance(query["route"], str) or query["route"] not in {
        "knowledge",
        "tool_required",
    }:
        query_errors.append("runtime_query.route 非法")
    if (
        isinstance(query["topic"], str)
        and TOPIC_PATTERN.fullmatch(query["topic"]) is None
    ):
        query_errors.append("runtime_query.topic 必须是稳定的 snake_case 标识")
    if query_errors:
        errors.extend(query_errors)
        return errors
    if trace["visibility"] != "privileged_audit":
        errors.append("audit_trace.visibility 必须为 privileged_audit")
    if isinstance(response, dict) and trace["trace_id"] != response.get("trace_id"):
        errors.append("公开 trace_id 与内部 audit trace 不一致")
    expected_trace_id = _trace_id(fixture, query)
    if trace["trace_id"] != expected_trace_id:
        errors.append("audit_trace.trace_id 未绑定 pipeline/query")
    pipeline = fixture["pipeline"]
    for field in (
        "pipeline_revision",
        "retrieval_revision",
        "rerank_revision",
        "context_policy_revision",
        "answer_policy_revision",
    ):
        if trace[field] != pipeline[field]:
            errors.append(f"audit_trace.{field} 与 fixture.pipeline 不一致")
    for field in ("id", "route", "topic", "authorization_revision", "as_of"):
        trace_field = "query_id" if field == "id" else field
        if trace[trace_field] != query[field]:
            errors.append(f"audit_trace.{trace_field} 与可信执行上下文不一致")
    failure_is_valid = (
        isinstance(trace["failure"], str) and trace["failure"] in VALID_FAILURES
    )
    if not failure_is_valid:
        errors.append("audit_trace.failure 非法")
    if type(trace["degraded"]) is not bool:
        errors.append("audit_trace.degraded 必须是布尔值")
    if type(trace["context_chars"]) is not int or trace["context_chars"] < 0:
        errors.append("audit_trace.context_chars 必须是非负整数")
    if trace["fallback"] is not None and not _nonempty_string(trace["fallback"]):
        errors.append("audit_trace.fallback 必须是 null 或非空字符串")
    expected_degraded = False
    expected_fallback: str | None = None
    expected_failure_status: str | None = None
    if query["route"] == "tool_required":
        expected_failure_status = "tool_required"
    elif failure_is_valid:
        failure_behavior = {
            "none": (False, None, None),
            "retrieval_error": (
                True,
                "retrieval_error:refuse",
                "dependency_unavailable",
            ),
            "reranker_error": (
                True,
                "reranker_error:retrieval_order",
                None,
            ),
            "generation_error": (
                True,
                "generation_error:refuse",
                "generation_unavailable",
            ),
        }
        expected_degraded, expected_fallback, expected_failure_status = (
            failure_behavior[trace["failure"]]
        )
    if trace["degraded"] != expected_degraded:
        errors.append("audit_trace.degraded 未绑定 route/failure 行为")
    if trace["fallback"] != expected_fallback:
        errors.append("audit_trace.fallback 未绑定 route/failure 行为")
    if (
        expected_failure_status is not None
        and isinstance(response, dict)
        and response.get("status") != expected_failure_status
    ):
        errors.append("response.status 未绑定 route/failure 行为")
    filter_summary = trace["filter_summary"]
    filter_shape_is_valid = isinstance(filter_summary, dict) and set(filter_summary) == {
        "visible",
        "filtered",
        "reasons",
    }
    if not filter_shape_is_valid:
        errors.append("audit_trace.filter_summary 字段不匹配")
    elif (
        type(filter_summary["visible"]) is not int
        or filter_summary["visible"] < 0
        or type(filter_summary["filtered"]) is not int
        or filter_summary["filtered"] < 0
        or not isinstance(filter_summary["reasons"], dict)
        or any(
            not _nonempty_string(reason)
            or type(count) is not int
            or count <= 0
            for reason, count in filter_summary["reasons"].items()
        )
    ):
        errors.append("audit_trace.filter_summary 值类型非法")

    stage_items = _validated_stage_items(trace, errors)
    stage_ids = {
        stage: [item["document_id"] for item in items]
        for stage, items in stage_items.items()
    }
    visible, recomputed_filter_summary, _ = filter_documents(fixture["documents"], query)
    visible_ids = {document["id"] for document in visible}
    for stage, ids in stage_ids.items():
        if any(document_id not in visible_ids for document_id in ids):
            errors.append(f"audit_trace.{stage} 含未授权、过期或未发布 document")

    expected_filter_summary = (
        recomputed_filter_summary
        if query["route"] == "knowledge"
        else {"visible": 0, "filtered": 0, "reasons": {}}
    )
    if filter_summary != expected_filter_summary:
        errors.append("audit_trace.filter_summary 未由可信语料重新计算")

    retrieved_items = stage_items["retrieved"]
    reranked_items = stage_items["reranked"]
    selected_items = stage_items["selected"]
    dropped_items = stage_items["dropped"]
    retrieved_by_id = {item["document_id"]: item for item in retrieved_items}
    reranked_by_id = {item["document_id"]: item for item in reranked_items}

    if set(stage_ids["reranked"]) != set(stage_ids["retrieved"]):
        errors.append("audit_trace.reranked 必须与 retrieved 保持相同 document 集合")
    for item in reranked_items:
        source = retrieved_by_id.get(item["document_id"])
        if source is not None and (
            item["retrieval_rank"] != source["rank"]
            or item["retrieval_score"] != source["score"]
        ):
            errors.append("audit_trace.reranked 的 retrieval rank/score 未绑定 retrieved")
    selected_ids = set(stage_ids["selected"])
    dropped_ids = set(stage_ids["dropped"])
    reranked_ids = set(stage_ids["reranked"])
    if selected_ids & dropped_ids:
        errors.append("audit_trace.selected 与 dropped 不得包含同一 document")
    if selected_ids | dropped_ids != reranked_ids:
        errors.append("audit_trace.selected+dropped 必须完整来源于 reranked")
    for item in selected_items:
        source = reranked_by_id.get(item["document_id"])
        if source is not None and (
            item["rank"] != source["rank"] or item["score"] != source["score"]
        ):
            errors.append("audit_trace.selected 的 rank/score 未绑定 reranked")

    visible_by_id = {document["id"]: document for document in visible}
    recomputed_context_chars = 0
    for item in selected_items:
        document = visible_by_id.get(item["document_id"])
        if document is None:
            continue
        expected_chars = len(document["title"]) + len(document["text"])
        recomputed_context_chars += expected_chars
        if item["chars"] != expected_chars:
            errors.append(
                f"audit_trace.selected chars 未由 document 重新计算：{item['document_id']}"
            )
    if trace["context_chars"] != recomputed_context_chars:
        errors.append("audit_trace.context_chars 未由 selected chars 重新计算")

    if failure_is_valid:
        expected_retrieved: list[dict[str, Any]] = []
        expected_reranked: list[dict[str, Any]] = []
        expected_selected: list[dict[str, Any]] = []
        expected_dropped: list[dict[str, Any]] = []
        expected_context_chars = 0
        if query["route"] == "knowledge" and trace["failure"] != "retrieval_error":
            expected_retrieved = retrieve(
                query, visible, pipeline["retrieval_limit"]
            )
            expected_reranked = rerank(
                query,
                expected_retrieved,
                visible_by_id,
                trace["failure"] == "reranker_error",
            )
            expected_selected, expected_dropped, expected_context_chars = select_context(
                expected_reranked,
                visible_by_id,
                pipeline["context_limit"],
                pipeline["max_context_chars"],
            )
        for stage, expected in (
            ("retrieved", expected_retrieved),
            ("reranked", expected_reranked),
            ("selected", expected_selected),
            ("dropped", expected_dropped),
        ):
            if trace[stage] != expected:
                errors.append(f"audit_trace.{stage} 未绑定确定性阶段转换")
        if trace["context_chars"] != expected_context_chars:
            errors.append("audit_trace.context_chars 未绑定上下文选择结果")
        if query["route"] == "tool_required":
            expected_response = _response(
                expected_trace_id,
                "tool_required",
                [],
                [],
            )
        elif trace["failure"] == "retrieval_error":
            expected_response = _response(
                expected_trace_id,
                "dependency_unavailable",
                [],
                [],
            )
        elif trace["failure"] == "generation_error":
            expected_response = _response(
                expected_trace_id,
                "generation_unavailable",
                [],
                [],
            )
        else:
            expected_status, expected_claims, expected_citations = (
                generate_extractively(
                    query,
                    expected_selected,
                    visible_by_id,
                )
            )
            expected_response = _response(
                expected_trace_id,
                expected_status,
                expected_claims,
                expected_citations,
            )
        if response != expected_response:
            errors.append("response 未绑定确定性 runtime 结果")

    if isinstance(response, dict) and isinstance(response.get("citations"), list):
        for citation in response["citations"]:
            document_id = citation.get("document_id") if isinstance(citation, dict) else None
            if isinstance(document_id, str) and document_id not in selected_ids:
                errors.append("citation 未来自 selected context")
    return errors


def oracle_failure_codes(query: dict[str, Any], response: dict[str, Any]) -> list[str]:
    """Return non-sensitive offline grader codes; never expose secret canary values."""

    codes: list[str] = []
    if response.get("status") != query["expected_status"]:
        codes.append("status_mismatch")
    citation_values = response.get("citations", [])
    if not isinstance(citation_values, list):
        citation_values = []
    actual_fact_ids = sorted(
        citation.get("fact_id")
        for citation in citation_values
        if isinstance(citation, dict) and isinstance(citation.get("fact_id"), str)
    )
    if actual_fact_ids != query["expected_fact_ids"]:
        codes.append("fact_set_mismatch")
    serialized = json.dumps(response, ensure_ascii=False, sort_keys=True)
    forbidden_document_ids = query.get("forbidden_document_ids", [])
    if not isinstance(forbidden_document_ids, list):
        forbidden_document_ids = []
    if any(
        item in serialized
        for item in forbidden_document_ids
        if isinstance(item, str)
    ):
        codes.append("forbidden_document_disclosure")
    forbidden_output_substrings = query.get("forbidden_output_substrings", [])
    if not isinstance(forbidden_output_substrings, list):
        forbidden_output_substrings = []
    if any(
        item in serialized
        for item in forbidden_output_substrings
        if isinstance(item, str)
    ):
        codes.append("forbidden_content_disclosure")
    return codes


def validate_oracle(query: dict[str, Any], response: dict[str, Any]) -> list[str]:
    messages = {
        "status_mismatch": "公开响应状态不符合离线 oracle",
        "fact_set_mismatch": "公开响应引用事实不符合离线 oracle",
        "forbidden_document_disclosure": "公开响应泄露了禁止 document id",
        "forbidden_content_disclosure": "公开响应泄露了禁止输出内容 canary",
    }
    return [messages[code] for code in oracle_failure_codes(query, response)]


def validate_result(
    fixture: dict[str, Any],
    query: dict[str, Any],
    response: Any,
    audit_trace: Any,
) -> list[str]:
    """Convenience validator combining runtime invariants and offline oracle checks."""

    query_errors: list[str] = []
    if not _exact_fields(query, QUERY_FIELDS, "query", query_errors):
        query_errors.extend(validate_public_response(fixture, response))
        return query_errors
    execution = {"response": response, "audit_trace": audit_trace}
    errors = validate_execution(fixture, _runtime_query(query), execution)
    if isinstance(response, dict):
        errors.extend(validate_oracle(query, response))
    return errors


def execute_pipeline(
    fixture: dict[str, Any], query_id: str, failure: str = "none"
) -> dict[str, Any]:
    """Run one case and return a protected execution envelope for operators/evaluators."""

    if failure not in VALID_FAILURES:  # 只接受测试明确建模的三种依赖故障与正常状态。
        raise ValueError(f"未知 failure：{failure}")  # 不把拼写错误当作可解释的降级行为。
    query_case = _find_query(fixture, query_id)  # 从含 oracle 的 fixture 找到完整测试用例。
    query = _runtime_query(query_case)  # 只提取运行时允许使用的字段，隔离 expected/forbidden oracle。
    trace = _base_trace(fixture, query, failure)  # 创建受保护阶段记录，公共响应不会直接暴露它。
    if query["route"] == "tool_required":  # 实时/动作类问题不能误走知识快照。
        response = _response(trace["trace_id"], "tool_required", [], [])  # 不检索、不生成事实 claim，直接返回受控状态。
    else:  # 只有知识 route 才进入检索到引用的管线。
        visible, filter_summary, _ = filter_documents(fixture["documents"], query)  # 在任何评分前完成 tenant、时间、状态和 ACL 过滤。
        trace["filter_summary"] = filter_summary  # 过滤统计仅保存在 protected audit trace。
        if failure == "retrieval_error":  # 检索不可用时不能用参数记忆编造内部答案。
            trace["degraded"] = True  # 明确标记本次执行没有走完整主路径。
            trace["fallback"] = "retrieval_error:refuse"  # 记录拒答而不是宽松检索的降级策略。
            response = _response(trace["trace_id"], "dependency_unavailable", [], [])  # 公共层返回依赖不可用且无 claim。
        else:  # 检索服务可用时才继续构建安全候选链。
            pipeline = fixture["pipeline"]  # 读取已验证的 retrieval/context 上限与版本配置。
            document_by_id = {document["id"]: document for document in visible}  # 映射只包含已授权文档，供后续 ID 查找。
            retrieved = retrieve(query, visible, pipeline["retrieval_limit"])  # 在安全集合内执行第一阶段词法召回。
            trace["retrieved"] = retrieved  # 记录召回结果，帮助定位 recall 与后续阶段的差异。
            use_rerank_fallback = failure == "reranker_error"  # 用故障注入决定是否跳过规则重排。
            reranked = rerank(query, retrieved, document_by_id, use_rerank_fallback)  # 正常时重排，故障时保留同一安全 retrieval 顺序。
            trace["reranked"] = reranked  # 无论是否降级都记录实际使用的排序。
            if use_rerank_fallback:  # 重排服务不可用不应扩大候选集合或放宽 ACL。
                trace["degraded"] = True  # 让评测与监控能统计降级比例。
                trace["fallback"] = "reranker_error:retrieval_order"  # 明确使用的是安全第一阶段顺序。
            selected, dropped, context_chars = select_context(  # 在固定预算内从排序候选选择真正可引用证据。
                reranked,  # 使用刚刚记录的实际排序，而不是另一条隐式列表。
                document_by_id,  # 只能从可见文档映射读取正文和 canonical ID。
                pipeline["context_limit"],  # 限制最多选择多少条证据。
                pipeline["max_context_chars"],  # 限制送入生成器的总字符预算。
            )
            trace["selected"] = selected  # 保存进入上下文的证据身份与分数。
            trace["dropped"] = dropped  # 保存去重或预算导致的舍弃原因。
            trace["context_chars"] = context_chars  # 保存实际消耗预算，便于成本排查。
            if failure == "generation_error":  # 已选到证据但生成阶段不可用时。
                trace["degraded"] = True  # 仍标记本次为降级而非正常 answered。
                trace["fallback"] = "generation_error:refuse"  # 本例选择拒绝输出未验证草稿。
                response = _response(trace["trace_id"], "generation_unavailable", [], [])  # 公共结果不含未经校验的 claim。
            else:  # 所有依赖可用时，使用确定性抽取式生成避免脱离证据。
                status, claims, citations = generate_extractively(  # 从 selected evidence 生成状态、claim 和 citation。
                    query, selected, document_by_id  # 生成器看不到未授权或未选中的文档。
                )
                response = _response(trace["trace_id"], status, claims, citations)  # 用验证器期望的公共结构包装结果。

    execution = {"response": response, "audit_trace": trace}  # 将公共响应与受保护 trace 成对交给内部验证器。
    errors = validate_execution(fixture, query, execution)  # 在边界发布前重算阶段和引用不变量。
    if errors:  # 教学实现绝不将内部不一致结果返回给调用方。
        raise RuntimeError("内部执行契约校验失败：\n- " + "\n- ".join(errors))  # 将所有契约错误合并为可诊断异常。
    return execution  # 只有通过验证的双投影执行结果才能供 public/audit 调用方使用。


def run_pipeline(
    fixture: dict[str, Any], query_id: str, failure: str = "none"
) -> dict[str, Any]:
    """Return only the public response; protected diagnostics stay out of this boundary."""

    return execute_pipeline(fixture, query_id, failure=failure)["response"]


def _recall(expected: set[str], actual: set[str]) -> float | None:
    if not expected:
        return None
    return round(len(expected & actual) / len(expected), 6)


def evaluate_fixture(
    fixture: dict[str, Any], failure: str = "none"
) -> dict[str, Any]:
    """Produce a deterministic, layered RAG evaluation artifact without leaking canaries."""

    if failure not in VALID_FAILURES:
        raise ValueError(f"未知 failure：{failure}")
    fact_lookup = _fact_lookup(fixture)
    cases: list[dict[str, Any]] = []
    total_expected = 0
    retrieved_hits = 0
    context_hits = 0
    citation_hits = 0
    status_hits = 0
    disclosure_violations = 0

    for query_case in fixture["queries"]:
        execution = execute_pipeline(fixture, query_case["id"], failure=failure)
        response = execution["response"]
        trace = execution["audit_trace"]
        codes = oracle_failure_codes(query_case, response)
        expected_facts = set(query_case["expected_fact_ids"])
        retrieved = {item["document_id"] for item in trace["retrieved"]}
        selected = {item["document_id"] for item in trace["selected"]}
        cited_facts = {item["fact_id"] for item in response["citations"]}
        retrieved_facts = {
            fact_id
            for fact_id in expected_facts
            if fact_lookup[fact_id][0]["id"] in retrieved
        }
        context_facts = {
            fact_id
            for fact_id in expected_facts
            if fact_lookup[fact_id][0]["id"] in selected
        }
        total_expected += len(expected_facts)
        retrieved_hits += len(retrieved_facts)
        context_hits += len(context_facts)
        citation_hits += len(expected_facts & cited_facts)
        status_match = response["status"] == query_case["expected_status"]
        status_hits += int(status_match)
        case_disclosures = sum(code.startswith("forbidden_") for code in codes)
        disclosure_violations += case_disclosures
        cases.append(
            {
                "query_id": query_case["id"],
                "slice": query_case["slice"],
                "critical": query_case["critical"],
                "status_match": status_match,
                "retrieval_fact_recall": _recall(expected_facts, retrieved_facts),
                "context_fact_recall": _recall(expected_facts, context_facts),
                "citation_fact_recall": _recall(expected_facts, cited_facts),
                "non_disclosure_pass": case_disclosures == 0,
                "failure_codes": codes,
                "passed": not codes,
            }
        )

    query_count = len(cases)
    critical_cases = [case for case in cases if case["critical"]]
    metrics = {
        "case_pass_rate": round(
            sum(case["passed"] for case in cases) / query_count, 6
        ),
        "critical_case_pass_rate": round(
            sum(case["passed"] for case in critical_cases) / len(critical_cases), 6
        ),
        "status_accuracy": round(status_hits / query_count, 6),
        "retrieval_fact_recall": round(retrieved_hits / total_expected, 6),
        "context_fact_recall": round(context_hits / total_expected, 6),
        "citation_fact_recall": round(citation_hits / total_expected, 6),
        "non_disclosure_violation_count": disclosure_violations,
    }
    policy = fixture["evaluation_policy"]
    checks = (
        (metrics["case_pass_rate"] < policy["min_case_pass_rate"], "case_pass_rate"),
        (
            metrics["critical_case_pass_rate"]
            < policy["min_critical_case_pass_rate"],
            "critical_case_pass_rate",
        ),
        (metrics["status_accuracy"] < policy["min_status_accuracy"], "status_accuracy"),
        (
            metrics["retrieval_fact_recall"] < policy["min_retrieval_fact_recall"],
            "retrieval_fact_recall",
        ),
        (
            metrics["context_fact_recall"] < policy["min_context_fact_recall"],
            "context_fact_recall",
        ),
        (
            metrics["citation_fact_recall"] < policy["min_citation_fact_recall"],
            "citation_fact_recall",
        ),
        (
            metrics["non_disclosure_violation_count"]
            > policy["max_non_disclosure_violations"],
            "non_disclosure_violation_count",
        ),
    )
    reasons = [f"gate_failed:{name}" for failed, name in checks if failed]
    fixture_fingerprint = _fingerprint(fixture)
    evidence = {
        "fixture_fingerprint": fixture_fingerprint,
        "failure": failure,
        "metrics": metrics,
        "cases": cases,
        "evaluation_policy": policy,
    }
    pipeline = {
        key: fixture["pipeline"][key]
        for key in (
            "pipeline_revision",
            "retrieval_revision",
            "rerank_revision",
            "context_policy_revision",
            "answer_policy_revision",
        )
    }
    return {
        "schema_version": "rag-evaluation-report-v1",
        "suite_revision": policy["suite_revision"],
        "harness_revision": policy["harness_revision"],
        "fixture_fingerprint": fixture_fingerprint,
        "evidence_fingerprint": _fingerprint(evidence),
        "pipeline": pipeline,
        "failure": failure,
        "query_count": query_count,
        "critical_query_count": len(critical_cases),
        "metrics": metrics,
        "action": "PASS" if not reasons else "BLOCK",
        "reasons": reasons,
        "cases": cases,
    }


def _add_failure_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--failure",
        choices=sorted(VALID_FAILURES),
        default="none",
        help="模拟依赖故障；正常教学运行使用 none",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).with_name("rag-fixture.json"),
        help="严格 JSON 教学数据",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo_parser = subparsers.add_parser("demo", help="运行 fixture 中全部 query")
    _add_failure_argument(demo_parser)
    ask_parser = subparsers.add_parser("ask", help="按稳定 query id 运行一个案例")
    ask_parser.add_argument("--query-id", required=True)
    _add_failure_argument(ask_parser)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="输出受保护的内部审计轨迹；教学 flag 不是实际授权机制",
    )
    inspect_parser.add_argument("--query-id", required=True)
    inspect_parser.add_argument(
        "--operator-view",
        action="store_true",
        help="明确确认当前输出含内部候选、过滤统计和授权版本",
    )
    _add_failure_argument(inspect_parser)
    evaluate_parser = subparsers.add_parser(
        "evaluate", help="生成不含私有 canary 的分层离线评测报告"
    )
    _add_failure_argument(evaluate_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        exit_code = 0
        if args.command == "demo":
            results = [
                {
                    "query_id": query["id"],
                    "response": run_pipeline(
                        fixture, query["id"], failure=args.failure
                    ),
                }
                for query in fixture["queries"]
            ]
            payload: dict[str, Any] = {
                "mode": "demo",
                "results": results,
            }
        elif args.command == "ask":
            payload = {
                "mode": "ask",
                "result": run_pipeline(fixture, args.query_id, failure=args.failure),
            }
        elif args.command == "inspect":
            if not args.operator_view:
                raise FixtureError(
                    "inspect 需要 --operator-view；该 flag 仅作教学确认，不替代真实鉴权"
                )
            payload = {
                "mode": "privileged_inspect",
                "execution": execute_pipeline(
                    fixture, args.query_id, failure=args.failure
                ),
            }
        else:
            report = evaluate_fixture(fixture, failure=args.failure)
            payload = {
                "mode": "evaluate",
                "report": report,
            }
            exit_code = 0 if report["action"] == "PASS" else 1
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return exit_code
    except (FixtureError, KeyError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
