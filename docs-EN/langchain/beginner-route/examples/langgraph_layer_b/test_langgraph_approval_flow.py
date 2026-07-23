from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from langgraph_approval_flow import (
    inspect_workflow,
    open_graph,
    resume_workflow,
    start_workflow,
)


class PausedSnapshotGraph:
    """Minimal graph boundary used to prove resume rejects before invocation."""

    def __init__(self, values: dict[str, object]) -> None:
        self.snapshot = SimpleNamespace(
            values=values,
            next=("review",),
            tasks=(SimpleNamespace(interrupts=(object(),)),),
        )
        self.invocations: list[object] = []

    def get_state(self, _config: object) -> SimpleNamespace:
        return self.snapshot

    def invoke(self, input_value: object, *_args: object, **_kwargs: object) -> None:
        self.invocations.append(input_value)


class LangGraphApprovalFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "checkpoints.sqlite3"
        self.thread_id = "tenant-a:workflow-1"
        self.owner_id = "tenant-a"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_start_pauses_with_bound_approval_payload(self) -> None:
        with open_graph(self.database) as graph:
            result = start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="  agent   reliability  ",
            )

        self.assertEqual(result["status"], "awaiting_approval")
        self.assertEqual(result["next"], ["review"])
        self.assertEqual(len(result["pending_interrupts"]), 1)
        payload = result["pending_interrupts"][0]
        self.assertEqual(payload["kind"], "approval")
        self.assertEqual(payload["preview"], "agent reliability")
        self.assertEqual(
            payload["action_fingerprint"],
            result["action_fingerprint"],
        )

    def test_approve_after_reopening_database_and_observe_node_replay(self) -> None:
        entries: list[str] = []
        with open_graph(
            self.database,
            on_review_enter=lambda: entries.append("review"),
        ) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="hello agent",
            )

        with open_graph(
            self.database,
            on_review_enter=lambda: entries.append("review"),
        ) as graph:
            result = resume_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                approved=True,
                reviewer="reviewer-a",
            )
            snapshot = graph.get_state(
                {"configurable": {"thread_id": self.thread_id}}
            )

        self.assertEqual(entries, ["review", "review"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["next"], [])
        self.assertEqual(snapshot.values["dry_run_result"], "HELLO AGENT")
        self.assertTrue(snapshot.values["dry_run_receipt"].startswith("sha256:"))

    def test_rejection_is_a_terminal_state_without_a_receipt(self) -> None:
        with open_graph(self.database) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="do not run",
            )
            result = resume_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                approved=False,
                reviewer="reviewer-b",
            )
            snapshot = graph.get_state(
                {"configurable": {"thread_id": self.thread_id}}
            )

        self.assertEqual(result["status"], "rejected")
        self.assertNotIn("dry_run_receipt", snapshot.values)

    def test_new_thread_is_empty_and_repeated_start_is_rejected(self) -> None:
        with open_graph(self.database) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="first",
            )
            empty = inspect_workflow(
                graph,
                "tenant-a:workflow-2",
                owner_id=self.owner_id,
            )
            with self.assertRaisesRegex(ValueError, "already has checkpoint state"):
                start_workflow(
                    graph,
                    thread_id=self.thread_id,
                    owner_id=self.owner_id,
                    text="second",
                )

        self.assertFalse(empty["exists"])
        self.assertEqual(empty["next"], [])

    def test_thread_id_normalization_survives_reopen_and_resume(self) -> None:
        raw_thread_id = "  tenant-a:workflow-whitespace  "
        with open_graph(self.database) as graph:
            started = start_workflow(
                graph,
                thread_id=raw_thread_id,
                owner_id=self.owner_id,
                text="normalized key",
            )

        self.assertEqual(started["thread_id"], "tenant-a:workflow-whitespace")
        with open_graph(self.database) as graph:
            resumed = resume_workflow(
                graph,
                thread_id=raw_thread_id,
                owner_id=self.owner_id,
                approved=True,
                reviewer="reviewer-normalized",
            )
            inspected = inspect_workflow(
                graph,
                "tenant-a:workflow-whitespace",
                owner_id=self.owner_id,
            )

        self.assertEqual(resumed["status"], "completed")
        self.assertEqual(inspected["thread_id"], "tenant-a:workflow-whitespace")

    def test_application_rejects_missing_and_completed_thread_resume(self) -> None:
        with open_graph(self.database) as graph:
            with self.assertRaisesRegex(ValueError, "no checkpoint state"):
                resume_workflow(
                    graph,
                    thread_id=self.thread_id,
                    owner_id=self.owner_id,
                    approved=True,
                    reviewer="reviewer",
                )
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="finish me",
            )
            with self.assertRaisesRegex(ValueError, "owner"):
                resume_workflow(
                    graph,
                    thread_id=self.thread_id,
                    owner_id="tenant-b",
                    approved=True,
                    reviewer="reviewer",
                )
            resume_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                approved=True,
                reviewer="reviewer",
            )
            with self.assertRaisesRegex(ValueError, "not paused"):
                resume_workflow(
                    graph,
                    thread_id=self.thread_id,
                    owner_id=self.owner_id,
                    approved=True,
                    reviewer="reviewer",
                )

    def test_tampered_fingerprint_fails_closed_and_can_be_retried(self) -> None:
        with open_graph(self.database) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="bound action",
            )
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                resume_workflow(
                    graph,
                    thread_id=self.thread_id,
                    owner_id=self.owner_id,
                    approved=True,
                    reviewer="reviewer",
                    fingerprint="0" * 64,
                )
            still_pending = inspect_workflow(
                graph,
                self.thread_id,
                owner_id=self.owner_id,
            )
            completed = resume_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                approved=True,
                reviewer="reviewer",
            )

        self.assertEqual(still_pending["next"], ["review"])
        self.assertEqual(completed["status"], "completed")

    def test_incompatible_checkpoint_versions_fail_closed_before_resume(self) -> None:
        incompatible_fields = {
            "schema_version": 999,
            "graph_version": "approval-flow-v0",
            "policy_version": "approval-policy-v0",
        }
        with open_graph(self.database) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="version guard",
            )
            values = dict(
                graph.get_state(
                    {"configurable": {"thread_id": self.thread_id}}
                ).values
            )

        for field, value in incompatible_fields.items():
            with self.subTest(field=field):
                tampered = dict(values)
                tampered[field] = value
                paused_graph = PausedSnapshotGraph(tampered)
                with self.assertRaisesRegex(ValueError, field):
                    resume_workflow(
                        paused_graph,
                        thread_id=self.thread_id,
                        owner_id=self.owner_id,
                        approved=True,
                        reviewer="reviewer",
                    )
                self.assertEqual(paused_graph.invocations, [])

        with open_graph(self.database) as graph:
            pending = inspect_workflow(
                graph,
                self.thread_id,
                owner_id=self.owner_id,
            )
        self.assertEqual(pending["next"], ["review"])

    def test_inconsistent_checkpoint_content_fails_closed_before_resume(self) -> None:
        with open_graph(self.database) as graph:
            start_workflow(
                graph,
                thread_id=self.thread_id,
                owner_id=self.owner_id,
                text="original action",
            )
            values = dict(
                graph.get_state(
                    {"configurable": {"thread_id": self.thread_id}}
                ).values
            )
            values["normalized_text"] = "different action"
            paused_graph = PausedSnapshotGraph(values)
            with self.assertRaisesRegex(ValueError, "normalized_text"):
                resume_workflow(
                    paused_graph,
                    thread_id=self.thread_id,
                    owner_id=self.owner_id,
                    approved=True,
                    reviewer="reviewer",
                )
            pending = inspect_workflow(
                graph,
                self.thread_id,
                owner_id=self.owner_id,
            )

        self.assertEqual(paused_graph.invocations, [])
        self.assertEqual(pending["next"], ["review"])

    def test_two_cli_processes_pause_inspect_and_resume(self) -> None:
        script = Path(__file__).with_name("langgraph_approval_flow.py")
        common = [
            sys.executable,
            "-B",
            str(script),
            "--db",
            str(self.database),
            "--thread-id",
            self.thread_id,
            "--owner-id",
            self.owner_id,
        ]
        environment = os.environ.copy()
        environment["LANGGRAPH_STRICT_MSGPACK"] = "true"
        start = subprocess.run(
            [*common, "start", "--text", "process restart"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        inspect = subprocess.run(
            [*common, "inspect"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        resume = subprocess.run(
            [
                *common,
                "resume",
                "--decision",
                "approve",
                "--reviewer",
                "process-reviewer",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertEqual(inspect.returncode, 0, inspect.stderr)
        self.assertEqual(resume.returncode, 0, resume.stderr)
        self.assertEqual(json.loads(start.stdout)["next"], ["review"])
        self.assertEqual(json.loads(inspect.stdout)["status"], "awaiting_approval")
        self.assertEqual(json.loads(resume.stdout)["status"], "completed")


if __name__ == "__main__":
    unittest.main()


