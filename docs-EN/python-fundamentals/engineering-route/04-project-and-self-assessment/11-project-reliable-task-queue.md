---
title: "Project: Reliable Task Queue"
tags:
  - ai-agent-engineer
  - Python
  - project
aliases: [ Reliable task-queue project, Reliable task-queue Agent-engineering practice ]
lang: en
translation_key: "Python基础/Agent工程路线/04-项目与自测/11-项目-可靠任务队列.md"
translation_source_hash: 1f48a6d616564022090fe5558c0cab5260a6cebd0fbf72c7dfa793b14b1f3cae
translation_route: zh-CN/Python基础/Agent工程路线/04-项目与自测/11-项目-可靠任务队列
translation_default_route: zh-CN/Python基础/Agent工程路线/04-项目与自测/11-项目-可靠任务队列
---

# Project: Reliable Task Queue

## What you will prove

This is the capstone project for the core foundations. It neither calls a model nor depends on a network. Instead, it first proves more basic Agent-engineering abilities: turn untrusted JSON into validated objects, separate calculations from I/O, classify failures stably, expose behavior through a CLI, and test boundaries. Retries, logging, and async concurrency remain deliberate advanced extensions; do not disguise a small project as a production task executor.

First implement it in your own empty directory, then compare it with the adjacent `examples/`. Reading and running a finished solution is not completing the project.

## Project objective

Read a set of JSON tasks into Python, reject invalid records, summarize statuses, and produce a JSON report. The entire program must run locally and offline, read no environment secrets, never write its input file, and produce deterministic results for the same input.

Supporting files:

```text
examples/
├── tasks.json
├── task_queue.py
└── test_task_queue.py
```

The supporting code is deliberately one file so beginners can see the boundaries. It is not a directory template every production project should copy. If you need a distributable CLI or more modules, split it into a package as described in [[python-fundamentals/engineering-route/03-concurrency-and-delivery/09-project-layout-cli-and-reproducible-runs|Project Layout, CLI, and Reproducible Runs]].

## Input and output contract

Every task must contain:

- `id`: a non-empty string, unique within the file;
- `title`: a non-empty string; and
- `status`: exactly one of `pending`, `running`, `done`, or `failed`.

The output is not a copy of the source data, but a report a next step can consume:

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

The input file is limited to **1,000,000 bytes**. Reject unknown fields, missing fields, duplicate IDs, forbidden statuses, non-UTF-8 text, invalid JSON, a non-array root, and oversize input. All three string fields reject empty values and leading or trailing whitespace; do not silently `strip` them. Do not “try to guess.” At an engineering boundary, explicit failure is easier to trace than silent correction.

`by_status` keys are sorted by their status string; `unfinished_ids` retain the original order of valid input records. When `--output` is given, its path must not point to the same file as the input, so the input cannot be overwritten.

### Failure contract

- Convert input and read failures to `TaskValidationError` while preserving the original causal chain.
- For expected input errors, the CLI writes to stderr and returns exit code `2`.
- Do not make a traceback an ordinary user hint, although tests or controlled logs can still view the cause.
- An output-path conflict or write failure is an execution failure: write to stderr and return `1`; do not disguise it as invalid input data.

## Implementation from scratch

1. Write a `Task` data class with three fields and their types; remember that type hints do not automatically validate JSON.
2. Write `parse_task(value, index)`, which only turns one untrusted object into `Task` or raises `TaskValidationError` with the array position.
3. Write `load_tasks(path)`: limit bytes first, then read UTF-8, parse JSON, require an array root, and check ID uniqueness.
4. Write `summarize(tasks)`: generate statistics only from validated objects and do not read or write files.
5. Write `write_report(report, path)`, clearly identifying when a file side effect occurs.
6. Write a command-line entry point with input and output paths as arguments rather than a hard-coded local absolute path; expected input errors return a stable exit code.
7. Start with the smallest success test, then add the failure matrix one behavior at a time; make every new behavior fail a test first.

This split tests parsing, business calculation, and I/O separately. If a task source later becomes an API, database, or model tool, the core summarization function remains reusable.

## How to run it

From the vault root, run:

```powershell
python -B '.\docs-EN\python-fundamentals\engineering-route\04-project-and-self-assessment\examples\task_queue.py' `
  '.\docs-EN\python-fundamentals\engineering-route\04-project-and-self-assessment\examples\tasks.json'
