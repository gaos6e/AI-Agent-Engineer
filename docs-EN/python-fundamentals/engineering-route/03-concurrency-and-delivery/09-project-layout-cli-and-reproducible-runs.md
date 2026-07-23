---
title: "Project Layout, CLI, and Reproducible Runs"
tags: [ ai-agent-engineer, Python, cli, packaging ]
aliases: [ Python project layout, Python CLI ]
lang: en
translation_key: "Python基础/Agent工程路线/03-并发与交付/09-项目结构CLI与可复现运行.md"
translation_source_hash: 106e89fd520c946c993f51cd12fd296aac7a4ee94b0dee64df9cfdd41b30a5a8
translation_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/09-项目结构CLI与可复现运行
translation_default_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/09-项目结构CLI与可复现运行
---

# Project Layout, CLI, and Reproducible Runs

## Objective

Turn scattered scripts into a minimal project with an entry point, dependency declaration, and test boundary. Design a command-line interface that automation can call, and distinguish “the source runs,” “the environment can be rebuilt,” and “the build artifact can be released.”

## Start with one file; do not add structure for its own sake

During learning, a tool with no third-party dependencies can begin like this:

```text
task-reporter/
├── task_reporter.py
├── sample_tasks.json
└── test_task_reporter.py
```

When modules multiply, an installable command is needed, or tests must avoid accidentally importing a working-directory file, move to a package layout:

```text
task-reporter/
├── pyproject.toml
├── README.md
├── src/
│   └── task_reporter/
│       ├── __init__.py
│       ├── cli.py
│       └── core.py
└── tests/
    └── test_core.py
```

Directories express boundaries: `core.py` holds pure logic, `cli.py` handles the command line and exit codes, external clients live in adapters, and tests do not depend on real credentials. Do not call every module the generic name `utils.py`.

## A CLI is a stable interface

People, scripts, and workflows call a command line, so specify:

- argument names, types, defaults, and mutual exclusions;
- whether standard output (stdout) is machine-readable;
- whether diagnostic logs and errors go to standard error (stderr);
- success and failure exit codes; and
- whether it writes files, its overwrite policy, and repeat-run behavior.

A minimum `argparse` entry point:

```python
import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a task summary")
    parser.add_argument("input", type=Path, help="UTF-8 JSON input")
    parser.add_argument("--output", type=Path, help="Optional output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args.input, args.output)
    except TaskValidationError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Taking `argv` as a parameter makes the CLI directly testable. Return an integer and raise `SystemExit` only at the outermost layer so core logic does not terminate the whole interpreter. Put the convention in the README rather than making readers infer it. Colored help and error suggestions in `argparse` were added in 3.14; portable 3.11+ code does not pass those newer constructor arguments.

## What `pyproject.toml` governs

`pyproject.toml` is the standard configuration entry point for a Python project. It can contain the build system, project metadata, and tool configuration. It is not a lock file.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "task-reporter"
version = "0.1.0"
requires-python = ">=3.11,<3.15"
dependencies = []

[project.scripts]
task-reporter = "task_reporter.cli:main"
```

This is a structural example; it does not require installing `hatchling` in this vault. A distributable package needs a selected and locked build backend. A `pyproject.toml` that only holds tool configuration can omit `[build-system]`. `requires-python` is an installation constraint; a PyPI classifier is not.

## The evidence chain for reproducible execution

Reproducibility is not “it runs on my machine.” At minimum, record:

1. the source-code and configuration version;
2. the supported Python range and actual tested version;
3. direct dependency declarations and the locking or constraint strategy;
4. exact commands to create the environment and run tests;
5. versions or contracts of external services, models, data, or environment variables; and
6. artifact provenance, hashes, or build records when the risk requires them.

`pip freeze` can snapshot the current environment, but does not explain direct dependencies or replace standard project metadata. With `uv`, teams usually commit `pyproject.toml` and `uv.lock`, not `.venv`. As of this page's retrieval date, `uv sync` defaults to exact sync and removes packages outside the locked environment, while `uv run` allows extra packages by default (inexact). Such tool semantics change quickly, so teams should fix commands by their locked version and current official documentation.

## Local run checklist

At the project root:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip --version
python -m pip install -e .
python -B -m unittest discover -s .\tests -p 'test_*.py' -v
python -m task_reporter.cli --help
```

With a `src/` layout, the project root does not directly add `src` to the import path. After the editable installation above, tests and `python -m` can import by package name. The example build backend causes a network installation and local-environment write, so this knowledge base has not run those installation commands; run them only in a separate practice directory using a locked policy. The course's single-file task queue does not need a project installation.

If a real project requires Python 3.14, use `py -3.14` or an environment manager to select the interpreter and verify it in CI. Do not claim cross-version compatibility merely because documentation says `python --version`.

## Minimum pre-delivery checks

- The repository contains no `.venv`, `__pycache__`, real `.env`, secrets, or large data.
- A new environment can be rebuilt from declarations, and tests do not depend on personal absolute paths.
- `--help` and failure exit codes match the documentation.
- Downstream tools can parse stdout reliably, and logs do not mix into JSON.
- File writes have an overwrite policy; failure does not leave a half-produced file that looks successful.
- Build, install, and run are three different actions and the instructions do not conflate them.

## Exercises

1. Refactor a one-file script into `core.py` and `cli.py`; the core function must not read `sys.argv`.
2. Assert exit codes, stdout, and stderr for CLI success, input error, and an unknown argument.
3. Write a minimum `pyproject.toml` and explain each of `[build-system]`, `[project]`, and `[project.scripts]`.
4. Rebuild an environment in a fresh temporary directory, record every command, and identify remaining unfixed external state.

## Self-check

- [ ] I can explain why to keep one file first and when to move to a `src/` layout.
- [ ] I can design machine-usable stdout, stderr, and exit codes.
- [ ] I can distinguish `pyproject.toml`, a requirements file, and a lock file.
- [ ] I can list the non-code evidence required to reproduce a run.
- [ ] I will not call “syntax parses” evidence that dependencies, integrations, and versions were all verified.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/03-concurrency-and-delivery/08-async-concurrency-cancellation-and-rate-limits|Async Concurrency, Cancellation, and Rate Limits]].
- Next, [[python-fundamentals/engineering-route/03-concurrency-and-delivery/10-agent-tool-function-design|Agent Tool Function Design]].
- See [[git/00-index|Git]] for version collaboration, and the MLOps and LLMOps courses for automated delivery and environment governance.

## References

Retrieved on **2026-07-14**.

- [Python: `argparse`](https://docs.python.org/3.14/library/argparse.html)
- [PyPA: writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PyPA: project metadata specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [uv: projects and locking](https://docs.astral.sh/uv/guides/projects/)
