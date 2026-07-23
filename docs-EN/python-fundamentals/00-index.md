---
title: "Python Fundamentals"
tags:
  - ai-agent-engineer
  - Python
  - learning-path
aliases:
  - Python Fundamentals index
  - Agent-engineering Python route
source_checked: 2026-07-19
course_baseline_checked: 2026-07-14
legacy_risk_checked: 2026-07-19
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: unknown
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 2
ai_learning_schema: 2
ai_learning_id: python-foundations
ai_learning_domain: foundations
ai_learning_catalog_order: 200
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 10
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 10
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 10
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 10
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: "Python基础/00-目录.md"
translation_source_hash: c5c1d86e08dd233c694b32e6f451012cb5048aa66aa55946759a3049f870ddf2
translation_route: zh-CN/Python基础/00-目录
translation_default_route: zh-CN/Python基础/00-目录
---

# Python Fundamentals

## About this knowledge base

This knowledge base has two layers: the original **Python 100 Days** public course is a frozen reference layer, while the new `engineering-route/` is the independently maintained required layer for this route. The goal is not to memorize every one of the 100 days. First master the engineering spine—environment, data boundaries, reliability, tests, concurrency, and tool contracts—then return to the public course as a project requires web development, databases, or data analysis.

> [!warning] Legacy tutorial image paths
>
> A small number of original tutorial image links hard-code the pre-rename `Python-100-Days-master` directory. To honor both “do not alter upstream prose” and “do not restore the old directory,” this route does not rewrite those original files or create an old-directory alias. The public English route exposes frozen pages as source-reference stubs, so consult the cited upstream material when a legacy image is unavailable. Wikilinks in the maintained route are verified against the current English paths.

> [!info] Currency and compatibility of material
>
> Python, third-party libraries, and installation methods change. This index was checked on **2026-07-14**: Python.org listed **Python 3.14.6** as the latest stable release, while Python 3.15 was still a prerelease branch and is not the default production baseline. The original course includes examples from different ecosystem periods. Read their dependency notes before running them and use a project's locked versions and current official documentation as the source of truth. The maintained route aims for Python 3.11+ compatibility; the actual local version and results for its examples are recorded under “Verification record,” which does not prove every Python version has been verified.

> [!danger] Known non-runnable or unsafe examples in the frozen reference layer
>
> The following issues were confirmed by local audit on 2026-07-19. They are retained to understand historical APIs, not as current run instructions:
>
> - [[python-fundamentals/upstream-references/day31-35/python-77300269|Advanced Python]] passes bare coroutines to `asyncio.wait()`; under this project's Python 3.11.9 it raises `TypeError: Passing coroutines is forbidden`. Modern code should create tasks first, or choose `gather()` / `TaskGroup` according to cancellation and error semantics rather than run that snippet unchanged.
> - `Day31-35/code/example24.py` uses `ssl=False` against a real site and lacks connection/total timeouts, status-code checks, and response-size checks. Do not disable certificate verification or request its site directly. Use a local fixture or test server for practice and explicitly verify timeout, status, size, and parse failures.
> - The public-course `example10.py` repeatedly requests real third-party pages with a hard-coded `BaiduSpider` user agent and no timeout, status check, or site-policy review. Do not run it directly. Teaching tests should use local HTML fixtures; real collection requires an honest contactable identity, rate limits, and prior review of robots rules and terms of service.
> - The public-course `requirements.txt` is a 2020 upstream environment snapshot containing several old and platform-specific dependencies. Do not run `pip install -r` in a modern environment; declare the minimum dependencies for the current exercise in isolation, resolve them again, and test.
> - `Day31-35/code/example01.py` can now be imported and tested without plotting packages. Only running `main()` to draw its complexity chart requires `matplotlib` and `numpy` (installable in an isolated environment with `python -m pip install matplotlib`).
>
> These files belong to the frozen third-party reference layer, so their prose and code are not rewritten here. The public site continues to provide source-reference stubs under its existing policy. Use the maintained `engineering-route/` for runnable current practice.

## Content boundary and how to use it

| Layer | Location | Purpose | Editing boundary |
| --- | --- | --- | --- |
| Required Agent-engineering layer | `engineering-route/` | Move from environment, types, and I/O to reliability, tests, concurrency, CLI, and tool contracts | The currently maintained layer of this knowledge base |
| Public-course reference layer | Original `Day01-20/`, `Day21-30/`, and similar directories | Fill gaps in syntax, OOP, web development, data analysis, and historical ecosystem context | Keep upstream course prose, code, and assets unchanged |
| Supporting verification layer | `engineering-route/04-project-and-self-assessment/examples/` | Offline JSON task queue and unit tests for the new route | Demonstrates only a small standard-library boundary, not a production system |

