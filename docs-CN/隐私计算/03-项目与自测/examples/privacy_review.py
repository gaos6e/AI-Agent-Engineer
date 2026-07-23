"""Deterministic offline privacy-design review over declared synthetic metadata."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_SCENARIO = HERE / "privacy_scenario_vulnerable.json"
HARDENED_SCENARIO = HERE / "privacy_scenario_hardened.json"
CONTRACT_ERROR_SCENARIO = HERE / "privacy_scenario_contract_error.json"

TOP_FIELDS = {
    "schema_version", "scenario_id", "purpose", "non_goals", "subject_scope",
    "data_fields", "participants", "data_flows", "processing", "release",
    "retention", "controls", "threat_model", "risk_policy",
}
DATA_FIELD_FIELDS = {"name", "privacy_class", "output_role", "necessary", "contribution_bound"}
PARTICIPANT_FIELDS = {"id", "role", "trusted"}
FLOW_FIELDS = {"id", "from", "to", "fields", "protection"}
PROCESSING_FIELDS = {
    "task_type", "local_training", "secure_aggregation", "mpc", "homomorphic_encryption",
    "tee", "protocol_participants", "protocol_security", "protocol_evidence",
}
RELEASE_FIELDS = {
    "public", "minimum_group_size", "adjacency", "epsilon_limit", "delta_limit",
    "mechanisms", "outputs",
}
ADJACENCY_FIELDS = {"unit", "relation", "time_window", "contribution_bounds_enforced"}
MECHANISM_FIELDS = {"id", "mechanism", "epsilon", "delta", "approved"}
OUTPUT_FIELDS = {"id", "fields", "transformation", "public"}
RETENTION_FIELDS = {"days", "deletion_verified", "backups_in_scope"}
CONTROL_FIELDS = {
    "access_control", "purpose_enforcement", "output_review", "budget_ledger",
    "provenance", "incident_plan", "linkage_evaluation", "update_validation",
}
THREAT_FIELDS = {
    "honest_but_curious_server", "collusion_threshold", "malicious_clients",
    "final_output_inference",
}
POLICY_FIELDS = {"block_severities", "review_severities"}

PRIVACY_CLASSES = {"direct_identifier", "quasi_identifier", "sensitive_attribute", "non_sensitive"}
OUTPUT_ROLES = {"dimension", "measure", "linkage_key", "not_released"}
ROLES = {"data_holder", "compute_service", "publisher", "auditor"}
FLOW_PROTECTIONS = {"raw", "locally_aggregated", "mpc_share", "he_ciphertext", "tee_input", "federated_update", "secure_update"}
OUTPUT_TRANSFORMATIONS = {"aggregate", "dp_aggregate", "record_level", "model"}
TASK_TYPES = {"aggregate_statistics", "federated_training_and_statistics"}
PROTOCOL_SECURITY = {"none", "semi_honest", "malicious"}
SEVERITIES = {"low", "medium", "high", "critical"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class ContractError(ValueError):
    """Raised when an input violates the declared review contract."""


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


def _decimal(value: Any, location: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str):
        raise ContractError(f"{location} must be a decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError(f"{location} must be a valid decimal string") from exc
    if not number.is_finite() or number < 0 or (positive and number == 0):
        qualifier = "positive and finite" if positive else "non-negative and finite"
        raise ContractError(f"{location} must be {qualifier}")
    return number


def _strings(value: Any, location: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " and non-empty"
        raise ContractError(f"{location} must be a list{qualifier}")
    result = [_text(item, f"{location}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ContractError(f"{location} must not contain duplicates")
    return result


def _objects(
    value: Any, fields: set[str], location: str, *, allow_empty: bool = False
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " and non-empty"
        raise ContractError(f"{location} must be a list{qualifier}")
    return [_exact(item, fields, f"{location}[{index}]") for index, item in enumerate(value)]


def _unique(values: Iterable[str], location: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ContractError(f"{location} identifiers must be unique")


def validate_scenario(raw: Any) -> dict[str, Any]:
    scenario = _exact(raw, TOP_FIELDS, "scenario")
    _text(scenario["schema_version"], "scenario.schema_version")
    _text(scenario["scenario_id"], "scenario.scenario_id")
    _text(scenario["purpose"], "scenario.purpose")
    _strings(scenario["non_goals"], "scenario.non_goals")
    _text(scenario["subject_scope"], "scenario.subject_scope")

    fields = _objects(scenario["data_fields"], DATA_FIELD_FIELDS, "scenario.data_fields")
    for index, field in enumerate(fields):
        _text(field["name"], f"scenario.data_fields[{index}].name")
        if field["privacy_class"] not in PRIVACY_CLASSES:
            raise ContractError(f"scenario.data_fields[{index}].privacy_class is invalid")
        if field["output_role"] not in OUTPUT_ROLES:
            raise ContractError(f"scenario.data_fields[{index}].output_role is invalid")
        _boolean(field["necessary"], f"scenario.data_fields[{index}].necessary")
        _integer(field["contribution_bound"], f"scenario.data_fields[{index}].contribution_bound", 1)
    _unique((field["name"] for field in fields), "data field")
    field_names = {field["name"] for field in fields}

    participants = _objects(
        scenario["participants"], PARTICIPANT_FIELDS, "scenario.participants"
    )
    for index, participant in enumerate(participants):
        _text(participant["id"], f"scenario.participants[{index}].id")
        if participant["role"] not in ROLES:
            raise ContractError(f"scenario.participants[{index}].role is invalid")
        _boolean(participant["trusted"], f"scenario.participants[{index}].trusted")
    _unique((participant["id"] for participant in participants), "participant")
    participant_ids = {participant["id"] for participant in participants}

    flows = _objects(scenario["data_flows"], FLOW_FIELDS, "scenario.data_flows")
    for index, flow in enumerate(flows):
        _text(flow["id"], f"scenario.data_flows[{index}].id")
        for endpoint in ("from", "to"):
            _text(flow[endpoint], f"scenario.data_flows[{index}].{endpoint}")
            if flow[endpoint] not in participant_ids:
                raise ContractError(
                    f"scenario.data_flows[{index}].{endpoint} references an unknown participant"
                )
        names = _strings(flow["fields"], f"scenario.data_flows[{index}].fields")
        unknown = sorted(set(names) - field_names)
        if unknown:
            raise ContractError(f"scenario.data_flows[{index}] references unknown fields: {unknown}")
        if flow["protection"] not in FLOW_PROTECTIONS:
            raise ContractError(f"scenario.data_flows[{index}].protection is invalid")
    _unique((flow["id"] for flow in flows), "data flow")

    processing = _exact(scenario["processing"], PROCESSING_FIELDS, "scenario.processing")
    if processing["task_type"] not in TASK_TYPES:
        raise ContractError("scenario.processing.task_type is invalid")
    for key in ("local_training", "secure_aggregation", "mpc", "homomorphic_encryption", "tee", "protocol_evidence"):
        _boolean(processing[key], f"scenario.processing.{key}")
    protocol_participants = _strings(
        processing["protocol_participants"],
        "scenario.processing.protocol_participants",
        allow_empty=True,
    )
    unknown_protocol_participants = sorted(set(protocol_participants) - participant_ids)
    if unknown_protocol_participants:
        raise ContractError(
            f"scenario.processing.protocol_participants references unknown participants: {unknown_protocol_participants}"
        )
    if processing["protocol_security"] not in PROTOCOL_SECURITY:
        raise ContractError("scenario.processing.protocol_security is invalid")

    update_flows = [flow for flow in flows if flow["protection"] in {"federated_update", "secure_update"}]
    if processing["local_training"] != bool(update_flows):
        raise ContractError("scenario.processing.local_training must match declared update flows")
    if processing["local_training"] != (processing["task_type"] == "federated_training_and_statistics"):
        raise ContractError("scenario.processing.task_type must match local_training")
    secure_update_flows = [flow for flow in flows if flow["protection"] == "secure_update"]
    if processing["secure_aggregation"] != bool(secure_update_flows):
        raise ContractError("scenario.processing.secure_aggregation must match secure_update flows")
    for flag, protection in (("mpc", "mpc_share"), ("homomorphic_encryption", "he_ciphertext"), ("tee", "tee_input")):
        if processing[flag] != any(flow["protection"] == protection for flow in flows):
            raise ContractError(f"scenario.processing.{flag} must match {protection} flows")
    protocol_enabled = any(
        processing[key] for key in ("secure_aggregation", "mpc", "homomorphic_encryption", "tee")
    )
    if protocol_enabled:
        if not protocol_participants:
            raise ContractError("enabled privacy protocol requires protocol_participants")
        if processing["protocol_security"] == "none":
            raise ContractError("enabled privacy protocol requires a declared security model")
        protected_flow_kinds = {"secure_update", "mpc_share", "he_ciphertext", "tee_input"}
        flow_participants = {
            endpoint
            for flow in flows
            if flow["protection"] in protected_flow_kinds
            for endpoint in (flow["from"], flow["to"])
        }
        if set(protocol_participants) != flow_participants:
            raise ContractError(
                "scenario.processing.protocol_participants must match protected-flow endpoints"
            )
    else:
        if protocol_participants or processing["protocol_security"] != "none" or processing["protocol_evidence"]:
            raise ContractError("protocol metadata must be N/A when no privacy protocol is enabled")

    release = _exact(scenario["release"], RELEASE_FIELDS, "scenario.release")
    _boolean(release["public"], "scenario.release.public")
    _integer(release["minimum_group_size"], "scenario.release.minimum_group_size", 1)
    adjacency = _exact(release["adjacency"], ADJACENCY_FIELDS, "scenario.release.adjacency")
    if adjacency["unit"] not in {"person", "organization", "event", "undefined"}:
        raise ContractError("scenario.release.adjacency.unit is invalid")
    if adjacency["relation"] not in {"add_remove", "replace_one", "undefined"}:
        raise ContractError("scenario.release.adjacency.relation is invalid")
    _text(adjacency["time_window"], "scenario.release.adjacency.time_window")
    _boolean(adjacency["contribution_bounds_enforced"], "scenario.release.adjacency.contribution_bounds_enforced")
    epsilon_limit = _decimal(release["epsilon_limit"], "scenario.release.epsilon_limit", positive=True)
    delta_limit = _decimal(release["delta_limit"], "scenario.release.delta_limit")
    if delta_limit >= 1:
        raise ContractError("scenario.release.delta_limit must be less than 1")
    mechanisms = _objects(
        release["mechanisms"], MECHANISM_FIELDS, "scenario.release.mechanisms"
    )
    for index, mechanism in enumerate(mechanisms):
        _text(mechanism["id"], f"scenario.release.mechanisms[{index}].id")
        _text(mechanism["mechanism"], f"scenario.release.mechanisms[{index}].mechanism")
        _decimal(mechanism["epsilon"], f"scenario.release.mechanisms[{index}].epsilon")
        delta = _decimal(mechanism["delta"], f"scenario.release.mechanisms[{index}].delta")
        if delta >= 1:
            raise ContractError(f"scenario.release.mechanisms[{index}].delta must be less than 1")
        _boolean(mechanism["approved"], f"scenario.release.mechanisms[{index}].approved")
    _unique((item["id"] for item in mechanisms), "release mechanism")
    outputs = _objects(release["outputs"], OUTPUT_FIELDS, "scenario.release.outputs")
    public_outputs = 0
    direct_identifiers = {
        field["name"] for field in fields if field["privacy_class"] == "direct_identifier"
    }
    not_released_fields = {
        field["name"] for field in fields if field["output_role"] == "not_released"
    }
    for index, output in enumerate(outputs):
        _text(output["id"], f"scenario.release.outputs[{index}].id")
        output_fields = _strings(output["fields"], f"scenario.release.outputs[{index}].fields")
        unknown = sorted(set(output_fields) - field_names)
        if unknown:
            raise ContractError(f"scenario.release.outputs[{index}] references unknown fields: {unknown}")
        if output["transformation"] not in OUTPUT_TRANSFORMATIONS:
            raise ContractError(f"scenario.release.outputs[{index}].transformation is invalid")
        is_public = _boolean(output["public"], f"scenario.release.outputs[{index}].public")
        public_outputs += int(is_public)
        if is_public and direct_identifiers.intersection(output_fields):
            raise ContractError("public release outputs must not include direct identifiers")
        if not_released_fields.intersection(output_fields):
            raise ContractError("release outputs reference fields declared not_released")
    _unique((item["id"] for item in outputs), "release output")
    if release["public"] != bool(public_outputs):
        raise ContractError("scenario.release.public must match declared public outputs")

    retention = _exact(scenario["retention"], RETENTION_FIELDS, "scenario.retention")
    _integer(retention["days"], "scenario.retention.days", 1)
    _boolean(retention["deletion_verified"], "scenario.retention.deletion_verified")
    _boolean(retention["backups_in_scope"], "scenario.retention.backups_in_scope")

    controls = _exact(scenario["controls"], CONTROL_FIELDS, "scenario.controls")
    for key in CONTROL_FIELDS:
        _boolean(controls[key], f"scenario.controls.{key}")

    threat = _exact(scenario["threat_model"], THREAT_FIELDS, "scenario.threat_model")
    for key in ("honest_but_curious_server", "malicious_clients", "final_output_inference"):
        _boolean(threat[key], f"scenario.threat_model.{key}")
    collusion_threshold = _integer(
        threat["collusion_threshold"], "scenario.threat_model.collusion_threshold", 0
    )
    if protocol_participants:
        if processing["mpc"] or processing["secure_aggregation"]:
            if len(protocol_participants) < 2:
                raise ContractError("MPC or secure aggregation requires at least two protocol participants")
        if not 0 <= collusion_threshold < len(protocol_participants):
            raise ContractError("collusion threshold must be lower than the protocol participant count")
    elif collusion_threshold != 0:
        raise ContractError("collusion threshold must be 0 when no privacy protocol is enabled")

    policy = _exact(scenario["risk_policy"], POLICY_FIELDS, "scenario.risk_policy")
    block = set(_strings(policy["block_severities"], "scenario.risk_policy.block_severities"))
    review = set(
        _strings(
            policy["review_severities"],
            "scenario.risk_policy.review_severities",
            allow_empty=True,
        )
    )
    invalid = sorted((block | review) - SEVERITIES)
    if invalid:
        raise ContractError(f"risk policy has invalid severities: {invalid}")
    overlap = sorted(block & review)
    if overlap:
        raise ContractError(f"risk policy severities overlap: {overlap}")
    uncovered = sorted(SEVERITIES - block - review)
    if uncovered:
        raise ContractError(f"risk policy must classify every severity; uncovered={uncovered}")
    return copy.deepcopy(scenario)


def finding(
    identifier: str,
    title: str,
    severity: str,
    privacy_problem: str,
    controls: list[str],
    verification: list[str],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title,
        "severity": severity,
        "privacy_problem": privacy_problem,
        "recommended_controls": controls,
        "verification": verification,
        "owner": "privacy-owner",
    }


def budget_totals(scenario: dict[str, Any]) -> tuple[Decimal, Decimal]:
    mechanisms = scenario["release"]["mechanisms"]
    epsilon = sum((Decimal(item["epsilon"]) for item in mechanisms), Decimal("0"))
    delta = sum((Decimal(item["delta"]) for item in mechanisms), Decimal("0"))
    return epsilon, delta


def raw_centralization_targets(scenario: dict[str, Any]) -> list[str]:
    """Derive central raw collection from declared topology instead of a self-reported flag."""
    participants = {item["id"]: item for item in scenario["participants"]}
    holders_by_target: dict[str, set[str]] = {}
    for flow in scenario["data_flows"]:
        if (
            flow["protection"] == "raw"
            and participants[flow["from"]]["role"] == "data_holder"
            and participants[flow["to"]]["role"] == "compute_service"
        ):
            holders_by_target.setdefault(flow["to"], set()).add(flow["from"])
    return sorted(target for target, holders in holders_by_target.items() if len(holders) > 1)


def review(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    fields = scenario["data_fields"]
    release = scenario["release"]
    processing = scenario["processing"]
    controls = scenario["controls"]
    threat = scenario["threat_model"]
    participants = {item["id"]: item for item in scenario["participants"]}

    unnecessary_fields = [
        field["name"]
        for field in fields
        if not field["necessary"]
    ]
    if unnecessary_fields:
        high_impact = any(
            field["name"] in unnecessary_fields
            and field["privacy_class"] in {"direct_identifier", "sensitive_attribute"}
            for field in fields
        )
        findings.append(
            finding(
                "PR-001", "Unnecessary data fields are collected", "high" if high_impact else "medium",
                "collecting data without a purpose expands harm, access, and response scope",
                ["exclude before collection", "separate any independently approved secondary purpose"],
                ["field-to-purpose review", "ingestion rejection test"],
            )
        )

    quasi = {field["name"] for field in fields if field["privacy_class"] == "quasi_identifier"}
    public_quasi_outputs = [
        output["id"]
        for output in release["outputs"]
        if output["public"] and quasi.intersection(output["fields"])
    ]
    if public_quasi_outputs and not controls["linkage_evaluation"]:
        findings.append(
            finding(
                "PR-002", "Public quasi-identifying dimensions lack linkage evaluation", "medium",
                "external data may link rare combinations back to people",
                ["generalize or suppress rare combinations", "evaluate linkage and output inference"],
                ["linkage attack exercise", "rare-group report"],
            )
        )

    if raw_centralization_targets(scenario):
        findings.append(
            finding(
                "PR-003", "Multiple holders centralize raw records", "high",
                "a central compromise exposes every participant input",
                ["first minimize data", "evaluate MPC, secure aggregation, or local computation"],
                ["end-to-end data-flow review", "raw-record absence check"],
            )
        )

    if release["public"] and release["minimum_group_size"] < 10:
        findings.append(
            finding(
                "PR-004", "Public output permits very small groups", "high",
                "small cells may reveal or strongly narrow an individual's attributes",
                ["justify and raise suppression threshold", "combine with a reviewed formal privacy mechanism"],
                ["small-cell negative tests", "differencing-query tests"],
            )
        )

    adjacency = release["adjacency"]
    if (
        adjacency["unit"] == "undefined"
        or adjacency["relation"] == "undefined"
        or adjacency["time_window"].strip().lower() == "undefined"
        or not adjacency["contribution_bounds_enforced"]
    ):
        findings.append(
            finding(
                "PR-005", "Differential-privacy adjacency is not defined", "high",
                "epsilon and delta have no interpretable subject-level guarantee without neighboring datasets",
                ["define add/remove or replace-one adjacency", "bound each subject's contribution"],
                ["adjacency design review", "contribution-bound property test"],
            )
        )

    epsilon_used, delta_used = budget_totals(scenario)
    if epsilon_used > Decimal(release["epsilon_limit"]) or delta_used > Decimal(release["delta_limit"]):
        findings.append(
            finding(
                "PR-006", "Illustrative privacy ledger exceeds its frozen limits", "critical",
                "combined releases exceed the design policy and must not be published",
                ["block publication", "reduce or remove releases", "obtain privacy-owner approval for a new policy"],
                ["exact-decimal ledger test", "release-gate test"],
            )
        )

    unapproved = [item["id"] for item in release["mechanisms"] if not item["approved"]]
    if unapproved or not controls["budget_ledger"]:
        findings.append(
            finding(
                "PR-007", "Release approval or privacy-budget accounting is incomplete", "high",
                "repeated queries can silently compose beyond the intended privacy loss",
                ["centralize a subject-scoped immutable ledger", "require release approval before consumption"],
                ["duplicate-release test", "concurrent budget reservation test"],
            )
        )

    retention = scenario["retention"]
    if retention["days"] > 90 or not retention["deletion_verified"] or not retention["backups_in_scope"]:
        findings.append(
            finding(
                "PR-008", "Retention and verified deletion are not minimized", "medium",
                "records or recoverable copies remain exposed beyond the stated task",
                ["derive retention from purpose", "cover replicas, caches, vectors, logs, models, and backups"],
                ["expiry job test", "deletion evidence sample", "restore-path check"],
            )
        )

    sensitive_names = {
        field["name"]
        for field in fields
        if field["privacy_class"] in {"direct_identifier", "quasi_identifier", "sensitive_attribute"}
    }
    unsafe_flows = [
        flow["id"]
        for flow in scenario["data_flows"]
        if flow["protection"] == "raw"
        and sensitive_names.intersection(flow["fields"])
        and not participants[flow["to"]]["trusted"]
    ]
    if unsafe_flows:
        findings.append(
            finding(
                "PR-009", "Raw sensitive fields flow to an untrusted participant", "critical",
                "a declared trust boundary exposes identifiable or sensitive records",
                ["remove the flow", "minimize before transfer", "use an independently reviewed protocol and endpoint"],
                ["flow-policy test", "destination and field-level audit"],
            )
        )

    update_flows = [
        flow for flow in scenario["data_flows"]
        if flow["protection"] in {"federated_update", "secure_update"}
    ]
    visible_update_flows = [
        flow for flow in update_flows if flow["protection"] == "federated_update"
    ]
    if visible_update_flows and threat["honest_but_curious_server"]:
        findings.append(
            finding(
                "PR-010", "Federated updates are visible to the curious server", "high",
                "keeping raw data local does not prevent inference from individual updates",
                ["evaluate secure aggregation", "bound and protect updates", "assess final-model leakage separately"],
                ["server-view review", "update-inference exercise", "minimum cohort test"],
            )
        )

    if update_flows and threat["malicious_clients"] and not controls["update_validation"]:
        findings.append(
            finding(
                "PR-011", "Malicious participant updates are not constrained", "high",
                "privacy protocols that hide updates may also hide poisoning or malformed contributions",
                ["validate contribution shape and bounds", "apply robust aggregation and participant controls"],
                ["malformed-update test", "poisoning simulation", "dropout/collusion exercise"],
            )
        )

    applicable_controls = set(CONTROL_FIELDS)
    if not update_flows:
        applicable_controls.remove("update_validation")
    missing = [key for key in sorted(applicable_controls) if not controls[key]]
    if any(processing[key] for key in ("secure_aggregation", "mpc", "homomorphic_encryption", "tee")):
        if not processing["protocol_evidence"]:
            missing.append("protocol_evidence")
    if missing:
        findings.append(
            finding(
                "PR-012", "Privacy lifecycle controls are incomplete", "medium",
                "a mathematical or cryptographic mechanism cannot enforce purpose, access, evidence, and response alone",
                ["assign owners for each missing control", "gate release on complete lifecycle evidence"],
                ["control-evidence review", "incident and deletion drill"],
            )
        )
    return sorted(findings, key=lambda item: (SEVERITY_ORDER[item["severity"]], item["id"]))


def candidate_controls(scenario: dict[str, Any]) -> list[dict[str, str]]:
    candidates = [
        {
            "technique": "data minimization, purpose limitation, aggregation, and deletion",
            "fit": "always evaluate before adding cryptography",
            "boundary": "does not quantify inference from a released statistic",
        }
    ]
    if len([p for p in scenario["participants"] if p["role"] == "data_holder"]) > 1:
        candidates.append(
            {
                "technique": "MPC or secure aggregation",
                "fit": "reduce visibility of individual inputs or updates during joint computation",
                "boundary": "does not make an overly revealing final output private or prove honest inputs",
            }
        )
    if scenario["release"]["public"]:
        candidates.append(
            {
                "technique": "reviewed differential-privacy mechanism",
                "fit": "quantify subject-level influence on repeated public releases",
                "boundary": "requires adjacency, contribution bounds, accounting, implementation evidence, and utility review",
            }
        )
    return candidates


def fingerprint(scenario: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {"scenario": scenario, "findings": findings},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def decision(scenario: dict[str, Any], findings: list[dict[str, Any]]) -> tuple[str, list[str]]:
    block = set(scenario["risk_policy"]["block_severities"])
    review_levels = set(scenario["risk_policy"]["review_severities"])
    blockers = [item["id"] for item in findings if item["severity"] in block]
    reviews = [item["id"] for item in findings if item["severity"] in review_levels]
    uncovered = [item["id"] for item in findings if item["severity"] not in (block | review_levels)]
    if uncovered:
        raise ContractError("risk policy left findings unclassified: " + ", ".join(uncovered))
    if blockers:
        return "BLOCK", ["blocking findings: " + ", ".join(blockers)]
    if reviews:
        return "REVIEW", ["review findings: " + ", ".join(reviews)]
    return "PASS", ["no finding crossed the frozen teaching policy"]


def build_report(scenario: dict[str, Any]) -> dict[str, Any]:
    findings = review(scenario)
    action, reasons = decision(scenario, findings)
    epsilon, delta = budget_totals(scenario)
    return {
        "action": action,
        "reasons": reasons,
        "scenario_id": scenario["scenario_id"],
        "purpose": scenario["purpose"],
        "non_goals": scenario["non_goals"],
        "release_outputs": scenario["release"]["outputs"],
        "budget_ledger": {
            "epsilon_used": str(epsilon),
            "epsilon_limit": scenario["release"]["epsilon_limit"],
            "delta_used": str(delta),
            "delta_limit": scenario["release"]["delta_limit"],
            "warning": "illustrative basic composition; not a validated DP guarantee",
        },
        "risk_counts": dict(sorted(Counter(item["severity"] for item in findings).items())),
        "finding_count": len(findings),
        "findings": findings,
        "candidate_controls": candidate_controls(scenario),
        "evidence_fingerprint": fingerprint(scenario, findings),
        "limitations": [
            "No personal data, model, DP library, FL system, MPC, FHE, TEE, or network was used.",
            "The ledger uses basic illustrative addition and does not validate a mechanism or accountant.",
            "A PASS result only means the declared metadata triggered no teaching rule.",
            "Protocol participants, protections, lineage, and evidence are declarations, not runtime verification.",
            "The report is not legal advice, a cryptographic review, or a production privacy assessment.",
        ],
    }


def run_from_path(path: Path) -> dict[str, Any]:
    return build_report(validate_scenario(load_json(path)))


def self_test() -> None:
    vulnerable = run_from_path(DEFAULT_SCENARIO)
    hardened = run_from_path(HARDENED_SCENARIO)
    expected = {f"PR-{number:03d}" for number in range(1, 13)}
    failures: list[str] = []
    if vulnerable["action"] != "BLOCK":
        failures.append("vulnerable scenario did not BLOCK")
    if {item["id"] for item in vulnerable["findings"]} != expected:
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
