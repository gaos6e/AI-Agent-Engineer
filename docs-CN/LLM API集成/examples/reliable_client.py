"""Provider-neutral reliability core for offline LLM client exercises."""

from __future__ import annotations

import math
import random
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol


TRANSIENT_CATEGORIES = frozenset(
    {"connection", "timeout", "rate_limit", "server_overloaded"}
)
PERMANENT_CATEGORIES = frozenset(
    {
        "authentication",
        "permission",
        "invalid_request",
        "quota",
        "unsupported_capability",
    }
)
COMPLETION_STATUSES = frozenset({"completed", "refused", "truncated"})
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,127}$")
MAX_USER_TEXT_CHARS = 100_000
MAX_STREAM_EVENTS = 4_096
MAX_STREAM_TEXT_CHARS = 100_000


class ClientError(RuntimeError):
    """Base class for the canonical client layer."""


class TransientError(ClientError):
    """A classified failure that may be retried within one bounded budget."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        retry_after_seconds: float | None = None,
        request_id: str | None = None,
    ) -> None:
        if category not in TRANSIENT_CATEGORIES:
            raise ValueError(f"unsupported transient category: {category!r}")
        _require_text(message, "message", maximum=500)
        if retry_after_seconds is not None:
            _require_number(
                retry_after_seconds,
                "retry_after_seconds",
                minimum=0.0,
                maximum=86_400.0,
            )
        if request_id is not None:
            _require_identifier(request_id, "request_id")
        super().__init__(message)
        self.category = category
        self.retry_after_seconds = retry_after_seconds
        self.request_id = request_id


class PermanentError(ClientError):
    """A classified failure that requires a request, policy, or config change."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        request_id: str | None = None,
    ) -> None:
        if category not in PERMANENT_CATEGORIES:
            raise ValueError(f"unsupported permanent category: {category!r}")
        _require_text(message, "message", maximum=500)
        if request_id is not None:
            _require_identifier(request_id, "request_id")
        super().__init__(message)
        self.category = category
        self.request_id = request_id


class RetryExhaustedError(ClientError):
    """One retry owner exhausted attempts or its retry deadline."""

    def __init__(
        self,
        reason: str,
        *,
        attempts: int,
        total_wait_seconds: float,
        last_error: TransientError,
    ) -> None:
        if reason not in {"attempts_exhausted", "retry_deadline_exhausted"}:
            raise ValueError(f"unsupported exhaustion reason: {reason!r}")
        super().__init__(
            f"{reason} after {attempts} attempt(s): "
            f"{last_error.category}: {last_error}"
        )
        self.reason = reason
        self.attempts = attempts
        self.total_wait_seconds = total_wait_seconds
        self.last_error = last_error


class StreamProtocolError(ClientError):
    """The canonical stream violated its local event contract."""


class StreamLimitError(StreamProtocolError):
    """A bounded stream resource exceeded the local contract."""

    def __init__(
        self,
        resource: str,
        *,
        limit: int,
        observed: int,
        request_id: str | None,
        partial_text: str,
    ) -> None:
        if resource not in {"events", "text_chars"}:
            raise ValueError(f"unsupported stream resource: {resource!r}")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not isinstance(observed, int) or isinstance(observed, bool) or observed <= limit:
            raise ValueError("observed must be an integer greater than limit")
        if request_id is not None:
            _require_identifier(request_id, "request_id")
        if not isinstance(partial_text, str):
            raise ValueError("partial_text must be a string")
        super().__init__(f"stream {resource} exceeds {limit} (observed {observed})")
        self.category = "resource-limit"
        self.resource = resource
        self.limit = limit
        self.observed = observed
        self.request_id = request_id
        self.partial_text = partial_text
        self.retryable = False


