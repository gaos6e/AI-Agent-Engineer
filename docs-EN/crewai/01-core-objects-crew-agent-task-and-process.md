---
title: "Core Objects: Crew, Agent, Task, and Process"
aliases:
  - CrewAI Core Objects
  - CrewAI Core Concepts
tags:
  - crewai
  - agent
  - task
  - process
source_checked: 2026-07-21
concept_source_checked: 2026-07-14
package_source_checked: 2026-07-21
lang: en
translation_key: CrewAI/01-核心对象-Crew Agent Task Process.md
translation_source_hash: a9614aa1f30acaa689c626b4b1bc87f986ff80ca23f5990c4d0c95258512df0a
translation_route: zh-CN/CrewAI/01-核心对象-Crew-Agent-Task-Process
translation_default_route: zh-CN/CrewAI/01-核心对象-Crew-Agent-Task-Process
---

# Core Objects: Crew, Agent, Task, and Process

## Learning objectives

After this lesson, you should understand the four core objects by responsibility rather than persona, write a structured Task contract, and choose between a sequential and a hierarchical Process. You should also be able to create an isolated Windows environment and confirm the version actually installed rather than relying on a web-page heading.

## Verify installation facts first

PyPI showed <code>crewai 1.15.5</code> as the latest stable package on 2026-07-21. This course’s real Layer B remains pinned to the revalidated <code>1.15.4</code>, whose Python constraint is <code>>=3.10,&lt;3.14</code>. If <code>python --version</code> reports 3.14, it does not satisfy that **tested baseline**. Create an environment with a compatible interpreter; do not expect a reliable run merely because pip can be forced past a constraint.

~~~powershell
py -0p  # List interpreters available through Python Launcher; first check that 3.13 exists.
py -3.13 -m venv .venv  # Create a project-specific environment that satisfies the course baseline.
.\.venv\Scripts\Activate.ps1  # Make this PowerShell session use the new .venv.
python -m pip install "crewai==1.15.4"  # Install the locked teaching baseline rather than chasing the newest release without validation.
python -c "from importlib.metadata import version; print(version('crewai'))"  # Print the resolved CrewAI version for the record.
python -m pip check  # Check whether installed packages still have unsatisfied dependencies.
~~~

This is a version snapshot for a learning project, not an instruction to ignore <code>1.15.5</code>. A team project should also keep a lockfile or a dependency manifest with hashes and rerun the regression suite before an upgrade. The official documentation currently recommends <code>uv</code>; after understanding virtual environments, interpreters, and dependency resolution, use the official CLI/UV workflow to create a conventional project.

## Responsibilities of the four objects

| Object | What it is responsible for | What it is not responsible for |
| --- | --- | --- |
| <code>Agent</code> | Role, goal, model, tools, delegation, and runtime budgets | Automatically receiving real knowledge or business authority |
| <code>Task</code> | Specific work, expected output, context, guardrails, and artifact format | Being only a vague wish |
| <code>Crew</code> | Collecting Agents and Tasks, configuring a Process, and starting collaboration | Defining a safe business terminal state |
| <code>Process</code> | Deciding how Tasks advance and are assigned | Guaranteeing correct decomposition or truthful results |

The official Agents page identifies <code>role</code>, <code>goal</code>, and <code>backstory</code> as core parameters and lists controls such as tools, model, maximum iterations, time, and rate. A role description helps a model understand its assignment, but cannot replace tool authority, sources, or acceptance tests.

## A Task contract comes before an Agent persona

An inadequate Task:

> Research this topic and write it professionally.

A testable Task:

- **Input:** three permitted documents and stable <code>source_id</code> values;
- **Output:** <code>claims</code>, <code>source_ids</code>, and <code>unknowns</code>;
- **Rules:** every claim has at least one known source; write to <code>unknowns</code> when evidence is absent;
- **Prohibited:** browsing for additions or calling a publication tool;
- **Failure:** invalid schema, unknown source, or exhausted step budget.

The official Tasks page offers <code>output_pydantic</code> and <code>output_json</code> for structured <code>TaskOutput</code>, plus <code>guardrail</code> to validate output. Passing a schema proves only that the structure is valid; whether a source actually supports a claim still needs application code or a human grader.

## Current official minimal object shape

The following shape comes from official Agents/Tasks/Crews documentation read on 2026-07-14. It is for recognizing object relationships. This course did not install the real package or configure a model, so it was not executed:

~~~python
from crewai import Agent, Crew, Process, Task  # Import collaboration actors, tasks, the orchestrator, and a progression strategy.

researcher = Agent(  # Define a research Agent that works only within approved sources.
    role="Local evidence researcher",  # A role helps the model understand its responsibility; it is not authorization.
    goal="Extract claims only from approved sources",  # State the acceptable evidence boundary in the work objective.
    backstory="You work within strict evidence boundaries.",  # Add behavioral context, still backed by code-side controls.
    allow_delegation=False,  # Prevent this Agent from handing work to another Agent on its own.
)

