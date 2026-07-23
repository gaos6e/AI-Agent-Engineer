"""Deterministic realtime-session event simulator.

The simulator models contracts and recovery boundaries only. It does not
capture audio, open sockets, call a model, or execute a real external tool.
"""

from __future__ import annotations  # Defer annotation evaluation for readable teaching code on modern Python.

import argparse  # Parse the fixture and the --pretty command-line option.
import hashlib  # Keep a content digest for event-ID deduplication.
import json  # Strictly read the event fixture and emit a JSON session summary.
import re  # Restrict the characters allowed in a tool name.
from pathlib import Path  # Represent the offline fixture path.
from typing import Any, Mapping  # Describe JSON values and validated read-only mappings.


class SessionContractError(ValueError):  # Controlled error for invalid event, ordering, or recovery contracts.
    """Raised when an event violates the realtime-session contract."""  # The CLI turns this into an actionable user error.


_EVENT_KEYS = {"event_id", "type", "at_ms", "payload"}  # Minimum envelope fields required on every event.
_EVENT_TYPES = {
    "audio.frame",  # Metadata for one user-input audio frame.
    "turn.commit",  # The user turn is committed and response generation may begin.
    "response.started",  # One assistant response begins.
    "response.audio",  # An assistant-output audio chunk.
    "user.interrupt",  # The user interrupts the current response.
    "tool.call",  # The assistant requests a controlled tool call.
    "tool.result",  # A tool adapter returns its result.
    "response.completed",  # An assistant response ends normally.
    "transport.disconnected",  # The transport link disconnected.
    "transport.resumed",  # Reconnect using recovery-token/state information.
    "session.timeout",  # The session ends on timeout.
    "session.completed",  # The overall session ends normally.
}  # End of the event types supported by this offline simulator.
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")  # Prevent whitespace, control characters, or unbounded tool names.
# These are deliberately conservative simulator contracts, not codec, provider,
# or product limits. A production adapter may apply flow control or an explicit
# quality downgrade before it reaches the same safety boundary.
_MAX_MEDIA_CHUNK_MS = 200  # Maximum single-frame duration; a teaching-resource budget, not a real codec limit.
_MAX_PLAYBACK_QUEUE_MS = 1_000  # Maximum playback backlog; use backpressure/degradation instead of unbounded queuing.


def _is_int(value: object) -> bool:  # Check for a JSON-semantic integer while excluding Python's bool subclass.
    return isinstance(value, int) and not isinstance(value, bool)  # True/False must not masquerade as 1/0 time or sequence values.


def _require_text(value: object, field: str) -> str:  # Require non-empty text for identifiers, reasons, and similar fields.
    if not isinstance(value, str) or not value.strip():  # Reject None, non-text values, and whitespace-only text.
        raise SessionContractError(f"{field} must be a non-empty string")  # Preserve the field path to locate fixture errors.
    return value  # Return the original text after type/non-empty validation.


def _require_int(value: object, field: str, minimum: int = 0) -> int:  # Check integer semantics and a lower bound for times/sequences.
    if not _is_int(value) or value < minimum:  # Reject floats, bools, and numbers below the minimum.
        raise SessionContractError(f"{field} must be an integer >= {minimum}")  # State the field and the required bound.
    return value  # Return an integer safe to compare and add.


def _require_bool(value: object, field: str) -> bool:  # Require fields such as speech to be actual booleans.
    if not isinstance(value, bool):  # The string "true" and the integer 1 are both rejected.
        raise SessionContractError(f"{field} must be a boolean")  # Keep the cross-language JSON contract consistent.
    return value  # Return the validated boolean.


