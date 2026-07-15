"""Build a deterministic governance pack for one synthetic AI system."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any


AS_OF = "2026-07-14"
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
            "personal_data": False,
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

    data_expected = {"id", "category", "source", "personal_data", "retention"}
    require(isinstance(raw["data"], list) and bool(raw["data"]), "scenario.data must be non-empty")
    data_ids: list[str] = []
    for index, item in enumerate(raw["data"]):
        require(isinstance(item, dict) and set(item) == data_expected, f"scenario.data[{index}] fields mismatch")
        for key in ("id", "category", "source", "retention"):
            _non_empty_text(item[key], f"scenario.data[{index}].{key}")
        require(isinstance(item["personal_data"], bool), f"scenario.data[{index}].personal_data must be boolean")
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

    vendor_expected = {"id", "name", "training_on_inputs", "change_notice", "exit_plan"}
    vendor = raw["vendor"]
    require(isinstance(vendor, dict) and set(vendor) == vendor_expected, "scenario.vendor fields mismatch")
    for key in ("id", "name", "change_notice", "exit_plan"):
        _non_empty_text(vendor[key], f"scenario.vendor.{key}")
    require(isinstance(vendor["training_on_inputs"], bool), "scenario.vendor.training_on_inputs must be boolean")

    facts_expected = {
        "severity", "likelihood", "consequential_context", "sensitive_or_personal_data",
        "autonomous_action", "uncertainty",
    }
    facts = raw["risk_facts"]
    require(isinstance(facts, dict) and set(facts) == facts_expected, "scenario.risk_facts fields mismatch")
    for key in ("severity", "likelihood"):
        value = facts[key]
        require(not isinstance(value, bool) and isinstance(value, int) and 1 <= value <= 5, f"scenario.risk_facts.{key} must be an integer from 1 to 5")
    for key in ("consequential_context", "sensitive_or_personal_data", "autonomous_action"):
        require(isinstance(facts[key], bool), f"scenario.risk_facts.{key} must be boolean")
    _non_empty_text(facts["uncertainty"], "scenario.risk_facts.uncertainty")
    return copy.deepcopy(raw)


def tier_risk(facts: dict[str, Any]) -> dict[str, Any]:
    """Apply a teaching rubric; this is not a legal classification."""
    for key in ("severity", "likelihood"):
        value = facts.get(key)
        require(not isinstance(value, bool) and isinstance(value, int) and 1 <= value <= 5, f"risk fact {key} must be an integer from 1 to 5")
    score = facts["severity"] * facts["likelihood"]
    if score >= 10:
        tier = "high"
    elif score >= 5:
        tier = "medium"
    else:
        tier = "low"
    reasons = [f"teaching matrix score={score} (severity x likelihood)"]
    if facts.get("consequential_context"):
        tier = "high"
        reasons.append("consequential public-benefit context forces high internal review")
    if facts.get("autonomous_action"):
        tier = "high"
        reasons.append("autonomous action forces high internal review")
    reasons.append(str(facts.get("uncertainty", "uncertainty not recorded")))
    return {
        "internal_tier": tier,
        "score": score,
        "reasons": reasons,
        "boundary": "internal teaching rubric; not a statutory or regulatory category",
    }


def build_pack(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario = validate_scenario(scenario)
    risk = tier_risk(scenario["risk_facts"])
    version_set = {
        item["id"]: item["version"] for item in scenario["components"]
    }
    return {
        "metadata": {
            "pack_version": "1.0",
            "as_of": AS_OF,
            "scenario_kind": "synthetic_offline_training",
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
            "next_review": "2026-08-13",
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
            "conditions": [
                "no real personal or case data",
                "no eligibility decision or ranking",
                "no external write or contact capability",
                "record every serious unsupported claim as a hazard",
            ],
            "expires": "2026-08-13",
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
            "nist_ai_rmf": "version 1.0; official site says revision in progress",
            "oecd_ai_principles": "updated May 2024",
            "legal_review": "not performed; deployment-specific review required",
        },
        "disclaimer": (
            "teaching artifact over synthetic facts; not legal advice, compliance evidence, "
            "certification, audit, or production approval"
        ),
    }


def validate_pack(pack: dict[str, Any]) -> None:
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
    require(pack["system_register"]["system_id"] == "GOV-EX-001", "system ID changed")
    require(pack["risk_assessment"]["internal_tier"] == "high", "risk tier must be high")
    require(
        pack["risk_assessment"]["boundary"]
        == "internal teaching rubric; not a statutory or regulatory category",
        "risk boundary is missing",
    )
    require(
        pack["approval"]["decision"] == "conditional_synthetic_sandbox_only",
        "approval scope changed",
    )
    require(pack["approval"]["production_approved"] is False, "production must remain unapproved")
    require(
        pack["approval"]["approved_version_set"]
        == pack["component_register"]["approved_version_set"],
        "approval is not bound to the component version set",
    )
    require(len(pack["change_triggers"]) >= 5, "too few change triggers")
    require(len(pack["monitoring_plan"]) >= 2, "too few monitoring controls")
    require(
        all(item.get("metric") and item.get("threshold") and item.get("action") and item.get("owner") for item in pack["monitoring_plan"]),
        "monitoring controls must include metric, threshold, action, and owner",
    )
    require(len(pack["retirement_plan"]) >= 5, "retirement plan is incomplete")
    require("not legal advice" in pack["disclaimer"], "legal boundary is missing")


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