research_task = Task(  # Wrap the research objective as an assignable, verifiable Task.
    description="Extract supported claims for {topic}.",  # The input dictionary supplies {topic} at kickoff.
    expected_output="Structured claims with source identifiers and unknowns.",  # Require source IDs and unknowns rather than generic prose.
    agent=researcher,  # Assign this Task to the researcher defined above.
)

crew = Crew(  # Assemble Agents, Tasks, and a collaboration progression strategy into a Crew.
    agents=[researcher],  # Register the Agents permitted to participate in this run.
    tasks=[research_task],  # Register the Task list in execution order.
    process=Process.sequential,  # Use deterministic sequential progression instead of dynamic manager assignment.
)

# result = crew.kickoff(inputs={"topic": "Agent reliability"})  # A model must be configured first; leave this commented to avoid an accidental real call.
~~~

The commented <code>kickoff</code> prevents readers from assuming that the example runs without model configuration. Verify actual parameters, defaults, and import paths against the pinned version.

## Sequential and hierarchical processes

The current official documentation states:

- <code>Process.sequential</code> runs the Task list in order. Upstream output can become downstream context, or a Task can specify <code>context</code> explicitly.
- <code>Process.hierarchical</code> has a manager assign and validate work. It requires <code>manager_llm</code> or <code>manager_agent</code>; Tasks are not prebound to a specific executing Agent.

A sequential Process suits an explicit research → writing → review dependency. A hierarchical Process adds a manager-model’s assignment, review, cost, and stopping conditions. Use it only when dynamic allocation demonstrably beats a fixed workflow in evaluation. Do not create one Agent for every verb, and do not treat a review Agent as an independent source of truth.

## Crew, Flow, or ordinary Python

- Fixed JSON transformations, validation, and file moves: ordinary Python.
- Branches, approvals, waits, persistent state, and external business steps: a Flow or ordinary state machine.
- Several language-reasoning Tasks with clear boundaries: a Crew.
- Outer business control plus inner cognitive collaboration: a Flow that calls one or more Crews.

If one model with two constrained tools completes the job, there is no need to split it across three Agents. The value of multi-Agent design must come from distinct contexts, authority, specialist evaluation, or demonstrable parallel benefit.

## YAML projects and direct code

The official Agents/Crews documentation recommends YAML configuration for Agents and Tasks, collected through the CrewAI project structure; direct Python definitions remain an alternative. Begin with direct code to see the objects clearly, then use the official Quickstart to generate a separate project and check:

- whether YAML variables are provided by <code>kickoff(inputs=...)</code>;
- whether Agent names and Task references agree;
- whether credentials come only from the environment;
- whether the project’s locked version matches the example.

## Common mistakes and diagnosis

- **Writing only a backstory:** add Task inputs, outputs, failure conditions, and a tool allowlist.
- **Giving every Agent every tool:** divide authority by Task and pass only necessary tools to each Agent/Task.
- **Parsing free text from an upstream Agent:** use <code>output_pydantic</code> or an application-layer schema.
- **Using hierarchical without a manager:** the current official documentation requires <code>manager_llm</code> or <code>manager_agent</code>.
- **Treating a documentation label as an installed version:** read the environment fact with <code>importlib.metadata.version('crewai')</code>.
- **Running only a demo after an upgrade:** first run frozen-input, structure, trajectory, and authority regression suites.

## Exercise

Break “produce a weekly project status” into at most three Tasks. For each Task, specify its input, output schema, executing Agent, permitted tools, completion condition, and failure condition. Then answer:

1. Is a fixed sequence sufficient?
2. What unknown assignment problem would a manager solve?
3. Which extra model calls and failure paths does a manager introduce?
4. Could one Agent with several Tasks achieve the same result?

## Mastery check

- [ ] Explain the four core objects without reciting APIs.
- [ ] Read the installed version from the environment and run <code>pip check</code>.
- [ ] Write machine-verifiable Task artifacts and failure conditions.
- [ ] Explain why hierarchical needs a manager and additional evaluation.
- [ ] Identify why a role description cannot substitute for knowledge, authority, or acceptance.

## Next step

Continue to [[crewai/02-flow-state-and-events|Flow, State, and Events]] to place a Crew inside a controlled business lifecycle.

## References

- [PyPI: crewai 1.15.4](https://pypi.org/project/crewai/1.15.4/) (tested baseline and Python constraints) and [PyPI: current crewai release](https://pypi.org/project/crewai/) (latest observed: 1.15.5; checked 2026-07-21).
- [CrewAI Installation](https://docs.crewai.com/en/installation) (dynamic documentation, page label <code>v1.14.0</code>; checked 2026-07-14).
- [Agents](https://docs.crewai.com/en/concepts/agents), [Tasks](https://docs.crewai.com/en/concepts/tasks), [Crews](https://docs.crewai.com/en/concepts/crews), and [Processes](https://docs.crewai.com/en/concepts/processes) (dynamic official documentation; checked 2026-07-14).