class StreamInterruptedError(ClientError):
    """The stream failed or ended before a valid terminal event."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        request_id: str | None,
        partial_text: str,
        retryable: bool,
    ) -> None:
        _require_identifier(category, "stream category")
        _require_text(message, "stream message", maximum=500)
        if request_id is not None:
            _require_identifier(request_id, "request_id")
        if not isinstance(partial_text, str):
            raise ValueError("partial_text must be a string")
        if not isinstance(retryable, bool):
            raise ValueError("retryable must be a boolean")
        super().__init__(message)
        self.category = category
        self.request_id = request_id
        self.partial_text = partial_text
        self.retryable = retryable


def _require_text(value: Any, context: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-blank string")
    if len(value) > maximum:
        raise ValueError(f"{context} exceeds {maximum} characters")
    return value


def _require_identifier(value: Any, context: str) -> str:
    text = _require_text(value, context, maximum=128)
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError(f"{context} must match {IDENTIFIER_PATTERN.pattern}")
    return text


def _require_integer(
    value: Any,
    context: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{context} must be between {minimum} and {maximum}")
    return value


def _require_number(
    value: Any,
    context: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{context} must be a finite number")
    if not minimum <= number <= maximum:
        raise ValueError(f"{context} must be between {minimum} and {maximum}")
    return number


@dataclass(frozen=True)
class LLMRequest:
    operation_id: str
    prompt_version: str
    model_profile: str
    user_text: str

    def __post_init__(self) -> None:
        _require_identifier(self.operation_id, "operation_id")
        _require_identifier(self.prompt_version, "prompt_version")
        _require_identifier(self.model_profile, "model_profile")
        _require_text(
            self.user_text, "user_text", maximum=MAX_USER_TEXT_CHARS
        )


@dataclass(frozen=True)
class LLMResponse:
    text: str
    status: str
    request_id: str
    provider: str
    model: str
    input_units: int
    output_units: int

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        if self.status not in COMPLETION_STATUSES:
            raise ValueError(f"unsupported completion status: {self.status!r}")
        _require_identifier(self.request_id, "request_id")
        _require_identifier(self.provider, "provider")
        _require_identifier(self.model, "model")
        _require_integer(
            self.input_units,
            "input_units",
            minimum=0,
            maximum=10_000_000_000,
        )
        _require_integer(
            self.output_units,
            "output_units",
            minimum=0,
            maximum=10_000_000_000,
        )


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    retry_deadline_seconds: float = 30.0
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter_ratio: float = 0.25

    def __post_init__(self) -> None:
        _require_integer(
            self.max_attempts, "max_attempts", minimum=1, maximum=20
        )
        _require_number(
            self.retry_deadline_seconds,
            "retry_deadline_seconds",
            minimum=0.001,
            maximum=86_400.0,
        )
        base = _require_number(
            self.base_delay_seconds,
            "base_delay_seconds",
            minimum=0.0,
            maximum=3_600.0,
        )
        maximum = _require_number(
            self.max_delay_seconds,
            "max_delay_seconds",
            minimum=0.0,
            maximum=3_600.0,
        )
        if maximum < base:
            raise ValueError("max_delay_seconds must be at least base_delay_seconds")
        _require_number(
            self.jitter_ratio,
            "jitter_ratio",
            minimum=0.0,
            maximum=1.0,
        )


@dataclass(frozen=True)
class AttemptRecord:
    attempt: int
    outcome: str
    category: str | None
    request_id: str | None
    wait_seconds: float


@dataclass(frozen=True)
class ClientResult:
    response: LLMResponse
    attempts: tuple[AttemptRecord, ...]
    total_wait_seconds: float


@dataclass(frozen=True)
class StreamResult:
    text: str
    status: str
    request_id: str
    input_units: int
    output_units: int


class Transport(Protocol):
    def send(self, request: LLMRequest) -> LLMResponse: ...


class MockTransport:
    """Return or raise queued outcomes and retain only test request objects."""

    def __init__(self, outcomes: list[LLMResponse | Exception]) -> None:
        if not outcomes:
            raise ValueError("outcomes must not be empty")
        self._outcomes = list(outcomes)
        self.requests: list[LLMRequest] = []

    def send(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._outcomes:
            raise RuntimeError("mock outcomes exhausted")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if not isinstance(outcome, LLMResponse):
            raise TypeError("mock outcome must be an LLMResponse or Exception")
        return outcome


def _retry_delay(
    policy: RetryPolicy,
    *,
    failed_attempt: int,
    error: TransientError,
    random_value: Callable[[], float],
) -> float:
    sample = _require_number(
        random_value(), "random_value", minimum=0.0, maximum=1.0
    )
    exponential = min(
        policy.max_delay_seconds,
        policy.base_delay_seconds * (2 ** (failed_attempt - 1)),
    )
    factor = 1.0 - policy.jitter_ratio + 2.0 * policy.jitter_ratio * sample
    delay = exponential * factor
    if error.retry_after_seconds is not None:
        delay = max(delay, error.retry_after_seconds)
    return delay


def _read_clock(clock: Callable[[], float]) -> float:
    value = clock()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("clock must return a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("clock must return a finite number")
    return number


def call_with_retry(
    transport: Transport,
    request: LLMRequest,
    *,
    policy: RetryPolicy,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
) -> ClientResult:
    """Retry only classified transient failures within one explicit budget."""
    started_at = _read_clock(clock)
    records: list[AttemptRecord] = []
    total_wait = 0.0
    last_error: TransientError | None = None

    for attempt in range(1, policy.max_attempts + 1):
        if attempt > 1:
            elapsed = _read_clock(clock) - started_at
            if elapsed < 0:
                raise ValueError("clock must be monotonic")
            if elapsed >= policy.retry_deadline_seconds:
                if last_error is None:
                    raise RuntimeError("retry deadline reached without an error")
                raise RetryExhaustedError(
                    "retry_deadline_exhausted",
                    attempts=attempt - 1,
                    total_wait_seconds=total_wait,
                    last_error=last_error,
                ) from last_error
        try:
            response = transport.send(request)
        except TransientError as exc:
            last_error = exc
            if attempt >= policy.max_attempts:
                records.append(
                    AttemptRecord(
                        attempt,
                        "transient_error",
                        exc.category,
                        exc.request_id,
                        0.0,
                    )
                )
                raise RetryExhaustedError(
                    "attempts_exhausted",
                    attempts=attempt,
                    total_wait_seconds=total_wait,
                    last_error=exc,
                ) from exc

            delay = _retry_delay(
                policy,
                failed_attempt=attempt,
                error=exc,
                random_value=random_value,
            )
            elapsed = _read_clock(clock) - started_at
            if elapsed < 0:
                raise ValueError("clock must be monotonic")
            if elapsed + delay >= policy.retry_deadline_seconds:
                records.append(
                    AttemptRecord(
                        attempt,
                        "transient_error",
                        exc.category,
                        exc.request_id,
                        0.0,
                    )
                )
                raise RetryExhaustedError(
                    "retry_deadline_exhausted",
                    attempts=attempt,
                    total_wait_seconds=total_wait,
                    last_error=exc,
                ) from exc
            records.append(
                AttemptRecord(
                    attempt,
                    "transient_error",
                    exc.category,
                    exc.request_id,
                    delay,
                )
            )
            sleeper(delay)
            total_wait += delay
            continue
        records.append(
            AttemptRecord(
                attempt,
                "success",
                None,
                response.request_id,
                0.0,
            )
        )
        return ClientResult(response, tuple(records), total_wait)

    raise RuntimeError("unreachable retry state")


def _require_event_fields(
    event: dict[str, Any], expected: set[str], event_type: str
) -> None:
    actual = set(event)
    missing = expected - actual
    unknown = actual - expected
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unknown:
            details.append(f"unknown={sorted(unknown)}")
        raise StreamProtocolError(
            f"{event_type} has invalid fields: {', '.join(details)}"
        )


def _parse_usage(raw: Any) -> tuple[int, int]:
    if not isinstance(raw, dict):
        raise StreamProtocolError("usage must be an object")
    _require_event_fields(raw, {"input_units", "output_units"}, "usage")
    try:
        input_units = _require_integer(
            raw["input_units"],
            "usage.input_units",
            minimum=0,
            maximum=10_000_000_000,
        )
        output_units = _require_integer(
            raw["output_units"],
            "usage.output_units",
            minimum=0,
            maximum=10_000_000_000,
        )
    except ValueError as exc:
        raise StreamProtocolError(str(exc)) from exc
    return input_units, output_units


def consume_canonical_stream(events: Iterable[dict[str, Any]]) -> StreamResult:
    """Consume adapter-normalized events and require one explicit terminal event."""
    state = "init"
    request_id: str | None = None
    parts: list[str] = []
    text_chars = 0
    result: StreamResult | None = None

    for event_index, event in enumerate(events, start=1):
        if event_index > MAX_STREAM_EVENTS:
            raise StreamLimitError(
                "events",
                limit=MAX_STREAM_EVENTS,
                observed=event_index,
                request_id=request_id,
                partial_text="".join(parts),
            )
        if not isinstance(event, dict):
            raise StreamProtocolError("each stream event must be an object")
        if result is not None:
            raise StreamProtocolError("event received after terminal event")
        event_type = event.get("type")
        if not isinstance(event_type, str):
            raise StreamProtocolError("event.type must be a string")

        if event_type == "response.started":
            _require_event_fields(event, {"type", "request_id"}, event_type)
            if state != "init":
                raise StreamProtocolError("response.started must be first")
            try:
                request_id = _require_identifier(
                    event["request_id"], "request_id"
                )
            except ValueError as exc:
                raise StreamProtocolError(str(exc)) from exc
            state = "streaming"
        elif event_type == "response.text.delta":
            _require_event_fields(event, {"type", "text"}, event_type)
            if state != "streaming":
                raise StreamProtocolError("text delta received before start")
            text = event["text"]
            if not isinstance(text, str):
                raise StreamProtocolError("delta text must be a string")
            text_chars += len(text)
            if text_chars > MAX_STREAM_TEXT_CHARS:
                raise StreamLimitError(
                    "text_chars",
                    limit=MAX_STREAM_TEXT_CHARS,
                    observed=text_chars,
                    request_id=request_id,
                    partial_text="".join(parts),
                )
            parts.append(text)
        elif event_type == "response.failed":
            _require_event_fields(
                event,
                {"type", "category", "message", "retryable"},
                event_type,
            )
            if state != "streaming":
                raise StreamProtocolError("failure received before start")
            retryable = event["retryable"]
            if not isinstance(retryable, bool):
                raise StreamProtocolError("retryable must be a boolean")
            try:
                category = _require_identifier(
                    event["category"], "stream category"
                )
                message = _require_text(
                    event["message"], "stream message", maximum=500
                )
            except ValueError as exc:
                raise StreamProtocolError(str(exc)) from exc
            raise StreamInterruptedError(
                category,
                message,
                request_id=request_id,
                partial_text="".join(parts),
                retryable=retryable,
            )
        elif event_type == "response.finished":
            _require_event_fields(
                event, {"type", "status", "usage"}, event_type
            )
            if state != "streaming" or request_id is None:
                raise StreamProtocolError("finish received before start")
            status = event["status"]
            if status not in COMPLETION_STATUSES:
                raise StreamProtocolError(
                    f"unsupported completion status: {status!r}"
                )
            input_units, output_units = _parse_usage(event["usage"])
            result = StreamResult(
                text="".join(parts),
                status=status,
                request_id=request_id,
                input_units=input_units,
                output_units=output_units,
            )
            state = "finished"
        else:
            raise StreamProtocolError(f"unknown canonical event: {event_type!r}")

    if result is None:
        raise StreamInterruptedError(
            "incomplete-stream",
            "stream ended without a terminal event",
            request_id=request_id,
            partial_text="".join(parts),
            retryable=True,
        )
    return result
