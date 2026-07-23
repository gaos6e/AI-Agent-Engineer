---
title: "Project: Offline Research-Brief Flow"
aliases:
  - Offline Research Brief Flow
  - CrewAI Offline Project
tags:
  - ai-agent-engineer
  - crewai
  - project
  - flow
  - python
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: CrewAI/07-项目-离线研究简报Flow.md
translation_source_hash: 0de44db85c14352f8f62433fc9a58f04e78a60d6afd975eba119ebc2f7b339a1
translation_route: zh-CN/CrewAI/07-项目-离线研究简报Flow
translation_default_route: zh-CN/CrewAI/07-项目-离线研究简报Flow
---

# Project: Offline Research-Brief Flow

## Project objective

This project practices the most important engineering boundaries for Crews and Flows **without installing CrewAI, calling a model, accessing the network, or using an API key**:

- researcher, writer, and reviewer each perform only one Task;
- Task input and output are verifiable JSON structures;
- the Flow records state, contiguous events, an attempt budget, and explicit terminal states;
- a missing citation receives bounded revision, then human review when the budget is exhausted;
- publication accepts only a reviewed artifact matching the frozen source catalog; before writing, it recomputes the deterministic reviewer and checks same-content receipt reuse and overwrite refusal.

It is not a replacement for the CrewAI SDK, nor can it prove real-model quality. It first makes deterministic business controls runnable and testable, then lets you replace boundaries with real Agents, Tasks, and Crews one at a time.

## Files

| File | Purpose |
| --- | --- |
| <code>examples/offline_research_flow.py</code> | Strict data validation, three Task stubs, sequential Crew execution, Flow routing, and idempotent publication |
| <code>examples/sources.json</code> | Two offline sources with schema version, stable source IDs, topics, and claims |
| <code>examples/test_offline_research_flow.py</code> | 39 <code>unittest</code> cases for catalog, Task, Flow, pre-publication source/reviewer recheck, and CLI behavior |

Read <code>sources.json</code> first, then follow <code>load_catalog → run_researcher_task → run_writer_task → run_reviewer_task → run_crew → run_flow</code>. Finish with <code>publish_report</code> to see why side effects need separate preconditions, a **same-source-version recheck**, and recovery rules. <code>publish_report</code> accepts a trusted catalog rather than state alone: it compares <code>catalog_fingerprint</code>, recomputes the deterministic reviewer, and only then writes a local file.

The <code>operation_id</code> in <code>run_flow</code> is determined from the frozen topic and catalog fingerprint to express the same business intent; it is not a unique Flow UUID per execution. Layer B explicitly separates those identifiers.

## Prepare the environment

This project uses only the Python standard library. The following begins at the project root containing <code>docs-CN/</code>, <code>docs-EN/</code>, and <code>.website/</code>. If you want a virtual environment, create it outside the vault, then enter the course using a project-relative path:

~~~powershell
$practice = Join-Path $HOME "Projects\crewai-offline-practice"  # Choose an absolute practice directory outside the vault.
New-Item -ItemType Directory -Path $practice -Force | Out-Null  # Create it if needed and suppress unrelated output.
Push-Location -LiteralPath $practice  # Move temporarily so environment files stay out of the course repository.
py -3 -m venv .venv  # Create an isolated environment with the locally default Python 3.
.\.venv\Scripts\Activate.ps1  # Activate it so later python commands use this interpreter.
python --version  # Confirm the Python version actually activated.
Pop-Location  # Return to the project root.
Push-Location -LiteralPath 'docs-EN\crewai'  # Enter the English course directory for the relative paths below.
~~~

> [!note]
> The course repository must not store <code>.venv</code>. If PowerShell execution policy blocks activation, run later commands through the absolute path to the external environment’s <code>python.exe</code>.

The project has no third-party dependencies, so do not run <code>pip install</code> or weaken machine-wide security settings merely to run it.

## First run: normal path

Run all following commands from the <code>crewai</code> course directory:

~~~powershell
python -B .\examples\offline_research_flow.py --topic "Agent reliability"  # Run normal input and prevent .pyc creation.
~~~

<code>-B</code> prevents <code>.pyc</code> writes. Standard output is JSON. Verify:

- <code>stage</code> is <code>ready_to_publish</code>;
- <code>attempt</code> is <code>1</code>;
- every claim in <code>result.research.claims</code> has <code>source_ids</code>;
- <code>result.draft.markdown</code> contains <code>[source-1]</code> and <code>[source-2]</code>;
- event <code>sequence</code> increments contiguously from 1.