def _exact_keys(value: object, expected: set[str], field: str) -> Mapping[str, Any]:  # Use closed schemas for events/payloads instead of ignoring unknown fields.
    if not isinstance(value, dict):  # Named fields cannot be read if the root type is not an object.
        raise SessionContractError(f"{field} must be an object")  # Fail closed immediately.
    actual = set(value)  # Obtain every actual key so missing and extra fields can be compared.
    if actual != expected:  # Missing fields and unknown additions both create interpretation ambiguity.
        missing = sorted(expected - actual)  # Calculate and sort missing fields for readable output.
        extra = sorted(actual - expected)  # Calculate and sort unknown fields to prevent silent contract extension.
        raise SessionContractError(  # Use one stable error to report both differences.
            f"{field} keys mismatch; missing={missing}, extra={extra}"  # Do not continue with a best-effort parse.
        )  # End error construction.
    return value  # Pass the mapping onward only when the key set is exact.


def _reject_json_constant(value: str) -> None:
    """Reject JSON extensions whose meaning is not portable or finite."""
    raise SessionContractError(f"non-standard JSON constant is forbidden: {value}")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object only when every JSON member name is unique."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SessionContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_loads(text: str, source: str) -> Any:
    """Parse a fixture without silently accepting duplicate keys or NaN values."""
    try:
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except SessionContractError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionContractError(f"cannot load {source}: {exc.msg}") from exc


def _event_digest(event: Mapping[str, Any]) -> str:  # Compute a stable, one-way digest to determine whether one event_id has the same content.
    try:  # First normalize the event into one unique JSON byte sequence.
        encoded = json.dumps(  # JSON serialization never executes event content.
            event,  # Use the validated event mapping.
            ensure_ascii=False,  # Retain Unicode directly for readability across escaping styles.
            sort_keys=True,  # Fix object-key order so equivalent content has the same digest.
            separators=(",", ":"),  # Fix whitespace so formatting differences do not change the digest.
            allow_nan=False,  # Reject non-standard numbers for cross-implementation consistency.
        ).encode("utf-8")  # Encode as UTF-8 bytes suitable for hashing.
    except (TypeError, ValueError) as exc:  # Objects that cannot become JSON must not enter deduplication state.
        raise SessionContractError("event must contain JSON-compatible values") from exc  # Convert to a controlled contract error.
    return hashlib.sha256(encoded).hexdigest()  # Return the hexadecimal SHA-256 content digest.


