"""Build a deterministic governance pack for one synthetic AI system."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import date
from typing import Any


AS_OF = "2026-07-22"
NEXT_REVIEW = "2026-08-22"
SCENARIO: dict[str, Any] = {
    "system_id": "GOV-EX-001",
    "name": "synthetic-benefit-intake-assistant",
    "status": "sandbox_proposal",
    "purpose": "summarize fictional application material and draft a missing-item checklist",
    "prohibited_uses": [
        "decide eligibility",
        "rank applicants",
        "contact an applicant automatically",
    ],
    "users": ["trained_caseworker"],
    "affected_groups": ["fictional_applicants"],
    "decision_role": "advisory_draft_only",
    "data": [
        {
            "id": "DATA-001",
            "category": "synthetic_application_text",
            "source": "locally_authored_fixture",
            "version": "fixture-v1",
            "owner": "fictional_data_owner",
            "personal_data": False,
            "sensitive_data": False,
            "retention": "discard_after_each_test_run",
        }
    ],
    "components": [
        {
            "id": "MODEL-001",
            "type": "model",
            "name": "fictional-hosted-model",
            "version": "snapshot-training-only",
            "owner": "model_owner",
        },
        {
            "id": "PROMPT-001",
            "type": "prompt",
            "name": "intake-summary-instructions",
            "version": "prompt-v1-teaching",
            "owner": "system_owner",
        },
        {
            "id": "TOOL-001",
            "type": "tool",
            "name": "read_synthetic_fixture",
            "version": "1.0",
            "owner": "system_owner",
        },
    ],
    "vendor": {
        "id": "VENDOR-001",
        "name": "fictional-model-provider",
        "profile_snapshot": "supplier-profile-2026-07-22",
        "owner": "fictional_procurement_owner",
        "training_on_inputs": False,
        "change_notice": "notice-required-before-material-change",
        "exit_plan": "disable endpoint and switch to manual review",
    },
    "risk_facts": {
        "severity": 4,
        "likelihood": 2,
        "consequential_context": True,
        "sensitive_or_personal_data": False,
        "autonomous_action": False,
        "uncertainty": "no production evidence; synthetic sandbox only",
    },
}


class GovernanceError(ValueError):
    """Raised when the synthetic scenario or generated pack breaks its contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GovernanceError(message)


