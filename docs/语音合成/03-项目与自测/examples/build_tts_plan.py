"""Build and validate a synthetic TTS plan without generating audio."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SSML_NAMESPACE = "http://www.w3.org/2001/10/synthesis"
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
LOCALE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
TOP_FIELDS = {"schema_version", "policy", "requests"}
POLICY_FIELDS = {
    "max_characters",
    "allowed_voices",
    "allowed_rates",
    "allowed_emphasis",
}
REQUEST_FIELDS = {
    "request_id",
    "locale",
    "voice_id",
    "source_text",
    "rate",
    "emphasis",
    "purpose",
    "authorization_reference",
}
ET.register_namespace("", SSML_NAMESPACE)


class FixtureError(ValueError):
    """Raised when an input fixture violates the structural contract."""


def qname(local_name: str) -> str:
    return f"{{{SSML_NAMESPACE}}}{local_name}"


def _reject_constant(value: str) -> None:
    raise FixtureError(f"non-finite JSON number is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_fields(
    value: Any, required: set[str], *, context: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{context} must be an object")
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing:
        raise FixtureError(f"{context} missing fields: {', '.join(missing)}")
    if unknown:
        raise FixtureError(f"{context} has unknown fields: {', '.join(unknown)}")
    return value


def _validate_string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise FixtureError(f"{context} must be a non-empty array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise FixtureError(f"{context} items must be non-empty strings")
    if len(value) != len(set(value)):
        raise FixtureError(f"{context} items must be unique")
    return value


def validate_fixture(payload: Any) -> dict[str, Any]:
    """Validate schema and types; allowlist findings are evaluated separately."""
    root = _require_exact_fields(payload, TOP_FIELDS, context="fixture")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version must be '1.0'")
    policy = _require_exact_fields(root["policy"], POLICY_FIELDS, context="policy")
    max_characters = policy["max_characters"]
    if (
        not isinstance(max_characters, int)
        or isinstance(max_characters, bool)
        or max_characters <= 0
    ):
        raise FixtureError("policy.max_characters must be a positive integer")
    _validate_string_list(policy["allowed_voices"], context="policy.allowed_voices")
    _validate_string_list(policy["allowed_rates"], context="policy.allowed_rates")
    _validate_string_list(
        policy["allowed_emphasis"], context="policy.allowed_emphasis"
    )

    requests = root["requests"]
    if not isinstance(requests, list) or not requests:
        raise FixtureError("requests must be a non-empty array")
    for index, raw_request in enumerate(requests):
        context = f"requests[{index}]"
        request = _require_exact_fields(raw_request, REQUEST_FIELDS, context=context)
        for field in REQUEST_FIELDS:
            value = request[field]
            if not isinstance(value, str) or not value.strip():
                raise FixtureError(f"{context}.{field} must be a non-empty string")
        if not LOCALE_PATTERN.fullmatch(request["locale"]):
            raise FixtureError(
                f"{context}.locale must match the documented BCP 47 teaching subset"
            )
    return root


def load_fixture(path: Path) -> dict[str, Any]:
    """Load UTF-8 strict JSON and validate its complete structural contract."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"cannot read fixture: {exc}") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    return validate_fixture(payload)


def build_ssml(request: dict[str, Any]) -> str:
    """Build a portable teaching subset of SSML from controlled fields."""
    speak = ET.Element(
        qname("speak"),
        {
            "version": "1.1",
            f"{{{XML_NAMESPACE}}}lang": request["locale"],
        },
    )
    voice = ET.SubElement(speak, qname("voice"), {"name": request["voice_id"]})
    sentence = ET.SubElement(voice, qname("s"))
    content_parent = sentence
    if request["rate"] != "medium":
        content_parent = ET.SubElement(
            content_parent, qname("prosody"), {"rate": request["rate"]}
        )
    if request["emphasis"] != "none":
        content_parent = ET.SubElement(
            content_parent, qname("emphasis"), {"level": request["emphasis"]}
        )
    content_parent.text = request["source_text"]
    return ET.tostring(speak, encoding="utf-8", xml_declaration=True).decode("utf-8")


