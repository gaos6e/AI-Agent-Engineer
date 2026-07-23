"""Offline Crew/Flow teaching project with deterministic task stubs.

The project does not import CrewAI, call a model, or access the network. It
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
        raise FlowError(f"{label} fields do not match; missing={missing}, extra={extra}")


def require_nonempty_text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise FlowError(f"{label} must be a string")
    normalized = value.strip()
    if not normalized:
        raise FlowError(f"{label} must not be empty")
    if len(normalized) > maximum:
        raise FlowError(f"{label} must not exceed {maximum} characters")
    return normalized


def _validate_text_list(value: Any, label: str, maximum_items: int = 50) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum_items:
        raise FlowError(f"{label} must be an array of 1–{maximum_items} strings")
    result = [require_nonempty_text(item, f"{label}[]", 1000) for item in value]
    if len(set(result)) != len(result):
        raise FlowError(f"{label} must not contain duplicates")
    return result


def validate_catalog(catalog: Any) -> None:
    if not isinstance(catalog, dict):
        raise FlowError("source catalog root must be a JSON object")
    require_exact_keys(catalog, {"schema_version", "sources"}, "source catalog")
    if catalog["schema_version"] != CATALOG_SCHEMA_VERSION:
        raise FlowError("source catalog schema_version is unsupported")
    if not isinstance(catalog["sources"], list) or not catalog["sources"]:
        raise FlowError("sources must be a non-empty array")

    identifiers: set[str] = set()
    for index, source in enumerate(catalog["sources"]):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            raise FlowError(f"{label} must be an object")
        require_exact_keys(source, {"id", "title", "topics", "claims"}, label)
        source_id = require_nonempty_text(source["id"], f"{label}.id", 64)
        if not all(
            character.isascii()
            and (character.isalnum() or character in "-_")
            for character in source_id
        ):
            raise FlowError(
                f"{label}.id may contain only ASCII letters, digits, hyphens, and underscores"
            )
        if source_id in identifiers:
            raise FlowError(f"duplicate source ID: {source_id}")
        identifiers.add(source_id)
        require_nonempty_text(source["title"], f"{label}.title", 200)
        _validate_text_list(source["topics"], f"{label}.topics", 20)
        _validate_text_list(source["claims"], f"{label}.claims", 50)


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FlowError(f"unable to read source catalog: {exc}") from exc
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


def validate_research(
    research: Any,
    catalog: Mapping[str, Any] | None = None,
) -> None:
    """Validate a research result, optionally against a trusted source catalog.

    State can be validated structurally after it has been persisted, but source
    identifiers are only meaningful relative to a concrete catalog revision.
    Callers at an external-effect boundary must therefore pass the catalog.
    """

    if not isinstance(research, dict):
        raise FlowError("research Task artifact must be an object")
    require_exact_keys(research, {"topic", "claims", "unknowns"}, "research")
    require_nonempty_text(research["topic"], "research.topic", 120)
    if not isinstance(research["claims"], list):
        raise FlowError("research.claims must be an array")
    known: dict[str, Mapping[str, Any]] | None = None
    if catalog is not None:
        validate_catalog(catalog)
        known = source_index(catalog)
    for index, claim in enumerate(research["claims"]):
        label = f"research.claims[{index}]"
        if not isinstance(claim, dict):
            raise FlowError(f"{label} must be an object")
        require_exact_keys(claim, {"text", "source_ids"}, label)
        require_nonempty_text(claim["text"], f"{label}.text", 1000)
        identifiers = _validate_text_list(claim["source_ids"], f"{label}.source_ids", 10)
        if known is not None:
            unknown = [identifier for identifier in identifiers if identifier not in known]
            if unknown:
                raise FlowError(f"{label} cites unknown sources: {unknown}")
    if not isinstance(research["unknowns"], list):
        raise FlowError("research.unknowns must be an array")
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
    unknowns = [] if claims else [f"The source catalog has no exact match for topic: {topic}"]
    research = {"topic": topic, "claims": claims, "unknowns": unknowns}
    validate_research(research, catalog)
    return research


def validate_draft(draft: Any) -> None:
    if not isinstance(draft, dict):
        raise FlowError("draft Task artifact must be an object")
    require_exact_keys(draft, {"markdown", "claim_count", "revision_note"}, "draft")
    require_nonempty_text(draft["markdown"], "draft.markdown", 20_000)
    if isinstance(draft["claim_count"], bool) or not isinstance(draft["claim_count"], int):
        raise FlowError("draft.claim_count must be an integer")
    if draft["claim_count"] < 0:
        raise FlowError("draft.claim_count must not be negative")
    if draft["revision_note"] is not None:
        require_nonempty_text(draft["revision_note"], "draft.revision_note", 500)


def run_writer_task(
    research: Mapping[str, Any],
    revision_note: str | None = None,
    omit_first_citation: bool = False,
) -> dict[str, Any]:
    """Deterministic stand-in for a writer Agent/Task."""

    lines = [f"# Research Brief: {research['topic']}", "", "## Sourced conclusions"]
    for index, claim in enumerate(research["claims"]):
        citations = "" if omit_first_citation and index == 0 else " ".join(
            f"[{source_id}]" for source_id in claim["source_ids"]
        )
        lines.append(f"- {claim['text']} {citations}".rstrip())
    if not research["claims"]:
        lines.append("- The current sources do not support a publishable conclusion.")
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in research["unknowns"])
    if not research["unknowns"]:
        lines.append("- The current sample records no unknowns.")
    if revision_note:
        lines.extend(["", "## Revision record", f"- {revision_note}"])
    draft = {
        "markdown": "\n".join(lines) + "\n",
        "claim_count": len(research["claims"]),
        "revision_note": revision_note,
    }
    validate_draft(draft)
    return draft


def validate_review(review: Any) -> None:
    if not isinstance(review, dict):
        raise FlowError("review Task artifact must be an object")
    require_exact_keys(
        review,
        {"passed", "reasons", "missing_citations", "unknown_sources"},
        "review",
    )
    if not isinstance(review["passed"], bool):
        raise FlowError("review.passed must be a boolean")
    for field in ("reasons", "missing_citations", "unknown_sources"):
        if not isinstance(review[field], list):
            raise FlowError(f"review.{field} must be an array")
        for item in review[field]:
            require_nonempty_text(item, f"review.{field}[]", 500)
    if review["passed"] is not (not review["reasons"]):
        raise FlowError("review.passed conflicts with reasons")


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
        reasons.append("no sourced conclusion is publishable")
    if draft["claim_count"] != len(research["claims"]):
        reasons.append("draft.claim_count does not match research.claims")
    if unknown_sources:
        reasons.append("unknown source IDs are present")
    if missing_citations:
        reasons.append("draft is missing citation markers")
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


def validate_state(
    state: Any,
    catalog: Mapping[str, Any] | None = None,
) -> None:
    if not isinstance(state, dict):
        raise FlowError("Flow state must be an object")
    require_exact_keys(
        state,
        {
            "schema_version",
            "operation_id",
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
        raise FlowError("Flow state schema_version is unsupported")
    require_nonempty_text(state["operation_id"], "state.operation_id", 80)
    require_nonempty_text(state["topic"], "state.topic", 120)
    if not isinstance(state["catalog_fingerprint"], str) or len(state["catalog_fingerprint"]) != 64:
        raise FlowError("state.catalog_fingerprint is invalid")
    if catalog is not None:
        validate_catalog(catalog)
        if state["catalog_fingerprint"] != fingerprint(catalog):
            raise FlowError("Flow state does not match the current source catalog version")
    if state["stage"] not in {
        "started",
        "revising",
        "ready_to_publish",
        "published",
        "human_review",
    }:
        raise FlowError("state.stage is invalid")
    for field in ("attempt", "max_attempts"):
        if isinstance(state[field], bool) or not isinstance(state[field], int):
            raise FlowError(f"state.{field} must be an integer")
    if not 0 <= state["attempt"] <= state["max_attempts"] or state["max_attempts"] < 1:
        raise FlowError("Flow attempt budget is invalid")
    if not isinstance(state["events"], list):
        raise FlowError("state.events must be an array")
    for sequence, event in enumerate(state["events"], start=1):
        if not isinstance(event, dict):
            raise FlowError("event must be an object")
        require_exact_keys(event, {"sequence", "type", "payload"}, "event")
        if event["sequence"] != sequence:
            raise FlowError("event.sequence must be contiguous")
        require_nonempty_text(event["type"], "event.type", 80)
        if not isinstance(event["payload"], dict):
            raise FlowError("event.payload must be an object")
    if state["result"] is not None:
        if not isinstance(state["result"], dict):
            raise FlowError("state.result must be an object or null")
        require_exact_keys(state["result"], {"research", "draft", "review"}, "state.result")
        validate_research(state["result"]["research"], catalog)
        validate_draft(state["result"]["draft"])
        validate_review(state["result"]["review"])
    if state["stage"] in TERMINAL_STAGES and state["result"] is None:
        raise FlowError("a terminal state must include the final Crew result")
    if state["stage"] == "published":
        if not isinstance(state["publication"], dict):
            raise FlowError("the published terminal state must include publication")
        require_exact_keys(
            state["publication"],
            {"path", "content_fingerprint", "recovered"},
            "publication",
        )
    elif state["publication"] is not None:
        raise FlowError("only the published terminal state may include publication")


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
        raise FlowError("max_attempts must be a positive integer")
    catalog_fingerprint = fingerprint(catalog)
    state: dict[str, Any] = {
        "schema_version": FLOW_SCHEMA_VERSION,
        "operation_id": f"operation-{fingerprint({'topic': topic, 'catalog': catalog_fingerprint})[:16]}",
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
            validate_state(state, catalog)
            return state
        if state["attempt"] < max_attempts:
            revision_note = "; ".join(result["review"]["reasons"])
            state["stage"] = "revising"
            emit(state, "routed:revise", reason=revision_note)

    state["stage"] = "human_review"
    emit(state, "routed:human_review")
    validate_state(state, catalog)
    return state


def validate_publication_contract(
    state: dict[str, Any],
    catalog: Mapping[str, Any],
) -> None:
    """Recheck trusted evidence immediately before the local side effect."""

    validate_state(state, catalog)
    if state["stage"] != "ready_to_publish":
        raise FlowError("only ready_to_publish state may be published")
    trusted_review = run_reviewer_task(
        state["result"]["research"],
        state["result"]["draft"],
        catalog,
    )
    if trusted_review != state["result"]["review"]:
        raise FlowError("state.review does not match the recomputed trusted reviewer result")
    if not trusted_review["passed"]:
        raise FlowError("the trusted reviewer did not pass; publication refused")


def publish_report(
    output_path: Path,
    state: dict[str, Any],
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish only after a same-catalog, deterministic pre-write recheck."""

    validate_publication_contract(state, catalog)
    content = state["result"]["draft"]["markdown"]
    recovered = False
    if output_path.exists():
        try:
            existing = output_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise FlowError(f"unable to read existing output: {exc}") from exc
        if existing != content:
            raise FlowError("output exists with different content; refusing overwrite")
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
            raise FlowError(f"unable to write output atomically: {exc}") from exc
    state["publication"] = {
        "path": str(output_path),
        "content_fingerprint": fingerprint(content),
        "recovered": recovered,
    }
    state["stage"] = "published"
    emit(state, "report_recovered" if recovered else "report_published")
    validate_state(state, catalog)
    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="Agent reliability")
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
            state = publish_report(args.output, state, catalog)
    except FlowError as exc:
        print(json.dumps({"stage": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if state["stage"] in {"ready_to_publish", "published"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
