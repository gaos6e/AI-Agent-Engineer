"""Deterministic, offline security review for a small tool-using agent."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_SCENARIO = HERE / "agent_scenario_vulnerable.json"
HARDENED_SCENARIO = HERE / "agent_scenario_hardened.json"
CONTRACT_ERROR_SCENARIO = HERE / "agent_scenario_contract_error.json"

TOP_FIELDS = {
    "schema_version",
    "scenario_id",
    "purpose",
    "non_goals",
    "assets",
    "trust_boundaries",
    "untrusted_sources",
    "identities",
    "tools",
    "dependencies",
    "controls",
    "risk_policy",
}
ASSET_FIELDS = {"id", "classification"}
BOUNDARY_FIELDS = {"id", "from", "to", "data_assets"}
SOURCE_FIELDS = {"id", "type", "trust_level"}
IDENTITY_FIELDS = {"id", "shared", "ttl_minutes", "scopes"}
TOOL_FIELDS = {
    "name",
    "mode",
    "destination",
    "side_effect",
    "required_for_purpose",
    "required_scopes",
}
DEPENDENCY_FIELDS = {"name", "version", "pinned", "provenance_verified"}
CONTROL_FIELDS = {
    "treat_external_content_as_data",
    "tool_allowlist",
    "destination_allowlist",
    "approval",
    "sandbox",
    "output_validation",
    "data_egress_validation",
    "memory_write_validation",
    "audit_logging",
    "rate_limit",
    "emergency_disable",
}
APPROVAL_FIELDS = {"required_for_tools", "binds_parameters", "expires_minutes"}
SANDBOX_FIELDS = {"enabled", "network_default_deny"}
POLICY_FIELDS = {"block_severities", "review_severities"}

CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
TRUST_LEVELS = {"trusted", "conditional", "untrusted"}
TOOL_MODES = {"read", "write", "execute"}
DESTINATIONS = {"local", "internal", "external"}
SEVERITIES = {"low", "medium", "high", "critical"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class ContractError(ValueError):
    """Raised when a scenario violates the review input contract."""


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-standard JSON constant is forbidden: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in {path}: {exc.msg}") from exc


def _exact(value: Any, expected: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{location} must be an object")
    actual = set(value)
    if actual != expected:
        raise ContractError(
            f"{location} fields mismatch; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{location} must be a non-empty string")
    return value


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{location} must be a boolean")
    return value


def _integer(value: Any, location: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractError(f"{location} must be an integer >= {minimum}")
    return value


def _strings(value: Any, location: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        suffix = "" if allow_empty else " and non-empty"
        raise ContractError(f"{location} must be a list{suffix}")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_text(item, f"{location}[{index}]"))
    if len(result) != len(set(result)):
        raise ContractError(f"{location} must not contain duplicates")
    return result


def _object_list(
    value: Any, fields: set[str], location: str, allow_empty: bool = False
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not value and not allow_empty):
        suffix = "" if allow_empty else " and non-empty"
        raise ContractError(f"{location} must be a list{suffix}")
    return [_exact(item, fields, f"{location}[{index}]") for index, item in enumerate(value)]


def _unique(items: Iterable[str], location: str) -> None:
    values = list(items)
    if len(values) != len(set(values)):
        raise ContractError(f"{location} identifiers must be unique")


def validate_scenario(raw: Any) -> dict[str, Any]:
    scenario = _exact(raw, TOP_FIELDS, "scenario")
    _text(scenario["schema_version"], "scenario.schema_version")
    _text(scenario["scenario_id"], "scenario.scenario_id")
    _text(scenario["purpose"], "scenario.purpose")
    _strings(scenario["non_goals"], "scenario.non_goals")

    assets = _object_list(scenario["assets"], ASSET_FIELDS, "scenario.assets")
    for index, asset in enumerate(assets):
        _text(asset["id"], f"scenario.assets[{index}].id")
        if asset["classification"] not in CLASSIFICATIONS:
            raise ContractError(f"scenario.assets[{index}].classification is invalid")
    _unique((item["id"] for item in assets), "asset")
    asset_ids = {item["id"] for item in assets}

    boundaries = _object_list(
        scenario["trust_boundaries"], BOUNDARY_FIELDS, "scenario.trust_boundaries"
    )
    for index, boundary in enumerate(boundaries):
        for key in ("id", "from", "to"):
            _text(boundary[key], f"scenario.trust_boundaries[{index}].{key}")
        data_assets = _strings(
            boundary["data_assets"],
            f"scenario.trust_boundaries[{index}].data_assets",
        )
        unknown_assets = sorted(set(data_assets) - asset_ids)
        if unknown_assets:
            raise ContractError(
                f"scenario.trust_boundaries[{index}] references unknown assets: {unknown_assets}"
            )
    _unique((item["id"] for item in boundaries), "trust boundary")

    sources = _object_list(
        scenario["untrusted_sources"], SOURCE_FIELDS, "scenario.untrusted_sources"
    )
    for index, source in enumerate(sources):
        _text(source["id"], f"scenario.untrusted_sources[{index}].id")
        _text(source["type"], f"scenario.untrusted_sources[{index}].type")
        if source["trust_level"] not in TRUST_LEVELS:
            raise ContractError(f"scenario.untrusted_sources[{index}].trust_level is invalid")
    _unique((item["id"] for item in sources), "source")

    identities = _object_list(
        scenario["identities"], IDENTITY_FIELDS, "scenario.identities"
    )
    for index, identity in enumerate(identities):
        _text(identity["id"], f"scenario.identities[{index}].id")
        _boolean(identity["shared"], f"scenario.identities[{index}].shared")
        _integer(identity["ttl_minutes"], f"scenario.identities[{index}].ttl_minutes", 1)
        _strings(identity["scopes"], f"scenario.identities[{index}].scopes")
    _unique((item["id"] for item in identities), "identity")
    available_scopes = {
        scope for identity in identities for scope in identity["scopes"]
    }

    tools = _object_list(scenario["tools"], TOOL_FIELDS, "scenario.tools")
    for index, tool in enumerate(tools):
        _text(tool["name"], f"scenario.tools[{index}].name")
        if tool["mode"] not in TOOL_MODES:
            raise ContractError(f"scenario.tools[{index}].mode is invalid")
        if tool["destination"] not in DESTINATIONS:
            raise ContractError(f"scenario.tools[{index}].destination is invalid")
        _boolean(tool["side_effect"], f"scenario.tools[{index}].side_effect")
        _boolean(
            tool["required_for_purpose"],
            f"scenario.tools[{index}].required_for_purpose",
        )
        required_scopes = _strings(
            tool["required_scopes"],
            f"scenario.tools[{index}].required_scopes",
        )
        missing_scopes = sorted(set(required_scopes) - available_scopes)
        if missing_scopes:
            raise ContractError(
                f"scenario.tools[{index}] has unavailable scopes: {missing_scopes}"
            )
    _unique((item["name"] for item in tools), "tool")
    tool_names = {item["name"] for item in tools}

    dependencies = _object_list(
        scenario["dependencies"], DEPENDENCY_FIELDS, "scenario.dependencies"
    )
    for index, dependency in enumerate(dependencies):
        _text(dependency["name"], f"scenario.dependencies[{index}].name")
        _text(dependency["version"], f"scenario.dependencies[{index}].version")
        _boolean(dependency["pinned"], f"scenario.dependencies[{index}].pinned")
        _boolean(
            dependency["provenance_verified"],
            f"scenario.dependencies[{index}].provenance_verified",
        )
    _unique((item["name"] for item in dependencies), "dependency")

    controls = _exact(scenario["controls"], CONTROL_FIELDS, "scenario.controls")
    for key in (
        "treat_external_content_as_data",
        "output_validation",
        "data_egress_validation",
        "memory_write_validation",
        "audit_logging",
        "rate_limit",
        "emergency_disable",
    ):
        _boolean(controls[key], f"scenario.controls.{key}")
    tool_allowlist = _strings(
        controls["tool_allowlist"], "scenario.controls.tool_allowlist", allow_empty=True
    )
    unknown_tools = sorted(set(tool_allowlist) - tool_names)
    if unknown_tools:
        raise ContractError(f"tool_allowlist references unknown tools: {unknown_tools}")
    destinations = _strings(
        controls["destination_allowlist"],
        "scenario.controls.destination_allowlist",
        allow_empty=True,
    )
    invalid_destinations = sorted(set(destinations) - DESTINATIONS)
    if invalid_destinations:
        raise ContractError(f"destination_allowlist has invalid values: {invalid_destinations}")

    approval = _exact(controls["approval"], APPROVAL_FIELDS, "scenario.controls.approval")
    approval_tools = _strings(
        approval["required_for_tools"],
        "scenario.controls.approval.required_for_tools",
        allow_empty=True,
    )
    unknown_approval_tools = sorted(set(approval_tools) - tool_names)
    if unknown_approval_tools:
        raise ContractError(
            f"approval references unknown tools: {unknown_approval_tools}"
        )
    _boolean(approval["binds_parameters"], "scenario.controls.approval.binds_parameters")
    _integer(approval["expires_minutes"], "scenario.controls.approval.expires_minutes", 1)

    sandbox = _exact(controls["sandbox"], SANDBOX_FIELDS, "scenario.controls.sandbox")
    _boolean(sandbox["enabled"], "scenario.controls.sandbox.enabled")
    _boolean(
        sandbox["network_default_deny"],
        "scenario.controls.sandbox.network_default_deny",
    )

    policy = _exact(scenario["risk_policy"], POLICY_FIELDS, "scenario.risk_policy")
    block = set(_strings(policy["block_severities"], "scenario.risk_policy.block_severities"))
    review = set(_strings(policy["review_severities"], "scenario.risk_policy.review_severities", allow_empty=True))
    invalid_severities = sorted((block | review) - SEVERITIES)
    if invalid_severities:
        raise ContractError(f"risk policy has invalid severities: {invalid_severities}")
    overlap = sorted(block & review)
    if overlap:
        raise ContractError(f"risk policy severities overlap: {overlap}")
    return copy.deepcopy(scenario)


def finding(
    identifier: str,
    title: str,
    severity: str,
    asset: str,
    attack_path: list[str],
    impact: str,
    controls: list[str],
    verification: list[str],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title,
        "severity": severity,
        "asset": asset,
        "attack_path": attack_path,
        "impact": impact,
        "recommended_controls": controls,
        "owner": "system-owner",
        "verification": verification,
    }


def review(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    controls = scenario["controls"]
    tools_by_name = {tool["name"]: tool for tool in scenario["tools"]}
    allowed_tools = [tools_by_name[name] for name in controls["tool_allowlist"]]
    untrusted = [
        source for source in scenario["untrusted_sources"] if source["trust_level"] == "untrusted"
    ]
    external_side_effects = [
        tool
        for tool in allowed_tools
        if tool["destination"] == "external" and tool["side_effect"]
    ]
    sensitive_assets = [
        asset
        for asset in scenario["assets"]
        if asset["classification"] in {"confidential", "restricted"}
    ]

    if untrusted and external_side_effects and not controls["treat_external_content_as_data"]:
        findings.append(
            finding(
                "AS-001",
                "Indirect prompt injection can reach a side-effecting tool",
                "critical",
                sensitive_assets[0]["id"] if sensitive_assets else scenario["assets"][0]["id"],
                ["untrusted content", "model context", "tool selection", "external side effect"],
                "attacker-controlled content can redirect the agent and cause unauthorized action or disclosure",
                [
                    "treat retrieved content as data rather than authority",
                    "remove unnecessary side-effecting tools",
                    "enforce authorization and destination policy outside the model",
                ],
                ["indirect-injection negative tests", "tool trace assertions"],
            )
        )

    unnecessary = [tool["name"] for tool in allowed_tools if not tool["required_for_purpose"]]
    if unnecessary:
        findings.append(
            finding(
                "AS-002",
                "Tool allowlist contains functionality not required for the purpose",
                "high",
                "agent-capability-boundary",
                ["agent session", f"unnecessary tools: {', '.join(unnecessary)}"],
                "model error or manipulation gains avoidable capability",
                ["remove unnecessary tools", "separate read and write services"],
                ["allowlist unit test", "purpose-to-capability review"],
            )
        )

    required_scopes = {
        scope
        for tool in allowed_tools
        if tool["required_for_purpose"]
        for scope in tool["required_scopes"]
    }
    for identity in scenario["identities"]:
        excess = sorted(set(identity["scopes"]) - required_scopes)
        if identity["shared"] or excess or identity["ttl_minutes"] > 60:
            findings.append(
                finding(
                    "AS-003",
                    "Identity is shared, long-lived, or broader than the required purpose",
                    "high",
                    "agent-identity",
                    ["agent run", identity["id"], f"scopes: {', '.join(identity['scopes'])}"],
                    "a compromised run inherits authority outside the intended task",
                    ["use per-user short-lived identity", "issue the minimum scopes at execution time"],
                    ["scope-diff test", "expired-token negative test", "audit subject assertion"],
                )
            )
            break

    approval = controls["approval"]
    missing_approval = [
        tool["name"]
        for tool in allowed_tools
        if tool["side_effect"] and tool["name"] not in approval["required_for_tools"]
    ]
    weak_approval = bool(external_side_effects) and (
        not approval["binds_parameters"] or approval["expires_minutes"] > 15
    )
    if missing_approval or weak_approval:
        findings.append(
            finding(
                "AS-004",
                "High-impact action lacks a fresh parameter-bound approval",
                "high",
                "external-action",
                ["model proposal", "stale or missing approval", "tool execution"],
                "the executed destination or parameters can differ from what the user approved",
                ["bind approval to normalized parameters and state version", "expire approval quickly"],
                ["approval replay test", "parameter-swap negative test"],
            )
        )

    if any(tool["destination"] not in controls["destination_allowlist"] for tool in external_side_effects):
        findings.append(
            finding(
                "AS-005",
                "External destination is not constrained by policy",
                "high",
                "data-egress-boundary",
                ["sensitive context", "external tool", "attacker-selected destination"],
                "confidential data can leave the authorized boundary",
                ["destination allowlist", "tenant-aware egress policy", "deny by default"],
                ["blocked-destination test", "cross-tenant negative test"],
            )
        )

    if sensitive_assets and external_side_effects and not controls["data_egress_validation"]:
        findings.append(
            finding(
                "AS-006",
                "Sensitive data can flow to an external tool without egress validation",
                "critical",
                sensitive_assets[0]["id"],
                ["restricted asset", "model-generated parameters", "external connector"],
                "private or restricted content can be disclosed",
                ["data classification enforcement", "field-level minimization", "egress validation"],
                ["canary-data exfiltration test", "redacted-field assertion"],
            )
        )

    weak_dependencies = [
        dependency["name"]
        for dependency in scenario["dependencies"]
        if not dependency["pinned"] or not dependency["provenance_verified"]
    ]
    if weak_dependencies:
        findings.append(
            finding(
                "AS-007",
                "Dependency or agent component is not pinned and provenance-verified",
                "medium",
                "software-supply-chain",
                ["build input", f"unverified dependency: {', '.join(weak_dependencies)}", "agent runtime"],
                "an unreviewed component can change tool or policy behavior",
                ["pin immutable versions", "verify source and signatures where available", "retain rollback artifact"],
                ["lockfile drift check", "provenance verification", "rebuild comparison"],
            )
        )

    if allowed_tools and (
        not controls["sandbox"]["enabled"]
        or not controls["sandbox"]["network_default_deny"]
    ):
        findings.append(
            finding(
                "AS-008",
                "Tool runner is not isolated with default-deny networking",
                "medium",
                "runtime-host",
                ["tool invocation", "unrestricted runner", "host or network"],
                "tool misuse can reach resources outside the task boundary",
                ["ephemeral sandbox", "filesystem allowlist", "network default deny", "resource limits"],
                ["sandbox escape test", "blocked-network test", "resource exhaustion test"],
            )
        )

    if allowed_tools and not controls["output_validation"]:
        findings.append(
            finding(
                "AS-009",
                "Model output reaches tools without typed validation",
                "high" if any(tool["side_effect"] for tool in allowed_tools) else "medium",
                "tool-parameter-integrity",
                ["model output", "unvalidated parameters", "tool adapter"],
                "malformed or attacker-shaped values can cross an interpreter boundary",
                ["strict schema", "server-side authorization", "context-appropriate escaping"],
                ["unknown-field test", "command-injection negative test", "schema fuzzing"],
            )
        )

    if untrusted and not controls["memory_write_validation"]:
        findings.append(
            finding(
                "AS-010",
                "Untrusted content can persist into memory or retrieval context",
                "high",
                "agent-memory",
                ["untrusted content", "memory write", "future session context"],
                "malicious instructions or false facts can persist and affect later users",
                ["separate observations from instructions", "validate and scope memory writes", "support deletion"],
                ["cross-session poisoning test", "tenant-isolation test", "memory deletion test"],
            )
        )

    missing_operations = [
        name
        for name in ("audit_logging", "rate_limit", "emergency_disable")
        if not controls[name]
    ]
    if missing_operations:
        findings.append(
            finding(
                "AS-011",
                "Detection, containment, or emergency controls are incomplete",
                "medium",
                "operational-control-plane",
                ["security event", f"missing controls: {', '.join(missing_operations)}", "delayed response"],
                "abuse can continue without sufficient evidence or rapid containment",
                ["tamper-evident audit events", "rate limits", "tested emergency disable and rollback"],
                ["alert drill", "kill-switch exercise", "evidence completeness check"],
            )
        )
    return sorted(findings, key=lambda item: (SEVERITY_ORDER[item["severity"]], item["id"]))


def fingerprint(scenario: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {"scenario": scenario, "findings": findings},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def decision(scenario: dict[str, Any], findings: list[dict[str, Any]]) -> tuple[str, list[str]]:
    policy = scenario["risk_policy"]
    block = set(policy["block_severities"])
    review_severities = set(policy["review_severities"])
    block_findings = [item for item in findings if item["severity"] in block]
    review_findings = [item for item in findings if item["severity"] in review_severities]
    if block_findings:
        return "BLOCK", [
            "blocking findings: " + ", ".join(item["id"] for item in block_findings)
        ]
    if review_findings:
        return "REVIEW", [
            "review findings: " + ", ".join(item["id"] for item in review_findings)
        ]
    return "PASS", ["no finding crossed the frozen teaching policy"]


def build_report(scenario: dict[str, Any]) -> dict[str, Any]:
    findings = review(scenario)
    action, reasons = decision(scenario, findings)
    return {
        "action": action,
        "reasons": reasons,
        "scenario_id": scenario["scenario_id"],
        "purpose": scenario["purpose"],
        "risk_counts": dict(sorted(Counter(item["severity"] for item in findings).items())),
        "finding_count": len(findings),
        "findings": findings,
        "evidence_fingerprint": fingerprint(scenario, findings),
        "limitations": [
            "Deterministic teaching rules are not a penetration test.",
            "No model, connector, identity provider, sandbox, or network was executed.",
            "A PASS result only means this small declared contract triggered no teaching rule.",
            "The report is not a legal, compliance, or risk-acceptance opinion.",
        ],
    }


def run_from_path(path: Path) -> dict[str, Any]:
    return build_report(validate_scenario(load_json(path)))


def self_test() -> None:
    vulnerable = run_from_path(DEFAULT_SCENARIO)
    hardened = run_from_path(HARDENED_SCENARIO)
    failures: list[str] = []
    expected_ids = {
        "AS-001",
        "AS-002",
        "AS-003",
        "AS-004",
        "AS-005",
        "AS-006",
        "AS-007",
        "AS-008",
        "AS-009",
        "AS-010",
        "AS-011",
    }
    if vulnerable["action"] != "BLOCK":
        failures.append("vulnerable scenario did not BLOCK")
    if {item["id"] for item in vulnerable["findings"]} != expected_ids:
        failures.append("vulnerable findings changed")
    if hardened["action"] != "PASS" or hardened["finding_count"] != 0:
        failures.append("hardened scenario did not PASS cleanly")
    if failures:
        raise ContractError("self-test failed: " + "; ".join(failures))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"self_test": "passed"}, ensure_ascii=False))
            return 0
        report = run_from_path(args.scenario)
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["action"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