If you have no programming experience, first pass the “zero-background prerequisite gate,” then complete the 12 Agent-engineering-route lessons. Learners with prior experience can use the checklist to decide what to skip. If a concept remains unfamiliar, return through prerequisite links or selective public-course review. Do not copy legacy dependency examples from the public course straight into a production project.

The original one-page [[python-fundamentals/00-python-agent-engineering-minimum-practice|Minimum Python Practice for Agent Engineering]] and root `examples/` remain as a historical quick entry. The expanded version is placed only in the new route's project directory so existing material is not overwritten.

## Where this fits in the overall route

Python is the programming spine of engineering foundations. API, data cleaning, RAG, Tool Calling, MCP, and Agent frameworks all require you to read functions, dictionaries/lists, exceptions, files, JSON, modules, and tests. Complete the “minimum required” material on this page before API and LLM applications; return to web frameworks and data-science lessons as needed.

## Learning objectives

- In Windows 11 and PowerShell 7, create a `venv` and install dependencies with `python -m pip`.
- Use variables, branches, loops, functions, modules, lists, dictionaries, and sets to express task logic.
- Express internal models with type hints and data classes while validating untrusted input at runtime.
- Read and write explicit UTF-8 and JSON, limit resources, and distinguish syntax, structure, and business errors.
- Design exceptions, total deadlines, bounded retries, logging, tests, cancellation, and concurrency caps.
- Build a reproducible CLI and a small, deep Python execution boundary for API, RAG, or Agent tools.

## Prerequisites

- You can locate a folder in File Explorer and run commands in PowerShell.
- No programming experience is required. When you meet an old screenshot or library API, understand the concept first and then check current documentation.

## Before you start: environment and version

In a separate practice directory, run:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If `python` is not the expected interpreter, first inspect its source with `Get-Command python`. `.venv` is local environment state and belongs neither in the vault nor Git. Learn `uv` only when you explicitly need faster environment or dependency management; beginners should understand the roles of `venv + pip` first.

## Recommended learning order

### Zero-background prerequisite gate

Complete these frozen-reference entries in order:

1. [[python-fundamentals/upstream-references/day01-20/python-5a3bb73a|First Encounter with Python]] and [[python-fundamentals/upstream-references/day01-20/python-84259c71|Your First Python Program]]: save and run a `.py` file, and read the file name and line number in a traceback.
2. [[python-fundamentals/upstream-references/day01-20/python-7977a0a3|Variables and Types]], [[python-fundamentals/upstream-references/day01-20/reference-05-cba46980|Branches]], and [[python-fundamentals/upstream-references/day01-20/reference-06-2411bcec|Loops]]: express steps with data, conditions, and repetition.
3. [[python-fundamentals/upstream-references/day01-20/1-52596d73|Lists]], [[python-fundamentals/upstream-references/day01-20/reference-11-5d134d16|Strings]], [[python-fundamentals/upstream-references/day01-20/reference-12-d6beb0f8|Sets]], and [[python-fundamentals/upstream-references/day01-20/reference-13-25101879|Dictionaries]]: create, iterate, index, and update common containers.
4. [[python-fundamentals/upstream-references/day01-20/reference-14-89b642be|Functions and Modules]]: write a function that receives arguments and returns a result, then import it from another file.

Before entering the Agent-engineering spine, complete this without notes: read a list of strings, filter blank items, count each string, and split the logic into functions. If you can explain `list`, `dict`, parameters, return values, and exception messages, continue. Otherwise, complete the relevant exercise rather than jumping to `dataclass` or async code.

### Agent-engineering spine (required)

#### Part 1: foundations and boundaries

1. [[python-fundamentals/engineering-route/01-foundations-and-boundaries/01-interpreter-virtual-environments-and-dependencies|Interpreter, Virtual Environments, and Dependencies]]: distinguish Python, `venv`, `pip`, declarations, and locks before choosing `uv`.
2. [[python-fundamentals/engineering-route/01-foundations-and-boundaries/02-type-hints-and-data-models|Type Hints and Data Models]]: express internal contracts with types without mistaking annotations for runtime validation.
3. [[python-fundamentals/engineering-route/01-foundations-and-boundaries/03-functions-modules-and-dependency-injection|Functions, Modules, and Dependency Injection]]: separate a pure core from side-effect adapters.
4. [[python-fundamentals/engineering-route/01-foundations-and-boundaries/04-files-json-and-input-validation|Files, JSON, and Input Validation]]: reject bad input progressively from bytes and encoding through syntax, structure, and business constraints.

#### Part 2: reliability and testing

