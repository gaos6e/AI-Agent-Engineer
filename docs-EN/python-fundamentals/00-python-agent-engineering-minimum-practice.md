---
title: "Minimum Python Practice for Agent Engineering"
tags:
  - ai-agent-engineer
  - Python
  - project
aliases:
  - Python task-queue project
  - Agent-engineering Python practice
lang: en
translation_key: "Python基础/00-Agent工程实践.md"
translation_source_hash: 47c9978390f17394defbc295da7ea0c4f6b8d25c749ae15012110b38909c4599
translation_route: zh-CN/Python基础/00-Agent工程实践
translation_default_route: zh-CN/Python基础/00-Agent工程实践
---

# Minimum Python Practice for Agent Engineering

## Project objective

Read a set of JSON tasks into Python, reject invalid records, summarize their statuses, and generate a JSON report. It does not call a model, but it practices the most important engineering boundaries of an Agent tool: input contracts, pure functions, explicit errors, deterministic output, and automated tests.

Supporting files:

```text
examples/
├── tasks.json
├── task_queue.py
└── test_task_queue.py
```

## Input and output contract

Every task must contain:

- `id`: a non-empty string, unique within the file;
- `title`: a non-empty string; and
- `status`: exactly one of `pending`, `running`, `done`, or `failed`.

The output is not a copy of the original data, but a report a later step can consume:

```json
{
  "total": 3,
  "by_status": {
    "done": 1,
    "pending": 2
  },
  "unfinished_ids": ["task-002", "task-003"]
}
```

Unknown fields, missing fields, duplicate IDs, and forbidden statuses must all fail. Do not “try to guess”; at an engineering boundary, explicit failure is easier to trace than silent correction.

## Implementation from scratch

1. Start with a `Task` data class and make its three fields and types explicit.
2. Write `parse_task(value)`, responsible only for turning one untrusted object into `Task` or raising `TaskValidationError`.
3. Write `load_tasks(path)`: read UTF-8, parse JSON, require an array root, and check ID uniqueness.
4. Write `summarize(tasks)`: produce statistics only from validated objects and perform no file I/O.
5. Write `write_report(report, path)`, making the file side effect explicit.
6. Write a command-line entry point that takes input and output paths as arguments instead of hard-coding a local absolute path.

This separation lets parsing, business calculation, and I/O be tested independently. When a future task source becomes an API, database, or model tool, the core summarization function can still be reused.

## How to run it

From the vault root, run:

```powershell
python -B '.\docs-EN\python-fundamentals\examples\task_queue.py' `
  '.\docs-EN\python-fundamentals\examples\tasks.json'
```

Without `--output`, the program writes JSON only to standard output and creates no file. To test file output:

```powershell
python -B '.\docs-EN\python-fundamentals\examples\task_queue.py' `
  '.\docs-EN\python-fundamentals\examples\tasks.json' `
  --output "$env:TEMP\task-report.json"
```

Run tests:

```powershell
python -B -m unittest discover `
  -s '.\docs-EN\python-fundamentals\examples' `
  -p 'test_*.py' `
  -v
```

`-B` prevents `.pyc` generation; tests use temporary directories and do not leave a report in the vault.

## Required exercises

1. Delete a task's `title`, then verify the program rejects it and identifies the failure.
2. Create a duplicate `id` and add a unit test for that failure.
3. Add an optional `owner` field: define the separate meanings of `null`, absence, and an empty string.
4. Add a `cancelled` status, updating validation, summary, and tests together rather than changing only one location.
5. Explain: if this program becomes an Agent tool, which errors can the model correct, which need retry, and which must stop for human attention?

## Common mistakes and diagnostics

- **Calculate directly from raw dictionaries**: invalid values move the error farther from its source. Convert to constrained objects first.
- **`except Exception: pass`**: bad data continues as though it succeeded. Catch only exceptions you can handle.
- **One function reads files, calls a network, calculates, and writes files**: testing becomes hard and side effects unclear. Keep I/O at the boundary.
- **Tests check only “no error”**: assert output values and error types too.
- **Paths are hard-coded to one machine**: use arguments and `pathlib.Path`.

## Self-check and mastery

- [ ] I can explain the difference between a data class, a dictionary, and a JSON object.
- [ ] I can explain why `parse_task` is easier to test than repeatedly taking fields in the main function.
- [ ] I can predict the result for an empty array, an object root, duplicate IDs, and a forbidden status.
- [ ] I can prove that running the same input again gives the same report.
- [ ] I can identify where the program's only persistent write occurs.
- [ ] I can rewrite an equivalent implementation without looking at the completed code and make every test pass.

When finished, return to [[python-fundamentals/00-index|the Python Fundamentals index]], then continue to API and JSON.

## References

Retrieved on **2026-07-13**.

- [Python `json` standard library](https://docs.python.org/3/library/json.html)
- [Python `dataclasses`](https://docs.python.org/3/library/dataclasses.html)
- [Python `pathlib`](https://docs.python.org/3/library/pathlib.html)
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)
