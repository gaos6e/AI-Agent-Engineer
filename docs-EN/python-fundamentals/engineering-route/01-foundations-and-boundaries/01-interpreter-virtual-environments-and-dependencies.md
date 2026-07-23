---
title: "Interpreter, Virtual Environments, and Dependencies"
tags: [ ai-agent-engineer, Python, environment-management ]
aliases: [ Python environment primer, venv and pip ]
lang: en
translation_key: "Python基础/Agent工程路线/01-基础与边界/01-解释器虚拟环境与依赖.md"
translation_source_hash: 4dfa18726f6a37460244ec75deff1d28f92595825e376961591620260f1d6339
translation_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/01-解释器虚拟环境与依赖
translation_default_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/01-解释器虚拟环境与依赖
---

# Interpreter, Virtual Environments, and Dependencies

## Objective

By the end of this lesson, you should be able to identify which Python Windows 11 and PowerShell 7 are using, explain the roles of the interpreter, `venv`, `pip`, dependency declarations, and lock files, and move from `venv + pip` to `uv` when it is useful.

## First distinguish five things

| Thing | Question it answers | Common check |
| --- | --- | --- |
| Python interpreter | Which program executes a `.py` file? | `python --version`, `Get-Command python` |
| Virtual environment | Which isolated interpreter and packages does this project use? | `python -c "import sys; print(sys.executable)"` |
| `pip` package installer | Which distribution is installed into the current environment? | `python -m pip --version` |
| Dependency declaration | Which packages and versions may or must the project use? | `pyproject.toml` or a requirements file |
| Locked resolution | Which exact versions did this reproducible installation resolve? | A lock file and its tool documentation |

Activating a virtual environment primarily puts its directory at the front of the current shell's `PATH`. The activation script also sets `VIRTUAL_ENV` and may change the prompt. It does not modify source code or guarantee that dependencies have been synchronized from the project declaration.

## Version baseline

As of **2026-07-14**, Python.org listed **Python 3.14.6** as the latest stable release; Python 3.15 was still a prerelease branch. The course examples avoid 3.14-only syntax so they can run in still-supported Python 3.11+ environments. A real project should state its supported range in `pyproject.toml` or its runbook and verify it in CI and tests instead of assuming that every Python 3 release behaves the same.

The original Python 100 Days course spans several ecosystem eras. Keep the teaching context when you encounter old installation screenshots, package names, or APIs, but use the project's locked versions and current official documentation as the operational source of truth.

## Build a minimum environment with venv + pip

In a new practice directory outside this vault, run:

```powershell
New-Item -ItemType Directory -Path "$HOME\python-agent-lab" -Force
Set-Location "$HOME\python-agent-lab"

python --version
Get-Command python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python -m pip --version
python -m pip install --upgrade pip
```

If execution policy prevents activation, directly invoke the environment's interpreter before weakening a machine-wide policy:

```powershell
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe .\main.py
```

`.venv` is reproducible local state and belongs neither in Git nor in this vault. Removing it does not remove project source code, but you need a dependency declaration and lock information before installing again.

## Why use `python -m pip`

A machine can have multiple Pythons and `pip.exe` programs. `python -m pip` explicitly means “have this interpreter execute its `pip` module,” which makes the target environment easier to verify than a bare `pip` command.

Check all three of these:

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
python -m pip check
```

The paths should point to the same `.venv`. `pip check` verifies whether installed packages declare compatible dependencies, but it cannot prove correct application behavior or supply-chain safety.

## Dependency declaration and locking are different jobs

`pyproject.toml` can declare project metadata, the Python version, and direct dependencies. A requirements file is often used to record or constrain an install set. A lock file is normally produced by a specific tool and records resolved exact versions and the full dependency graph.

A minimal conceptual example:

```toml
[project]
name = "agent-lab"
version = "0.1.0"
requires-python = ">=3.11,<3.15"
dependencies = []
```

The examples in this course use only the standard library, so no third-party dependency needs to be installed. If a project adds an SDK, record why it is needed, its permitted version range, update process, license and security review, regression tests, and rollback target.

Do not put real tokens in dependency files, command history, or installation URLs. Extra package sources can create dependency-confusion risk and must be explicitly configured and reviewed by the organization.

## When to use uv

`uv` is Astral's third-party Python project and package-management tool. It can manage Python, virtual environments, dependencies, lock files, and tool execution. Understand the preceding objects first, then consider:

```powershell
uv init agent-lab
Set-Location .\agent-lab
uv run python --version
uv add httpx
uv lock
uv sync
```

Commands evolve with `uv` releases, so check the official documentation and lock down team conventions when implementing it. The provenance of Python distributions managed by `uv` also differs from the python.org installer; verify it where compliance or runtime-origin requirements apply. `uv` is not a magic layer that removes the need to understand environments.

## Common mistakes and diagnostics

| Symptom | Check first | Common cause |
| --- | --- | --- |
| Installation succeeded but `import` fails | `sys.executable` and `pip --version` | The package was installed into another interpreter |
| The environment disappears after closing a terminal | Whether it was activated again | Activation affects only the current shell |
| A teammate cannot reproduce the setup | Dependency declaration, lock file, Python range | Only `.venv` or an informal version was shared |
| Behavior changes after an upgrade | Resolved versions and changelog | An unbounded dependency was upgraded without regression tests |
| Git shows many environment files | `.gitignore` and status | `.venv` was accidentally versioned |

## Exercise

Create an environment outside the vault and record `python --version`, `sys.executable`, and `python -m pip --version`. Close and reopen PowerShell, then run the same script once by activation and once by directly calling `.venv\Scripts\python.exe`; explain the difference.

## Self-check

1. What do the interpreter, virtual environment, and `pip` each do?
2. Why should `.venv` not be committed while a dependency declaration should be?
3. Do a version range and a lock file solve the same problem?
4. Why is `python -m pip` easier to debug than bare `pip`?
5. Which foundational objects must you still understand before using `uv`?

## Related concepts and next step

- For PowerShell paths and commands, see the cross-platform material in [[linux-commands/00-index|Linux Commands]]; for version control, see [[git/00-index|Git]].
- Next, [[python-fundamentals/engineering-route/01-foundations-and-boundaries/02-type-hints-and-data-models|Type Hints and Data Models]] uses explicit types to express tool inputs and outputs.

## References

Retrieved on **2026-07-14**.

- [Python downloads and release status](https://www.python.org/downloads/)
- [Python `venv`](https://docs.python.org/3.14/library/venv.html)
- [Python Packaging User Guide: pip and virtual environments](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
- [Python Packaging User Guide: `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [uv official getting started guide](https://docs.astral.sh/uv/getting-started/)
- [uv: managed Python distributions](https://docs.astral.sh/uv/concepts/python-versions/)
