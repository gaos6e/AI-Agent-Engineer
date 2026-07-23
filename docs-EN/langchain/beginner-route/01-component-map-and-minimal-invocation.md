---
title: "Component Map, Environment, and a Minimal LCEL Invocation"
aliases:
  - LangChain Component Map
  - Introduction to LCEL
tags:
  - langchain
  - beginner
  - lcel
source_checked: 2026-07-19
concept_source_checked: 2026-07-14
package_source_checked: 2026-07-19
lang: en
translation_key: "LangChain/00-初学者路线/01-组件地图与最小调用.md"
translation_source_hash: 270bf4ac4b85dbb34ed39b880fe7212d00dcbdd794a11745fed8c9c5098b0268
translation_route: zh-CN/LangChain/00-初学者路线/01-组件地图与最小调用
translation_default_route: zh-CN/LangChain/00-初学者路线/01-组件地图与最小调用
---

# Component Map, Environment, and a Minimal LCEL Invocation

## Objectives

After this lesson, you should be able to separate a “LangChain project” into ordinary Python, `langchain-core` components, high-level LangChain Agents, the LangGraph runtime, and provider integration packages. You should also be able to write an LCEL (LangChain Expression Language) composition that does not call a model. The point is not to memorize class names, but to see the input, output, and failure boundary at every step.

## Start with the problem, not the framework

Suppose the task is: receive a support-ticket message, normalize it, classify it, then decide whether to call a lookup tool. There are at least four implementation levels:

| Layer | What it fits | What it should not be asked to do |
| --- | --- | --- |
| Ordinary Python functions | Fixed steps, deterministic logic, no framework observability needed | Do not wrap it merely to make it look like an Agent |
| Runnable / LCEL | A shared `invoke`, `batch`, async, streaming, or composition contract | It does not automatically provide autonomous decisions or durable state |
| LangChain `create_agent` | A standard “the model decides whether to call a tool” loop and middleware | It is not for hiding complex topology or side-effect semantics |
| LangGraph | Explicit state, branches, loops, parallelism, checkpoints, pause/resume | It does not define authorization, idempotency, or business truth for you |

LangChain v1 narrowed the top-level `langchain` namespace to core entry points such as Agents, messages, tools, models, and embeddings; historical chain APIs such as `LLMChain` moved to `langchain-classic`. When you encounter an old tutorial, verify its version first instead of mechanically changing imports.

## How the packages relate

- `langchain-core`: interfaces and composition protocols for models, messages, prompts, tools, retrievers, and Runnables; it does not include third-party provider implementations.
- `langchain`: the current high-level Agent API, including `create_agent`, Agent state, and middleware entry points.
- `langgraph`: a stateful, durable graph runtime; LangChain’s high-level Agents are built on top of it.
- `langchain-<provider>`: separately installed model-provider integrations, each configured according to its own documentation.
- `langchain-classic`: migration-period compatibility for older chains, retrievers, and related functionality; it is not the default starting point for new projects.

Deep Agents is a higher-level harness for long-running tasks. It is not a required dependency for every beginner LangChain project, and its versioning policy is more likely to change than the 1.x LangChain/LangGraph lines.

## Environment and version baseline

The current official installation page requires Python 3.10+ for LangChain. On Windows 11 with PowerShell 7, start with `venv + pip`:

~~~powershell
py -3.12 -m venv .venv  # Create an isolated environment for the exercise with a compatible Python 3.12.
.\.venv\Scripts\Activate.ps1  # Activate it so this shell's python and pip point to .venv.
python -m pip install --upgrade pip  # Upgrade the resolver in the environment to reduce installation-time dependency issues.
python -m pip install langchain  # Install the main LangChain package; install provider packages separately as needed.
~~~

Then install the independent package for the model provider selected by the project. Tutorials must not contain real secrets; inject keys through environment variables or a secret-management service. After installation, record the fully resolved dependencies:

~~~powershell
python -m pip freeze | Set-Content -Encoding utf8 requirements.lock.txt  # Record the fully resolved dependency snapshot.
python -c "import langchain_core; print(langchain_core.__version__)"  # Print the installed core-package version for verification.
~~~