5. [[python-fundamentals/engineering-route/02-reliability-and-testing/05-exceptions-timeouts-retries-and-resource-management|Exceptions, Timeouts, Retries, and Resource Management]]: put failure, total budget, idempotency, and cleanup into the contract.
6. [[python-fundamentals/engineering-route/02-reliability-and-testing/06-configuration-logging-and-sensitive-information|Configuration, Logging, and Sensitive Information]]: make runs diagnosable without leaking credentials or content.
7. [[python-fundamentals/engineering-route/02-reliability-and-testing/07-unit-testing-mocks-and-regression|Unit Testing, Mocks, and Regression]]: use deterministic tests for success, boundary, and failure paths.

#### Part 3: concurrency, delivery, and tool contracts

8. [[python-fundamentals/engineering-route/03-concurrency-and-delivery/08-async-concurrency-cancellation-and-rate-limits|Async Concurrency, Cancellation, and Rate Limits]]: introduce controlled concurrency only for wait-heavy I/O.
9. [[python-fundamentals/engineering-route/03-concurrency-and-delivery/09-project-layout-cli-and-reproducible-runs|Project Layout, CLI, and Reproducible Runs]]: turn a script into a stable, automatable project entry point.
10. [[python-fundamentals/engineering-route/03-concurrency-and-delivery/10-agent-tool-function-design|Agent Tool Function Design]]: put validation, authorization, and audit between a model proposal and real execution.
11. [[python-fundamentals/engineering-route/04-project-and-self-assessment/11-project-reliable-task-queue|Project: Reliable Task Queue]]: implement JSON input, validation, reporting, CLI, and tests offline.
12. [[python-fundamentals/engineering-route/04-project-and-self-assessment/12-course-wide-self-check-and-mastery|Course-Wide Self-Check and Mastery]]: explain the course from memory and complete two integrated tasks from an empty directory.

### Selective review of the public course

The following entries retain the original course's learning value but do not claim that their third-party library versions remain current recommendations.

#### Syntax and program control

1. [[python-fundamentals/upstream-references/day01-20/python-5a3bb73a|First Encounter with Python]]: understand the interpreter, installation, and where it fits.
2. [[python-fundamentals/upstream-references/day01-20/python-84259c71|Your First Python Program]]: start with editing, running, and locating an error.
3. [[python-fundamentals/upstream-references/day01-20/python-7977a0a3|Variables and Types]] and [[python-fundamentals/upstream-references/day01-20/python-ca88e5e7|Operators]]: understand values, types, and expressions.
4. [[python-fundamentals/upstream-references/day01-20/reference-05-cba46980|Branches]] and [[python-fundamentals/upstream-references/day01-20/reference-06-2411bcec|Loops]]: make a program repeat or stop according to conditions.
5. [[python-fundamentals/upstream-references/day01-20/reference-07-8f3c64ee|Branch and Loop Practice]]: verify control flow with small problems instead of merely reading syntax.

#### Data structures and functions

1. [[python-fundamentals/upstream-references/day01-20/1-52596d73|Lists]] and [[python-fundamentals/upstream-references/day01-20/reference-11-5d134d16|Strings]]: process ordered data and text.
2. [[python-fundamentals/upstream-references/day01-20/reference-12-d6beb0f8|Sets]] and [[python-fundamentals/upstream-references/day01-20/reference-13-25101879|Dictionaries]]: deduplicate, look up, and work with JSON-style records.
3. [[python-fundamentals/upstream-references/day01-20/reference-14-89b642be|Functions and Modules]] and [[python-fundamentals/upstream-references/day01-20/reference-16-bdac99a6|Advanced Functions]]: put reusable logic behind an explicit interface.
4. [[python-fundamentals/upstream-references/day01-20/reference-18-45a4b3b0|Introduction to Object-Oriented Programming]]: first learn to read classes and objects; do not turn simple functions into classes merely to seem advanced.

#### I/O, testing, and concurrency supplements

1. [[python-fundamentals/upstream-references/day21-30/reference-21-e0f5ffd9|File I/O and Exception Handling]]: every external input can fail.
2. [[python-fundamentals/upstream-references/day21-30/reference-22-3eb39cd5|Serialization and Deserialization]] and [[python-fundamentals/upstream-references/day21-30/python-csv-b1413a13|CSV with Python]]: understand boundary data formats.
3. [[python-fundamentals/upstream-references/day21-30/reference-30-bf15c320|Regular Expressions]]: use them for lightweight text extraction rather than give them every complex parse.
4. [[python-fundamentals/upstream-references/day46-60/reference-59-1f3f7c3d|Unit Testing]]: make input, output, and failure behavior repeatably verifiable.
5. [[python-fundamentals/upstream-references/day61-65/python-1-ef174ce0|Obtaining Network Resources]]: a lead-in to API study; real calls need timeouts, retries, and authentication safety.
6. [[python-fundamentals/upstream-references/day61-65/python-1-183e403c|Introduction to Concurrent Programming]]: learn it only when there is a real waiting or throughput problem; concurrency is not a default answer.

