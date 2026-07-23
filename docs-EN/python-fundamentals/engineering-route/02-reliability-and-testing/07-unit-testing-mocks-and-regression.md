---
title: "Unit Testing, Mocks, and Regression"
tags: [ ai-agent-engineer, Python, testing ]
aliases: [ Python unit testing, Python mocks ]
lang: en
translation_key: "Python基础/Agent工程路线/02-可靠性与测试/07-单元测试Mock与回归.md"
translation_source_hash: 47e494b82cc5bfa2c863bdb2d0a7e184694ccbcced95d3ee00f2d62fcb378817
translation_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/07-单元测试Mock与回归
translation_default_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/07-单元测试Mock与回归
---

# Unit Testing, Mocks, and Regression

## Objective

Use fast, deterministic, repeatable tests to prove core logic and failure contracts. At external boundaries such as files, clocks, and network clients, use substitutes rather than mocking every implementation detail.

## What a test should answer

A useful test fixes at least one observable contract:

```text
Given input/state → execute public behavior → observe output, side effect, or error
```

Common levels are:

| Level | Focus | Example |
| --- | --- | --- |
| Unit test | Logic and boundaries of one function or module | A forbidden task status is rejected |
| Integration test | Whether two real components cooperate | A real file can be parsed after it is written |
| End-to-end test | Whether a user path completes | A CLI generates a report from an input file |
| Regression test | Whether an observed defect stays fixed | Duplicate IDs were once missed |

A mock test is not an integration test. A test suite should let most core logic run without a network, then use a small number of controlled integration tests to check real SDKs, services, or file formats.

## Arrange—Act—Assert

```python
import unittest


class RetryTests(unittest.TestCase):
    def test_succeeds_after_one_transient_failure(self) -> None:
        # Arrange
        outcomes = iter([TemporaryDependencyFailure(), "ok"])
        delays: list[float] = []

        def operation() -> str:
            value = next(outcomes)
            if isinstance(value, Exception):
                raise value
            return value

        # Act
        result = retry_transient(
            operation, attempts=2, sleep=delays.append, base_delay=0.1
        )

        # Assert
        self.assertEqual(result, "ok")
        self.assertEqual(delays, [0.1])
```

A test name should describe behavior. Assert only contract-relevant results so a failure is easy to locate.

## Boundary values and failure paths

For a JSON tool, cover at least:

- minimum valid input and typical valid input;
- empty input, upper limits, and values just beyond a limit;
- wrong root type, missing fields, unknown fields, and forbidden enum values;
- missing files and UTF-8/JSON parsing failures;
- duplicate IDs, ordering, and deterministic output; and
- error behavior when output writing fails.

Use `subTest` to organize table-driven cases for one contract:

```python
def test_invalid_statuses(self) -> None:
    for status in ("", "DONE", None, 3):
        with self.subTest(status=status):
            with self.assertRaises(TaskValidationError):
                parse_task({"id": "a", "title": "x", "status": status}, 0)
```

Do not assert only that “an exception was raised.” Prefer a stable exception type or error category; complete natural-language text is brittle when wording changes.

## Make side effects replaceable

The simplest test double is often not `mock.patch`, but an explicit dependency:

```python
from collections.abc import Callable


def create_report(fetch: Callable[[], list[Task]]) -> dict[str, object]:
    return summarize(fetch())
```

Tests pass `lambda: [...]`; production passes a real client. The contract is clear and does not depend on internal module names.

When `patch()` is necessary, patch the name where the module under test **looks it up**. If `worker.py` uses `from client import send`, patch `worker.send`, not `client.send`. `autospec=True` can check attributes and call signatures, but it cannot prove the network protocol is correct; dynamic attributes or side-effecting properties can also limit autospec.

Use `AsyncMock` for asynchronous dependencies, while still testing real control flow for cancellation, timeouts, and concurrency limits.

## Files, time, and random values

- Files: use `tempfile.TemporaryDirectory()`, not a fixed repository path.
- Time: inject `clock()`; assertions should not depend on the wall clock.
- Waiting: inject `sleep()`; tests should not actually sleep.
- Randomness: inject a fixed-seed random source, or assert a range instead of one accidental value.
- Environment variables: pass a dictionary to the loading function, or patch and restore after the test.

Determinism not only stabilizes tests; it also makes Agent tools easier to replay and audit.

## Minimal evidence for a regression test

When fixing a defect, keep the smallest failing input:

1. Write a test that failed before the fix.
2. Name the test for the defect, not a ticket number.
3. Make the smallest fix.
4. Run neighboring tests as well.
5. If a protocol or security boundary changed, add an integration test and change note.

Coverage says only which lines executed. It cannot prove assertions are sufficient, data represents real distributions, or a system is safe. Use coverage to locate blind spots, not as a quality target in itself.

## Run this course's tests

From the vault root, run:

```powershell
python -B -m unittest discover `
  -s '.\docs-EN\python-fundamentals\examples' `
  -p 'test_*.py' `
  -v
```

`-B` prevents Python from writing `.pyc` files during tests; the tests use temporary directories themselves.

## Exercises

1. Add task-queue tests for a non-array root, invalid JSON, unknown fields, forbidden status, and an empty string.
2. Write a test where order changes but summary counts do not; then decide whether `unfinished_ids` should retain input order.
3. Test `load_settings()` with an ordinary dictionary rather than modifying real `os.environ`.
4. Find an unnecessary mock and refactor it into a pure function or an explicit dependency.

## Self-check

- [ ] I can state Given—When—Then for every test.
- [ ] I can distinguish unit, integration, end-to-end, and regression tests.
- [ ] I know to patch the lookup location, rather than blindly patch the definition location.
- [ ] I can control files, time, waiting, and randomness in a test.
- [ ] I will not claim that coverage or passing mocks prove a real service was verified.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/02-reliability-and-testing/06-configuration-logging-and-sensitive-information|Configuration, Logging, and Sensitive Information]].
- Next, [[python-fundamentals/engineering-route/03-concurrency-and-delivery/08-async-concurrency-cancellation-and-rate-limits|Async Concurrency, Cancellation, and Rate Limits]].
- Evaluation data and model behavior belong to the evaluation course; ordinary unit tests do not replace model-quality evaluation.

## References

Retrieved on **2026-07-14**.

- [Python: `unittest`](https://docs.python.org/3.14/library/unittest.html)
- [Python: `unittest.mock`](https://docs.python.org/3.14/library/unittest.mock.html)
- [Python: `tempfile`](https://docs.python.org/3.14/library/tempfile.html)
