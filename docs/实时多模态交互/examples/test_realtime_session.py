from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from realtime_session import RealtimeSession, SessionContractError, run_fixture


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "session_fixture.json"
SCRIPT = HERE / "realtime_session.py"


def event(event_id: str, event_type: str, at_ms: int, **payload: object) -> dict[str, object]:
    return {"event_id": event_id, "type": event_type, "at_ms": at_ms, "payload": payload}


def feed_turn(
    session: RealtimeSession,
    *,
    prefix: str = "a",
    turn_id: str = "turn-1",
    response_id: str = "response-1",
) -> None:
    session.apply(event(f"{prefix}-1", "audio.frame", 0, turn_id=turn_id, sequence=0, duration_ms=20, speech=True))
    session.apply(event(f"{prefix}-2", "turn.commit", 20, turn_id=turn_id))
    session.apply(event(f"{prefix}-3", "response.started", 40, response_id=response_id, turn_id=turn_id))


class FixtureTests(unittest.TestCase):
    def test_fixture_covers_interrupt_tool_duplicate_and_resume(self) -> None:
        summary = run_fixture(FIXTURE)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["duplicate_events"], 1)
        self.assertEqual(summary["checkpoint_version"], 1)
        self.assertEqual(summary["responses"]["response-1"]["status"], "canceled")
        self.assertEqual(summary["responses"]["response-2"]["status"], "completed")
        self.assertEqual(summary["tool_calls"]["call-1"]["status"], "succeeded")

    def test_cli_emits_json_without_writing_artifacts(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "-W", "error", str(SCRIPT), str(FIXTURE)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["terminal_reason"], "user_goodbye")

    def test_fixture_schema_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_path = Path(temp_dir) / "bad.json"
            bad_path.write_text(
                json.dumps({"session": {"session_id": "s", "resume_token": "r"}, "events": [], "extra": 1}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SessionContractError, "keys mismatch"):
                run_fixture(bad_path)

    def test_fixture_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_path = Path(temp_dir) / "duplicate.json"
            bad_path.write_text(
                '{"session":{"session_id":"s","resume_token":"r"},'
                '"events":[],"events":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SessionContractError, "duplicate JSON key"):
                run_fixture(bad_path)

    def test_fixture_rejects_non_standard_json_constants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_path = Path(temp_dir) / "non-finite.json"
            bad_path.write_text(
                '{"session":{"session_id":"s","resume_token":"r"},'
                '"events":[{"event_id":"e1","type":"audio.frame",'
                '"at_ms":NaN,"payload":{}}]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SessionContractError, "non-standard JSON constant"
            ):
                run_fixture(bad_path)


class EventContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = RealtimeSession("session-1", "resume-1")

    def test_audio_frames_are_contiguous(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "contiguous"):
            self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=1, duration_ms=20, speech=True))
        self.assertNotIn("t1", self.session.turns)

    def test_silence_only_turn_cannot_commit(self) -> None:
        self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=20, speech=False))
        with self.assertRaisesRegex(SessionContractError, "silence-only"):
            self.session.apply(event("e2", "turn.commit", 20, turn_id="t1"))

    def test_audio_after_commit_is_rejected(self) -> None:
        self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=20, speech=True))
        self.session.apply(event("e2", "turn.commit", 20, turn_id="t1"))
        with self.assertRaisesRegex(SessionContractError, "committed turn"):
            self.session.apply(event("e3", "audio.frame", 40, turn_id="t1", sequence=1, duration_ms=20, speech=True))

    def test_response_requires_committed_turn(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "committed turn"):
            self.session.apply(event("e1", "response.started", 0, response_id="r1", turn_id="missing"))

    def test_duration_rejects_boolean_and_oversized_frame(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "integer"):
            self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=True, speech=True))
        with self.assertRaisesRegex(SessionContractError, "<= 200"):
            self.session.apply(event("e2", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=201, speech=True))

    def test_output_chunk_uses_the_same_bounded_media_contract(self) -> None:
        feed_turn(self.session)
        with self.assertRaisesRegex(SessionContractError, "<= 200"):
            self.session.apply(
                event(
                    "e4",
                    "response.audio",
                    60,
                    response_id="response-1",
                    sequence=0,
                    duration_ms=201,
                )
            )

    def test_unknown_event_and_extra_field_are_rejected(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "unsupported"):
            self.session.apply(event("e1", "audio.magic", 0))
        bad = event("e2", "turn.commit", 0, turn_id="t1")
        bad["trace"] = "not-allowed"
        with self.assertRaisesRegex(SessionContractError, "keys mismatch"):
            self.session.apply(bad)

    def test_payload_extra_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "keys mismatch"):
            self.session.apply(event("e1", "turn.commit", 0, turn_id="t1", inferred=True))

    def test_time_cannot_move_backwards(self) -> None:
        self.session.apply(event("e1", "audio.frame", 10, turn_id="t1", sequence=0, duration_ms=20, speech=True))
        with self.assertRaisesRegex(SessionContractError, "backwards"):
            self.session.apply(event("e2", "turn.commit", 9, turn_id="t1"))


class InterruptionAndToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = RealtimeSession("session-1", "resume-1")
        feed_turn(self.session)

    def test_interrupt_cancels_old_output_and_clears_playback(self) -> None:
        self.session.apply(event("e4", "response.audio", 60, response_id="response-1", sequence=0, duration_ms=120))
        effect = self.session.apply(event("e5", "user.interrupt", 80, turn_id="turn-2", response_id="response-1", reason="barge_in"))
        self.assertEqual(effect["effect"], "response_canceled:response-1")
        self.assertEqual(self.session.responses["response-1"]["status"], "canceled")
        self.assertEqual(self.session.playback_queue_ms, 0)
        self.assertEqual(self.session.phase, "listening")
        with self.assertRaisesRegex(SessionContractError, "active response"):
            self.session.apply(event("e6", "response.audio", 100, response_id="response-1", sequence=1, duration_ms=20))

    def test_interrupt_without_output_is_invalid(self) -> None:
        self.session.apply(event("e4", "response.completed", 60, response_id="response-1"))
        with self.assertRaisesRegex(SessionContractError, "active response"):
            self.session.apply(event("e5", "user.interrupt", 80, turn_id="turn-2", response_id="response-1", reason="barge_in"))

    def test_interrupt_must_match_active_response(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "correlate"):
            self.session.apply(event("e4", "user.interrupt", 60, turn_id="turn-2", response_id="stale", reason="barge_in"))
        self.assertEqual(self.session.active_response_id, "response-1")
        self.assertEqual(self.session.responses["response-1"]["status"], "active")

    def test_tool_result_must_match_call_and_response(self) -> None:
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="lookup", arguments={"q": "x"}))
        with self.assertRaisesRegex(SessionContractError, "no matching"):
            self.session.apply(event("e5", "tool.result", 80, call_id="missing", response_id="response-1", ok=True, result="x"))
        with self.assertRaisesRegex(SessionContractError, "does not match"):
            self.session.apply(event("e6", "tool.result", 80, call_id="c1", response_id="wrong", ok=True, result="x"))

    def test_tool_call_persists_its_derived_turn_link(self) -> None:
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="lookup", arguments={}))
        self.assertEqual(self.session.tool_calls["c1"]["turn_id"], "turn-1")

    def test_non_finite_tool_arguments_are_rejected(self) -> None:
        with self.assertRaisesRegex(SessionContractError, "JSON-compatible"):
            self.session.apply(
                event(
                    "e4",
                    "tool.call",
                    60,
                    call_id="c1",
                    response_id="response-1",
                    name="lookup",
                    arguments={"value": float("nan")},
                )
            )

    def test_response_waits_for_tool_result(self) -> None:
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="lookup", arguments={}))
        with self.assertRaisesRegex(SessionContractError, "waiting for a tool"):
            self.session.apply(event("e5", "response.completed", 80, response_id="response-1"))
        self.session.apply(event("e6", "tool.result", 80, call_id="c1", response_id="response-1", ok=True, result="done"))
        self.session.apply(event("e7", "response.completed", 100, response_id="response-1"))
        self.assertEqual(self.session.responses["response-1"]["status"], "completed")

    def test_waiting_tool_holds_output_until_every_result_arrives(self) -> None:
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="lookup", arguments={}))
        self.session.apply(event("e5", "tool.call", 80, call_id="c2", response_id="response-1", name="lookup", arguments={}))
        with self.assertRaisesRegex(SessionContractError, "waiting for a tool"):
            self.session.apply(
                event(
                    "e6",
                    "response.audio",
                    100,
                    response_id="response-1",
                    sequence=0,
                    duration_ms=20,
                )
            )
        with self.assertRaisesRegex(SessionContractError, "waiting for a tool"):
            self.session.apply(
                event(
                    "e7",
                    "audio.frame",
                    100,
                    turn_id="turn-2",
                    sequence=0,
                    duration_ms=20,
                    speech=True,
                )
            )
        self.session.apply(event("e8", "tool.result", 120, call_id="c1", response_id="response-1", ok=True, result="one"))
        self.assertEqual(self.session.phase, "waiting_tool")
        self.session.apply(event("e9", "tool.result", 140, call_id="c2", response_id="response-1", ok=True, result="two"))
        self.assertEqual(self.session.phase, "thinking")
        self.session.apply(
            event(
                "e10",
                "response.audio",
                160,
                response_id="response-1",
                sequence=0,
                duration_ms=20,
            )
        )

    def test_interrupted_pending_tool_requires_reconciliation(self) -> None:
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="write", arguments={}))
        self.session.apply(event("e5", "user.interrupt", 80, turn_id="turn-2", response_id="response-1", reason="barge_in"))
        self.assertEqual(self.session.tool_calls["c1"]["status"], "requires_reconciliation")
        self.session.apply(event("e6", "tool.result", 100, call_id="c1", response_id="response-1", ok=True, result="receipt-1"))
        self.assertEqual(self.session.tool_calls["c1"]["status"], "succeeded")


class IdempotencyAndRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = RealtimeSession("session-1", "resume-1")

    def test_exact_duplicate_is_ignored(self) -> None:
        first = event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=20, speech=True)
        self.session.apply(first)
        result = self.session.apply(first)
        self.assertEqual(result["effect"], "duplicate_ignored")
        self.assertEqual(self.session.turns["t1"]["frames"], 1)
        self.assertEqual(self.session.duplicate_events, 1)

    def test_same_id_with_different_content_is_rejected(self) -> None:
        self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=20, speech=True))
        with self.assertRaisesRegex(SessionContractError, "reused"):
            self.session.apply(event("e1", "audio.frame", 0, turn_id="t1", sequence=0, duration_ms=40, speech=True))

    def test_disconnect_checkpoints_and_resume_requires_token(self) -> None:
        self.session.apply(event("e1", "transport.disconnected", 0, reason="network_change"))
        self.assertEqual(self.session.checkpoint_version, 1)
        with self.assertRaisesRegex(SessionContractError, "token"):
            self.session.apply(event("e2", "transport.resumed", 20, resume_token="wrong"))
        self.session.apply(event("e3", "transport.resumed", 20, resume_token="resume-1"))
        self.assertEqual(self.session.status, "connected")

    def test_disconnect_cancels_stale_audio_and_blocks_regular_events(self) -> None:
        feed_turn(self.session)
        self.session.apply(event("e4", "response.audio", 60, response_id="response-1", sequence=0, duration_ms=120))
        self.session.apply(event("e5", "transport.disconnected", 80, reason="packet_loss"))
        self.assertEqual(self.session.responses["response-1"]["status"], "canceled")
        self.assertEqual(self.session.playback_queue_ms, 0)
        with self.assertRaisesRegex(SessionContractError, "only resume"):
            self.session.apply(event("e6", "audio.frame", 100, turn_id="t2", sequence=0, duration_ms=20, speech=True))

    def test_resume_reconciles_pending_tool_before_accepting_new_work(self) -> None:
        feed_turn(self.session)
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="write", arguments={}))
        self.session.apply(event("e5", "transport.disconnected", 80, reason="network_change"))
        self.session.apply(event("e6", "transport.resumed", 100, resume_token="resume-1"))
        self.assertEqual(self.session.phase, "reconciling")
        with self.assertRaisesRegex(SessionContractError, "reconciliation"):
            self.session.apply(event("e7", "audio.frame", 120, turn_id="turn-2", sequence=0, duration_ms=20, speech=True))
        self.session.apply(event("e8", "tool.result", 140, call_id="c1", response_id="response-1", ok=True, result="receipt-1"))
        self.assertEqual(self.session.phase, "listening")
        self.session.apply(event("e9", "audio.frame", 160, turn_id="turn-2", sequence=0, duration_ms=20, speech=True))

    def test_recovery_preserves_tool_turn_link_and_rejects_overfull_playback(self) -> None:
        feed_turn(self.session)
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="write", arguments={}))
        self.session.apply(event("e5", "transport.disconnected", 80, reason="network_change"))
        self.session.apply(event("e6", "transport.resumed", 100, resume_token="resume-1"))
        self.assertEqual(self.session.tool_calls["c1"]["turn_id"], "turn-1")
        with self.assertRaisesRegex(SessionContractError, "reconciliation"):
            self.session.apply(event("e7", "response.audio", 120, response_id="response-1", sequence=0, duration_ms=200))

    def test_playback_queue_has_a_bounded_contract(self) -> None:
        feed_turn(self.session)
        for sequence in range(5):
            self.session.apply(
                event(
                    f"e{sequence + 4}",
                    "response.audio",
                    60 + sequence * 20,
                    response_id="response-1",
                    sequence=sequence,
                    duration_ms=200,
                )
            )
        self.assertEqual(self.session.playback_queue_ms, 1_000)
        with self.assertRaisesRegex(SessionContractError, "backpressure"):
            self.session.apply(
                event(
                    "e9",
                    "response.audio",
                    180,
                    response_id="response-1",
                    sequence=5,
                    duration_ms=20,
                )
            )
        self.assertEqual(self.session.playback_queue_ms, 1_000)

    def test_timeout_is_terminal_and_marks_unknown_tool(self) -> None:
        feed_turn(self.session)
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="write", arguments={}))
        self.session.apply(event("e5", "session.timeout", 80, reason="deadline_exceeded"))
        self.assertEqual(self.session.status, "timed_out")
        self.assertEqual(self.session.tool_calls["c1"]["status"], "requires_reconciliation")
        with self.assertRaisesRegex(SessionContractError, "terminal"):
            self.session.apply(event("e6", "session.completed", 100, reason="late"))

    def test_completed_session_rejects_new_events(self) -> None:
        final_event = event("e1", "session.completed", 0, reason="user_goodbye")
        self.session.apply(final_event)
        self.assertEqual(self.session.apply(final_event)["effect"], "duplicate_ignored")
        with self.assertRaisesRegex(SessionContractError, "terminal"):
            self.session.apply(event("e2", "audio.frame", 20, turn_id="t1", sequence=0, duration_ms=20, speech=True))

    def test_session_cannot_complete_with_pending_tool(self) -> None:
        feed_turn(self.session)
        self.session.apply(event("e4", "tool.call", 60, call_id="c1", response_id="response-1", name="lookup", arguments={}))
        self.session.apply(event("e5", "user.interrupt", 80, turn_id="turn-2", response_id="response-1", reason="barge_in"))
        with self.assertRaisesRegex(SessionContractError, "unresolved"):
            self.session.apply(event("e6", "session.completed", 100, reason="done"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
