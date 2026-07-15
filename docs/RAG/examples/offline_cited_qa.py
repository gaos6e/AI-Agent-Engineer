"""Strict offline RAG teaching pipeline with safe filters and extractive citations.

This module deliberately uses no embedding model, vector index, LLM, network, or key.
Its purpose is to make orchestration contracts observable and testable before real
components are connected.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


ROOT_FIELDS = {"schema_version", "pipeline", "documents", "queries"}
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
    "as_of",
    "route",
    "topic",
    "expected_status",
    "expected_fact_ids",
    "forbidden_document_ids",
}
RESULT_FIELDS = {"status", "answer", "claims", "citations", "trace"}
TRACE_FIELDS = {
    "pipeline_revision",
    "retrieval_revision",
    "rerank_revision",
    "context_policy_revision",
    "answer_policy_revision",
    "query_id",
    "route",
    "topic",
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


class FixtureError(ValueError):
    """Raised when the teaching fixture violates its explicit contract."""


def _reject_constant(value: str) -> None:
    raise FixtureError(f"JSON 不允许非有限常量：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


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
    return isinstance(value, str) and bool(value.strip())


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
    strings = list(value)
    if strings != sorted(set(strings)):
        errors.append(f"{label} 必须已排序且无重复")
    return strings


def validate_fixture(fixture: Any) -> list[str]:
    """Return every detectable fixture-contract violation without using assert."""

    errors: list[str] = []
    if not _exact_fields(fixture, ROOT_FIELDS, "root", errors):
        return errors
    if fixture["schema_version"] != "1.0":
        errors.append("schema_version 必须为 '1.0'")

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
        for field in ("retrieval_limit", "context_limit", "max_context_chars"):
            if type(pipeline[field]) is not int or pipeline[field] <= 0:
                errors.append(f"pipeline.{field} 必须是正整数")

    documents = fixture["documents"]
    if not isinstance(documents, list) or not documents:
        errors.append("documents 必须是非空列表")
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
        if document["status"] not in {"published", "draft", "archived"}:
            errors.append(f"{label}.status 非法")
        start = _parse_iso_date(document["effective_from"], f"{label}.effective_from", errors)
        end_value = document["effective_to"]
        end = None
        if end_value is not None:
            end = _parse_iso_date(end_value, f"{label}.effective_to", errors)
        if start is not None and end is not None and end < start:
            errors.append(f"{label} 的 effective_to 早于 effective_from")
        if type(document["authority"]) is not int or not 0 <= document["authority"] <= 100:
            errors.append(f"{label}.authority 必须是 0..100 的整数")

        facts = document["facts"]
        if not isinstance(facts, list) or not facts:
            errors.append(f"{label}.facts 必须是非空列表")
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
    if not isinstance(queries, list) or not queries:
        errors.append("queries 必须是非空列表")
        queries = []
    query_ids: set[str] = set()
    for index, query in enumerate(queries):
        label = f"queries[{index}]"
        if not _exact_fields(query, QUERY_FIELDS, label, errors):
            continue
        for field in ("id", "text", "tenant_id", "topic"):
            if not _nonempty_string(query[field]):
                errors.append(f"{label}.{field} 必须是非空字符串")
        query_id = query["id"]
        if isinstance(query_id, str):
            if query_id in query_ids:
                errors.append(f"query id 重复：{query_id}")
            query_ids.add(query_id)
        _sorted_unique_strings(query["subject_groups"], f"{label}.subject_groups", errors)
        _parse_iso_date(query["as_of"], f"{label}.as_of", errors)
        if query["route"] not in {"knowledge", "tool_required"}:
            errors.append(f"{label}.route 非法")
        topic = query["topic"]
        if isinstance(topic, str) and TOPIC_PATTERN.fullmatch(topic) is None:
            errors.append(f"{label}.topic 必须是稳定的 snake_case 标识")
        if query["expected_status"] not in VALID_STATUSES:
            errors.append(f"{label}.expected_status 非法")
        expected_fact_ids = _sorted_unique_strings(
            query["expected_fact_ids"], f"{label}.expected_fact_ids", errors
        )
        forbidden_ids = _sorted_unique_strings(
            query["forbidden_document_ids"], f"{label}.forbidden_document_ids", errors
        )
        if expected_fact_ids is not None:
            unknown_facts = sorted(set(expected_fact_ids) - fact_ids)
            if unknown_facts:
                errors.append(f"{label} 引用了未知 fact：{unknown_facts}")
        if forbidden_ids is not None:
            unknown_documents = sorted(set(forbidden_ids) - document_ids)
            if unknown_documents:
                errors.append(f"{label} 引用了未知 forbidden document：{unknown_documents}")
        if query["route"] == "tool_required" and query["expected_status"] != "tool_required":
            errors.append(f"{label} 的 tool_required 路由必须期望 tool_required 状态")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    """Load strict JSON and reject duplicate keys, NaN, Infinity, and bad schemas."""

    try:
        raw = path.read_text(encoding="utf-8")
        fixture = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"无法读取 fixture：{exc}") from exc
    errors = validate_fixture(fixture)
    if errors:
        raise FixtureError("fixture 校验失败：\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root 必须是对象")
    return fixture


def text_features(text: str) -> set[str]:
    """Create transparent ASCII tokens plus CJK unigrams/bigrams for the toy retriever."""

    lowered = text.lower()
    features = {f"a:{token}" for token in ASCII_TOKEN_PATTERN.findall(lowered)}
    for run in CJK_RUN_PATTERN.findall(lowered):
        features.update(f"c1:{character}" for character in run)
        features.update(f"c2:{run[index:index + 2]}" for index in range(len(run) - 1))
    return features


def filter_documents(
    documents: list[dict[str, Any]], query: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, list[str]]]:
    """Apply tenant, lifecycle, time, and ACL constraints before any scoring."""

    as_of = date.fromisoformat(query["as_of"])
    groups = set(query["subject_groups"])
    visible: list[dict[str, Any]] = []
    decisions: dict[str, list[str]] = {}
    reason_counts: dict[str, int] = {}
    for document in documents:
        reasons: list[str] = []
        if document["tenant_id"] != query["tenant_id"]:
            reasons.append("tenant_mismatch")
        if document["status"] != "published":
            reasons.append("not_published")
        effective_from = date.fromisoformat(document["effective_from"])
        effective_to = (
            date.fromisoformat(document["effective_to"])
            if document["effective_to"] is not None
            else None
        )
        if as_of < effective_from or (effective_to is not None and as_of > effective_to):
            reasons.append("outside_effective_window")
        acl = set(document["acl"])
        if "public" not in acl and not (acl & groups):
            reasons.append("acl_denied")
        decisions[document["id"]] = reasons
        if reasons:
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        else:
            visible.append(document)
    summary = {
        "visible": len(visible),
        "filtered": len(documents) - len(visible),
        "reasons": dict(sorted(reason_counts.items())),
    }
    return visible, summary, decisions


def retrieve(
    query: dict[str, Any], documents: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Return positive lexical candidates; scores are comparable only within this query."""

    query_features = text_features(query["text"])
    candidates: list[dict[str, Any]] = []
    for document in documents:
        document_features = text_features(f"{document['title']} {document['text']}")
        overlap = len(query_features & document_features)
        denominator = math.sqrt(max(1, len(query_features)) * max(1, len(document_features)))
        score = overlap / denominator
        if score > 0.0:
            candidates.append({"document_id": document["id"], "score": round(score, 6)})
    candidates.sort(key=lambda item: (-item["score"], item["document_id"]))
    limited = candidates[:limit]
    return [
        {"document_id": item["document_id"], "rank": index, "score": item["score"]}
        for index, item in enumerate(limited, start=1)
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


def _base_trace(fixture: dict[str, Any], query: dict[str, Any], failure: str) -> dict[str, Any]:
    pipeline = fixture["pipeline"]
    return {
        "pipeline_revision": pipeline["pipeline_revision"],
        "retrieval_revision": pipeline["retrieval_revision"],
        "rerank_revision": pipeline["rerank_revision"],
        "context_policy_revision": pipeline["context_policy_revision"],
        "answer_policy_revision": pipeline["answer_policy_revision"],
        "query_id": query["id"],
        "route": query["route"],
        "topic": query["topic"],
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
) -> tuple[str, str, list[dict[str, Any]], list[dict[str, str]]]:
    """Generate only exact fixture statements and surface active-source conflicts."""

    matching: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for selected_item in selected:
        document = document_by_id[selected_item["document_id"]]
        for fact in document["facts"]:
            if fact["topic"] == query["topic"]:
                matching.append((document, fact))
    if not matching:
        return (
            "insufficient_evidence",
            "当前可访问且有效的资料不足以回答；请补充问题或转人工核验。",
            [],
            [],
        )

    value_groups = {(fact["value"], fact["unit"]) for _, fact in matching}
    if len(value_groups) > 1:
        claims = [_claim(index, fact, document) for index, (document, fact) in enumerate(matching, 1)]
        citations = [_citation(document, fact) for document, fact in matching]
        statements = "；".join(fact["statement"] for _, fact in matching)
        return (
            "conflict",
            f"现有有效资料互相冲突，暂不选择其一：{statements}",
            claims,
            citations,
        )

    document, fact = matching[0]
    return "answered", fact["statement"], [_claim(1, fact, document)], [_citation(document, fact)]


def _find_query(fixture: dict[str, Any], query_id: str) -> dict[str, Any]:
    for query in fixture["queries"]:
        if query["id"] == query_id:
            return query
    raise KeyError(f"未知 query id：{query_id}")


def _result(
    status: str,
    answer: str,
    claims: list[dict[str, Any]],
    citations: list[dict[str, str]],
    trace: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "answer": answer,
        "claims": claims,
        "citations": citations,
        "trace": trace,
    }


def validate_result(
    fixture: dict[str, Any], query: dict[str, Any], result: Any
) -> list[str]:
    """Validate grounding, citation provenance, status policy, and non-disclosure."""

    errors: list[str] = []
    if not _exact_fields(result, RESULT_FIELDS, "result", errors):
        return errors
    if result["status"] not in VALID_STATUSES:
        errors.append("result.status 非法")
    if not _nonempty_string(result["answer"]):
        errors.append("result.answer 必须是非空字符串")
    if not isinstance(result["claims"], list):
        errors.append("result.claims 必须是列表")
        return errors
    if not isinstance(result["citations"], list):
        errors.append("result.citations 必须是列表")
        return errors
    trace = result["trace"]
    if not _exact_fields(trace, TRACE_FIELDS, "trace", errors):
        return errors
    if trace["query_id"] != query["id"] or trace["route"] != query["route"]:
        errors.append("trace 的 query/route 与输入不一致")
    if trace["failure"] not in VALID_FAILURES:
        errors.append("trace.failure 非法")
    if type(trace["degraded"]) is not bool:
        errors.append("trace.degraded 必须是布尔值")

    document_by_id = {document["id"]: document for document in fixture["documents"]}
    fact_lookup: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for document in fixture["documents"]:
        for fact in document["facts"]:
            fact_lookup[fact["fact_id"]] = (document, fact)

    selected_ids: list[str] = []
    if isinstance(trace["selected"], list):
        for item in trace["selected"]:
            if not isinstance(item, dict) or set(item) != {"document_id", "rank", "score", "chars"}:
                errors.append("trace.selected 元素字段不匹配")
                continue
            selected_ids.append(item["document_id"])
    else:
        errors.append("trace.selected 必须是列表")
    if len(selected_ids) != len(set(selected_ids)):
        errors.append("trace.selected 含重复 document id")
    if any(document_id not in document_by_id for document_id in selected_ids):
        errors.append("trace.selected 含未知 document id")

    top_citations: set[tuple[str, str]] = set()
    for citation in result["citations"]:
        if not isinstance(citation, dict) or set(citation) != {
            "document_id",
            "fact_id",
            "source_revision",
        }:
            errors.append("citation 字段不匹配")
            continue
        key = (citation["document_id"], citation["fact_id"])
        if key in top_citations:
            errors.append(f"citation 重复：{key}")
        top_citations.add(key)
        if citation["document_id"] not in selected_ids:
            errors.append(f"citation 未来自 selected context：{key}")
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
    for claim in result["claims"]:
        if not isinstance(claim, dict) or set(claim) != {"claim_id", "text", "citations"}:
            errors.append("claim 字段不匹配")
            continue
        if claim["claim_id"] in claim_ids:
            errors.append(f"claim id 重复：{claim['claim_id']}")
        claim_ids.add(claim["claim_id"])
        if not _nonempty_string(claim["text"]):
            errors.append("claim.text 必须是非空字符串")
        if not isinstance(claim["citations"], list) or not claim["citations"]:
            errors.append(f"claim {claim['claim_id']} 必须有引用")
            continue
        supported = False
        for reference in claim["citations"]:
            if not isinstance(reference, dict) or set(reference) != {"document_id", "fact_id"}:
                errors.append("claim citation 字段不匹配")
                continue
            key = (reference["document_id"], reference["fact_id"])
            claim_citations.add(key)
            if key not in top_citations:
                errors.append(f"claim citation 不在顶层 citations：{key}")
            fact_entry = fact_lookup.get(reference["fact_id"])
            if fact_entry is not None:
                document, fact = fact_entry
                if document["id"] == reference["document_id"] and claim["text"] == fact["statement"]:
                    supported = True
        if not supported:
            errors.append(f"claim 没有逐字支持证据：{claim['claim_id']}")
    if claim_citations != top_citations:
        errors.append("claims 与顶层 citations 的集合不一致")

    evidence_statuses = {"answered", "conflict"}
    if result["status"] in evidence_statuses and not result["claims"]:
        errors.append("answered/conflict 必须包含有引用的 claims")
    if result["status"] not in evidence_statuses and (result["claims"] or result["citations"]):
        errors.append("非证据回答不得携带 claims/citations")
    if trace["failure"] == "none" and result["status"] != query["expected_status"]:
        errors.append(
            f"状态不符合 fixture：expected={query['expected_status']}, actual={result['status']}"
        )
    if trace["failure"] == "none":
        actual_fact_ids = sorted(citation[1] for citation in top_citations)
        if actual_fact_ids != query["expected_fact_ids"]:
            errors.append(
                f"引用事实不符合 fixture：expected={query['expected_fact_ids']}, actual={actual_fact_ids}"
            )
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    for forbidden_document_id in query["forbidden_document_ids"]:
        if forbidden_document_id in serialized:
            errors.append(f"结果泄露了被过滤 document id：{forbidden_document_id}")
    return errors


def run_pipeline(
    fixture: dict[str, Any], query_id: str, failure: str = "none"
) -> dict[str, Any]:
    """Run one deterministic query through route, retrieve, rerank, context, and answer."""

    if failure not in VALID_FAILURES:
        raise ValueError(f"未知 failure：{failure}")
    query = _find_query(fixture, query_id)
    trace = _base_trace(fixture, query, failure)
    if query["route"] == "tool_required":
        result = _result(
            "tool_required",
            "这是实时状态问题，应调用经过鉴权的受控工具；离线知识快照不回答当前状态。",
            [],
            [],
            trace,
        )
    else:
        visible, filter_summary, _ = filter_documents(fixture["documents"], query)
        trace["filter_summary"] = filter_summary
        if failure == "retrieval_error":
            trace["degraded"] = True
            trace["fallback"] = "retrieval_error:refuse"
            result = _result(
                "dependency_unavailable",
                "检索依赖当前不可用；为避免脱离证据回答，本次请求已停止。",
                [],
                [],
                trace,
            )
        else:
            pipeline = fixture["pipeline"]
            document_by_id = {document["id"]: document for document in visible}
            retrieved = retrieve(query, visible, pipeline["retrieval_limit"])
            trace["retrieved"] = retrieved
            use_rerank_fallback = failure == "reranker_error"
            reranked = rerank(query, retrieved, document_by_id, use_rerank_fallback)
            trace["reranked"] = reranked
            if use_rerank_fallback:
                trace["degraded"] = True
                trace["fallback"] = "reranker_error:retrieval_order"
            selected, dropped, context_chars = select_context(
                reranked,
                document_by_id,
                pipeline["context_limit"],
                pipeline["max_context_chars"],
            )
            trace["selected"] = selected
            trace["dropped"] = dropped
            trace["context_chars"] = context_chars
            if failure == "generation_error":
                trace["degraded"] = True
                trace["fallback"] = "generation_error:refuse"
                result = _result(
                    "generation_unavailable",
                    "回答组件当前不可用；已保留检索 trace，但不会用未验证文本代替答案。",
                    [],
                    [],
                    trace,
                )
            else:
                status, answer, claims, citations = generate_extractively(
                    query, selected, document_by_id
                )
                result = _result(status, answer, claims, citations, trace)

    errors = validate_result(fixture, query, result)
    if errors:
        raise RuntimeError("内部结果校验失败：\n- " + "\n- ".join(errors))
    return result


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        if args.command == "demo":
            results = [
                run_pipeline(fixture, query["id"], failure=args.failure)
                for query in fixture["queries"]
            ]
            payload: dict[str, Any] = {
                "fixture": str(args.fixture),
                "mode": "demo",
                "results": results,
            }
        else:
            payload = {
                "fixture": str(args.fixture),
                "mode": "ask",
                "result": run_pipeline(fixture, args.query_id, failure=args.failure),
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (FixtureError, KeyError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
