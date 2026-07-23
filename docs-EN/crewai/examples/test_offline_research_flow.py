"""Tests that remain effective when Python runs with optimization enabled."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

import offline_research_flow as project


class ProjectTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = Path(__file__).with_name("sources.json")
        cls.catalog = project.load_catalog(cls.fixture_path)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)


class CatalogTests(ProjectTestCase):
    def test_fixture_is_valid(self) -> None:
        project.validate_catalog(self.catalog)
        self.assertEqual(len(self.catalog["sources"]), 2)

    def test_catalog_must_be_object(self) -> None:
        with self.assertRaises(project.FlowError):
            project.validate_catalog([])

    def test_unknown_top_level_field_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["extra"] = True
        with self.assertRaises(project.FlowError):
            project.validate_catalog(catalog)

    def test_schema_version_is_strict(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["schema_version"] = 2
        with self.assertRaises(project.FlowError):
            project.validate_catalog(catalog)

    def test_duplicate_source_id_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["sources"][1]["id"] = catalog["sources"][0]["id"]
        with self.assertRaises(project.FlowError):
            project.validate_catalog(catalog)

    def test_invalid_source_id_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["sources"][0]["id"] = "sourcé"
        with self.assertRaises(project.FlowError):
            project.validate_catalog(catalog)

    def test_empty_claim_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["sources"][0]["claims"] = [" "]
        with self.assertRaises(project.FlowError):
            project.validate_catalog(catalog)

    def test_invalid_json_file_is_rejected(self) -> None:
        path = self.root / "bad.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(project.FlowError):
            project.load_catalog(path)


class TaskContractTests(ProjectTestCase):
    def test_researcher_selects_matching_sources(self) -> None:
        research = project.run_researcher_task("Agent reliability", self.catalog)
        self.assertEqual(len(research["claims"]), 2)
        self.assertEqual(research["unknowns"], [])

    def test_researcher_marks_unknown_topic(self) -> None:
        research = project.run_researcher_task(
            "A topic that is not in the catalog", self.catalog
        )
        self.assertEqual(research["claims"], [])
        self.assertEqual(len(research["unknowns"]), 1)

    def test_empty_topic_is_rejected(self) -> None:
        with self.assertRaises(project.FlowError):
            project.run_researcher_task(" ", self.catalog)

    def test_research_unknown_source_is_rejected(self) -> None:
        research = {
            "topic": "x",
            "claims": [{"text": "claim", "source_ids": ["missing"]}],
            "unknowns": [],
        }
        with self.assertRaises(project.FlowError):
            project.validate_research(research, self.catalog)

    def test_writer_emits_every_citation(self) -> None:
        research = project.run_researcher_task("Agent reliability", self.catalog)
        draft = project.run_writer_task(research)
        self.assertIn("[source-1]", draft["markdown"])
        self.assertIn("[source-2]", draft["markdown"])

    def test_writer_can_create_revision_record(self) -> None:
        research = project.run_researcher_task("Agent reliability", self.catalog)
        draft = project.run_writer_task(research, "Add the missing citation")
        self.assertEqual(draft["revision_note"], "Add the missing citation")
        self.assertIn("Revision record", draft["markdown"])

    def test_reviewer_detects_missing_citation(self) -> None:
        research = project.run_researcher_task("Agent reliability", self.catalog)
        draft = project.run_writer_task(research, omit_first_citation=True)
        review = project.run_reviewer_task(research, draft, self.catalog)
        self.assertFalse(review["passed"])
        self.assertEqual(review["missing_citations"], ["source-1"])

    def test_reviewer_rejects_no_claims(self) -> None:
        research = project.run_researcher_task(
            "A topic that is not in the catalog", self.catalog
        )
        draft = project.run_writer_task(research)
        review = project.run_reviewer_task(research, draft, self.catalog)
        self.assertFalse(review["passed"])
        self.assertIn("no sourced conclusion is publishable", review["reasons"])

    def test_review_contradiction_is_rejected(self) -> None:
        review = {
            "passed": True,
            "reasons": ["bad"],
            "missing_citations": [],
            "unknown_sources": [],
        }
        with self.assertRaises(project.FlowError):
            project.validate_review(review)


class FlowTests(ProjectTestCase):
    def test_normal_flow_is_ready_in_one_attempt(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        self.assertEqual(state["stage"], "ready_to_publish")
        self.assertEqual(state["attempt"], 1)

    def test_forced_revision_uses_two_attempts(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog, force_revision=True)
        self.assertEqual(state["stage"], "ready_to_publish")
        self.assertEqual(state["attempt"], 2)
        self.assertIn("routed:revise", [event["type"] for event in state["events"]])

    def test_forced_failure_stops_for_human(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog, force_failure=True)
        self.assertEqual(state["stage"], "human_review")
        self.assertEqual(state["attempt"], 2)

    def test_unknown_topic_stops_for_human(self) -> None:
        state = project.run_flow("A topic that is not in the catalog", self.catalog)
        self.assertEqual(state["stage"], "human_review")

    def test_attempt_budget_is_required(self) -> None:
        with self.assertRaises(project.FlowError):
            project.run_flow("Agent reliability", self.catalog, max_attempts=0)

    def test_boolean_attempt_budget_is_rejected(self) -> None:
        with self.assertRaises(project.FlowError):
            project.run_flow("Agent reliability", self.catalog, max_attempts=True)

    def test_events_are_contiguous(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog, force_revision=True)
        self.assertEqual(
            [event["sequence"] for event in state["events"]],
            list(range(1, len(state["events"]) + 1)),
        )

    def test_operation_id_is_deterministic_for_frozen_inputs(self) -> None:
        first = project.run_flow("Agent reliability", self.catalog)
        second = project.run_flow("Agent reliability", self.catalog)
        self.assertEqual(first["operation_id"], second["operation_id"])

    def test_state_unknown_field_is_rejected(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        state["extra"] = True
        with self.assertRaises(project.FlowError):
            project.validate_state(state)

    def test_terminal_state_requires_result(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        state["result"] = None
        with self.assertRaises(project.FlowError):
            project.validate_state(state)

    def test_state_rejects_unknown_research_source_against_catalog(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        state["result"]["research"]["claims"][0]["source_ids"] = ["missing"]
        with self.assertRaises(project.FlowError):
            project.validate_state(state, self.catalog)


class PublicationTests(ProjectTestCase):
    def test_publish_writes_validated_draft(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        output = self.root / "brief.md"
        project.publish_report(output, state, self.catalog)
        self.assertEqual(state["stage"], "published")
        self.assertEqual(
            output.read_text(encoding="utf-8"),
            state["result"]["draft"]["markdown"],
        )

    def test_publish_is_idempotent_for_same_content(self) -> None:
        first = project.run_flow("Agent reliability", self.catalog)
        output = self.root / "brief.md"
        project.publish_report(output, first, self.catalog)
        original = output.read_text(encoding="utf-8")
        second = project.run_flow("Agent reliability", self.catalog)
        project.publish_report(output, second, self.catalog)
        self.assertTrue(second["publication"]["recovered"])
        self.assertEqual(output.read_text(encoding="utf-8"), original)

    def test_publish_refuses_different_existing_content(self) -> None:
        output = self.root / "brief.md"
        output.write_text("other", encoding="utf-8")
        state = project.run_flow("Agent reliability", self.catalog)
        with self.assertRaises(project.FlowError):
            project.publish_report(output, state, self.catalog)

    def test_human_review_cannot_publish(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog, force_failure=True)
        with self.assertRaises(project.FlowError):
            project.publish_report(self.root / "brief.md", state, self.catalog)

    def test_temporary_file_is_not_left_after_publish(self) -> None:
        output = self.root / "brief.md"
        state = project.run_flow("Agent reliability", self.catalog)
        project.publish_report(output, state, self.catalog)
        self.assertFalse((self.root / "brief.md.tmp").exists())

    def test_publish_rejects_catalog_changed_after_review(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        changed_catalog = copy.deepcopy(self.catalog)
        changed_catalog["sources"][0]["title"] = "Updated source title"
        output = self.root / "brief.md"

        with self.assertRaisesRegex(
            project.FlowError, "current source catalog version"
        ):
            project.publish_report(output, state, changed_catalog)

        self.assertFalse(output.exists())

    def test_publish_rechecks_reviewer_before_effect(self) -> None:
        state = project.run_flow("Agent reliability", self.catalog)
        state["result"]["draft"]["markdown"] = state["result"]["draft"][
            "markdown"
        ].replace("[source-1]", "", 1)
        output = self.root / "brief.md"

        with self.assertRaisesRegex(project.FlowError, "trusted reviewer"):
            project.publish_report(output, state, self.catalog)

        self.assertFalse(output.exists())


class CliTests(ProjectTestCase):
    def call_main(self, *arguments: str) -> tuple[int, dict[str, object]]:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = project.main(["--sources", str(self.fixture_path), *arguments])
        return code, json.loads(stream.getvalue())

    def test_cli_ready_output_is_json(self) -> None:
        code, payload = self.call_main("--topic", "Agent reliability")
        self.assertEqual(code, 0)
        self.assertEqual(payload["stage"], "ready_to_publish")

    def test_cli_can_publish(self) -> None:
        output = self.root / "brief.md"
        code, payload = self.call_main(
            "--topic",
            "Agent reliability",
            "--output",
            str(output),
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["stage"], "published")
        self.assertTrue(output.exists())

    def test_cli_failure_exit_code(self) -> None:
        code, payload = self.call_main(
            "--topic",
            "Agent reliability",
            "--force-failure",
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["stage"], "human_review")

    def test_cli_invalid_catalog_exit_code(self) -> None:
        bad = self.root / "bad.json"
        bad.write_text("[]", encoding="utf-8")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = project.main(["--sources", str(bad)])
        payload = json.loads(stream.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(payload["stage"], "error")


if __name__ == "__main__":
    unittest.main()
