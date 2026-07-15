"""Offline Crew/Flow teaching project with deterministic task stubs.

The project does not import CrewAI, call a model, or access the network.  It
demonstrates contracts that can later be mapped to CrewAI Agents, Tasks, Crews,
and Flows after the real dependency and provider have been pinned and tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


CATALOG_SCHEMA_VERSION = 1
FLOW_SCHEMA_VERSION = 1
TERMINAL_STAGES = {"ready_to_publish", "published", "human_review"}


class FlowError(RuntimeError):
    """Raised when an input or task boundary fails closed."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise FlowError(f"{label} 字段不匹配；缺失={missing}，多余={extra}")


def require_nonempty_text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise FlowError(f"{label} 必须是字符串")
    normalized = value.strip()
    if not normalized:
        raise FlowError(f"{label} 不能为空")
    if len(normalized) > maximum:
        raise FlowError(f"{label} 不能超过 {maximum} 个字符")
    return normalized


def _validate_text_list(value: Any, label: str, maximum_items: int = 50) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum_items:
        raise FlowError(f"{label} 必须是 1–{maximum_items} 个字符串组成的数组")
    result = [require_nonempty_text(item, f"{label}[]", 1000) for item in value]
    if len(set(result)) != len(result):
        raise FlowError(f"{label} 不能包含重复项")
    return result


def validate_catalog(catalog: Any) -> None:
    if not isinstance(catalog, dict):
        raise FlowError("来源目录顶层必须是 JSON 对象")
    require_exact_keys(catalog, {"schema_version", "sources"}, "来源目录")
    if catalog["schema_version"] != CATALOG_SCHEMA_VERSION:
        raise FlowError("来源目录 schema_version 不受支持")
    if not isinstance(catalog["sources"], list) or not catalog["sources"]:
        raise FlowError("sources 必须是非空数组")

    identifiers: set[str] = set()
    for index, source in enumerate(catalog["sources"]):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            raise FlowError(f"{label} 必须是对象")
        require_exact_keys(source, {"id", "title", "topics", "claims"}, label)
        source_id = require_nonempty_text(source["id"], f"{label}.id", 64)
        if not all(character.isascii() and (character.isalnum() or character in "-_") for character in source_id):
            raise FlowError(f"{label}.id 只能使用 ASCII 字母、数字、连字符和下划线")
        if source_id in identifiers:
            raise FlowError(f"来源 ID 重复：{source_id}")
        identifiers.add(source_id)
        require_nonempty_text(source["title"], f"{label}.title", 200)
        _validate_text_list(source["topics"], f"{label}.topics", 20)
        _validate_text_list(source["claims"], f"{label}.claims", 50)


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FlowError(f"无法读取来源目录：{exc}") from exc
    validate_catalog(value)
    return value


