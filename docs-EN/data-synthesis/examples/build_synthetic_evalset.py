"""Build and audit a small, deterministic synthetic evaluation dataset.

The program is deliberately offline and uses only the Python standard library.
It demonstrates contracts, provenance, filtering, family-level splits, quality
gates, and reproducible evidence. It does not provide a privacy guarantee.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE / "synthesis_spec.json"
QUALITY_REGRESSION_SPEC = HERE / "synthesis_spec_quality_regression.json"
CONTRACT_ERROR_SPEC = HERE / "synthesis_spec_contract_error.json"

TOP_LEVEL_FIELDS = {
    "dataset_id",
    "dataset_version",
    "schema_version",
    "purpose",
    "non_goals",
    "generator",
    "split",
    "quality_gates",
    "teaching_faults",
    "conditions",
}
GENERATOR_FIELDS = {
    "type",
    "version",
    "source_checked",
    "contains_real_data",
}
SPLIT_FIELDS = {"seed", "development_family_count"}
GATE_FIELDS = {
    "min_records_per_cell",
    "min_released_records",
    "max_duplicate_fraction",
    "require_all_conditions",
}
FAULT_FIELDS = {"inject_duplicate", "inject_missing_expected_action"}
CONDITION_FIELDS = {"expected_action", "critical", "templates"}
CANDIDATE_FIELDS = {
    "candidate_id",
    "family_id",
    "language",
    "scenario",
    "input",
    "expected_action",
    "critical",
    "synthetic",
    "provenance",
}
PROVENANCE_FIELDS = {
    "generator_type",
    "generator_version",
    "template_id",
    "variables",
    "contains_real_data",
}
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)")


class ContractError(ValueError):
    """Raised when an input does not satisfy the frozen data contract."""


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


def _require_exact_fields(value: Any, expected: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{location} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ContractError(
            f"{location} fields mismatch; missing={missing}, unknown={unknown}"
        )
    return value


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{location} must be a non-empty string")
    return value


def _require_bool(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{location} must be a boolean")
    return value


def _require_int(value: Any, location: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractError(f"{location} must be an integer >= {minimum}")
    return value


def _require_number(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{location} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{location} must be a finite number")
    return number


def validate_spec(raw: Any) -> dict[str, Any]:
    spec = _require_exact_fields(raw, TOP_LEVEL_FIELDS, "spec")
    _require_string(spec["dataset_id"], "spec.dataset_id")
    _require_string(spec["dataset_version"], "spec.dataset_version")
    _require_string(spec["schema_version"], "spec.schema_version")
    _require_string(spec["purpose"], "spec.purpose")
    non_goals = spec["non_goals"]
    if not isinstance(non_goals, list) or not non_goals:
        raise ContractError("spec.non_goals must be a non-empty list")
    for index, item in enumerate(non_goals):
        _require_string(item, f"spec.non_goals[{index}]")

    generator = _require_exact_fields(
        spec["generator"], GENERATOR_FIELDS, "spec.generator"
    )
    for key in ("type", "version", "source_checked"):
        _require_string(generator[key], f"spec.generator.{key}")
    _require_bool(generator["contains_real_data"], "spec.generator.contains_real_data")

    split = _require_exact_fields(spec["split"], SPLIT_FIELDS, "spec.split")
    _require_int(split["seed"], "spec.split.seed")
    development_family_count = _require_int(
        split["development_family_count"],
        "spec.split.development_family_count",
        minimum=1,
    )

    gates = _require_exact_fields(
        spec["quality_gates"], GATE_FIELDS, "spec.quality_gates"
    )
    _require_int(gates["min_records_per_cell"], "spec.quality_gates.min_records_per_cell", 1)
    _require_int(gates["min_released_records"], "spec.quality_gates.min_released_records", 1)
    duplicate_fraction = _require_number(
        gates["max_duplicate_fraction"],
        "spec.quality_gates.max_duplicate_fraction",
    )
    if not 0.0 <= duplicate_fraction <= 1.0:
        raise ContractError("spec.quality_gates.max_duplicate_fraction must be in [0, 1]")
    _require_bool(
        gates["require_all_conditions"],
        "spec.quality_gates.require_all_conditions",
    )

    faults = _require_exact_fields(
        spec["teaching_faults"], FAULT_FIELDS, "spec.teaching_faults"
    )
    for key in FAULT_FIELDS:
        _require_bool(faults[key], f"spec.teaching_faults.{key}")

    conditions = spec["conditions"]
    if not isinstance(conditions, dict) or not conditions:
        raise ContractError("spec.conditions must be a non-empty object")
    family_count = 0
    for language, scenarios in conditions.items():
        _require_string(language, "spec.conditions language key")
        if not isinstance(scenarios, dict) or not scenarios:
            raise ContractError(f"spec.conditions.{language} must be a non-empty object")
        for scenario, raw_condition in scenarios.items():
            _require_string(scenario, f"spec.conditions.{language} scenario key")
            condition = _require_exact_fields(
                raw_condition,
                CONDITION_FIELDS,
                f"spec.conditions.{language}.{scenario}",
            )
            _require_string(
                condition["expected_action"],
                f"spec.conditions.{language}.{scenario}.expected_action",
            )
            _require_bool(
                condition["critical"],
                f"spec.conditions.{language}.{scenario}.critical",
            )
            templates = condition["templates"]
            if not isinstance(templates, list) or not templates:
                raise ContractError(
                    f"spec.conditions.{language}.{scenario}.templates must be non-empty"
                )
            for index, template in enumerate(templates):
                _require_string(
                    template,
                    f"spec.conditions.{language}.{scenario}.templates[{index}]",
                )
            family_count += 1
    if development_family_count >= family_count:
        raise ContractError(
            "development_family_count must leave at least one family for test"
        )
    return copy.deepcopy(spec)


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def condition_pairs(spec: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (language, scenario)
        for language, scenarios in spec["conditions"].items()
        for scenario in scenarios
    ]


def generate_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    order_number = 1
    generator = spec["generator"]
    for language, scenarios in spec["conditions"].items():
        for scenario, condition in scenarios.items():
            family_id = f"{language}-{scenario}"
            for template_index, template in enumerate(condition["templates"], start=1):
                order_id = f"SYN-{order_number:03d}"
                order_number += 1
                candidates.append(
                    {
                        "candidate_id": f"candidate-{family_id}-{template_index}",
                        "family_id": family_id,
                        "language": language,
                        "scenario": scenario,
                        "input": template.format(order_id=order_id),
                        "expected_action": condition["expected_action"],
                        "critical": condition["critical"],
                        "synthetic": True,
                        "provenance": {
                            "generator_type": generator["type"],
                            "generator_version": generator["version"],
                            "template_id": f"{language}/{scenario}/{template_index}",
                            "variables": {"order_id": order_id},
                            "contains_real_data": generator["contains_real_data"],
                        },
                    }
                )

    faults = spec["teaching_faults"]
    if faults["inject_duplicate"] and candidates:
        duplicate = copy.deepcopy(candidates[0])
        duplicate["candidate_id"] = "candidate-injected-duplicate"
        candidates.append(duplicate)
    if faults["inject_missing_expected_action"] and candidates:
        invalid = copy.deepcopy(candidates[-2 if faults["inject_duplicate"] else -1])
        invalid["candidate_id"] = "candidate-injected-missing-action"
        invalid["input"] = "deliberately fictional teaching sample missing a label"
        invalid.pop("expected_action", None)
        candidates.append(invalid)
    return candidates


def candidate_errors(candidate: Any, spec: dict[str, Any]) -> list[str]:
    if not isinstance(candidate, dict):
        return ["candidate-must-be-object"]
    actual = set(candidate)
    missing = sorted(CANDIDATE_FIELDS - actual)
    unknown = sorted(actual - CANDIDATE_FIELDS)
    errors = [f"missing:{field}" for field in missing]
    errors.extend(f"unknown:{field}" for field in unknown)
    if missing:
        return errors
    for field in ("candidate_id", "family_id", "language", "scenario", "input", "expected_action"):
        if not isinstance(candidate[field], str) or not candidate[field].strip():
            errors.append(f"{field}-must-be-nonempty-string")
    if candidate.get("synthetic") is not True:
        errors.append("synthetic-must-be-true")
    if not isinstance(candidate.get("critical"), bool):
        errors.append("critical-must-be-boolean")
    language = candidate.get("language")
    scenario = candidate.get("scenario")
    condition = spec["conditions"].get(language, {}).get(scenario)
    if condition is None:
        errors.append("unknown-condition")
    elif candidate.get("expected_action") != condition["expected_action"]:
        errors.append("expected-action-mismatch")
    provenance = candidate.get("provenance")
    errors.extend(
        provenance_errors(
            provenance,
            spec,
            language=language,
            scenario=scenario,
        )
    )
    text = candidate.get("input")
    if isinstance(text, str) and (EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text)):
        errors.append("possible-personal-data-pattern")
    return errors


def provenance_errors(
    provenance: Any,
    spec: dict[str, Any],
    *,
    language: Any,
    scenario: Any,
) -> list[str]:
    """Validate that sample-level lineage agrees with the frozen generator contract.

    Having the expected keys is not enough: a stale generator version or a template
    identifier from another condition would make a record look traceable while
    pointing at the wrong production evidence.
    """

    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS:
        return ["invalid-provenance-fields"]

    errors: list[str] = []
    generator = spec["generator"]
    if provenance["generator_type"] != generator["type"]:
        errors.append("provenance-generator-type-mismatch")
    if provenance["generator_version"] != generator["version"]:
        errors.append("provenance-generator-version-mismatch")
    if provenance["contains_real_data"] is not generator["contains_real_data"]:
        errors.append("provenance-source-mismatch")

    template_id = provenance["template_id"]
    expected_prefix = f"{language}/{scenario}/"
    if not isinstance(template_id, str) or not template_id.startswith(expected_prefix):
        errors.append("provenance-template-id-mismatch")
    variables = provenance["variables"]
    if not isinstance(variables, dict) or not variables:
        errors.append("provenance-variables-invalid")
    return errors


def filter_and_deduplicate(
    candidates: Iterable[dict[str, Any]], spec: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_content: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        errors = candidate_errors(candidate, spec)
        candidate_id = candidate.get("candidate_id", "<missing>")
        if isinstance(candidate_id, str) and candidate_id in seen_ids:
            errors.append("duplicate-candidate-id")
        if isinstance(candidate_id, str):
            seen_ids.add(candidate_id)
        if errors:
            rejected.append({"candidate_id": candidate_id, "stage": "contract", "reasons": sorted(errors)})
            continue
        key = (
            candidate["language"],
            candidate["scenario"],
            normalize(candidate["input"]),
        )
        if key in seen_content:
            rejected.append(
                {
                    "candidate_id": candidate_id,
                    "stage": "deduplication",
                    "reasons": ["normalized-exact-duplicate"],
                }
            )
            continue
        seen_content.add(key)
        accepted.append(copy.deepcopy(candidate))
    return accepted, rejected


def assign_splits(
    accepted: Iterable[dict[str, Any]], seed: int, development_family_count: int
) -> list[dict[str, Any]]:
    accepted_list = list(accepted)
    families = sorted({candidate["family_id"] for candidate in accepted_list})
    rng = random.Random(seed)
    rng.shuffle(families)
    development_families = set(families[:development_family_count])
    records: list[dict[str, Any]] = []
    for candidate in accepted_list:
        record = copy.deepcopy(candidate)
        record["id"] = record.pop("candidate_id").replace("candidate-", "syn-", 1)
        record["split"] = (
            "development" if record["family_id"] in development_families else "test"
        )
        records.append(record)
    return sorted(records, key=lambda item: item["id"])


def verify_records(records: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, bool]:
    normalized_keys = [
        (record["language"], record["scenario"], normalize(record["input"]))
        for record in records
    ]
    family_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        family_splits[record["family_id"]].add(record["split"])
    required_coverage = set(condition_pairs(spec))
    actual_coverage = {(record["language"], record["scenario"]) for record in records}
    checks = {
        "unique_ids": len(records) == len({record["id"] for record in records}),
        "unique_normalized_inputs": len(normalized_keys) == len(set(normalized_keys)),
        "families_do_not_cross_splits": all(len(value) == 1 for value in family_splits.values()),
        "development_and_test_exist": {record["split"] for record in records} == {"development", "test"},
        "required_conditions_covered": actual_coverage == required_coverage,
        "all_records_marked_synthetic": all(record["synthetic"] is True for record in records),
        "provenance_matches_generator_contract": all(
            not provenance_errors(
                record["provenance"],
                spec,
                language=record["language"],
                scenario=record["scenario"],
            )
            for record in records
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ContractError(f"released dataset integrity failure: {failed}")
    return checks


def content_fingerprint(spec: dict[str, Any], records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {"spec": spec, "records": records},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def quality_decision(
    spec: dict[str, Any],
    raw_count: int,
    records: list[dict[str, Any]],
    rejection_log: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    gates = spec["quality_gates"]
    coverage = Counter((record["language"], record["scenario"]) for record in records)
    hard_reasons: list[str] = []
    review_reasons: list[str] = []
    if gates["require_all_conditions"]:
        missing = sorted(set(condition_pairs(spec)) - set(coverage))
        if missing:
            hard_reasons.append(f"missing condition cell(s): {missing}")
    low_cells = sorted(
        f"{language}|{scenario}={coverage[(language, scenario)]}"
        for language, scenario in condition_pairs(spec)
        if coverage[(language, scenario)] < gates["min_records_per_cell"]
    )
    if low_cells:
        hard_reasons.append("condition coverage below gate: " + ", ".join(low_cells))
    if len(records) < gates["min_released_records"]:
        hard_reasons.append(
            f"released records {len(records)} < {gates['min_released_records']}"
        )
    duplicate_count = sum(
        item["stage"] == "deduplication" for item in rejection_log
    )
    duplicate_fraction = duplicate_count / raw_count if raw_count else 0.0
    if duplicate_fraction > gates["max_duplicate_fraction"]:
        review_reasons.append(
            "duplicate fraction "
            f"{duplicate_fraction:.3f} > {gates['max_duplicate_fraction']:.3f}"
        )
    if spec["generator"]["contains_real_data"]:
        hard_reasons.append(
            "generator declares real data; authorization and privacy review are required"
        )
    if hard_reasons:
        return "BLOCK", hard_reasons + review_reasons
    if review_reasons:
        return "REVIEW", review_reasons
    return "PASS", ["all frozen teaching gates passed"]


def build_dataset(spec: dict[str, Any]) -> dict[str, Any]:
    candidates = generate_candidates(spec)
    accepted, rejection_log = filter_and_deduplicate(candidates, spec)
    records = assign_splits(
        accepted,
        spec["split"]["seed"],
        spec["split"]["development_family_count"],
    )
    integrity = verify_records(records, spec)
    action, reasons = quality_decision(spec, len(candidates), records, rejection_log)
    coverage = Counter(
        f"{record['language']}|{record['scenario']}" for record in records
    )
    split_records = Counter(record["split"] for record in records)
    split_families: dict[str, set[str]] = defaultdict(set)
    for record in records:
        split_families[record["split"]].add(record["family_id"])
    return {
        "action": action,
        "reasons": reasons,
        "manifest": {
            "dataset_id": spec["dataset_id"],
            "dataset_version": spec["dataset_version"],
            "schema_version": spec["schema_version"],
            "purpose": spec["purpose"],
            "non_goals": spec["non_goals"],
            "generator": spec["generator"],
            "fingerprint": content_fingerprint(spec, records),
        },
        "counts": {
            "raw": len(candidates),
            "contract_rejected": sum(item["stage"] == "contract" for item in rejection_log),
            "duplicate_rejected": sum(item["stage"] == "deduplication" for item in rejection_log),
            "released": len(records),
        },
        "coverage": dict(sorted(coverage.items())),
        "splits": {
            split: {"records": split_records[split], "families": len(families)}
            for split, families in sorted(split_families.items())
        },
        "integrity": integrity,
        "rejection_log": rejection_log,
        "records": records,
        "limitations": [
            "Author-designed fictional templates only",
            "Balanced condition coverage is not production prevalence",
            "Normalized exact deduplication cannot detect semantic near-duplicates",
            "No differential privacy or anonymity guarantee",
            "No downstream utility claim without an independent real holdout",
        ],
    }


def run_from_path(path: Path) -> dict[str, Any]:
    return build_dataset(validate_spec(load_json(path)))


def self_test() -> None:
    first = run_from_path(DEFAULT_SPEC)
    second = run_from_path(DEFAULT_SPEC)
    expected_counts = {
        "raw": 14,
        "contract_rejected": 1,
        "duplicate_rejected": 1,
        "released": 12,
    }
    failures: list[str] = []
    if first["action"] != "PASS":
        failures.append("default action is not PASS")
    if first["counts"] != expected_counts:
        failures.append(f"unexpected counts: {first['counts']}")
    if len(first["coverage"]) != 6 or set(first["coverage"].values()) != {2}:
        failures.append("unexpected condition coverage")
    if first["manifest"]["fingerprint"] != second["manifest"]["fingerprint"]:
        failures.append("fingerprint is not deterministic")
    if not all(first["integrity"].values()):
        failures.append("integrity checks are not all true")
    if failures:
        raise ContractError("self-test failed: " + "; ".join(failures))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"self_test": "passed"}, ensure_ascii=False))
            return 0
        report = run_from_path(args.spec)
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["action"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