def validate_event(raw_event: object) -> dict[str, Any]:  # Convert an untrusted input event into a strict object safe for the state machine.
    """Return a validated event without accepting implicit coercions."""  # Do not coerce strings to numbers or fill missing defaults.

    event = dict(_exact_keys(raw_event, _EVENT_KEYS, "event"))  # Copy the envelope that passed the closed-schema check.
    _require_text(event["event_id"], "event.event_id")  # The event ID serves both deduplication and audit, so it cannot be empty.
    event_type = _require_text(event["type"], "event.type")  # Read and validate the event-type text.
    if event_type not in _EVENT_TYPES:  # Allow only events that this offline state machine implements explicitly.
        raise SessionContractError(f"unsupported event type: {event_type}")  # An unknown event cannot be ignored while execution continues.
    _require_int(event["at_ms"], "event.at_ms")  # The timestamp must be non-negative integer milliseconds.
    payload = event["payload"]  # Apply an exact schema to the payload by event type below.

    if event_type == "audio.frame":
        data = _exact_keys(
            payload, {"turn_id", "sequence", "duration_ms", "speech"}, "payload"
        )
        _require_text(data["turn_id"], "payload.turn_id")
        _require_int(data["sequence"], "payload.sequence")
        duration = _require_int(data["duration_ms"], "payload.duration_ms", 1)
        if duration > _MAX_MEDIA_CHUNK_MS:
            raise SessionContractError(
                f"payload.duration_ms must be <= {_MAX_MEDIA_CHUNK_MS}"
            )
        _require_bool(data["speech"], "payload.speech")
    elif event_type in {"turn.commit", "response.completed"}:
        key = "turn_id" if event_type == "turn.commit" else "response_id"
        data = _exact_keys(payload, {key}, "payload")
        _require_text(data[key], f"payload.{key}")
    elif event_type == "response.started":
        data = _exact_keys(payload, {"response_id", "turn_id"}, "payload")
        _require_text(data["response_id"], "payload.response_id")
        _require_text(data["turn_id"], "payload.turn_id")
    elif event_type == "response.audio":
        data = _exact_keys(
            payload, {"response_id", "sequence", "duration_ms"}, "payload"
        )
        _require_text(data["response_id"], "payload.response_id")
        _require_int(data["sequence"], "payload.sequence")
        duration = _require_int(data["duration_ms"], "payload.duration_ms", 1)
        if duration > _MAX_MEDIA_CHUNK_MS:
            raise SessionContractError(
                f"payload.duration_ms must be <= {_MAX_MEDIA_CHUNK_MS}"
            )
    elif event_type == "user.interrupt":
        data = _exact_keys(
            payload, {"turn_id", "response_id", "reason"}, "payload"
        )
        _require_text(data["turn_id"], "payload.turn_id")
        _require_text(data["response_id"], "payload.response_id")
        _require_text(data["reason"], "payload.reason")
    elif event_type == "tool.call":
        data = _exact_keys(
            payload, {"call_id", "response_id", "name", "arguments"}, "payload"
        )
        _require_text(data["call_id"], "payload.call_id")
        _require_text(data["response_id"], "payload.response_id")
        name = _require_text(data["name"], "payload.name")
        if _TOOL_NAME.fullmatch(name) is None:
            raise SessionContractError("payload.name has unsupported characters")
        if not isinstance(data["arguments"], dict):
            raise SessionContractError("payload.arguments must be an object")
        _event_digest(data["arguments"])
    elif event_type == "tool.result":
        data = _exact_keys(
            payload, {"call_id", "response_id", "ok", "result"}, "payload"
        )
        _require_text(data["call_id"], "payload.call_id")
        _require_text(data["response_id"], "payload.response_id")
        _require_bool(data["ok"], "payload.ok")
        _require_text(data["result"], "payload.result")
    elif event_type in {
        "transport.disconnected",
        "session.timeout",
        "session.completed",
    }:
        data = _exact_keys(payload, {"reason"}, "payload")
        _require_text(data["reason"], "payload.reason")
    elif event_type == "transport.resumed":
        data = _exact_keys(payload, {"resume_token"}, "payload")
        _require_text(data["resume_token"], "payload.resume_token")

    return event  # Return an executable event only after every type branch has passed.


