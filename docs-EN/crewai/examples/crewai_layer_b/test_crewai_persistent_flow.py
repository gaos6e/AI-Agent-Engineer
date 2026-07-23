from __future__ import annotations

import gc
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
import warnings


# Keep all CrewAI switches ahead of the module's CrewAI import.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TESTING", "true")

# CrewAI 1.15.4's transitive OpenTelemetry/import hooks emit these two known
# Python 3.11 warnings during import. Keep the allowlist exact so -W error
# still catches warnings from this example and future, differently worded ones.
warnings.filterwarnings(
    "ignore",
    message=r"SelectableGroups dict interface is deprecated\. Use select\.",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"Cannot set an attribute on 'crewai\.rag' for child module 'embeddings'",
    category=ImportWarning,
)

from crewai_persistent_flow import (  # noqa: E402
    InjectedCrash,
    ReceiptStore,
    fork_flow,
    inspect_flow,
    resume_flow,
    start_flow,
)
from crewai.events.listeners.tracing.utils import should_enable_tracing  # noqa: E402


class CrewAIPersistentFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.state_database = root / "flow-state.sqlite3"
        self.effect_database = root / "effect-receipts.sqlite3"

    def tearDown(self) -> None:
        gc.collect()
        self.temporary_directory.cleanup()

    def start(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "state_database": self.state_database,
            "effect_database": self.effect_database,
            "topic": "  agent   reliability  ",
            "operation_id": "publish-001",
        }
        arguments.update(overrides)
        return start_flow(**arguments)

    def test_locked_runtime_version_and_key_free_route(self) -> None:
        result = self.start()

        self.assertEqual(importlib.metadata.version("crewai"), "1.15.4")
        self.assertFalse(should_enable_tracing(override=False))
        self.assertEqual(result["stage"], "done")
        self.assertEqual(result["topic"], "agent reliability")
        self.assertEqual(result["result"], "PUBLISHED:AGENT RELIABILITY")
        self.assertEqual(result["effect_count"], 1)
        self.assertIn("router:route_execute", result["steps"])

    def test_old_schema_is_rejected_before_effect(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported schema_version"):
            self.start(schema_version=0)

        self.assertEqual(ReceiptStore(self.effect_database).effect_count("publish-001"), 0)

    def test_operation_id_rejects_a_different_payload_without_a_second_effect(self) -> None:
        self.start()

        with self.assertRaisesRegex(ValueError, "different payload"):
            start_flow(
                state_database=self.state_database,
                effect_database=self.effect_database,
                topic="different topic",
                operation_id="publish-001",
            )

        self.assertEqual(ReceiptStore(self.effect_database).effect_count("publish-001"), 1)

    def test_same_uuid_hydrates_and_does_not_repeat_effect(self) -> None:
        first = self.start()
        resumed = resume_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=str(first["flow_id"]),
        )

        self.assertEqual(resumed["flow_id"], first["flow_id"])
        self.assertEqual(resumed["effect_count"], 1)
        self.assertIn("prepare:already_done", resumed["steps"])

    def test_flow_id_normalization_is_consistent_across_inspect_and_resume(self) -> None:
        first = self.start()
        raw_flow_id = f"  {first['flow_id']}  "

        inspected = inspect_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=raw_flow_id,
        )
        resumed = resume_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=raw_flow_id,
        )

        self.assertEqual(inspected["flow_id"], first["flow_id"])
        self.assertEqual(resumed["flow_id"], first["flow_id"])

    def test_fork_hydrates_snapshot_under_a_new_uuid(self) -> None:
        first = self.start()
        forked = fork_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=str(first["flow_id"]),
        )

        self.assertNotEqual(forked["flow_id"], first["flow_id"])
        self.assertEqual(forked["forked_from"], first["flow_id"])
        self.assertEqual(forked["effect_count"], 1)

    def test_unknown_uuid_fails_closed_for_resume_and_fork(self) -> None:
        self.start()
        unknown = str(uuid4())
        for operation in (resume_flow, fork_flow):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(ValueError, "unknown flow_id"):
                    operation(
                        state_database=self.state_database,
                        effect_database=self.effect_database,
                        flow_id=unknown,
                    )

    def test_crash_after_receipt_then_resume_has_one_effect(self) -> None:
        with self.assertRaises(InjectedCrash) as captured:
            self.start(crash_after_receipt=True)
        flow_id = captured.exception.flow_id
        persisted = inspect_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=flow_id,
        )
        resumed = resume_flow(
            state_database=self.state_database,
            effect_database=self.effect_database,
            flow_id=flow_id,
        )

        self.assertEqual(persisted["stage"], "prepared")
        self.assertEqual(persisted["effect_count"], 1)
        self.assertEqual(resumed["stage"], "done")
        self.assertTrue(resumed["recovered_receipt"])
        self.assertEqual(resumed["effect_count"], 1)

    def test_two_process_failure_recovery_is_utf8_and_machine_readable(self) -> None:
        script = Path(__file__).with_name("crewai_persistent_flow.py")
        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONUTF8": "1",
                "CREWAI_DISABLE_TELEMETRY": "true",
                "CREWAI_TESTING": "true",
            }
        )
        common = [
            sys.executable,
            "-B",
            str(script),
            "--state-db",
            str(self.state_database),
            "--effect-db",
            str(self.effect_database),
        ]
        failed = subprocess.run(
            [
                *common,
                "start",
                "--topic",
                "process recovery",
                "--operation-id",
                "publish-process-001",
                "--crash-after-receipt",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        failure_line = failed.stderr.strip().splitlines()[-1]
        failure = json.loads(failure_line)
        resumed = subprocess.run(
            [*common, "resume", "--flow-id", failure["flow_id"]],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

        self.assertEqual(failed.returncode, 3, failed.stderr)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)["effect_count"], 1)
        combined_stderr = f"{failed.stderr}\n{resumed.stderr}"
        self.assertNotIn("codec can't encode", combined_stderr)
        self.assertNotIn("CrewAIEventsBus", combined_stderr)


if __name__ == "__main__":
    unittest.main()
