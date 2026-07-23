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
    raise FixtureError(f"JSON does not allow non-finite constants: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # Do not reflect an untrusted member name into a CLI error.  Besides
            # needless disclosure, a JSON-escaped lone surrogate cannot be
            # written to a strict UTF-8 terminal.
            raise FixtureError("JSON contains a duplicate member")
        result[key] = value
    return result


def _reject_invalid_unicode(value: Any) -> None:
    """Reject JSON strings/keys that cannot become strict UTF-8 evidence bytes."""

    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise FixtureError("fixture contains invalid Unicode") from exc
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
                raise FixtureError(f"JSON container nesting must not exceed {MAX_JSON_DEPTH} levels")
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        raise FixtureError("fixture must be JSON text")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise FixtureError("fixture contains invalid Unicode") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise FixtureError(f"fixture must not exceed {MAX_FIXTURE_BYTES} UTF-8 bytes")
    _reject_excessive_json_nesting(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(f"fixture JSON could not be parsed: {exc.msg}") from exc
    except RecursionError as exc:
        raise FixtureError("fixture JSON nesting exceeds the parser limit") from exc
    _reject_invalid_unicode(parsed)
    return parsed


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        errors.append(f"{label} fields mismatch: missing={missing}, extra={extra}")
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
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} is not a valid ISO date: {value!r}")
        return None


def _sorted_unique_strings(value: Any, label: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not all(_nonempty_string(item) for item in value):
        errors.append(f"{label} must be a list of non-empty strings")
        return None
    if len(value) > MAX_LIST_ITEMS:
        errors.append(f"{label} must not exceed {MAX_LIST_ITEMS} items")
        return None
    strings = list(value)
    if strings != sorted(set(strings)):
        errors.append(f"{label} must be sorted and unique")
    return strings


def _unit_interval(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be a finite number in 0..1")
        return
    try:
        number = float(value)
    except OverflowError:
        errors.append(f"{label} must be a finite number in 0..1")
        return
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        errors.append(f"{label} must be a finite number in 0..1")


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
        errors.append("schema_version must be '2.0'")

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
                errors.append(f"pipeline.{field} must be a non-empty string")
        for field in ("retrieval_limit", "context_limit"):
            if type(pipeline[field]) is not int or pipeline[field] <= 0:
                errors.append(f"pipeline.{field} must be a positive integer")
            elif pipeline[field] > MAX_STAGE_LIMIT:
                errors.append(
                    f"pipeline.{field} must not exceed {MAX_STAGE_LIMIT}"
                )
        if (
            type(pipeline["max_context_chars"]) is not int
            or not 1 <= pipeline["max_context_chars"] <= MAX_CONTEXT_CHARS
        ):
            errors.append(
                f"pipeline.max_context_chars must be an integer in 1..{MAX_CONTEXT_CHARS}"
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
                errors.append(f"evaluation_policy.{field} must be a non-empty string")
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
                "evaluation_policy.max_non_disclosure_violations must be a non-negative integer"
            )

    documents = fixture["documents"]
    if (
        not isinstance(documents, list)
        or not documents
        or len(documents) > MAX_DOCUMENTS
    ):
        errors.append(f"documents must be a list with 1..{MAX_DOCUMENTS} items")
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
                errors.append(f"{label}.{field} must be a non-empty string")
        document_id = document["id"]
        if isinstance(document_id, str):
            if document_id in document_ids:
                errors.append(f"duplicate document id: {document_id}")
            document_ids.add(document_id)
        acl = _sorted_unique_strings(document["acl"], f"{label}.acl", errors)
        if acl == []:
            errors.append(f"{label}.acl must not be empty")
        if not isinstance(document["status"], str) or document["status"] not in {
            "published",
            "draft",
            "archived",
        }:
            errors.append(f"{label}.status is invalid")
        start = _parse_iso_date(document["effective_from"], f"{label}.effective_from", errors)
        end_value = document["effective_to"]
        end = None
        if end_value is not None:
            end = _parse_iso_date(end_value, f"{label}.effective_to", errors)
        if start is not None and end is not None and end <= start:
            errors.append(f"{label} effective window must satisfy [effective_from, effective_to)")
        if type(document["authority"]) is not int or not 0 <= document["authority"] <= 100:
            errors.append(f"{label}.authority must be an integer in 0..100")

        facts = document["facts"]
        if (
            not isinstance(facts, list)
            or not facts
            or len(facts) > MAX_FACTS_PER_DOCUMENT
        ):
            errors.append(
                f"{label}.facts must be a list with 1..{MAX_FACTS_PER_DOCUMENT} items"
            )
            continue
        for fact_index, fact in enumerate(facts):
            fact_label = f"{label}.facts[{fact_index}]"
            if not _exact_fields(fact, FACT_FIELDS, fact_label, errors):
                continue
            for field in FACT_FIELDS:
                if not _nonempty_string(fact[field]):
                    errors.append(f"{fact_label}.{field} must be a non-empty string")
            fact_id = fact["fact_id"]
            if isinstance(fact_id, str):
                if fact_id in fact_ids:
                    errors.append(f"duplicate fact id: {fact_id}")
                fact_ids.add(fact_id)
            topic = fact["topic"]
            if isinstance(topic, str) and TOPIC_PATTERN.fullmatch(topic) is None:
                errors.append(f"{fact_label}.topic must be a stable snake_case identifier")
            if isinstance(fact["statement"], str) and isinstance(document["text"], str):
                if fact["statement"] not in document["text"]:
                    errors.append(f"{fact_label}.statement must occur verbatim in document.text")

    queries = fixture["queries"]
    if (
        not isinstance(queries, list)
        or not queries
        or len(queries) > MAX_QUERIES
    ):
        errors.append(f"queries must be a list with 1..{MAX_QUERIES} items")
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
                errors.append(f"{label}.{field} must be a non-empty string")
        query_id = query["id"]
        if isinstance(query_id, str):
            if query_id in query_ids:
                errors.append(f"duplicate query id: {query_id}")
            query_ids.add(query_id)
        subject_groups = _sorted_unique_strings(
            query["subject_groups"], f"{label}.subject_groups", errors
        )
        if subject_groups == []:
            errors.append(f"{label}.subject_groups must not be empty; public access must resolve to a trusted group")
        _parse_iso_date(query["as_of"], f"{label}.as_of", errors)
        if not isinstance(query["route"], str) or query["route"] not in {
            "knowledge",
            "tool_required",
        }:
            errors.append(f"{label}.route is invalid")
        topic = query["topic"]
        if isinstance(topic, str) and TOPIC_PATTERN.fullmatch(topic) is None:
            errors.append(f"{label}.topic must be a stable snake_case identifier")
        slice_name = query["slice"]
        if isinstance(slice_name, str) and TOPIC_PATTERN.fullmatch(slice_name) is None:
            errors.append(f"{label}.slice must be a stable snake_case identifier")
        if type(query["critical"]) is not bool:
            errors.append(f"{label}.critical must be a boolean")
        if (
            not isinstance(query["expected_status"], str)
            or query["expected_status"] not in VALID_STATUSES
        ):
            errors.append(f"{label}.expected_status is invalid")
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
                errors.append(f"{label} references unknown fact IDs: {unknown_facts}")
        if forbidden_ids is not None:
            unknown_documents = sorted(set(forbidden_ids) - document_ids)
            if unknown_documents:
                errors.append(f"{label} references unknown forbidden document IDs: {unknown_documents}")
        if forbidden_substrings is not None:
            if any(len(item) < 4 for item in forbidden_substrings):
                errors.append(f"{label}.forbidden_output_substrings items must have at least 4 characters")
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
                        "must come from a forbidden document test canary"
                    )
        if query["route"] == "tool_required" and query["expected_status"] != "tool_required":
            errors.append(f"{label} tool_required route must expect tool_required status")
    if queries and not any(
        isinstance(query, dict) and query.get("critical") is True for query in queries
    ):
        errors.append("queries need at least one critical case to calculate the critical-slice gate")
    if queries and not any(
        isinstance(query, dict) and query.get("expected_fact_ids") for query in queries
    ):
        errors.append("queries need at least one expected fact to calculate layered fact recall")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    """Load strict JSON and reject duplicate keys, NaN, Infinity, and bad schemas."""

    try:
        with path.open("rb") as handle:
            raw_bytes = handle.read(MAX_FIXTURE_BYTES + 1)
        if len(raw_bytes) > MAX_FIXTURE_BYTES:
            raise FixtureError(
                f"fixture must not exceed {MAX_FIXTURE_BYTES} UTF-8 bytes"
            )
        raw = raw_bytes.decode("utf-8", errors="strict")
        fixture = strict_json_loads(raw)
    except FixtureError:
        raise
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"could not read fixture: {type(exc).__name__}") from exc
    errors = validate_fixture(fixture)
    if errors:
        raise FixtureError("fixture validation failed:\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root must be an object")
    return fixture


def text_features(text: str) -> set[str]:
    """Create transparent ASCII tokens plus CJK unigrams/bigrams for the toy retriever."""

    lowered = text.lower()  # Normalize ASCII case; this is a transparent lexical baseline, not a tokenizer.
    features = {f"a:{token}" for token in ASCII_TOKEN_PATTERN.findall(lowered)}  # Prefix each ASCII word to avoid mixing it with CJK segments.
    for run in CJK_RUN_PATTERN.findall(lowered):  # Process each run of consecutive CJK characters.
        features.update(f"c1:{character}" for character in run)  # Include individual-character features so short terms can still match.
        features.update(f"c2:{run[index:index + 2]}" for index in range(len(run) - 1))  # Include adjacent pairs to retain minimal local order.
    return features  # Return a deduplicated set; later stages compare only overlap counts.


def filter_documents(
    documents: list[dict[str, Any]], query: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, list[str]]]:
    """Apply tenant, lifecycle, time, and ACL constraints before any scoring."""

    as_of = date.fromisoformat(query["as_of"])  # Parse the trusted runtime timestamp for effective-window checks.
    groups = set(query["subject_groups"])  # Gather trusted principal groups for each document ACL intersection.
    visible: list[dict[str, Any]] = []  # Only documents that satisfy every mandatory constraint join this list.
    decisions: dict[str, list[str]] = {}  # The protected trace retains each document's filter reasons.
    reason_counts: dict[str, int] = {}  # Aggregate reason counts are not visible in the public response.
    for document in documents:  # Apply safety filters document by document before computing any retrieval score.
        reasons: list[str] = []  # A single document can trigger more than one filter reason.
        if document["tenant_id"] != query["tenant_id"]:  # Tenant IDs must match exactly; semantic similarity is irrelevant.
            reasons.append("tenant_mismatch")  # Record an internal reason for audit and tests.
        if document["status"] != "published":  # Draft and archived documents do not participate in online retrieval.
            reasons.append("not_published")  # Filter lifecycle state first to prevent later scoring from leaking it.
        effective_from = date.fromisoformat(document["effective_from"])
        effective_to = (
            date.fromisoformat(document["effective_to"])
            if document["effective_to"] is not None
            else None
        )
        if as_of < effective_from or (effective_to is not None and as_of >= effective_to):  # The effective window is half-open: [from, to).
            reasons.append("outside_effective_window")  # The document stops being usable on its effective_to date.
        acl = set(document["acl"])  # A document ACL is the set of groups allowed to read it.
        if not (acl & groups):  # The current principal must match at least one authorized group.
            reasons.append("acl_denied")  # Fail closed when no group overlaps.
        decisions[document["id"]] = reasons  # Retain internal decisions even for invisible documents for protected audit.
        if reasons:  # Any failed mandatory condition keeps the document out of the candidate set.
            for reason in reasons:  # Count each failure type to help detect policy drift.
                reason_counts[reason] = reason_counts.get(reason, 0) + 1  # Increment the aggregate for this reason.
        else:  # Only documents that pass every condition can be scored by the retriever.
            visible.append(document)  # Preserve the complete visible teaching record.
    summary = {  # Form an internal filter summary that must not enter the public response.
        "visible": len(visible),
        "filtered": len(documents) - len(visible),
        "reasons": dict(sorted(reason_counts.items())),
    }
    return visible, summary, decisions  # Return safe candidates, the summary, and per-document decisions to the protected execution chain.