#### Project-specific electives

- Data processing: start from [[python-fundamentals/upstream-references/day66-80/reference-66-df874d11|Data Analysis Overview]] for NumPy, pandas, and visualization.
- Machine learning: start from [[python-fundamentals/upstream-references/day81-90/reference-81-242ae273|A Brief Introduction to Machine Learning]] for the workflow, then return to the dedicated Machine Learning knowledge base.
- API design: [[python-fundamentals/upstream-references/day91-100/api-8886e7ed|Network API Interface Design]]; recheck its specific framework and version against current documentation.
- Testing and delivery: [[python-fundamentals/upstream-references/day91-100/reference-96-3ea5056f|Software Testing and Automated Testing]].

## Hands-on practice and project entry point

Complete [[python-fundamentals/engineering-route/04-project-and-self-assessment/11-project-reliable-task-queue|Project: Reliable Task Queue]]: read JSON tasks, limit input, validate fields, summarize status, and emit a report. Its supporting code lives in `python-fundamentals/engineering-route/04-project-and-self-assessment/examples/`, uses no network or key, and is best implemented independently before you compare examples and tests. Then use [[python-fundamentals/engineering-route/04-project-and-self-assessment/12-course-wide-self-check-and-mastery|Course-Wide Self-Check and Mastery]] for closed-book acceptance.

Recommended exercise order:

1. Type one minimal example for every required lesson, deliberately create an exception, and explain its traceback.
2. Add one invalid input and its corresponding failing test to the example.
3. Draw “read → validate → process → output” as four data-flow stages, marking the type and error at each stage.

## Mastery standard

- [ ] I can create and activate a `venv` from an empty directory and explain its relationship to the Python interpreter and `pip`.
- [ ] I can independently write a program containing functions, type hints, `if`, `for`, lists, and dictionaries.
- [ ] I can read and write text with `encoding="utf-8"`, parse JSON, and validate required fields.
- [ ] I can distinguish syntax errors, type/value errors, I/O errors, and business-validation errors.
- [ ] I can write at least three unit tests whose failures carry meaningful information.
- [ ] I can state whether a program has network, file-write, credential, or repeat-execution side effects.
- [ ] When encountering a legacy tutorial API, I check official documentation rather than guessing parameters from memory.

## Relationships with other knowledge bases

- Data Structures Fundamentals and the JSON course deepen containers, complexity, and cross-system data contracts.
- [[api/00-index|API]] extends function calls into interprocess HTTP contracts.
- [[data-cleaning/00-index|Data Cleaning]], the Machine Learning course, and [[data-visualization/00-index|Data Visualization]] use Python to process and validate data.
- [[tool-calling-function-calling/00-index|Tool Calling]], MCP, and [[agent-core/00-index|Agent Core]] require tool functions to be validatable, observable, recoverable, and authorized.
- [[git/00-index|Git]], [[linux-commands/00-index|Linux Commands]], MLOps, and LLMOps cover versioning, servers, and delivery environments.

## Verification record

- Current route examples use only the Python standard library. Under local **Python 3.11.9**, `unittest` ran with **23 tests passing**; both `.py` files were also parsed as ASTs and the example JSON was parsed. The frozen-reference `example01.py` algorithm test can likewise run in a base environment without plotting packages; its plotting entry point still needs the optional dependencies noted above.
- The public-course reference layer contains **714 files**. This work made only a local testability fix to `Day31-35/code/example01.py` (deferred optional plotting imports) and did not rewrite the remaining historical dependencies or hard-coded image paths in bulk.
- No Python 3.14 interpreter, real network SDK, permissions system, or production deployment was run, so those environments remain explicitly unverified.

## Primary references

Retrieved on **2026-07-14**.

- [Python 3.14 official tutorial](https://docs.python.org/3.14/tutorial/)
- [Python 3.14.6 release page](https://www.python.org/downloads/release/python-3146/)
- [Python 3.15.0b3 release page](https://www.python.org/downloads/release/python-3150b3/): prerelease; not the default production baseline.
- [Python `venv` documentation](https://docs.python.org/3.14/library/venv.html)
- [Python Packaging User Guide: installing packages](https://packaging.python.org/en/latest/tutorials/installing-packages/)
- [PyPA: writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [uv project guide](https://docs.astral.sh/uv/guides/projects/): learn it as needed after `venv + pip`.
- [Python 100 Days upstream repository](https://github.com/jackfrued/Python-100-Days): source entry point for the original course material in this directory; its prose was not rewritten in this work.