def source_index(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {source["id"]: source for source in catalog["sources"]}


def emit(state: dict[str, Any], event_type: str, **payload: Any) -> None:
    state["events"].append(
        {
            "sequence": len(state["events"]) + 1,
            "type": require_nonempty_text(event_type, "event.type", 80),
            "payload": payload,
        }
    )


def validate_research(research: Any, catalog: Mapping[str, Any]) -> None:
    if not isinstance(research, dict):
        raise FlowError("research Task 产物必须是对象")
    require_exact_keys(research, {"topic", "claims", "unknowns"}, "research")
    require_nonempty_text(research["topic"], "research.topic", 120)
    if not isinstance(research["claims"], list):
        raise FlowError("research.claims 必须是数组")
    known = source_index(catalog)
    for index, claim in enumerate(research["claims"]):
        label = f"research.claims[{index}]"
        if not isinstance(claim, dict):
            raise FlowError(f"{label} 必须是对象")
        require_exact_keys(claim, {"text", "source_ids"}, label)
        require_nonempty_text(claim["text"], f"{label}.text", 1000)
        identifiers = _validate_text_list(claim["source_ids"], f"{label}.source_ids", 10)
        unknown = [identifier for identifier in identifiers if identifier not in known]
        if unknown:
            raise FlowError(f"{label} 引用了未知来源：{unknown}")
    if not isinstance(research["unknowns"], list):
        raise FlowError("research.unknowns 必须是数组")
    for item in research["unknowns"]:
        require_nonempty_text(item, "research.unknowns[]", 500)


def run_researcher_task(topic: str, catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic stand-in for one bounded researcher Agent/Task."""

    normalized_topic = require_nonempty_text(topic, "topic", 120).casefold()
    matches = [
        source
        for source in catalog["sources"]
        if normalized_topic in {item.casefold() for item in source["topics"]}
    ]
    claims = [
        {"text": claim, "source_ids": [source["id"]]}
        for source in matches
        for claim in source["claims"]
    ]
    unknowns = [] if claims else [f"来源目录没有与“{topic}”精确匹配的主题"]
    research = {"topic": topic, "claims": claims, "unknowns": unknowns}
    validate_research(research, catalog)
    return research


def validate_draft(draft: Any) -> None:
    if not isinstance(draft, dict):
        raise FlowError("draft Task 产物必须是对象")
    require_exact_keys(draft, {"markdown", "claim_count", "revision_note"}, "draft")
    require_nonempty_text(draft["markdown"], "draft.markdown", 20_000)
    if isinstance(draft["claim_count"], bool) or not isinstance(draft["claim_count"], int):
        raise FlowError("draft.claim_count 必须是整数")
    if draft["claim_count"] < 0:
        raise FlowError("draft.claim_count 不能为负数")
    if draft["revision_note"] is not None:
        require_nonempty_text(draft["revision_note"], "draft.revision_note", 500)


def run_writer_task(
    research: Mapping[str, Any],
    revision_note: str | None = None,
    omit_first_citation: bool = False,
) -> dict[str, Any]:
    """Deterministic stand-in for a writer Agent/Task."""

    lines = [f"# {research['topic']}研究简报", "", "## 有来源的结论"]
    for index, claim in enumerate(research["claims"]):
        citations = "" if omit_first_citation and index == 0 else " ".join(
            f"[{source_id}]" for source_id in claim["source_ids"]
        )
        lines.append(f"- {claim['text']} {citations}".rstrip())
    if not research["claims"]:
        lines.append("- 当前没有足够来源支持结论。")
    lines.extend(["", "## 未知项"])
    lines.extend(f"- {item}" for item in research["unknowns"])
    if not research["unknowns"]:
        lines.append("- 当前样本未记录未知项。")
    if revision_note:
        lines.extend(["", "## 修订记录", f"- {revision_note}"])
    draft = {
        "markdown": "\n".join(lines) + "\n",
        "claim_count": len(research["claims"]),
        "revision_note": revision_note,
    }
    validate_draft(draft)
    return draft


def validate_review(review: Any) -> None:
    if not isinstance(review, dict):
        raise FlowError("review Task 产物必须是对象")
    require_exact_keys(
        review,
        {"passed", "reasons", "missing_citations", "unknown_sources"},
        "review",
    )
    if not isinstance(review["passed"], bool):
        raise FlowError("review.passed 必须是布尔值")
    for field in ("reasons", "missing_citations", "unknown_sources"):
        if not isinstance(review[field], list):
            raise FlowError(f"review.{field} 必须是数组")
        for item in review[field]:
            require_nonempty_text(item, f"review.{field}[]", 500)
    if review["passed"] is not (not review["reasons"]):
        raise FlowError("review.passed 与 reasons 矛盾")


def run_reviewer_task(
    research: Mapping[str, Any],
    draft: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Deterministic guardrail; it is not an independent truth oracle."""

    known = source_index(catalog)
    unknown_sources = sorted(
        {
            source_id
            for claim in research["claims"]
            for source_id in claim["source_ids"]
            if source_id not in known
        }
    )
    missing_citations = sorted(
        {
            source_id
            for claim in research["claims"]
            for source_id in claim["source_ids"]
            if f"[{source_id}]" not in draft["markdown"]
        }
    )
    reasons: list[str] = []
    if not research["claims"]:
        reasons.append("没有可发布的有来源结论")
    if draft["claim_count"] != len(research["claims"]):
        reasons.append("draft.claim_count 与 research.claims 数量不一致")
    if unknown_sources:
        reasons.append("存在未知来源 ID")
    if missing_citations:
        reasons.append("草稿缺少引用标记")
    review = {
        "passed": not reasons,
        "reasons": reasons,
        "missing_citations": missing_citations,
        "unknown_sources": unknown_sources,
    }
    validate_review(review)
    return review


def run_crew(
    topic: str,
    catalog: Mapping[str, Any],
    revision_note: str | None = None,
    omit_first_citation: bool = False,
) -> dict[str, Any]:
    """Run three sequential, explicit Task contracts."""

    research = run_researcher_task(topic, catalog)
    draft = run_writer_task(research, revision_note, omit_first_citation)
    review = run_reviewer_task(research, draft, catalog)
    return {"research": research, "draft": draft, "review": review}


def validate_state(state: Any) -> None:
    if not isinstance(state, dict):
        raise FlowError("Flow state 必须是对象")
    require_exact_keys(
        state,
        {
            "schema_version",
            "run_id",
            "topic",
            "catalog_fingerprint",
            "stage",
            "attempt",
            "max_attempts",
            "events",
            "result",
            "publication",
        },
        "Flow state",
    )
    if state["schema_version"] != FLOW_SCHEMA_VERSION:
        raise FlowError("Flow state schema_version 不受支持")
    require_nonempty_text(state["run_id"], "state.run_id", 80)
    require_nonempty_text(state["topic"], "state.topic", 120)
    if not isinstance(state["catalog_fingerprint"], str) or len(state["catalog_fingerprint"]) != 64:
        raise FlowError("state.catalog_fingerprint 非法")
    if state["stage"] not in {
        "started",
        "revising",
        "ready_to_publish",
        "published",
        "human_review",
    }:
        raise FlowError("state.stage 非法")
    for field in ("attempt", "max_attempts"):
        if isinstance(state[field], bool) or not isinstance(state[field], int):
            raise FlowError(f"state.{field} 必须是整数")
    if not 0 <= state["attempt"] <= state["max_attempts"] or state["max_attempts"] < 1:
        raise FlowError("Flow attempt 预算非法")
    if not isinstance(state["events"], list):
        raise FlowError("state.events 必须是数组")
    for sequence, event in enumerate(state["events"], start=1):
        if not isinstance(event, dict):
            raise FlowError("event 必须是对象")
        require_exact_keys(event, {"sequence", "type", "payload"}, "event")
        if event["sequence"] != sequence:
            raise FlowError("event.sequence 必须连续")
        require_nonempty_text(event["type"], "event.type", 80)
        if not isinstance(event["payload"], dict):
            raise FlowError("event.payload 必须是对象")
    if state["result"] is not None:
        if not isinstance(state["result"], dict):
            raise FlowError("state.result 必须是对象或 null")
        require_exact_keys(state["result"], {"research", "draft", "review"}, "state.result")
        validate_draft(state["result"]["draft"])
        validate_review(state["result"]["review"])
    if state["stage"] in TERMINAL_STAGES and state["result"] is None:
        raise FlowError("终态必须包含最后一次 Crew 结果")
    if state["stage"] == "published":
        if not isinstance(state["publication"], dict):
            raise FlowError("published 终态必须包含 publication")
        require_exact_keys(state["publication"], {"path", "content_fingerprint", "recovered"}, "publication")
    elif state["publication"] is not None:
        raise FlowError("只有 published 终态可以包含 publication")


def run_flow(
    topic: str,
    catalog: Mapping[str, Any],
    force_revision: bool = False,
    force_failure: bool = False,
    max_attempts: int = 2,
) -> dict[str, Any]:
    validate_catalog(catalog)
    topic = require_nonempty_text(topic, "topic", 120)
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise FlowError("max_attempts 必须是正整数")
    catalog_fingerprint = fingerprint(catalog)
    state: dict[str, Any] = {
        "schema_version": FLOW_SCHEMA_VERSION,
        "run_id": f"run-{fingerprint({'topic': topic, 'catalog': catalog_fingerprint})[:16]}",
        "topic": topic,
        "catalog_fingerprint": catalog_fingerprint,
        "stage": "started",
        "attempt": 0,
        "max_attempts": max_attempts,
        "events": [],
        "result": None,
        "publication": None,
    }
    emit(state, "flow_started", topic=topic)
    revision_note: str | None = None

    while state["attempt"] < max_attempts:
        state["attempt"] += 1
        emit(state, "crew_started", attempt=state["attempt"])
        omit_citation = force_failure or (force_revision and state["attempt"] == 1)
        result = run_crew(topic, catalog, revision_note, omit_citation)
        state["result"] = result
        emit(
            state,
            "review_completed",
            attempt=state["attempt"],
            passed=result["review"]["passed"],
        )
        if result["review"]["passed"]:
            state["stage"] = "ready_to_publish"
            emit(state, "routed:ready_to_publish")
            validate_state(state)
            return state
        if state["attempt"] < max_attempts:
            revision_note = "；".join(result["review"]["reasons"])
            state["stage"] = "revising"
            emit(state, "routed:revise", reason=revision_note)

    state["stage"] = "human_review"
    emit(state, "routed:human_review")
    validate_state(state)
    return state


def publish_report(output_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    validate_state(state)
    if state["stage"] != "ready_to_publish":
        raise FlowError("只有 ready_to_publish 状态可以发布")
    content = state["result"]["draft"]["markdown"]
    recovered = False
    if output_path.exists():
        try:
            existing = output_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise FlowError(f"无法读取已有输出：{exc}") from exc
        if existing != content:
            raise FlowError("输出文件已存在且内容不同，拒绝覆盖")
        recovered = True
    else:
        temporary = output_path.with_name(output_path.name + ".tmp")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, output_path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise FlowError(f"无法原子写入输出：{exc}") from exc
    state["publication"] = {
        "path": str(output_path),
        "content_fingerprint": fingerprint(content),
        "recovered": recovered,
    }
    state["stage"] = "published"
    emit(state, "report_recovered" if recovered else "report_published")
    validate_state(state)
    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="Agent 可靠性")
    parser.add_argument(
        "--sources",
        type=Path,
        default=Path(__file__).with_name("sources.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force-revision", action="store_true")
    parser.add_argument("--force-failure", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        catalog = load_catalog(args.sources)
        state = run_flow(
            args.topic,
            catalog,
            force_revision=args.force_revision,
            force_failure=args.force_failure,
        )
        if args.output is not None and state["stage"] == "ready_to_publish":
            state = publish_report(args.output, state)
    except FlowError as exc:
        print(json.dumps({"stage": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if state["stage"] in {"ready_to_publish", "published"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