def retrieve(
    query: dict[str, Any], documents: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Return positive lexical candidates; scores are comparable only within this query."""

    query_features = text_features(query["text"])  # Convert the query into a transparent lexical feature set.
    candidates: list[dict[str, Any]] = []  # The received documents have already passed tenant, ACL, and lifecycle filters.
    for document in documents:  # Compute teaching retrieval scores only inside the visible set.
        document_features = text_features(f"{document['title']} {document['text']}")  # Both title and body participate in recall.
        overlap = len(query_features & document_features)  # Count shared features across the two sets.
        denominator = math.sqrt(max(1, len(query_features)) * max(1, len(document_features)))  # Use the geometric mean of lengths for simple normalization.
        score = overlap / denominator  # Produce a non-negative lexical score comparable only within this query.
        if score > 0.0:  # Zero-score candidates share no terms and do not warrant later rerank capacity.
            candidates.append({"document_id": document["id"], "score": round(score, 6)})  # Fix presentation precision while retaining document identity.
    candidates.sort(key=lambda item: (-item["score"], item["document_id"]))  # Sort descending by score and break ties stably by ID.
    limited = candidates[:limit]  # Enforce the first-stage candidate cap to prevent unbounded downstream growth.
    return [  # Produce lightweight candidate projections with consecutive ranks.
        {"document_id": item["document_id"], "rank": index, "score": item["score"]}  # Do not carry the body; it remains behind the controlled mapping.
        for index, item in enumerate(limited, start=1)  # Number from 1 for user-readable ranks.
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
        raise FixtureError("fixture cannot be serialized to a strict UTF-8 fingerprint") from exc
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
    raise KeyError(f"unknown query id: {query_id}")


NON_EVIDENCE_ANSWERS = {
    "insufficient_evidence": "The currently accessible and effective material is insufficient to answer; clarify the question or request human verification.",
    "tool_required": "This is a real-time status question; use an authorized, controlled tool. The offline knowledge snapshot does not answer current-state questions.",
    "dependency_unavailable": "The retrieval dependency is unavailable; to avoid answering without evidence, this request has stopped.",
    "generation_unavailable": "The answering component is unavailable; the internal audit trace is retained, but unverified text will not replace an answer.",
}


def render_answer(status: str, claims: list[dict[str, Any]]) -> str:
    """Render the public answer only from a validated status and claim set."""

    if status == "answered":
        if len(claims) != 1:
            raise ValueError("answered must contain exactly one claim")
        return str(claims[0]["text"])
    if status == "conflict":
        if len(claims) < 2:
            raise ValueError("conflict must contain at least two claims")
        statements = "; ".join(str(claim["text"]) for claim in claims)
        return f"Current effective sources conflict; no choice is made: {statements}"
    if status in NON_EVIDENCE_ANSWERS:
        if claims:
            raise ValueError("non-evidence statuses must not render claims")
        return NON_EVIDENCE_ANSWERS[status]
    raise ValueError(f"unknown status: {status}")


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
        errors.append("response.trace_id must be a non-empty string")
    status_is_valid = (
        isinstance(response["status"], str) and response["status"] in VALID_STATUSES
    )
    if not status_is_valid:
        errors.append("response.status is invalid")
    if not _nonempty_string(response["answer"]):
        errors.append("response.answer must be a non-empty string")
    if not isinstance(response["claims"], list):
        errors.append("response.claims must be a list")
        return errors
    if not isinstance(response["citations"], list):
        errors.append("response.citations must be a list")
        return errors

    fact_lookup = _fact_lookup(fixture)
    top_citations: set[tuple[str, str]] = set()
    for citation in response["citations"]:
        if not isinstance(citation, dict) or set(citation) != {
            "document_id",
            "fact_id",
            "source_revision",
        }:
            errors.append("citation fields mismatch")
            continue
        if not _nonempty_string(citation["document_id"]):
            errors.append("citation.document_id must be a non-empty string")
            continue
        if not _nonempty_string(citation["fact_id"]):
            errors.append("citation.fact_id must be a non-empty string")
            continue
        if not _nonempty_string(citation["source_revision"]):
            errors.append("citation.source_revision must be a non-empty string")
            continue
        key = (citation["document_id"], citation["fact_id"])
        if key in top_citations:
            errors.append(f"duplicate citation: {key}")
        top_citations.add(key)
        fact_entry = fact_lookup.get(citation["fact_id"])
        if fact_entry is None:
            errors.append(f"citation references unknown fact: {citation['fact_id']}")
            continue
        document, _ = fact_entry
        if document["id"] != citation["document_id"]:
            errors.append(f"citation document/fact mismatch: {key}")
        if document["source_revision"] != citation["source_revision"]:
            errors.append(f"citation source_revision mismatch: {key}")

    claim_citations: set[tuple[str, str]] = set()
    claim_ids: set[str] = set()
    structurally_valid_claims = True
    for claim in response["claims"]:
        if not isinstance(claim, dict) or set(claim) != {"claim_id", "text", "citations"}:
            errors.append("claim fields mismatch")
            structurally_valid_claims = False
            continue
        claim_id = claim["claim_id"]
        if not _nonempty_string(claim_id):
            errors.append("claim.claim_id must be a non-empty string")
            structurally_valid_claims = False
        else:
            if claim_id in claim_ids:
                errors.append(f"duplicate claim id: {claim_id}")
            claim_ids.add(claim_id)
        if not _nonempty_string(claim["text"]):
            errors.append("claim.text must be a non-empty string")
            structurally_valid_claims = False
        if not isinstance(claim["citations"], list) or not claim["citations"]:
            errors.append(f"claim {claim_id!r} must have citations")
            structurally_valid_claims = False
            continue
        references_seen: set[tuple[str, str]] = set()
        for reference in claim["citations"]:
            if not isinstance(reference, dict) or set(reference) != {"document_id", "fact_id"}:
                errors.append("claim citation fields mismatch")
                structurally_valid_claims = False
                continue
            if not _nonempty_string(reference["document_id"]):
                errors.append("claim citation.document_id must be a non-empty string")
                structurally_valid_claims = False
                continue
            if not _nonempty_string(reference["fact_id"]):
                errors.append("claim citation.fact_id must be a non-empty string")
                structurally_valid_claims = False
                continue
            key = (reference["document_id"], reference["fact_id"])
            if key in references_seen:
                errors.append(f"duplicate claim citation: {claim_id!r} {key}")
                structurally_valid_claims = False
                continue
            references_seen.add(key)
            claim_citations.add(key)
            if key not in top_citations:
                errors.append(f"claim citation is absent from top-level citations: {key}")
            fact_entry = fact_lookup.get(reference["fact_id"])
            if fact_entry is None:
                errors.append(f"claim citation references unknown fact: {reference['fact_id']}")
                continue
            document, fact = fact_entry
            if (
                document["id"] != reference["document_id"]
                or claim["text"] != fact["statement"]
            ):
                errors.append(
                    f"each citation for a claim must support the claim verbatim: {claim_id!r} {key}"
                )
    if claim_citations != top_citations:
        errors.append("claims and top-level citations have mismatched sets")

    evidence_statuses = {"answered", "conflict"}
    if status_is_valid and response["status"] in evidence_statuses and not response["claims"]:
        errors.append("answered/conflict must contain cited claims")
    if status_is_valid and response["status"] not in evidence_statuses and (
        response["claims"] or response["citations"]
    ):
        errors.append("non-evidence answers must not carry claims/citations")
    if status_is_valid and structurally_valid_claims:
        try:
            expected_answer = render_answer(response["status"], response["claims"])
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if response["answer"] != expected_answer:
                errors.append("response.answer is not deterministically rendered from validated status/claims")
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
            errors.append(f"audit_trace.{stage} must be a list")
            stage_items[stage] = []
            continue
        valid_items: list[dict[str, Any]] = []
        ids: list[str] = []
        for index, item in enumerate(items):
            label = f"audit_trace.{stage}[{index}]"
            if not isinstance(item, dict) or set(item) != shape:
                errors.append(f"{label} fields mismatch")
                continue
            item_is_valid = True
            if not _nonempty_string(item["document_id"]):
                errors.append(f"{label}.document_id must be a non-empty string")
                item_is_valid = False
            else:
                ids.append(item["document_id"])
            if stage in {"retrieved", "reranked", "selected"}:
                if type(item["rank"]) is not int or item["rank"] <= 0:
                    errors.append(f"{label}.rank must be a positive integer")
                    item_is_valid = False
                if not _finite_number(item["score"]):
                    errors.append(f"{label}.score must be a finite number")
                    item_is_valid = False
            if stage == "retrieved" and _finite_number(item["score"]):
                if not 0.0 <= float(item["score"]) <= 1.0:
                    errors.append(f"{label}.score must be in 0..1")
                    item_is_valid = False
            if stage == "reranked":
                if type(item["retrieval_rank"]) is not int or item["retrieval_rank"] <= 0:
                    errors.append(f"{label}.retrieval_rank must be a positive integer")
                    item_is_valid = False
                if not _finite_number(item["retrieval_score"]):
                    errors.append(f"{label}.retrieval_score must be a finite number")
                    item_is_valid = False
                if type(item["topic_match"]) is not bool:
                    errors.append(f"{label}.topic_match must be a boolean")
                    item_is_valid = False
            if stage == "selected":
                if type(item["chars"]) is not int or item["chars"] <= 0:
                    errors.append(f"{label}.chars must be a positive integer")
                    item_is_valid = False
            if stage == "dropped":
                if not isinstance(item["reason"], str) or item["reason"] not in {
                    "canonical_duplicate",
                    "context_limit",
                    "character_budget",
                }:
                    errors.append(f"{label}.reason is invalid")
                    item_is_valid = False
            if item_is_valid:
                valid_items.append(item)
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate audit_trace.{stage} document_id")
        if stage in {"retrieved", "reranked"} and len(valid_items) == len(items):
            ranks = [item["rank"] for item in valid_items]
            if ranks != list(range(1, len(valid_items) + 1)):
                errors.append(f"audit_trace.{stage}.rank must increase consecutively from 1")
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
            query_errors.append(f"runtime_query.{field} must be a non-empty string")
    _sorted_unique_strings(
        query["subject_groups"], "runtime_query.subject_groups", query_errors
    )
    _parse_iso_date(query["as_of"], "runtime_query.as_of", query_errors)
    if not isinstance(query["route"], str) or query["route"] not in {
        "knowledge",
        "tool_required",
    }:
        query_errors.append("runtime_query.route is invalid")
    if (
        isinstance(query["topic"], str)
        and TOPIC_PATTERN.fullmatch(query["topic"]) is None
    ):
        query_errors.append("runtime_query.topic must be a stable snake_case identifier")
    if query_errors:
        errors.extend(query_errors)
        return errors
    if trace["visibility"] != "privileged_audit":
        errors.append("audit_trace.visibility must be privileged_audit")
    if isinstance(response, dict) and trace["trace_id"] != response.get("trace_id"):
        errors.append("public trace_id does not match internal audit trace")
    expected_trace_id = _trace_id(fixture, query)
    if trace["trace_id"] != expected_trace_id:
        errors.append("audit_trace.trace_id is not bound to pipeline/query")
    pipeline = fixture["pipeline"]
    for field in (
        "pipeline_revision",
        "retrieval_revision",
        "rerank_revision",
        "context_policy_revision",
        "answer_policy_revision",
    ):
        if trace[field] != pipeline[field]:
            errors.append(f"audit_trace.{field} does not match fixture.pipeline")
    for field in ("id", "route", "topic", "authorization_revision", "as_of"):
        trace_field = "query_id" if field == "id" else field
        if trace[trace_field] != query[field]:
            errors.append(f"audit_trace.{trace_field} does not match the trusted execution context")
    failure_is_valid = (
        isinstance(trace["failure"], str) and trace["failure"] in VALID_FAILURES
    )
    if not failure_is_valid:
        errors.append("audit_trace.failure is invalid")
    if type(trace["degraded"]) is not bool:
        errors.append("audit_trace.degraded must be a boolean")
    if type(trace["context_chars"]) is not int or trace["context_chars"] < 0:
        errors.append("audit_trace.context_chars must be a non-negative integer")
    if trace["fallback"] is not None and not _nonempty_string(trace["fallback"]):
        errors.append("audit_trace.fallback must be null or a non-empty string")
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
        errors.append("audit_trace.degraded is not bound to route/failure behavior")
    if trace["fallback"] != expected_fallback:
        errors.append("audit_trace.fallback is not bound to route/failure behavior")
    if (
        expected_failure_status is not None
        and isinstance(response, dict)
        and response.get("status") != expected_failure_status
    ):
        errors.append("response.status is not bound to route/failure behavior")
    filter_summary = trace["filter_summary"]
    filter_shape_is_valid = isinstance(filter_summary, dict) and set(filter_summary) == {
        "visible",
        "filtered",
        "reasons",
    }
    if not filter_shape_is_valid:
        errors.append("audit_trace.filter_summary fields mismatch")
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
        errors.append("audit_trace.filter_summary value types are invalid")

    stage_items = _validated_stage_items(trace, errors)
    stage_ids = {
        stage: [item["document_id"] for item in items]
        for stage, items in stage_items.items()
    }
    visible, recomputed_filter_summary, _ = filter_documents(fixture["documents"], query)
    visible_ids = {document["id"] for document in visible}
    for stage, ids in stage_ids.items():
        if any(document_id not in visible_ids for document_id in ids):
            errors.append(f"audit_trace.{stage} contains an unauthorized, expired, or unpublished document")

    expected_filter_summary = (
        recomputed_filter_summary
        if query["route"] == "knowledge"
        else {"visible": 0, "filtered": 0, "reasons": {}}
    )
    if filter_summary != expected_filter_summary:
        errors.append("audit_trace.filter_summary was not recomputed from the trusted corpus")

    retrieved_items = stage_items["retrieved"]
    reranked_items = stage_items["reranked"]
    selected_items = stage_items["selected"]
    dropped_items = stage_items["dropped"]
    retrieved_by_id = {item["document_id"]: item for item in retrieved_items}
    reranked_by_id = {item["document_id"]: item for item in reranked_items}

    if set(stage_ids["reranked"]) != set(stage_ids["retrieved"]):
        errors.append("audit_trace.reranked must retain the same document set as retrieved")
    for item in reranked_items:
        source = retrieved_by_id.get(item["document_id"])
        if source is not None and (
            item["retrieval_rank"] != source["rank"]
            or item["retrieval_score"] != source["score"]
        ):
            errors.append("audit_trace.reranked retrieval rank/score is not bound to retrieved")
    selected_ids = set(stage_ids["selected"])
    dropped_ids = set(stage_ids["dropped"])
    reranked_ids = set(stage_ids["reranked"])
    if selected_ids & dropped_ids:
        errors.append("audit_trace.selected and dropped must not contain the same document")
    if selected_ids | dropped_ids != reranked_ids:
        errors.append("audit_trace.selected+dropped must come entirely from reranked")
    for item in selected_items:
        source = reranked_by_id.get(item["document_id"])
        if source is not None and (
            item["rank"] != source["rank"] or item["score"] != source["score"]
        ):
            errors.append("audit_trace.selected rank/score is not bound to reranked")

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
                f"audit_trace.selected chars were not recomputed from document: {item['document_id']}"
            )
    if trace["context_chars"] != recomputed_context_chars:
        errors.append("audit_trace.context_chars was not recomputed from selected chars")

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
                errors.append(f"audit_trace.{stage} is not bound to a deterministic stage transition")
        if trace["context_chars"] != expected_context_chars:
            errors.append("audit_trace.context_chars is not bound to the context-selection result")
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
            errors.append("response is not bound to the deterministic runtime result")

    if isinstance(response, dict) and isinstance(response.get("citations"), list):
        for citation in response["citations"]:
            document_id = citation.get("document_id") if isinstance(citation, dict) else None
            if isinstance(document_id, str) and document_id not in selected_ids:
                errors.append("citation does not come from selected context")
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
        "status_mismatch": "public response status does not match the offline oracle",
        "fact_set_mismatch": "public response cited facts do not match the offline oracle",
        "forbidden_document_disclosure": "public response discloses a forbidden document ID",
        "forbidden_content_disclosure": "public response discloses a forbidden-output canary",
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

    if failure not in VALID_FAILURES:  # Accept only the three modeled dependency failures and the normal state.
        raise ValueError(f"unknown failure: {failure}")  # Do not treat a typo as an explainable degraded behavior.
    query_case = _find_query(fixture, query_id)  # Find the complete test case in the fixture that includes the oracle.
    query = _runtime_query(query_case)  # Project only runtime-permitted fields, isolating the expected/forbidden oracle.
    trace = _base_trace(fixture, query, failure)  # Create a protected stage record that the public response does not expose directly.
    if query["route"] == "tool_required":  # Real-time or action questions must not use the knowledge snapshot.
        response = _response(trace["trace_id"], "tool_required", [], [])  # Do not retrieve or generate factual claims; return the controlled status directly.
    else:  # Only the knowledge route enters the retrieval-to-citation pipeline.
        visible, filter_summary, _ = filter_documents(fixture["documents"], query)  # Filter tenant, time, status, and ACL before any scoring.
        trace["filter_summary"] = filter_summary  # Filter statistics remain only in the protected audit trace.
        if failure == "retrieval_error":  # An unavailable retriever must not fabricate an internal answer from parameter memory.
            trace["degraded"] = True  # Explicitly mark that this execution did not take the full primary path.
            trace["fallback"] = "retrieval_error:refuse"  # Record refusal rather than a permissive retrieval fallback.
            response = _response(trace["trace_id"], "dependency_unavailable", [], [])  # The public layer returns the unavailable-dependency status without claims.
        else:  # Build the safe candidate chain only when retrieval is available.
            pipeline = fixture["pipeline"]  # Read validated retrieval/context limits and version configuration.
            document_by_id = {document["id"]: document for document in visible}  # The mapping contains only authorized documents for subsequent ID lookup.
            retrieved = retrieve(query, visible, pipeline["retrieval_limit"])  # Run first-stage lexical recall within the safe set.
            trace["retrieved"] = retrieved  # Record recall results to distinguish recall from later-stage behavior.
            use_rerank_fallback = failure == "reranker_error"  # Failure injection decides whether to skip rule-based reranking.
            reranked = rerank(query, retrieved, document_by_id, use_rerank_fallback)  # Rerank normally; retain the same safe retrieval order during failure.
            trace["reranked"] = reranked  # Record the actual ordering used whether or not it is degraded.
            if use_rerank_fallback:  # A failed reranker must not expand candidates or relax ACLs.
                trace["degraded"] = True  # Let evaluation and monitoring count the degraded share.
                trace["fallback"] = "reranker_error:retrieval_order"  # Make the safe first-stage order explicit.
            selected, dropped, context_chars = select_context(  # Select actually citable evidence from ranked candidates under a fixed budget.
                reranked,  # Use the actual ordering just recorded, not another implicit list.
                document_by_id,  # Read body text and canonical IDs only from the visible-document mapping.
                pipeline["context_limit"],  # Limit the number of selected evidence items.
                pipeline["max_context_chars"],  # Limit the total character budget sent to the generator.
            )
            trace["selected"] = selected  # Preserve the identity and scores of the evidence that entered context.
            trace["dropped"] = dropped  # Preserve reasons items were dropped by deduplication or budget.
            trace["context_chars"] = context_chars  # Preserve actual budget consumption for cost investigation.
            if failure == "generation_error":  # Evidence was selected but the generation stage is unavailable.
                trace["degraded"] = True  # Still mark this as degraded rather than normally answered.
                trace["fallback"] = "generation_error:refuse"  # This example refuses to output an unverified draft.
                response = _response(trace["trace_id"], "generation_unavailable", [], [])  # The public result contains no unverified claims.
            else:  # When all dependencies are available, use deterministic extractive generation to avoid unsupported output.
                status, claims, citations = generate_extractively(  # Generate status, claims, and citations from selected evidence.
                    query, selected, document_by_id  # The generator cannot see unauthorized or unselected documents.
                )
                response = _response(trace["trace_id"], status, claims, citations)  # Wrap the result in the public structure expected by the validator.

    execution = {"response": response, "audit_trace": trace}  # Pair the public response with its protected trace for internal validation.
    errors = validate_execution(fixture, query, execution)  # Recompute stage and citation invariants before publication at the boundary.
    if errors:  # The teaching implementation never returns internally inconsistent results to its caller.
        raise RuntimeError("internal execution contract validation failed:\n- " + "\n- ".join(errors))  # Combine contract errors into a diagnosable exception.
    return execution  # Only validated dual-projection results are available to public and audit callers.


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
        raise ValueError(f"unknown failure: {failure}")
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
        help="Simulate a dependency failure; use none for normal teaching runs",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).with_name("rag-fixture.json"),
        help="Strict JSON teaching data",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo_parser = subparsers.add_parser("demo", help="Run every query in the fixture")
    _add_failure_argument(demo_parser)
    ask_parser = subparsers.add_parser("ask", help="Run one case by stable query ID")
    ask_parser.add_argument("--query-id", required=True)
    _add_failure_argument(ask_parser)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Output the protected internal audit trace; this teaching flag is not real authorization",
    )
    inspect_parser.add_argument("--query-id", required=True)
    inspect_parser.add_argument(
        "--operator-view",
        action="store_true",
        help="Explicitly confirm that the output contains internal candidates, filter statistics, and authorization version",
    )
    _add_failure_argument(inspect_parser)
    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Generate a layered offline evaluation report without private canaries"
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
                    "inspect requires --operator-view; this flag is only a teaching confirmation and does not replace real authorization"
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
