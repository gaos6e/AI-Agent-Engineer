"""Tests for the deterministic context-pack builder."""

from __future__ import annotations

import copy
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

import context_budget


class ContextBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = Path(__file__).with_name("chunks.json")
        cls.schema_path = context_budget.OUTPUT_SCHEMA
        cls.raw = json.loads(cls.fixture_path.read_text(encoding="utf-8"))

    def write_fixture(self, directory: Path, data: object) -> Path:
        path = directory / "chunks.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def test_sample_fixture_and_expected_selection(self) -> None:
        fixture = context_budget.load_fixture(self.fixture_path)
        pack = context_budget.build_context_pack(fixture)
        self.assertEqual(fixture.fixture_version, "context-pack-2026-07-14-v1")
        self.assertEqual(len(fixture.chunks), 11)
        self.assertEqual(pack.budget_tokens, 170)
        self.assertEqual(pack.used_tokens, 162)
        self.assertEqual(pack.remaining_tokens, 8)
        self.assertEqual(
            [chunk.chunk_id for chunk in pack.selected],
            [
                "policy",
                "task-state",
                "current-refund-policy",
                "refund-faq",
                "current-input",
            ],
        )

    def test_strict_json_rejects_duplicate_keys_and_non_finite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.json"
            duplicate.write_text(
                '{"fixture_version":"a","fixture_version":"b"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(context_budget.ContextPackError, "duplicate"):
                context_budget.load_fixture(duplicate)
            non_finite = root / "non-finite.json"
            non_finite.write_text('{"x": NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "non-finite"
            ):
                context_budget.load_fixture(non_finite)

    def test_root_and_request_fields_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mutate in (
                lambda raw: raw.pop("selector_version"),
                lambda raw: raw.update(extra=True),
                lambda raw: raw["request"].pop("as_of"),
                lambda raw: raw["request"].update(extra=True),
            ):
                raw = copy.deepcopy(self.raw)
                mutate(raw)
                with self.assertRaisesRegex(
                    context_budget.ContextPackError, "invalid fields"
                ):
                    context_budget.load_fixture(self.write_fixture(root, raw))

    def test_request_values_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = (
                ("as_of", "2026/07/14", "YYYY-MM-DD"),
                ("pack_budget_tokens", True, "integer"),
                ("pack_budget_tokens", 0, "between"),
                ("granted_permissions", [], "non-empty"),
                ("allowed_trust", ["secret"], "unsupported"),
            )
            for field, value, message in cases:
                with self.subTest(field=field, value=value):
                    raw = copy.deepcopy(self.raw)
                    raw["request"][field] = value
                    with self.assertRaisesRegex(
                        context_budget.ContextPackError, message
                    ):
                        context_budget.load_fixture(
                            self.write_fixture(root, raw)
                        )

    def test_chunk_fields_types_and_enums_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mutations = (
                (lambda item: item.pop("source_uri"), "invalid fields"),
                (lambda item: item.update(extra=True), "invalid fields"),
                (lambda item: item.update(section="hidden"), "unsupported"),
                (lambda item: item.update(source_uri="relative"), "absolute URI"),
                (lambda item: item.update(trust="secret"), "unsupported"),
                (lambda item: item.update(priority=True), "integer"),
                (lambda item: item.update(required=1), "boolean"),
                (lambda item: item.update(content=""), "non-blank"),
            )
            for mutate, message in mutations:
                raw = copy.deepcopy(self.raw)
                mutate(raw["chunks"][0])
                with self.assertRaisesRegex(
                    context_budget.ContextPackError, message
                ):
                    context_budget.load_fixture(self.write_fixture(root, raw))

    def test_duplicate_ids_and_invalid_date_ranges_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = copy.deepcopy(self.raw)
            duplicate["chunks"][1]["id"] = duplicate["chunks"][0]["id"]
            with self.assertRaisesRegex(context_budget.ContextPackError, "unique"):
                context_budget.load_fixture(self.write_fixture(root, duplicate))
            dates = copy.deepcopy(self.raw)
            dates["chunks"][0]["expires_on"] = "2026-07-01"
            with self.assertRaisesRegex(context_budget.ContextPackError, "later"):
                context_budget.load_fixture(self.write_fixture(root, dates))

    def test_required_chunk_cannot_share_a_dedupe_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            raw["chunks"][1]["dedupe_key"] = raw["chunks"][0]["dedupe_key"]
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "required chunks"
            ):
                context_budget.load_fixture(
                    self.write_fixture(Path(temporary), raw)
                )

    def test_dedupe_group_cannot_cross_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            mirror = next(
                item for item in raw["chunks"] if item["id"] == "mirror-refund-policy"
            )
            mirror["section"] = "current-input"
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "section"
            ):
                context_budget.load_fixture(
                    self.write_fixture(Path(temporary), raw)
                )

    def test_dedupe_group_cannot_cross_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            mirror = next(
                item for item in raw["chunks"] if item["id"] == "mirror-refund-policy"
            )
            mirror["required_permission"] = "public-read"
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "required_permission"
            ):
                context_budget.load_fixture(
                    self.write_fixture(Path(temporary), raw)
                )

    def test_dedupe_group_cannot_cross_trust_classes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            mirror = next(
                item for item in raw["chunks"] if item["id"] == "mirror-refund-policy"
            )
            mirror["trust"] = "user-input"
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "trust"
            ):
                context_budget.load_fixture(
                    self.write_fixture(Path(temporary), raw)
                )

    def test_all_optional_exclusion_reasons_are_visible(self) -> None:
        fixture = context_budget.load_fixture(self.fixture_path)
        pack = context_budget.build_context_pack(fixture)
        reasons = {item.chunk_id: item.reason for item in pack.excluded}
        self.assertEqual(reasons["legal-note"], "permission_denied")
        self.assertEqual(reasons["forum-claim"], "trust_denied")
        self.assertEqual(reasons["future-refund-policy"], "not_yet_effective")
        self.assertEqual(reasons["old-refund-policy"], "expired")
        self.assertEqual(reasons["mirror-refund-policy"], "duplicate")
        self.assertEqual(reasons["shipping-note"], "budget")
        self.assertEqual(set(reasons.values()), context_budget.EXCLUSION_REASONS)

    def test_required_gate_failure_is_not_silently_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mutations = (
                lambda raw: raw["request"]["granted_permissions"].remove(
                    "policy-read"
                ),
                lambda raw: raw["request"]["allowed_trust"].remove(
                    "application-policy"
                ),
                lambda raw: raw["chunks"][0].update(
                    effective_from="2026-08-01"
                ),
                lambda raw: raw["chunks"][0].update(expires_on="2026-07-14"),
            )
            for mutate in mutations:
                raw = copy.deepcopy(self.raw)
                mutate(raw)
                fixture = context_budget.load_fixture(
                    self.write_fixture(root, raw)
                )
                with self.assertRaisesRegex(
                    context_budget.ContextPackError, "required chunk"
                ):
                    context_budget.build_context_pack(fixture)

    def test_required_budget_overflow_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            raw["request"]["pack_budget_tokens"] = 79
            fixture = context_budget.load_fixture(
                self.write_fixture(Path(temporary), raw)
            )
            with self.assertRaisesRegex(
                context_budget.ContextPackError, "required chunks exceed"
            ):
                context_budget.build_context_pack(fixture)

    def test_dedupe_uses_priority_then_date_then_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            mirror = next(
                item for item in raw["chunks"] if item["id"] == "mirror-refund-policy"
            )
            mirror["priority"] = 99
            fixture = context_budget.load_fixture(
                self.write_fixture(Path(temporary), raw)
            )
            pack = context_budget.build_context_pack(fixture)
            selected = {chunk.chunk_id for chunk in pack.selected}
            reasons = {item.chunk_id: item.reason for item in pack.excluded}
            self.assertIn("mirror-refund-policy", selected)
            self.assertEqual(reasons["current-refund-policy"], "duplicate")

    def test_selection_is_deterministic_when_input_order_changes(self) -> None:
        baseline = context_budget.build_context_pack(
            context_budget.load_fixture(self.fixture_path)
        ).as_dict()
        with tempfile.TemporaryDirectory() as temporary:
            raw = copy.deepcopy(self.raw)
            random.Random(20260714).shuffle(raw["chunks"])
            shuffled = context_budget.build_context_pack(
                context_budget.load_fixture(
                    self.write_fixture(Path(temporary), raw)
                )
            ).as_dict()
        self.assertEqual(shuffled, baseline)

    def test_output_schema_matches_runtime_contract(self) -> None:
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        pack = context_budget.build_context_pack(
            context_budget.load_fixture(self.fixture_path)
        ).as_dict()
        self.assertEqual(set(schema["required"]), set(pack))
        self.assertFalse(schema["additionalProperties"])
        selected_required = set(schema["properties"]["selected"]["items"]["required"])
        self.assertEqual(selected_required, set(pack["selected"][0]))
        reason_enum = set(
            schema["properties"]["excluded"]["items"]["properties"]["reason"][
                "enum"
            ]
        )
        self.assertEqual(reason_enum, context_budget.EXCLUSION_REASONS)

    def test_cli_success_writes_a_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "pack.json"
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = context_budget.run(
                ["--fixture", str(self.fixture_path), "--json-pack", str(output_path)],
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("budget=170 used=162 remaining=8", stdout.getvalue())
            pack = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(pack["used_tokens"], 162)

    def test_cli_failure_returns_two_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = copy.deepcopy(self.raw)
            raw["request"]["granted_permissions"].remove("policy-read")
            path = self.write_fixture(root, raw)
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = context_budget.run(
                ["--fixture", str(path)], stdout=stdout, stderr=stderr
            )
            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("required chunk", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
