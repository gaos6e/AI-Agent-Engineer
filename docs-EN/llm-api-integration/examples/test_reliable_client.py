"""Tests for the provider-neutral LLM client reliability core."""

from __future__ import annotations

import math
import unittest

from reliable_client import (
    ClientResult,
    LLMRequest,
    LLMResponse,
    MAX_STREAM_EVENTS,
    MAX_STREAM_TEXT_CHARS,
    MockTransport,
    PermanentError,
    RetryExhaustedError,
    RetryPolicy,
    StreamInterruptedError,
    StreamLimitError,
    StreamProtocolError,
    TransientError,
    call_with_retry,
    consume_canonical_stream,
)


REQUEST = LLMRequest(
    operation_id="operation-001",
    prompt_version="router-1.0.0",
    model_profile="offline-mock",
    user_text="classify this ticket",
)
RESPONSE = LLMResponse(
    text='{"label":"other"}',
    status="completed",
    request_id="mock-request-001",
    provider="offline",
    model="mock-model-1",
    input_units=10,
    output_units=5,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


def policy(**overrides: object) -> RetryPolicy:
    values: dict[str, object] = {
        "max_attempts": 3,
        "retry_deadline_seconds": 30.0,
        "base_delay_seconds": 1.0,
        "max_delay_seconds": 8.0,
        "jitter_ratio": 0.0,
    }
    values.update(overrides)
    return RetryPolicy(**values)  # type: ignore[arg-type]


def completed_events(status: str = "completed") -> list[dict[str, object]]:
    return [
        {"type": "response.started", "request_id": "stream-request-1"},
        {"type": "response.text.delta", "text": "hel"},
        {"type": "response.text.delta", "text": "lo"},
        {
            "type": "response.finished",
            "status": status,
            "usage": {"input_units": 7, "output_units": 2},
        },
    ]


class ValidationTests(unittest.TestCase):
    def test_request_fields_are_validated(self) -> None:
        cases = (
            {"operation_id": "", "message": "non-blank"},
            {"prompt_version": "bad value", "message": "match"},
            {"model_profile": "", "message": "non-blank"},
            {"user_text": "", "message": "non-blank"},
        )
        base = {
            "operation_id": "op-1",
            "prompt_version": "prompt-1",
            "model_profile": "profile-1",
            "user_text": "hello",
        }
        for case in cases:
            with self.subTest(field=next(iter(case))):
                values = dict(base)
                message = str(case["message"])
                values.update(
                    {
                        key: value
                        for key, value in case.items()
                        if key != "message"
                    }
                )
                with self.assertRaisesRegex(ValueError, message):
                    LLMRequest(**values)

    def test_response_fields_are_validated(self) -> None:
        base = {
            "text": "ok",
            "status": "completed",
            "request_id": "req-1",
            "provider": "offline",
            "model": "mock-1",
            "input_units": 1,
            "output_units": 1,
        }
        cases = (
            ("text", None, "string"),
            ("status", "unknown", "unsupported"),
            ("request_id", "bad id", "match"),
            ("input_units", True, "integer"),
            ("output_units", -1, "between"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                values = dict(base)
                values[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    LLMResponse(**values)

    def test_policy_and_error_metadata_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_attempts"):
            policy(max_attempts=0)
        with self.assertRaisesRegex(ValueError, "at least"):
            policy(base_delay_seconds=2.0, max_delay_seconds=1.0)
        with self.assertRaisesRegex(ValueError, "finite"):
            policy(retry_deadline_seconds=math.inf)
        with self.assertRaisesRegex(ValueError, "unsupported transient"):
            TransientError("secret", "bad")
        with self.assertRaisesRegex(ValueError, "retry_after"):
            TransientError("rate_limit", "wait", retry_after_seconds=-1.0)
        with self.assertRaisesRegex(ValueError, "unsupported stream resource"):
            StreamLimitError(
                "bytes", limit=1, observed=2, request_id=None, partial_text=""
            )
        with self.assertRaisesRegex(ValueError, "positive integer"):
            StreamLimitError(
                "events", limit=True, observed=2, request_id=None, partial_text=""
            )
        with self.assertRaisesRegex(ValueError, "greater than limit"):
            StreamLimitError(
                "events", limit=2, observed=2, request_id=None, partial_text=""
            )


class RetryTests(unittest.TestCase):
    def test_direct_success_has_one_attempt(self) -> None:
        clock = FakeClock()
        transport = MockTransport([RESPONSE])
        result = call_with_retry(
            transport,
            REQUEST,
            policy=policy(),
            clock=clock,
            sleeper=clock.sleep,
            random_value=lambda: 0.5,
        )
        self.assertIsInstance(result, ClientResult)
        self.assertEqual(result.response, RESPONSE)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.total_wait_seconds, 0.0)
        self.assertEqual(len(transport.requests), 1)

    def test_transient_failure_retries_same_operation_then_succeeds(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [TransientError("connection", "temporary", request_id="req-fail"), RESPONSE]
        )
        result = call_with_retry(
            transport,
            REQUEST,
            policy=policy(),
            clock=clock,
            sleeper=clock.sleep,
            random_value=lambda: 0.5,
        )
        self.assertEqual(clock.sleeps, [1.0])
        self.assertEqual(result.total_wait_seconds, 1.0)
        self.assertEqual(
            [request.operation_id for request in transport.requests],
            [REQUEST.operation_id, REQUEST.operation_id],
        )
        self.assertEqual(result.attempts[0].category, "connection")

    def test_retry_after_is_a_minimum_wait(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [
                TransientError(
                    "rate_limit", "slow down", retry_after_seconds=3.5
                ),
                RESPONSE,
            ]
        )
        result = call_with_retry(
            transport,
            REQUEST,
            policy=policy(),
            clock=clock,
            sleeper=clock.sleep,
            random_value=lambda: 0.0,
        )
        self.assertEqual(clock.sleeps, [3.5])
        self.assertEqual(result.total_wait_seconds, 3.5)

    def test_jitter_is_bounded_and_injected(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [TransientError("timeout", "temporary"), RESPONSE]
        )
        result = call_with_retry(
            transport,
            REQUEST,
            policy=policy(jitter_ratio=0.5),
            clock=clock,
            sleeper=clock.sleep,
            random_value=lambda: 1.0,
        )
        self.assertEqual(clock.sleeps, [1.5])
        self.assertEqual(result.attempts[0].wait_seconds, 1.5)

    def test_permanent_failure_is_not_retried(self) -> None:
        transport = MockTransport(
            [PermanentError("authentication", "bad key"), RESPONSE]
        )
        with self.assertRaises(PermanentError):
            call_with_retry(transport, REQUEST, policy=policy())
        self.assertEqual(len(transport.requests), 1)

    def test_unknown_exception_is_not_retried(self) -> None:
        transport = MockTransport([RuntimeError("adapter bug"), RESPONSE])
        with self.assertRaisesRegex(RuntimeError, "adapter bug"):
            call_with_retry(transport, REQUEST, policy=policy())
        self.assertEqual(len(transport.requests), 1)

    def test_attempt_budget_is_bounded(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [TransientError("timeout", "first"), TransientError("timeout", "second")]
        )
        with self.assertRaises(RetryExhaustedError) as captured:
            call_with_retry(
                transport,
                REQUEST,
                policy=policy(max_attempts=2),
                clock=clock,
                sleeper=clock.sleep,
                random_value=lambda: 0.5,
            )
        self.assertEqual(captured.exception.reason, "attempts_exhausted")
        self.assertEqual(captured.exception.attempts, 2)
        self.assertEqual(len(transport.requests), 2)

    def test_retry_deadline_prevents_another_attempt(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [
                TransientError(
                    "rate_limit", "wait", retry_after_seconds=5.0
                ),
                RESPONSE,
            ]
        )
        with self.assertRaises(RetryExhaustedError) as captured:
            call_with_retry(
                transport,
                REQUEST,
                policy=policy(retry_deadline_seconds=5.0),
                clock=clock,
                sleeper=clock.sleep,
                random_value=lambda: 0.5,
            )
        self.assertEqual(captured.exception.reason, "retry_deadline_exhausted")
        self.assertEqual(clock.sleeps, [])
        self.assertEqual(len(transport.requests), 1)

    def test_retry_deadline_is_rechecked_after_sleep(self) -> None:
        clock = FakeClock()
        transport = MockTransport(
            [TransientError("timeout", "temporary"), RESPONSE]
        )

        def oversleep(_seconds: float) -> None:
            clock.value += 10.0

        with self.assertRaises(RetryExhaustedError) as captured:
            call_with_retry(
                transport,
                REQUEST,
                policy=policy(retry_deadline_seconds=5.0),
                clock=clock,
                sleeper=oversleep,
                random_value=lambda: 0.5,
            )
        self.assertEqual(captured.exception.reason, "retry_deadline_exhausted")
        self.assertEqual(captured.exception.attempts, 1)
        self.assertEqual(len(transport.requests), 1)

    def test_random_source_must_return_a_probability(self) -> None:
        transport = MockTransport(
            [TransientError("connection", "temporary"), RESPONSE]
        )
        with self.assertRaisesRegex(ValueError, "between"):
            call_with_retry(
                transport,
                REQUEST,
                policy=policy(jitter_ratio=0.5),
                random_value=lambda: 2.0,
            )
        self.assertEqual(len(transport.requests), 1)
        with self.assertRaisesRegex(ValueError, "clock must return"):
            call_with_retry(
                MockTransport([RESPONSE]),
                REQUEST,
                policy=policy(),
                clock=lambda: math.nan,
            )


class StreamingTests(unittest.TestCase):
    def test_completed_stream_returns_usage_and_request_id(self) -> None:
        result = consume_canonical_stream(completed_events())
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.request_id, "stream-request-1")
        self.assertEqual((result.input_units, result.output_units), (7, 2))

    def test_refusal_and_truncation_are_explicit_terminal_states(self) -> None:
        for status in ("refused", "truncated"):
            with self.subTest(status=status):
                result = consume_canonical_stream(completed_events(status))
                self.assertEqual(result.status, status)

    def test_midstream_failure_preserves_partial_text_as_failed_state(self) -> None:
        events = completed_events()[:2] + [
            {
                "type": "response.failed",
                "category": "connection-lost",
                "message": "stream disconnected",
                "retryable": True,
            }
        ]
        with self.assertRaises(StreamInterruptedError) as captured:
            consume_canonical_stream(events)
        self.assertEqual(captured.exception.partial_text, "hel")
        self.assertEqual(captured.exception.request_id, "stream-request-1")
        self.assertTrue(captured.exception.retryable)

    def test_missing_terminal_event_is_incomplete_not_success(self) -> None:
        with self.assertRaises(StreamInterruptedError) as captured:
            consume_canonical_stream(completed_events()[:-1])
        self.assertEqual(captured.exception.category, "incomplete-stream")
        self.assertEqual(captured.exception.partial_text, "hello")

    def test_event_order_and_unknown_types_are_rejected(self) -> None:
        cases = (
            ([{"type": "response.text.delta", "text": "x"}], "before start"),
            (
                [
                    {"type": "response.started", "request_id": "req-1"},
                    {"type": "response.started", "request_id": "req-1"},
                ],
                "must be first",
            ),
            (
                [
                    {"type": "response.started", "request_id": "req-1"},
                    {"type": "vendor.new_event"},
                ],
                "unknown canonical",
            ),
        )
        for events, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(StreamProtocolError, message):
                    consume_canonical_stream(events)

    def test_invalid_delta_and_usage_are_rejected(self) -> None:
        bad_delta = completed_events()
        bad_delta[1] = {"type": "response.text.delta", "text": 42}
        with self.assertRaisesRegex(StreamProtocolError, "delta text"):
            consume_canonical_stream(bad_delta)

        bad_usage = completed_events()
        bad_usage[-1] = {
            "type": "response.finished",
            "status": "completed",
            "usage": {"input_units": True, "output_units": 2},
        }
        with self.assertRaisesRegex(StreamProtocolError, "integer"):
            consume_canonical_stream(bad_usage)

    def test_fields_are_exact_and_events_after_terminal_are_rejected(self) -> None:
        extra = completed_events()
        extra[1] = {
            "type": "response.text.delta",
            "text": "hel",
            "secret": "unexpected",
        }
        with self.assertRaisesRegex(StreamProtocolError, "unknown"):
            consume_canonical_stream(extra)

        trailing = completed_events() + [
            {"type": "response.text.delta", "text": "late"}
        ]
        with self.assertRaisesRegex(StreamProtocolError, "after terminal"):
            consume_canonical_stream(trailing)

    def test_stream_event_count_is_bounded(self) -> None:
        events = [{"type": "response.started", "request_id": "req-bounded"}] + [
            {"type": "response.text.delta", "text": ""}
        ] * MAX_STREAM_EVENTS
        with self.assertRaisesRegex(StreamLimitError, "events exceeds") as captured:
            consume_canonical_stream(events)
        self.assertEqual("events", captured.exception.resource)
        self.assertEqual(MAX_STREAM_EVENTS + 1, captured.exception.observed)
        self.assertEqual("req-bounded", captured.exception.request_id)
        self.assertFalse(captured.exception.retryable)

    def test_aggregate_stream_text_is_bounded(self) -> None:
        oversized = completed_events()
        oversized[1] = {
            "type": "response.text.delta",
            "text": "a" * (MAX_STREAM_TEXT_CHARS + 1),
        }
        with self.assertRaisesRegex(StreamLimitError, "text_chars exceeds") as captured:
            consume_canonical_stream(oversized)
        self.assertEqual("text_chars", captured.exception.resource)
        self.assertEqual(MAX_STREAM_TEXT_CHARS + 1, captured.exception.observed)
        self.assertEqual("stream-request-1", captured.exception.request_id)
        self.assertEqual("", captured.exception.partial_text)

        events = completed_events()
        events[1] = {
            "type": "response.text.delta",
            "text": "a" * MAX_STREAM_TEXT_CHARS,
        }
        events[2] = {"type": "response.text.delta", "text": "b"}
        with self.assertRaisesRegex(StreamLimitError, "text_chars exceeds") as captured:
            consume_canonical_stream(events)
        self.assertEqual(MAX_STREAM_TEXT_CHARS, len(captured.exception.partial_text))


if __name__ == "__main__":
    unittest.main()