def validate_generated_ssml(ssml: str) -> list[str]:
    """Validate the exact SSML subset emitted by this teaching project."""
    try:
        root = ET.fromstring(ssml)
    except ET.ParseError as exc:
        return [f"invalid XML: {exc}"]
    errors: list[str] = []
    allowed_attributes = {
        qname("speak"): {"version", f"{{{XML_NAMESPACE}}}lang"},
        qname("voice"): {"name"},
        qname("s"): set(),
        qname("prosody"): {"rate"},
        qname("emphasis"): {"level"},
    }
    if root.tag != qname("speak"):
        errors.append("root element must be SSML speak")
    for element in root.iter():
        if element.tag not in allowed_attributes:
            errors.append(f"unsupported generated tag: {element.tag}")
            continue
        unknown = sorted(set(element.attrib) - allowed_attributes[element.tag])
        if unknown:
            errors.append(f"unsupported attributes on {element.tag}: {', '.join(unknown)}")
    if root.attrib.get("version") != "1.1":
        errors.append("speak version must be 1.1")
    if not root.attrib.get(f"{{{XML_NAMESPACE}}}lang"):
        errors.append("speak xml:lang is required")
    voices = list(root)
    if len(voices) != 1 or voices[0].tag != qname("voice"):
        errors.append("speak must contain exactly one voice")
    return errors


def build_plan(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Build auditable plans; this function never calls a TTS engine."""
    validate_fixture(payload)
    errors: list[str] = []
    plans: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    policy = payload["policy"]
    allowed_voices = set(policy["allowed_voices"])
    allowed_rates = set(policy["allowed_rates"])
    allowed_emphasis = set(policy["allowed_emphasis"])

    for request in payload["requests"]:
        request_id = request["request_id"]
        item_errors: list[str] = []
        if request_id in seen_ids:
            item_errors.append(f"duplicate request_id: {request_id}")
        seen_ids.add(request_id)
        if request["voice_id"] not in allowed_voices:
            item_errors.append(f"{request_id}: voice_id is not allowed")
        if request["rate"] not in allowed_rates:
            item_errors.append(f"{request_id}: rate is not allowed")
        if request["emphasis"] not in allowed_emphasis:
            item_errors.append(f"{request_id}: emphasis is not allowed")
        if len(request["source_text"]) > policy["max_characters"]:
            item_errors.append(f"{request_id}: source_text exceeds max_characters")

        ssml = build_ssml(request)
        item_errors.extend(
            f"{request_id}: {message}" for message in validate_generated_ssml(ssml)
        )
        errors.extend(item_errors)
        plans.append(
            {
                "request_id": request_id,
                "locale": request["locale"],
                "voice_id": request["voice_id"],
                "purpose": request["purpose"],
                "authorization_reference": request["authorization_reference"],
                "source_text_sha256": hashlib.sha256(
                    request["source_text"].encode("utf-8")
                ).hexdigest(),
                "ssml": ssml,
                "generation_status": "not_generated",
                "plan_valid": not item_errors,
            }
        )

    return {
        "plan_schema_version": "1.0",
        "source_schema_version": payload["schema_version"],
        "items": plans,
        "audio_generated": False,
        "notes": [
            "synthetic plan and portable SSML subset only",
            "no audio, network, external resource, model, or TTS service was used",
        ],
    }, errors


def run_self_test() -> None:
    """Run checks that remain active under Python optimization."""
    request = {
        "locale": "zh-CN",
        "voice_id": "demo",
        "source_text": "A&B <测试>",
        "rate": "medium",
        "emphasis": "none",
    }
    ssml = build_ssml(request)
    if "&amp;" not in ssml or "&lt;" not in ssml:
        raise RuntimeError("SSML escaping self-test failed")
    if validate_generated_ssml(ssml):
        raise RuntimeError("SSML validation self-test failed")
    root = ET.fromstring(ssml)
    if "".join(root.itertext()) != request["source_text"]:
        raise RuntimeError("SSML text round-trip self-test failed")
    print("self-test: PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", type=Path, help="UTF-8 JSON fixture")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    if args.fixture is None:
        print("fixture is required unless --self-test is used", file=sys.stderr)
        return 2
    try:
        plan, errors = build_plan(load_fixture(args.fixture))
    except FixtureError as exc:
        print(f"fixture error: {exc}", file=sys.stderr)
        return 2
    report = {"plan": plan, "errors": errors}
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