def _non_empty_text(value: Any, location: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{location} must be non-empty text")
    return value


def _text_list(value: Any, location: str) -> list[str]:
    require(isinstance(value, list) and bool(value), f"{location} must be a non-empty list")
    result = [_non_empty_text(item, f"{location}[{index}]") for index, item in enumerate(value)]
    require(len(result) == len(set(result)), f"{location} must not contain duplicates")
    return result


def _exact_object(value: Any, fields: set[str], location: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{location} must be an object")
    require(set(value) == fields, f"{location} fields must match the frozen contract")
    return value


def _iso_date(value: Any, location: str) -> date:
    text = _non_empty_text(value, location)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise GovernanceError(f"{location} must be an ISO date") from exc
    require(parsed.isoformat() == text, f"{location} must use YYYY-MM-DD")
    return parsed


def _validate_risk_facts(value: Any, location: str) -> dict[str, Any]:
    expected = {
        "severity", "likelihood", "consequential_context", "sensitive_or_personal_data",
        "autonomous_action", "uncertainty",
    }
    facts = _exact_object(value, expected, location)
    for key in ("severity", "likelihood"):
        item = facts[key]
        require(
            not isinstance(item, bool) and isinstance(item, int) and 1 <= item <= 5,
            f"{location}.{key} must be an integer from 1 to 5",
        )
    for key in ("consequential_context", "sensitive_or_personal_data", "autonomous_action"):
        require(isinstance(facts[key], bool), f"{location}.{key} must be boolean")
    _non_empty_text(facts["uncertainty"], f"{location}.uncertainty")
    return facts


def scenario_fingerprint(scenario: dict[str, Any]) -> str:
    """Bind generated evidence with stable local serialization, not a signature."""
    canonical = json.dumps(
        scenario,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_scenario(raw: Any) -> dict[str, Any]:
    """Validate the frozen in-memory teaching contract and return a deep copy."""
    expected = {
        "system_id", "name", "status", "purpose", "prohibited_uses", "users",
        "affected_groups", "decision_role", "data", "components", "vendor", "risk_facts",
    }
    require(isinstance(raw, dict), "scenario must be an object")
    require(set(raw) == expected, "scenario top-level fields must match the frozen contract")
    for key in ("system_id", "name", "status", "purpose", "decision_role"):
        _non_empty_text(raw[key], f"scenario.{key}")
    _text_list(raw["prohibited_uses"], "scenario.prohibited_uses")
    _text_list(raw["users"], "scenario.users")
    _text_list(raw["affected_groups"], "scenario.affected_groups")

    data_expected = {
        "id",
        "category",
        "source",
        "version",
        "owner",
        "personal_data",
        "sensitive_data",
        "retention",
    }
    require(isinstance(raw["data"], list) and bool(raw["data"]), "scenario.data must be non-empty")
    data_ids: list[str] = []
    for index, item in enumerate(raw["data"]):
        require(isinstance(item, dict) and set(item) == data_expected, f"scenario.data[{index}] fields mismatch")
        for key in ("id", "category", "source", "version", "owner", "retention"):
            _non_empty_text(item[key], f"scenario.data[{index}].{key}")
        for key in ("personal_data", "sensitive_data"):
            require(isinstance(item[key], bool), f"scenario.data[{index}].{key} must be boolean")
        data_ids.append(item["id"])
    require(len(data_ids) == len(set(data_ids)), "scenario data IDs must be unique")

    component_expected = {"id", "type", "name", "version", "owner"}
    require(isinstance(raw["components"], list) and bool(raw["components"]), "scenario.components must be non-empty")
    component_ids: list[str] = []
    for index, item in enumerate(raw["components"]):
        require(isinstance(item, dict) and set(item) == component_expected, f"scenario.components[{index}] fields mismatch")
        for key in component_expected:
            _non_empty_text(item[key], f"scenario.components[{index}].{key}")
        require(item["type"] in {"model", "prompt", "tool"}, f"scenario.components[{index}].type is invalid")
        component_ids.append(item["id"])
    require(len(component_ids) == len(set(component_ids)), "scenario component IDs must be unique")

    vendor_expected = {
        "id",
        "name",
        "profile_snapshot",
        "owner",
        "training_on_inputs",
        "change_notice",
        "exit_plan",
    }
    vendor = raw["vendor"]
    require(isinstance(vendor, dict) and set(vendor) == vendor_expected, "scenario.vendor fields mismatch")
    for key in ("id", "name", "profile_snapshot", "owner", "change_notice", "exit_plan"):
        _non_empty_text(vendor[key], f"scenario.vendor.{key}")
    require(isinstance(vendor["training_on_inputs"], bool), "scenario.vendor.training_on_inputs must be boolean")

    require(raw["status"] == "sandbox_proposal", "teaching scenario status must remain sandbox_proposal")
    require(
        raw["decision_role"] == "advisory_draft_only",
        "teaching scenario decision_role must remain advisory_draft_only",
    )
    facts = _validate_risk_facts(raw["risk_facts"], "scenario.risk_facts")
    declared_sensitive = any(
        item["personal_data"] or item["sensitive_data"] for item in raw["data"]
    )
    require(
        facts["sensitive_or_personal_data"] == declared_sensitive,
        "scenario.risk_facts.sensitive_or_personal_data must match the data register",
    )
    return copy.deepcopy(raw)


def tier_risk(facts: dict[str, Any]) -> dict[str, Any]:
    """Apply a teaching rubric; this is not a legal classification."""
    facts = _validate_risk_facts(facts, "risk_facts")
    score = facts["severity"] * facts["likelihood"]
    if score >= 10:
        tier = "high"
    elif score >= 5:
        tier = "medium"
    else:
        tier = "low"
    reasons = [f"teaching matrix score={score} (severity x likelihood)"]
    required_reviews: list[str] = []
    if facts["consequential_context"]:
        tier = "high"
        reasons.append("consequential public-benefit context forces high internal review")
        required_reviews.extend(["domain", "independent_risk"])
    if facts["autonomous_action"]:
        tier = "high"
        reasons.append("autonomous action forces high internal review")
        required_reviews.extend(["safety", "independent_risk"])
    if facts["sensitive_or_personal_data"]:
        reasons.append("personal or sensitive data requires privacy review independent of the tier")
        required_reviews.append("privacy")
    reasons.append(facts["uncertainty"])
    return {
        "internal_tier": tier,
        "score": score,
        "reasons": reasons,
        "required_reviews": sorted(set(required_reviews)),
        "boundary": "internal teaching rubric; not a statutory or regulatory category",
    }


def build_pack(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario = validate_scenario(scenario)
    risk = tier_risk(scenario["risk_facts"])
    scenario_sha256 = scenario_fingerprint(scenario)
    version_set = {
        item["id"]: item["version"] for item in scenario["components"]
    }
    return {
        "metadata": {
            "pack_version": "1.0",
            "as_of": AS_OF,
            "scenario_kind": "synthetic_offline_training",
            "scenario_sha256": scenario_sha256,
        },
        "system_register": {
            "system_id": scenario["system_id"],
            "name": scenario["name"],
            "status": scenario["status"],
            "purpose": scenario["purpose"],
            "prohibited_uses": scenario["prohibited_uses"],
            "business_owner": "fictional_service_owner",
            "system_owner": "fictional_product_owner",
            "users": scenario["users"],
            "affected_groups": scenario["affected_groups"],
            "decision_role": scenario["decision_role"],
            "deployment_regions": ["training-only"],
            "next_review": NEXT_REVIEW,
        },
        "role_assignment": {
            "accountable": "fictional_service_owner",
            "responsible": ["fictional_product_owner", "fictional_operations_owner"],
            "independent_review": ["fictional_risk_reviewer"],
            "consulted": ["fictional_domain_expert", "fictional_security_privacy_reviewer"],
            "informed": ["fictional_caseworker", "fictional_support_desk"],
            "decision_rights": {
                "approve_sandbox": "fictional_service_owner",
                "accept_high_residual_risk": "fictional_governance_board",
                "emergency_stop": "fictional_operations_owner",
            },
        },
        "risk_assessment": risk,
        "impact_assessment": {
            "benefit": "reduce time spent locating missing items in fictional material",
            "non_ai_baseline": "caseworker uses a deterministic checklist",
            "impact_paths": [
                "omitted evidence -> incomplete draft -> delayed human review",
                "unsupported inference -> misleading draft -> caseworker over-reliance",
                "scope expansion -> eligibility recommendation -> loss of human determination",
            ],
            "controls": [
                "synthetic data only",
                "source-linked draft with deterministic required-field check",
                "trained caseworker must verify and may reject every suggestion",
                "no write or communication tool",
                "sandbox stop on serious unsupported claim",
            ],
            "residual_risk": "reviewer may over-trust a fluent but incomplete draft",
            "affected_party_feedback": "required before any real-user pilot",
        },
        "component_register": {
            "data": scenario["data"],
            "components": scenario["components"],
            "vendor": scenario["vendor"],
            "approved_version_set": dict(version_set),
        },
        "approval": {
            "decision": "conditional_synthetic_sandbox_only",
            "approved_version_set": dict(version_set),
            "scenario_sha256": scenario_sha256,
            "conditions": [
                "no real personal or case data",
                "no eligibility decision or ranking",
                "no external write or contact capability",
                "record every serious unsupported claim as a hazard",
            ],
            "expires": NEXT_REVIEW,
            "production_approved": False,
        },
        "change_triggers": [
            "real users or real data",
            "model, prompt, tool, vendor, or data-source version changes",
            "new region or affected group",
            "automatic communication, ranking, or eligibility influence",
            "serious hazard, complaint, or control failure",
        ],
        "monitoring_plan": [
            {
                "metric": "serious_unsupported_claim_rate",
                "threshold": "greater than 0 in the 20-case sandbox fixture",
                "action": "stop sandbox and investigate before another run",
                "owner": "fictional_operations_owner",
            },
            {
                "metric": "source_link_coverage",
                "threshold": "less than 100 percent for factual draft statements",
                "action": "reject the draft and open a quality issue",
                "owner": "fictional_product_owner",
            },
        ],
        "incident_and_hazard_plan": {
            "containment": ["stop run", "disable model endpoint", "preserve minimal trace"],
            "record_fields": [
                "event_id",
                "system_and_versions",
                "actual_or_potential_impact",
                "affected_group",
                "evidence",
                "actions_and_owners",
            ],
            "external_notification": "qualified teams decide under current applicable rules",
        },
        "retirement_plan": [
            "disable endpoint and scheduled runs",
            "revoke service identity",
            "delete synthetic fixtures and transient traces under the recorded retention rule",
            "archive minimum governance decision evidence",
            "confirm manual checklist remains available",
            "verify no downstream dependency or recurring charge remains",
        ],
        "source_status": {
            "as_of": AS_OF,
            "snapshot_kind": "frozen_static_training_snapshot",
            "nist_ai_rmf": {
                "version_status": "version 1.0; official site says revision in progress",
                "official_url": "https://www.nist.gov/itl/ai-risk-management-framework",
            },
            "oecd_ai_principles": {
                "version_status": "updated May 2024",
                "official_url": "https://oecd.ai/en/ai-principles",
            },
            "legal_review": "not performed; deployment-specific review required",
        },
        "disclaimer": (
            "teaching artifact over synthetic facts; not legal advice, compliance evidence, "
            "certification, audit, or production approval"
        ),
    }


def validate_pack(pack: dict[str, Any], scenario: dict[str, Any] | None = None) -> None:
    """Validate every frozen section and bind it back to canonical scenario facts."""
    validated_scenario = validate_scenario(SCENARIO if scenario is None else scenario)
    required = {
        "metadata",
        "system_register",
        "role_assignment",
        "risk_assessment",
        "impact_assessment",
        "component_register",
        "approval",
        "change_triggers",
        "monitoring_plan",
        "incident_and_hazard_plan",
        "retirement_plan",
        "source_status",
        "disclaimer",
    }
    require(isinstance(pack, dict), "pack must be an object")
    require(required == set(pack), "pack top-level sections must match the frozen contract")
    metadata = _exact_object(
        pack["metadata"], {"pack_version", "as_of", "scenario_kind", "scenario_sha256"}, "pack.metadata",
    )
    require(metadata["pack_version"] == "1.0", "pack version changed")
    as_of = _iso_date(metadata["as_of"], "pack.metadata.as_of")
    require(metadata["as_of"] == AS_OF, "pack source date changed")
    require(metadata["scenario_kind"] == "synthetic_offline_training", "scenario kind changed")
    expected_fingerprint = scenario_fingerprint(validated_scenario)
    require(metadata["scenario_sha256"] == expected_fingerprint, "metadata is not bound to the scenario")

    system = _exact_object(
        pack["system_register"],
        {
            "system_id", "name", "status", "purpose", "prohibited_uses", "business_owner",
            "system_owner", "users", "affected_groups", "decision_role", "deployment_regions",
            "next_review",
        },
        "pack.system_register",
    )
    for key in ("system_id", "name", "status", "purpose", "prohibited_uses", "users", "affected_groups", "decision_role"):
        require(system[key] == validated_scenario[key], f"system register {key} is not scenario-derived")
    _non_empty_text(system["business_owner"], "pack.system_register.business_owner")
    _non_empty_text(system["system_owner"], "pack.system_register.system_owner")
    _text_list(system["deployment_regions"], "pack.system_register.deployment_regions")
    require(_iso_date(system["next_review"], "pack.system_register.next_review") > as_of, "next review must follow the snapshot date")

    roles = _exact_object(
        pack["role_assignment"],
        {"accountable", "responsible", "independent_review", "consulted", "informed", "decision_rights"},
        "pack.role_assignment",
    )
    _non_empty_text(roles["accountable"], "pack.role_assignment.accountable")
    for key in ("responsible", "independent_review", "consulted", "informed"):
        _text_list(roles[key], f"pack.role_assignment.{key}")
    rights = _exact_object(
        roles["decision_rights"], {"approve_sandbox", "accept_high_residual_risk", "emergency_stop"},
        "pack.role_assignment.decision_rights",
    )
    for key in rights:
        _non_empty_text(rights[key], f"pack.role_assignment.decision_rights.{key}")

    risk = _exact_object(
        pack["risk_assessment"], {"internal_tier", "score", "reasons", "required_reviews", "boundary"},
        "pack.risk_assessment",
    )
    require(risk == tier_risk(validated_scenario["risk_facts"]), "risk assessment is not scenario-derived")

    impact = _exact_object(
        pack["impact_assessment"],
        {"benefit", "non_ai_baseline", "impact_paths", "controls", "residual_risk", "affected_party_feedback"},
        "pack.impact_assessment",
    )
    for key in ("benefit", "non_ai_baseline", "residual_risk", "affected_party_feedback"):
        _non_empty_text(impact[key], f"pack.impact_assessment.{key}")
    for key in ("impact_paths", "controls"):
        _text_list(impact[key], f"pack.impact_assessment.{key}")

    component = _exact_object(
        pack["component_register"], {"data", "components", "vendor", "approved_version_set"},
        "pack.component_register",
    )
    require(component["data"] == validated_scenario["data"], "data register is not scenario-derived")
    require(component["components"] == validated_scenario["components"], "component register is not scenario-derived")
    require(component["vendor"] == validated_scenario["vendor"], "vendor register is not scenario-derived")
    expected_versions = {item["id"]: item["version"] for item in validated_scenario["components"]}
    require(component["approved_version_set"] == expected_versions, "component version set is not scenario-derived")

    approval = _exact_object(
        pack["approval"],
        {"decision", "approved_version_set", "scenario_sha256", "conditions", "expires", "production_approved"},
        "pack.approval",
    )
    require(approval["decision"] == "conditional_synthetic_sandbox_only", "approval scope changed")
    require(approval["production_approved"] is False, "production must remain unapproved")
    require(approval["approved_version_set"] == expected_versions, "approval is not bound to scenario versions")
    require(approval["scenario_sha256"] == expected_fingerprint, "approval is not bound to the scenario")
    _text_list(approval["conditions"], "pack.approval.conditions")
    require(_iso_date(approval["expires"], "pack.approval.expires") > as_of, "approval must expire after the snapshot date")

    require(len(_text_list(pack["change_triggers"], "pack.change_triggers")) >= 5, "too few change triggers")
    require(isinstance(pack["monitoring_plan"], list) and len(pack["monitoring_plan"]) >= 2, "too few monitoring controls")
    metrics: list[str] = []
    for index, item in enumerate(pack["monitoring_plan"]):
        record = _exact_object(item, {"metric", "threshold", "action", "owner"}, f"pack.monitoring_plan[{index}]")
        for key in record:
            _non_empty_text(record[key], f"pack.monitoring_plan[{index}].{key}")
        metrics.append(record["metric"])
    require(len(metrics) == len(set(metrics)), "monitoring metrics must be unique")

    incident = _exact_object(
        pack["incident_and_hazard_plan"], {"containment", "record_fields", "external_notification"},
        "pack.incident_and_hazard_plan",
    )
    _text_list(incident["containment"], "pack.incident_and_hazard_plan.containment")
    _text_list(incident["record_fields"], "pack.incident_and_hazard_plan.record_fields")
    _non_empty_text(incident["external_notification"], "pack.incident_and_hazard_plan.external_notification")
    require(len(_text_list(pack["retirement_plan"], "pack.retirement_plan")) >= 5, "retirement plan is incomplete")

    source = _exact_object(
        pack["source_status"], {"as_of", "snapshot_kind", "nist_ai_rmf", "oecd_ai_principles", "legal_review"},
        "pack.source_status",
    )
    require(source["as_of"] == AS_OF, "source status date changed")
    require(source["snapshot_kind"] == "frozen_static_training_snapshot", "source snapshot boundary changed")
    for key in ("nist_ai_rmf", "oecd_ai_principles"):
        record = _exact_object(source[key], {"version_status", "official_url"}, f"pack.source_status.{key}")
        _non_empty_text(record["version_status"], f"pack.source_status.{key}.version_status")
        require(record["official_url"].startswith("https://"), f"pack.source_status.{key}.official_url must use HTTPS")
    require("not performed" in _non_empty_text(source["legal_review"], "pack.source_status.legal_review"), "legal review boundary is missing")
    require("not legal advice" in _non_empty_text(pack["disclaimer"], "pack.disclaimer"), "legal boundary is missing")

    require(pack == build_pack(validated_scenario), "pack content must match the scenario-derived frozen contract")


def self_test() -> None:
    pack = build_pack(SCENARIO)
    validate_pack(pack)
    rendered = json.dumps(pack, ensure_ascii=False)
    forbidden = ("api_key", "access_token", "bearer ", "password")
    require(not any(item in rendered.lower() for item in forbidden), "forbidden credential marker found")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"self_test": "passed"}, ensure_ascii=False))
            return 0
        pack = build_pack(SCENARIO)
        validate_pack(pack)
    except GovernanceError as exc:
        print(f"governance contract error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