The CLI return code <code>0</code> means it reached <code>ready_to_publish</code> or <code>published</code>; it does not independently verify real-world facts.

## Observe revision and human takeover

### First citation missing, second attempt fixed

~~~powershell
python -B .\examples\offline_research_flow.py --topic "Agent reliability" --force-revision  # Inject a missing citation first and observe bounded revision routing.
~~~

The first writer intentionally omits one citation. The reviewer finds it, the Flow emits <code>routed:revise</code>, then the second attempt adds a revision record and reaches <code>ready_to_publish</code>. Confirm <code>attempt == 2</code>: routing, not an unbounded loop, controls retries.

### Both attempts fail, then human handling

~~~powershell
python -B .\examples\offline_research_flow.py --topic "Agent reliability" --force-failure  # Force review failure twice and verify human-takeover terminal state.
$LASTEXITCODE  # Print the previous process exit code.
~~~

The result should have <code>stage == "human_review"</code>, <code>attempt == 2</code>, and process return code <code>1</code>. Human takeover is an expected terminal state, not a crash.

### No matching source

~~~powershell
python -B .\examples\offline_research_flow.py --topic "A topic that is not in the catalog"  # Exercise no-match behavior and verify the system refuses to invent conclusions.
~~~

The researcher does not invent a conclusion; it records the gap in <code>unknowns</code>. The reviewer rejects publication with no sourced conclusion, and the Flow ends in <code>human_review</code>.

## Publication receipts and repeated calls

Use a unique temporary file so you neither modify course material nor collide with old output:

~~~powershell
$output = Join-Path $env:TEMP ("crewai-offline-brief-{0}.md" -f [guid]::NewGuid())  # Create a unique temporary output path.
python -B .\examples\offline_research_flow.py --topic "Agent reliability" --output $output  # Write a publishable brief.
Get-Content -LiteralPath $output  # Inspect the artifact corresponding to the receipt.
~~~

The first run writes through a temporary file and atomic replacement, ending at <code>published</code>. Repeat with exactly the same input:

~~~powershell
python -B .\examples\offline_research_flow.py --topic "Agent reliability" --output $output  # Reuse the path to exercise idempotency and conflict protection.
~~~

The second run does not rewrite different content; <code>publication.recovered</code> is <code>true</code>. This proves reuse of a local file-content receipt, not CrewAI Flow-state or checkpoint recovery. If existing content differs, the project refuses to overwrite it and returns error code <code>2</code>.

If the catalog changes after <code>run_flow</code>, or someone changes a draft in state while preserving an old reviewer verdict, the write also fails closed. A real system should extend the same idea: reread trusted sources by version/ACL before an external effect and validate through an independent execution layer instead of trusting a persisted model artifact.

Afterward, delete only the temporary file you created:

~~~powershell
Remove-Item -LiteralPath $output  # Delete only the unique temporary brief created by this walkthrough.
~~~

## Run the complete test suite

Run tests from <code>examples</code> so Python imports the sibling module correctly:

~~~powershell
Push-Location .\examples  # Enter the example directory so unittest can import the sibling module directly.
$env:PYTHONDONTWRITEBYTECODE = "1"  # Prevent bytecode caches during testing.
python -B -m unittest -v test_offline_research_flow.py  # Normal mode, with test names.
python -B -O -m unittest -v test_offline_research_flow.py  # Optimization mode: key checks must not depend on bare assert.
python -B -W error -m unittest -q test_offline_research_flow.py  # Treat warnings as failures.
python -B -O -W error -m unittest -q test_offline_research_flow.py  # Combine optimization and strict warning handling.
Pop-Location  # Return from examples to the CrewAI course directory.
Pop-Location  # Return from the course directory to the project root.
~~~

The modes provide different evidence:

- ordinary mode: all 39 behavior tests pass;
- <code>-O</code>: key checks do not depend on bare <code>assert</code>, which optimization removes;
- <code>-W error</code>: Python warnings become failures and reveal potential compatibility problems;
- combined mode: confirms both protections at once.

If a command fails, retain the full name and exception from the first failing test, then make the smallest reproduction. Do not merely repeat a run until it happens to pass.

## Mapping the offline implementation to CrewAI concepts