```

Without `--output`, the program writes JSON only to stdout and creates no file. To test file output:

```powershell
python -B '.\docs-EN\python-fundamentals\engineering-route\04-project-and-self-assessment\examples\task_queue.py' `
  '.\docs-EN\python-fundamentals\engineering-route\04-project-and-self-assessment\examples\tasks.json' `
  --output "$env:TEMP\task-report.json"
```

Run tests with:

```powershell
python -B -m unittest discover `
  -s '.\docs-EN\python-fundamentals\engineering-route\04-project-and-self-assessment\examples' `
  -p 'test_*.py' `
  -v
```

`-B` prevents `.pyc` generation; tests use temporary directories and leave no report in the vault.

### Acceptance matrix

| Dimension | Minimum verification |
| --- | --- |
| Success | Empty array, typical tasks, Unicode, deterministic status sorting |
| Fields | Missing field, unknown field, whitespace string, forbidden status |
| Files | Missing file, invalid UTF-8, invalid JSON, wrong root type, oversize input |
| Collection | Duplicate ID and the unfinished-ID ordering contract |
| Output | UTF-8 JSON can be parsed again; stdout and file modes agree |
| CLI | `0` on success, `2` for expected input errors, `1` for output conflict/write failure; failures do not emit successful JSON |

### Optional advanced extensions

Choose one only after the required acceptance passes; do not break core determinism:

1. Add bounded retries for a simulated transient dependency, inject `sleep`, and never really wait in tests.
2. Write diagnostic logs to stderr with an operation ID that omits task body content, while keeping stdout pure JSON.
3. Simulate bounded async concurrency for several independent read-only tasks, verifying the cap, cancellation, and partial-failure policy.

## Required exercises

1. Delete one task's `title`, then verify that the program rejects it and identifies its array position.
2. Create a duplicate `id`, write a failing test first, then fix the implementation.
3. Add an optional `owner` field: first define the distinct meanings of `null`, absence, and an empty string, then update the data class, validation, and tests.
4. Add a `cancelled` status; update validation, summary, and tests together rather than changing only one place.
5. Add `--fail-on-unfinished`: return a nonzero exit code when unfinished tasks exist while still emitting a valid report; document how this differs from invalid input.
6. Explain which failures could let a model correct parameters, which require retry, and which must stop for human attention if this program becomes an Agent tool.

## Common mistakes and diagnostics

- **Calculate directly from raw dictionaries**: unvalidated values move failures farther from their cause. Convert to constrained objects first.
- **`except Exception: pass`**: invalid data can continue as if successful. Catch only what you can handle.
- **One function reads, calls a network, calculates, and writes**: testing is difficult and side effects are unclear. Put I/O at the boundary.
- **Tests assert only “no error”**: assert values and error types too.
- **Hard-code a local path**: use parameters and `pathlib.Path`.
- **Test only success examples**: input boundaries matter chiefly in failure behavior; fill the acceptance matrix row by row.
- **Mistake this project for a task executor**: it only validates and summarizes tasks; it does not schedule, execute concurrently, or implement durable queue semantics.

## Self-check and mastery

- [ ] I can explain the difference between a data class, a dictionary, and a JSON object.
- [ ] I can explain why `parse_task` is easier to test than repeatedly taking fields in `main`.
- [ ] I can predict the results for an empty array, object root, duplicate ID, and forbidden status.
- [ ] I can prove that running the same input again yields the same report.
- [ ] I can identify where the program's sole persistent write occurs.
- [ ] I can distinguish what stdout, stderr, and exit codes each communicate.
- [ ] I can state the production concerns the example does not cover: atomic writes, concurrent writes, real queue persistence, authorization, and recovery.
- [ ] I can rewrite an equivalent implementation without looking at the solution and make every test pass.

Next, complete [[python-fundamentals/engineering-route/04-project-and-self-assessment/12-course-wide-self-check-and-mastery|Course-Wide Self-Check and Mastery]], then return to [[python-fundamentals/00-index|the Python Fundamentals index]].

## References

Retrieved on **2026-07-14**.

- [Python `json` standard library](https://docs.python.org/3.14/library/json.html)
- [Python `dataclasses`](https://docs.python.org/3.14/library/dataclasses.html)
- [Python `pathlib`](https://docs.python.org/3.14/library/pathlib.html)
- [Python `unittest`](https://docs.python.org/3.14/library/unittest.html)