The 2026-07-19 PyPI snapshot lists `langchain 1.3.14`, `langgraph 1.2.9`, and `langchain-core 1.4.9`. These are verification points, not instructions to hand-assemble three version pins: let the package resolver find a compatible set, then preserve the working result with a lockfile and tests.

## A minimal intuition for LCEL

A Runnable is a unit of work that receives input and produces output. LCEL’s `|` sends one step’s output to the next, forming a `RunnableSequence`; a dictionary form creates parallel branches. Common methods in the shared protocol include `invoke`, `batch`, `stream`, and their asynchronous counterparts. The following example needs neither a model nor a key:

~~~python
from langchain_core.runnables import RunnableLambda, RunnableParallel  # Import composable function Runnables and the parallel-branch container.

normalize = RunnableLambda(lambda text: " ".join(text.strip().split()))  # Remove leading, trailing, and repeated whitespace to normalize the input.
features = RunnableParallel(  # Compute multiple side-effect-free features from the same normalized text in parallel.
    text=lambda text: text,  # Preserve the normalized text for downstream use.
    length=lambda text: len(text),  # Calculate the text length as a second output field.
)
pipeline = normalize | features  # Connect the preceding string output to the parallel feature branches.

print(pipeline.invoke("  hello   agent  "))  # Run the pipeline synchronously and print the structured result.
# {'text': 'hello agent', 'length': 11}
~~~

The same runnable file is in `examples/lcel_no_key.py`. The base environment does not keep `langchain-core` installed; on 2026-07-19, the example ran in an isolated `langchain-core==1.4.9` environment and produced the result above. The missing-dependency branch still exits explicitly, so a skip must never be reported as a pass.

> [!warning] LCEL does not mean “automatically correct”
> `|` expresses composition only. If the preceding output shape does not match the next input, if parallel steps write the same external resource, or if retries repeat side effects, the application still has to solve those problems. Write types and contracts before optimizing for a compact expression.

## When not to use LCEL

- For two or three pure functions with no need for a shared runtime protocol, ordinary Python is more direct.
- When a model must decide dynamically which tools to use and how many steps to take, use `create_agent` instead of hand-writing an unbounded loop.
- When durable state, interrupts, explicit routing, or recovery are needed, use LangGraph.
- When the only reason is to reuse an old `LLMChain` tutorial, read the v1 migration guide first instead of adding dependencies for a historical abstraction.

## Practice

1. Write “trim whitespace → lowercase → count length” with ordinary Python.
2. Convert the three steps into Runnables, then run both `invoke` and `batch`.
3. Deliberately make the second step expect a dictionary but receive a string, and record the boundary where the error occurs.
4. For a fixed classification flow and a model that autonomously looks up information, respectively choose ordinary Python, LCEL, an Agent, or LangGraph and explain why.

## Self-check

- [ ] Explain how `langchain`, `langchain-core`, provider packages, and `langgraph` relate.
- [ ] Explain what LCEL’s `|` and `RunnableParallel` express—and what they do not.
- [ ] Recognize `LLMChain` in a v0.x tutorial and check v1 migration material first.
- [ ] Before locking versions, distinguish an example from current documentation from an interface verified by this project.

## Next

Continue to [[langchain/beginner-route/02-models-messages-prompts-and-structured-output|Models, Messages, Prompts, and Structured Output]] to establish clear contracts for model interaction.

## Source baseline

Official facts checked on 2026-07-14.

- [LangChain installation](https://docs.langchain.com/oss/python/langchain/install)
- [LangChain v1 changes](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [langchain-core Runnables API](https://reference.langchain.com/python/langchain-core/runnables)
- [Runnable.pipe API](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/pipe)
- [LangChain versioning policy](https://docs.langchain.com/oss/python/versioning)
- [PyPI langchain](https://pypi.org/project/langchain/) and [PyPI langgraph](https://pypi.org/project/langgraph/)
- [[langchain/upstream-references/conceptual-overviews/langchain-vs-langgraph-vs-deep-agents|Existing official translation: product boundaries]]