| Offline project | Corresponding CrewAI concept | What cannot be inferred |
| --- | --- | --- |
| Pure functions such as <code>run_researcher_task</code> | A limited role fulfilled by an Agent | A real LLM reliably follows that role |
| <code>validate_research/draft/review</code> | Task output contract, structured output, guardrail | Correct structure means factual correctness |
| <code>run_crew</code> | A three-Task sequential Crew | Multiple Agents are automatically better than one |
| <code>run_flow</code> | Flow state, events, routing, and attempt budget | Official decorators have the same signature in every version |
| <code>publish_report</code> | Business boundary and same-catalog/reviewer recheck before a side-effecting Tool | Local atomic replacement equals a remote transaction |
| <code>sources.json</code> | A minimal Knowledge/retrieval catalog | Two samples represent real RAG |

## Migrate incrementally to real CrewAI

Place real integration in a separate project or new isolated example; do not break this offline baseline.

1. Create a new <code>venv</code> and pin verified CrewAI, Python, and model SDK versions.
2. Replace only the researcher stub with one real Agent/Task while retaining the same output schema.
3. Have the existing deterministic reviewer check it against a fixed evaluation set.
4. Replace the writer while retaining source IDs, unknowns, and the attempt budget.
5. Organize Tasks with a real <code>Crew(process=Process.sequential)</code>.
6. Verify imports and behavior of <code>Flow</code>, <code>@start</code>, <code>@listen</code>, and <code>@router</code> on the pinned version.
7. Last, integrate real Tools, Memory, Knowledge, event listeners, and checkpoints.
8. Put side-effecting Tools behind preview/sandbox first, then add approval and idempotency keys.
9. Record model, Prompt, dependencies, evaluation set, cost, and unvalidated risk.

Replace one boundary per migration step so a failure can be localized to the model, Tool, Crew orchestration, or Flow control. Adjacent [[crewai/08-project-real-crewai-persistent-flow|Layer B]] executes pinned-version Flow decorators and SQLite persistence; this project itself proves only standard-library contracts, and neither layer executes a real model provider.

## Integrated task

Extend the project without accessing the network:

1. add one topic and two sources to <code>sources.json</code>;
2. add an explicit <code>awaiting_approval</code> state that publishes only with a one-time approval object;
3. simulate one retryable Tool timeout and one non-retryable permission denial;
4. ensure total retries are bounded;
5. test changed approval content, repeated publication, unknown sources, and an old schema;
6. list commands actually run, test count, and unvalidated items in a README or experiment record.

## Acceptance checklist

- [ ] A normal sample passes once and reaches <code>ready_to_publish</code>.
- [ ] The forced-revision sample revises only once and then passes.
- [ ] Forced failure and unknown topic both reach <code>human_review</code>.
- [ ] Every publishable claim has a known source ID and a citation in the draft.
- [ ] Event numbers are contiguous and attempts never exceed budget.
- [ ] Repeated same-content publication recovers; different content is not overwritten.
- [ ] All 39 tests pass in normal, <code>-O</code>, warnings-as-errors, and combined modes.
- [ ] The run creates no <code>.pyc</code>, real credentials, or output inside the course directory.
- [ ] You can state which real CrewAI capabilities the offline project does not validate.

## Relationship to the rest of the course

- Objects and sequential execution: [[crewai/01-core-objects-crew-agent-task-and-process|Core Objects: Crew, Agent, Task, and Process]]
- Flow and events: [[crewai/02-flow-state-and-events|Flow, State, and Events]]
- Tools and structured output: [[crewai/03-tool-boundaries-and-structured-output|Tool Boundaries and Structured Output]]
- Information boundaries: [[crewai/04-memory-knowledge-and-context|Memory, Knowledge, and Context]]
- Evaluation: [[crewai/05-testing-evaluation-and-observability|Testing, Evaluation, and Observability]]
- Production boundaries: [[crewai/06-safety-failure-recovery-and-production-boundaries|Safety, Failure Recovery, and Production Boundaries]]

## Primary references

Sources checked on 2026-07-21:

- [CrewAI Agents](https://docs.crewai.com/en/concepts/agents)
- [CrewAI Tasks](https://docs.crewai.com/en/concepts/tasks)
- [CrewAI Crews](https://docs.crewai.com/en/concepts/crews)
- [CrewAI Processes](https://docs.crewai.com/en/concepts/processes)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Testing](https://docs.crewai.com/en/concepts/testing)
- [CrewAI on PyPI](https://pypi.org/project/crewai/)