class RealtimeSession:  # Model real-time session, interruption, tool, and recovery boundaries with a deterministic state machine.
    """Apply strict events to a deterministic, resumable session state."""  # No audio capture, network calls, model calls, or real tools.

    def __init__(self, session_id: str, resume_token: str) -> None:  # Create a session state that has not processed any event yet.
        self.session_id = _require_text(session_id, "session_id")  # Retain the validated session ID without treating it as an identity credential.
        self.resume_token = _require_text(resume_token, "resume_token")  # Retain the fixture recovery-token reference; production systems store/validate it securely.
        self.status = "connected"  # Initial transport status is connected.
        self.phase = "listening"  # Initial business phase awaits user audio/a turn.
        self.last_at_ms = -1  # There is no event time yet; the first non-negative time passes the monotonic check.
        self.processed_events = 0  # Count unique events that were processed.
        self.duplicate_events = 0  # Count identical replays that were safely ignored.
        self.checkpoint_version = 0  # Increment after every unique event for recovery/audit observation.
        self.terminal_reason: str | None = None  # There is no ending reason before a terminal state.
        self.active_response_id: str | None = None  # No assistant response is playing/generating yet.
        self.playback_queue_ms = 0  # The playback queue starts empty.
        self.turns: dict[str, dict[str, Any]] = {}  # Store user-input frame state by turn ID.
        self.responses: dict[str, dict[str, Any]] = {}  # Store assistant-response state by response ID.
        self.tool_calls: dict[str, dict[str, Any]] = {}  # Store tool calls awaiting a result/reconciliation by call ID.
        self.effects: list[dict[str, Any]] = []  # Retain observable event effects for tests and the summary.
        self._seen_events: dict[str, str] = {}  # event_id -> content digest; detects substitution under a duplicate ID.

    def apply(self, raw_event: object) -> dict[str, Any]:  # Apply one event atomically: validate, check ordering/state, then record its effect.
        """Apply one event atomically and return its observable effect."""  # A failed gate neither writes seen-event state nor advances the session.

        event = validate_event(raw_event)  # Constrain external input to the exact event contract first.
        event_id = event["event_id"]  # Use the stable event ID as the deduplication key.
        digest = _event_digest(event)  # Digest the complete event to detect substitution under a reused ID.
        prior_digest = self._seen_events.get(event_id)  # Check whether this ID was already handled in the session.
        if prior_digest is not None:  # A seen event follows a replay/duplicate-delivery path.
            if prior_digest != digest:  # Same ID with different content is a serious protocol conflict.
                raise SessionContractError(  # Fail closed rather than guessing which version to use.
                    f"event_id {event_id!r} was reused with different content"  # Report the specific conflicting ID for audit.
                )  # End error construction.
            self.duplicate_events += 1  # An identical safe replay is counted but does not change state again.
            return {"event_id": event_id, "effect": "duplicate_ignored"}  # Return the observable idempotent effect.

        at_ms = event["at_ms"]  # Read this event's session-relative time.
        if at_ms < self.last_at_ms:  # Time reversal makes playback, timeout, and recovery decisions untrustworthy.
            raise SessionContractError("event.at_ms must not move backwards")  # Reject out-of-order input rather than silently sorting it.
        if self.status in {"completed", "timed_out"}:  # A terminal session cannot accept more business events.
            raise SessionContractError(f"session is terminal: {self.status}")  # Prevent stale links/replays from reopening a session.

        event_type = event["type"]  # Use the validated event type to select a state-machine branch.
        if self.status == "disconnected" and event_type not in {  # While disconnected, allow only resume or timeout.
            "transport.resumed",  # Restore transport and enter reconciliation/continuation logic.
            "session.timeout",  # Abandon the session that was not recovered.
        }:  # Other input is unsafe to process while disconnected.
            raise SessionContractError("only resume or timeout is valid while disconnected")  # Do not produce side effects after a disconnect.
        if self.status == "connected" and event_type == "transport.resumed":  # An already connected session cannot resume again.
            raise SessionContractError("cannot resume an already connected session")  # Avoid state divergence from two resumptions.
        if self.phase == "reconciling" and event_type not in {  # Freeze new work while tool side effects are unreconciled.
            "tool.result",  # Permit a result for an existing tool call.
            "transport.disconnected",  # Permit another disconnect.
            "session.timeout",  # Permit terminating the wait.
        }:  # Any new user/model work would bypass unresolved side effects.
            raise SessionContractError(  # Fail closed until reconciliation is complete.
                "reconciliation must finish before accepting new work"  # Give the caller an explicit recovery order.
            )  # End error construction.
        if self.phase == "waiting_tool" and event_type not in {  # During a tool wait, allow only a small set of relevant events.
            "tool.call",  # Permit another defined tool call for the same response.
            "tool.result",  # Permit a tool result to return.
            "user.interrupt",  # The user may cancel the current response/tool wait.
            "transport.disconnected",  # The transport may disconnect.
            "session.timeout",  # The session may end on timeout.
        }:  # Do not produce fresh audio/completion events that bypass the tool result.
            raise SessionContractError(  # Preserve the waiting-tool state-machine invariant.
                "only tool events, interrupt, disconnect, or timeout are valid "  # First stable part of the error message.
                "while waiting for a tool"  # State the allowed scope for this phase.
            )  # End error construction.

        handler_name = "_on_" + event_type.replace(".", "_")  # Map the protocol event name to a controlled internal handler name.
        handler = getattr(self, handler_name)  # Obtain only a fixed class handler, never executable code from external text.
        effect = handler(event["payload"])  # Update relevant substate only after all preceding gates passed.

        self._seen_events[event_id] = digest  # Register the ID/digest only after success so a corrected event can retry.
        self.last_at_ms = at_ms  # Advance the monotonic time baseline.
        self.processed_events += 1  # Count one unique successfully processed event.
        record = {"event_id": event_id, "effect": effect}  # Create a non-sensitive observable-effect record.
        self.effects.append(record)  # Retain effects in order for tests and the session summary.
        return record  # Return the deterministic result of this event.

    def _turn(self, turn_id: str) -> dict[str, Any]:
        return self.turns.setdefault(
            turn_id,
            {"status": "receiving", "next_sequence": 0, "frames": 0, "speech": False},
        )

    def _cancel_active_response(self, reason: str) -> str | None:
        response_id = self.active_response_id
        if response_id is None:
            return None
        response = self.responses[response_id]
        response["status"] = "canceled"
        response["cancel_reason"] = reason
        for call in self.tool_calls.values():
            if call["response_id"] == response_id and call["status"] == "pending":
                call["status"] = "requires_reconciliation"
        self.active_response_id = None
        self.playback_queue_ms = 0
        return response_id

    def _has_unreconciled_calls(self) -> bool:
        """Return whether recovery must still query a prior side effect."""
        return any(
            call["status"] == "requires_reconciliation"
            for call in self.tool_calls.values()
        )

    def _has_unresolved_calls_for_response(self, response_id: str) -> bool:
        """Return whether this active response still waits on a tool outcome."""
        return any(
            call["response_id"] == response_id
            and call["status"] in {"pending", "requires_reconciliation"}
            for call in self.tool_calls.values()
        )

    def _on_audio_frame(self, payload: Mapping[str, Any]) -> str:
        turn = self.turns.get(payload["turn_id"])
        if turn is None:
            if payload["sequence"] != 0:
                raise SessionContractError("audio sequence must be contiguous from zero")
            turn = self._turn(payload["turn_id"])
        if turn["status"] != "receiving":
            raise SessionContractError("audio cannot be appended to a committed turn")
        if payload["sequence"] != turn["next_sequence"]:
            raise SessionContractError("audio sequence must be contiguous from zero")
        turn["next_sequence"] += 1
        turn["frames"] += 1
        turn["speech"] = turn["speech"] or payload["speech"]
        self.phase = "listening"
        return "audio_buffered"

    def _on_turn_commit(self, payload: Mapping[str, Any]) -> str:
        turn = self.turns.get(payload["turn_id"])
        if turn is None or turn["frames"] == 0:
            raise SessionContractError("turn must contain audio before commit")
        if turn["status"] != "receiving":
            raise SessionContractError("turn was already committed")
        if not turn["speech"]:
            raise SessionContractError("silence-only turn cannot be committed")
        turn["status"] = "committed"
        self.phase = "thinking"
        return "turn_committed"

    def _on_response_started(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        turn = self.turns.get(payload["turn_id"])
        if turn is None or turn["status"] != "committed":
            raise SessionContractError("response must correlate to a committed turn")
        if response_id in self.responses:
            raise SessionContractError("response_id must be unique")
        if self.active_response_id is not None:
            raise SessionContractError("only one response may be active")
        self.responses[response_id] = {
            "turn_id": payload["turn_id"],
            "status": "active",
            "next_audio_sequence": 0,
        }
        self.active_response_id = response_id
        self.phase = "thinking"
        return "response_started"

    def _on_response_audio(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("audio must correlate to the active response")
        response = self.responses[response_id]
        if payload["sequence"] != response["next_audio_sequence"]:
            raise SessionContractError("response audio sequence must be contiguous from zero")
        if self.playback_queue_ms + payload["duration_ms"] > _MAX_PLAYBACK_QUEUE_MS:
            raise SessionContractError(
                "playback queue must remain <= "
                f"{_MAX_PLAYBACK_QUEUE_MS}ms; apply backpressure or cancel"
            )
        response["next_audio_sequence"] += 1
        self.playback_queue_ms += payload["duration_ms"]
        self.phase = "speaking"
        return "output_audio_queued"

    def _on_user_interrupt(self, payload: Mapping[str, Any]) -> str:
        if self.active_response_id is None:
            raise SessionContractError("barge-in requires an active response")
        if payload["response_id"] != self.active_response_id:
            raise SessionContractError("interrupt must correlate to the active response")
        if payload["turn_id"] in self.turns:
            raise SessionContractError("interrupt turn_id must be new")
        canceled = self._cancel_active_response(payload["reason"])
        if canceled is None:  # Defensive: guarded above, retained for type clarity.
            raise SessionContractError("barge-in requires an active response")
        self._turn(payload["turn_id"])
        self.phase = "listening"
        return f"response_canceled:{canceled}"

    def _on_tool_call(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("tool call must correlate to the active response")
        response = self.responses[response_id]
        call_id = payload["call_id"]
        if call_id in self.tool_calls:
            raise SessionContractError("call_id must be unique")
        self.tool_calls[call_id] = {
            # Providers do not always repeat a turn ID on every tool event. The
            # runtime must nevertheless persist the canonical relation so a
            # receipt is still attributable after a reconnect.
            "turn_id": response["turn_id"],
            "response_id": response_id,
            "name": payload["name"],
            "arguments": payload["arguments"],
            "status": "pending",
        }
        self.phase = "waiting_tool"
        return "tool_call_recorded"

    def _on_tool_result(self, payload: Mapping[str, Any]) -> str:
        call = self.tool_calls.get(payload["call_id"])
        if call is None:
            raise SessionContractError("tool result has no matching call_id")
        if call["response_id"] != payload["response_id"]:
            raise SessionContractError("tool result response_id does not match its call")
        if call["status"] not in {"pending", "requires_reconciliation"}:
            raise SessionContractError("tool call already has a terminal result")
        was_reconciliation_required = call["status"] == "requires_reconciliation"
        if self.phase == "reconciling" and not was_reconciliation_required:
            raise SessionContractError("tool result is not awaiting reconciliation")
        call["status"] = "succeeded" if payload["ok"] else "failed"
        call["result"] = payload["result"]
        if self.phase == "reconciling" and not self._has_unreconciled_calls():
            self.phase = "listening"
        elif self._has_unresolved_calls_for_response(payload["response_id"]):
            self.phase = "waiting_tool"
        elif self.active_response_id == payload["response_id"]:
            self.phase = "thinking"
        return "tool_result_correlated"

    def _on_response_completed(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("only the active response can complete")
        unresolved = [
            call_id
            for call_id, call in self.tool_calls.items()
            if call["response_id"] == response_id
            and call["status"] in {"pending", "requires_reconciliation"}
        ]
        if unresolved:
            raise SessionContractError(f"response has unresolved tool calls: {unresolved}")
        self.responses[response_id]["status"] = "completed"
        self.active_response_id = None
        self.playback_queue_ms = 0
        self.phase = "listening"
        return "response_completed"

    def _on_transport_disconnected(self, payload: Mapping[str, Any]) -> str:
        canceled = self._cancel_active_response("transport_disconnected")
        self.status = "disconnected"
        self.phase = "disconnected"
        self.checkpoint_version += 1
        suffix = f":canceled={canceled}" if canceled is not None else ""
        return f"checkpoint_saved{suffix}"

    def _on_transport_resumed(self, payload: Mapping[str, Any]) -> str:
        if payload["resume_token"] != self.resume_token:
            raise SessionContractError("resume token does not match the session")
        self.status = "connected"
        if self._has_unreconciled_calls():
            self.phase = "reconciling"
            return (
                f"session_resumed:checkpoint={self.checkpoint_version}"
                ":reconciliation_required"
            )
        self.phase = "listening"
        return f"session_resumed:checkpoint={self.checkpoint_version}"

    def _on_session_timeout(self, payload: Mapping[str, Any]) -> str:
        self._cancel_active_response("session_timeout")
        for call in self.tool_calls.values():
            if call["status"] == "pending":
                call["status"] = "requires_reconciliation"
        self.status = "timed_out"
        self.phase = "terminal"
        self.terminal_reason = payload["reason"]
        return "session_timed_out"

    def _on_session_completed(self, payload: Mapping[str, Any]) -> str:
        if self.active_response_id is not None:
            raise SessionContractError("cannot complete with an active response")
        unresolved = [
            call_id
            for call_id, call in self.tool_calls.items()
            if call["status"] in {"pending", "requires_reconciliation"}
        ]
        if unresolved:
            raise SessionContractError(f"cannot complete with unresolved calls: {unresolved}")
        self.status = "completed"
        self.phase = "terminal"
        self.terminal_reason = payload["reason"]
        return "session_completed"

    def summary(self) -> dict[str, Any]:
        """Return a stable, JSON-serializable snapshot for tests and review."""

        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase,
            "terminal_reason": self.terminal_reason,
            "processed_events": self.processed_events,
            "duplicate_events": self.duplicate_events,
            "checkpoint_version": self.checkpoint_version,
            "active_response_id": self.active_response_id,
            "playback_queue_ms": self.playback_queue_ms,
            "turns": self.turns,
            "responses": self.responses,
            "tool_calls": self.tool_calls,
        }


def run_fixture(path: Path) -> dict[str, Any]:  # Load and run one strict fixture without creating output files or network connections.
    """Load and run one strict fixture without writing any output files."""  # Lets learners repeatedly observe a deterministic outcome for one event sequence.

    try:  # Convert file-read errors into a uniform session-contract error.
        text = path.read_text(encoding="utf-8")  # Force UTF-8 instead of depending on terminal/system defaults.
    except OSError as exc:  # Missing paths and inadequate permissions are user-fixable input errors.
        raise SessionContractError(f"cannot load fixture: {exc}") from exc  # Preserve the exception chain to locate the file issue.
    raw = _strict_json_loads(text, f"fixture {path}")  # Reject duplicate keys, NaN/Infinity, and ordinary JSON syntax errors.
    fixture = _exact_keys(raw, {"session", "events"}, "fixture")  # The fixture root permits only session and events.
    session_data = _exact_keys(  # Also use a closed schema for the session object.
        fixture["session"], {"session_id", "resume_token"}, "fixture.session"  # Do not accept hidden token/configuration fields.
    )  # Finish session-data validation.
    if not isinstance(fixture["events"], list):  # An event sequence must be an array to preserve the given order.
        raise SessionContractError("fixture.events must be an array")  # Do not let a dictionary reorder events by key.
    session = RealtimeSession(  # Build a deterministic state machine from the validated session ID/resume token.
        session_id=session_data["session_id"], resume_token=session_data["resume_token"]  # Do not infer session identity from an event payload.
    )  # Finish session initialization.
    for event in fixture["events"]:  # Process every event in fixture order; apply rejects ordering errors.
        session.apply(event)  # Each event independently passes schema, deduplication, phase, and handler gates.
    return session.summary()  # Return an auditable summary without raw audio or secrets.


def main() -> int:  # CLI entry point: run a fixture and optionally print a formatted JSON summary.
    parser = argparse.ArgumentParser(description=__doc__)  # Show this simulator's explicit capability boundary in --help.
    parser.add_argument("fixture", type=Path, help="strict JSON event fixture")  # Receive the strict JSON fixture location.
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")  # Allow human-readable indentation without changing data semantics.
    args = parser.parse_args()  # Parse command-line input.
    try:  # Catch only expected contract errors so unexpected program errors remain visible.
        result = run_fixture(args.fixture)  # Run the complete offline session state machine.
    except SessionContractError as exc:  # The fixture/event violates the contract.
        parser.error(str(exc))  # argparse emits a controlled usage error and nonzero status.
    print(  # stdout emits only the successful JSON summary.
        json.dumps(  # Serialize a plain dictionary result without raw input payloads.
            result,  # The summary contains only session-controlled fields.
            ensure_ascii=False,  # Retain Unicode in readable form.
            sort_keys=True,  # Fix key order for tests and diffs.
            indent=2 if args.pretty else None,  # Enable indentation only for --pretty.
            allow_nan=False,  # Successful output also forbids non-standard JSON numbers.
        )  # Finish producing JSON text.
    )  # Write it to standard output.
    return 0  # The fixture ran successfully.


if __name__ == "__main__":  # Start the CLI only when run directly, not when imported by tests.
    raise SystemExit(main())  # Use main's integer result as the process exit code.
