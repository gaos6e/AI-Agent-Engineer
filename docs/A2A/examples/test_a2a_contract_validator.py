"""Offline tests for the A2A teaching contract validator."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from a2a_contract_validator import (
    load_cases,
    run_cases,
    validate_agent_card,
    validate_part,
    validate_task_snapshots,
)


FIXTURE = Path(__file__).with_name("a2a_cases.json")


class A2AContractValidatorTests(unittest.TestCase):
    def test_fixture_expectations_match_validator(self) -> None:
        passed, failed = run_cases(load_cases(FIXTURE))
        self.assertEqual(failed, [])
        self.assertEqual(
            passed,
            [
                "valid-v1-contract",
                "reject-v03-shape",
                "reject-terminal-regression",
                "reject-ambiguous-part",
            ],
        )

    def test_agent_card_rejects_non_https_production_url(self) -> None:
        card = load_cases(FIXTURE)[0]["agentCard"] | {
            "supportedInterfaces": [
                {
                    "url": "http://agent.example.test/a2a",
                    "protocolBinding": "HTTP+JSON",
                    "protocolVersion": "1.0",
                }
            ]
        }
        errors = validate_agent_card(card)
        self.assertTrue(any("absolute HTTPS URL" in error for error in errors))

    def test_custom_binding_requires_absolute_uri(self) -> None:
        card = load_cases(FIXTURE)[0]["agentCard"] | {
            "supportedInterfaces": [
                {
                    "url": "https://agent.example.test/a2a",
                    "protocolBinding": "WEBSOCKET",
                    "protocolVersion": "1.0",
                }
            ]
        }
        errors = validate_agent_card(card)
        self.assertTrue(any("core binding or an absolute" in error for error in errors))

    def test_part_accepts_one_structured_data_member(self) -> None:
        self.assertEqual(validate_part({"data": {"ok": True}}, "part"), [])

    def test_part_rejects_invalid_base64_raw_member(self) -> None:
        errors = validate_part({"raw": "not base64!"}, "part")
        self.assertTrue(any("valid base64" in error for error in errors))

    def test_part_accepts_valid_base64_raw_member(self) -> None:
        self.assertEqual(validate_part({"raw": "YTIyYQ=="}, "part"), [])

    def test_fixture_rejects_duplicate_json_fields(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "duplicate.json"
            fixture.write_text(
                '{"cases": [], "cases": [{"name": "shadowed"}]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate JSON field: cases"):
                load_cases(fixture)

    def test_fixture_rejects_nonstandard_json_number(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "nan.json"
            fixture.write_text('{"cases": [NaN]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-standard JSON number: NaN"):
                load_cases(fixture)

    def test_completed_task_requires_artifact(self) -> None:
        errors = validate_task_snapshots(
            [
                {
                    "id": "task-no-artifact",
                    "contextId": "context-no-artifact",
                    "status": {"state": "TASK_STATE_COMPLETED"},
                }
            ]
        )
        self.assertTrue(any("artifacts must be a non-empty list" in error for error in errors))

    def test_task_identity_cannot_change_within_sequence(self) -> None:
        errors = validate_task_snapshots(
            [
                {
                    "id": "task-a",
                    "contextId": "context-a",
                    "status": {"state": "TASK_STATE_WORKING"},
                },
                {
                    "id": "task-b",
                    "contextId": "context-a",
                    "status": {"state": "TASK_STATE_FAILED"},
                },
            ]
        )
        self.assertTrue(any("id changed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
