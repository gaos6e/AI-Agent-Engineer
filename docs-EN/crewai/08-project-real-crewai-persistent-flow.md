---
title: "Project: Real CrewAI Persistent Flow"
aliases:
  - CrewAI Persistent Flow Layer B
  - CrewAI Real Runtime Project
tags:
  - crewai
  - flow
  - persistence
  - idempotency
  - project
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: CrewAI/08-项目-真实CrewAI持久化Flow.md
translation_source_hash: a263521a924df30757ac949dc273859d154cb91033fc9ad8440425cb282452eb
translation_route: zh-CN/CrewAI/08-项目-真实CrewAI持久化Flow
translation_default_route: zh-CN/CrewAI/08-项目-真实CrewAI持久化Flow
---

# Project: Real CrewAI Persistent Flow

## Project objective

This layer runs <code>crewai==1.15.4</code> directly, still without model calls or an API key. It validates real <code>Flow</code>, <code>@start()</code>, <code>@router()</code>, <code>@listen()</code>, <code>@persist(...)</code>, and <code>SQLiteFlowPersistence</code>, and injects the most dangerous recovery window: the business effect has committed but Flow state has not yet been saved. PyPI’s latest stable package observation on 2026-07-21 was <code>1.15.5</code>; this project does not confuse “latest installable” with “validated version.”

[[crewai/07-project-offline-research-brief-flow|Layer A: Offline Research Brief]] remains responsible for framework-independent Tasks, events, revision budget, and publication contracts. This project does not replace it.

## Why state ID and operation ID are separate

| Identifier | Managed by | Use |
| --- | --- | --- |
| <code>state.id</code> | CrewAI Flow state UUID | Find one persisted execution lineage |
| <code>operation_id</code> | Caller, from business intent | Idempotency, receipt, and conflict detection |
| <code>payload_hash</code> | Application, from normalized payload | Prevent one operation ID from being used for different content |

Layer A originally called its deterministic fingerprint <code>run_id</code>, which could imply a unique UUID for each execution. It is now named <code>operation_id</code>. Real Layer B keeps both a framework UUID and a business idempotency key.

## The responsibilities of two SQLite databases

~~~mermaid
flowchart LR
    A["start: validate schema, topic, operation_id"] --> B["router: route_execute"]
    B --> C["ReceiptStore.apply_once"]
    C --> D[("effect-receipts.sqlite3")]
    C -. "inject crash: receipt committed" .-> X["process failure"]
    A -. "@persist after method completes" .-> S[("flow-state.sqlite3")]
    X --> R["new process: resume same state.id"]
    R --> C
    C -->|"matching payload receipt found"| E["reuse result; effect_count remains 1"]
    E --> F["stage=done; then save Flow state"]
~~~

Flow persistence and a business receipt are different concepts. <code>@persist</code> saves state after a method completes successfully. If the effect commits and the method then raises, current state can still be <code>prepared</code>. Recovery must query the receipt before serial replay, or it can produce a second effect.

This project has one <code>@start()</code>; it proves idempotent receipt behavior only under **single-process, serial recovery**. It makes no assertion about scheduling of several satisfied starts. Multi-worker concurrency, remote APIs, database isolation levels, and cross-region failure need separate validation.

## Pinned-version API facts

- <code>@persist</code> is an invoked decorator: use <code>@persist()</code> or <code>@persist(SQLiteFlowPersistence(path))</code>. In <code>1.15.4</code>, bare <code>@persist</code> replaces the class with a decorator function.
- Route labels and listener method names must be separate. This project uses <code>route_execute</code>/<code>route_done</code> so a handler cannot listen to itself.
- <code>kickoff(inputs={"id": uuid})</code> hydrates the latest state under the same UUID and then re-enters satisfied <code>@start()</code> graph nodes; it does not automatically skip individual nodes.
- <code>kickoff(restore_from_state_id=uuid)</code> forks from a snapshot and assigns a new <code>state.id</code>.
- An unknown UUID may silently begin a new Flow. The wrapper checks persistence before invoking real <code>kickoff</code> for both <code>resume</code> and <code>fork</code>; unknown IDs fail closed.

Checkpointing is another capability. Pinned-version <code>Flow.from_checkpoint</code> requires <code>CheckpointConfig</code>; it must not be conflated with <code>@persist</code> hydration, and early-release/best-effort checkpoints cannot replace a business receipt.

## Files and environment

~~~text
examples/crewai_layer_b/
├── crewai_persistent_flow.py
├── requirements.txt
└── test_crewai_persistent_flow.py
~~~

Run from that directory:

~~~powershell
$practice = Join-Path $env:TEMP ("crewai-layer-b-{0}" -f [guid]::NewGuid())  # Create a unique temporary environment outside the vault.
py -3.11 -m venv $practice  # Create an isolated environment with course-revalidated Python 3.11.
$python = Join-Path $practice "Scripts\python.exe"  # Keep the absolute interpreter path instead of relying on shell activation.
& $python -m pip install --upgrade pip  # Upgrade pip in the temporary environment for the known resolver prerequisite.
& $python -m pip install --requirement .\requirements.txt  # Install the real CrewAI runtime from the direct dependency list.
& $python -m pip check  # Verify no unsatisfied requirements remain.
$env:PYTHONUTF8 = "1"  # Force UTF-8 for output that can contain emoji.
$env:CREWAI_DISABLE_TELEMETRY = "true"  # Request that this test process disable CrewAI telemetry.
$env:CREWAI_TESTING = "true"  # Enable the pinned-version isolation switch used by automated tests.
$env:OTEL_SDK_DISABLED = "true"  # Disable OpenTelemetry SDK instrumentation in this test process.
$env:DO_NOT_TRACK = "1"  # Declare non-tracking intent; production still needs independent egress verification.
~~~

<code>PYTHONUTF8=1</code> avoids Windows default GBK failing to encode emoji in CrewAI event output. <code>CREWAI_TESTING</code> is an internal isolation switch used by the pinned version’s automated tests, not a production configuration. <code>OTEL_SDK_DISABLED</code> and <code>DO_NOT_TRACK</code> are likewise only for this isolated test process; they do not replace deployment egress audit. A non-test service must explicitly perform noninteractive trace opt-out and verify outbound networking and telemetry.

When verified on 2026-07-20, a new Python 3.11 virtual environment with bundled pip 24.0 failed resolving <code>jsonschema → rpds-py</code>. Upgrading pip **inside that temporary environment** to 26.1.2 let the same <code>crewai==1.15.4</code> install and <code>pip check</code> pass, making the upgrade a reproducible prerequisite. <code>requirements.txt</code> pins one direct dependency, not a complete lockfile. That resolution contained 138 distributions, occupied about 800 MB, and included transitive ChromaDB, LanceDB, MCP, OpenAI SDK, and OpenTelemetry dependencies. A production project must trim for its actual feature set, create a complete hash-locked manifest, and perform license/supply-chain scanning; do not treat the teaching environment as a minimal deployment.

## Normal run, same-lineage recovery, and fork

~~~powershell
$stateDb = Join-Path $env:TEMP ("crewai-state-{0}.sqlite3" -f [guid]::NewGuid())  # Create a unique Flow-state SQLite path.
$effectDb = Join-Path $env:TEMP ("crewai-effect-{0}.sqlite3" -f [guid]::NewGuid())  # Create a separate effect-ledger SQLite path.
$fresh = (& $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb start --topic "Agent reliability" --operation-id "publish-001") | ConvertFrom-Json  # Start a lineage and retain its Flow UUID.
& $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb resume --flow-id $fresh.flow_id  # Resume the same persisted snapshot.
& $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb fork --flow-id $fresh.flow_id  # Fork a separate runtime lineage from it.
~~~

A normal run returns <code>stage=done</code>, the CrewAI UUID, business <code>operation_id</code>, receipt, and <code>effect_count=1</code>. Same-lineage recovery retains the UUID. A fork gets a new UUID, but hydrates the same completed snapshot and does not resubmit the effect.

## Inject a crash after the receipt

~~~powershell
$failureLine = & $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb start --topic "Failure recovery" --operation-id "publish-002" --crash-after-receipt 2>&1 | Select-Object -Last 1  # Keep the final JSON failure payload.
$failure = $failureLine | ConvertFrom-Json  # Obtain the Flow UUID for inspection and recovery.
& $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb inspect --flow-id $failure.flow_id  # Inspect the crashed state without mutation.
& $python -B .\crewai_persistent_flow.py --state-db $stateDb --effect-db $effectDb resume --flow-id $failure.flow_id  # Resume and recover receipt rather than duplicate the effect.
~~~

The failing process returns exit code <code>3</code>. Inspect should show Flow state still <code>prepared</code>, while the effect ledger is already 1. After recovery in a new process, <code>recovered_receipt=true</code>, <code>stage=done</code>, and effect count remains 1.

## Run the nine real CrewAI tests

~~~powershell
& $python -B -m unittest -v test_crewai_persistent_flow.py  # Normal-mode regression tests.
& $python -B -O -m unittest -v test_crewai_persistent_flow.py  # Ensure checks do not rely on optimization-removed bare assert.
$env:PYTHONWARNINGS = "error"  # Make warnings not explicitly allowed fail immediately.
& $python -B -m unittest -v test_crewai_persistent_flow.py  # Strict-warning mode.
& $python -B -O -m unittest -v test_crewai_persistent_flow.py  # Optimization plus strict warnings.
Remove-Item Env:PYTHONWARNINGS  # Clear this session-only policy.
~~~

The suite covers the pinned version, no-key routing, old-schema rejection, same-UUID hydration, normalization of leading/trailing whitespace around <code>flow_id</code>, forks, fail-closed unknown UUIDs in both resume and fork, post-receipt crash recovery, and two independent processes. It also proves one <code>operation_id</code> cannot bind different payloads: conflict causes no second effect. It checks stderr for absence of Windows codec/CrewAIEventsBus errors. Transitive <code>1.15.4</code> dependencies emit one OpenTelemetry <code>SelectableGroups</code> deprecation and one <code>crewai.rag</code> ImportWarning on Python 3.11. The tests allowlist only those two full messages; all other warnings still fail under <code>-W error</code>. Review them again during upgrades rather than broadening ignores.

In isolated revalidation on 2026-07-21, all nine tests passed once in normal, <code>-O</code>, <code>-W error</code>, and <code>-O -W error</code> modes. Logs showed no API, LLM, HTTP, or telemetry errors, but no packet capture was performed. This proves only the current code and logging boundary; it does not prove absolute zero network connection.

## Telemetry, AMP tracing, and application logs

Govern these channels independently:

- <code>CREWAI_DISABLE_TELEMETRY=true</code> disables CrewAI anonymous telemetry only and is preferable to globally disabling OpenTelemetry for one library.
- <code>Flow(..., tracing=False)</code> is this project’s explicit AMP-tracing override in <code>1.15.4</code>. That version treats only <code>CREWAI_TRACING_ENABLED=true/1</code> as an enable signal; an environment value of <code>false</code> can still read locally saved <code>trace_consent</code>, so it is not reliable opt-out. Production must manage persistent consent through the official CLI and verify actual egress.
- <code>OTEL_SDK_DISABLED=true</code> disables all OpenTelemetry instrumentation in the same process and should be used only when global shutdown is required.
- <code>suppress_flow_events=True</code> disables Flow and method lifecycle event emission, reducing local listeners and observability. This fixture uses it to isolate recovery tests; do not copy it into a Flow that needs event audit. Redirecting logs changes only local output. Neither setting proves anonymous telemetry is disabled.

The fixture uses the CrewAI-specific variable for anonymous telemetry and sets <code>tracing=False</code> on every Flow. Production must not rely on <code>CREWAI_TESTING</code>, and a lack of outbound traffic in a test must not imply that deployment images, plug-ins, or exporters are equally safe.

## Acceptance checklist

- [ ] Explain the different responsibilities of state UUID, operation ID, and payload hash.
- [ ] Same-UUID recovery and fork have the expected ID/history semantics.
- [ ] The application rejects unknown UUIDs rather than silently creating a Flow.
- [ ] A crash after receipt commit then recovery retains a serial effect count of 1.
- [ ] Explain the difference between <code>@persist</code> hydration, checkpoint skipping, and external receipts.
- [ ] Windows tests have no encoding error and anonymous telemetry and AMP tracing are configured separately.
- [ ] Do not extrapolate local SQLite results to concurrent or distributed exactly-once behavior.

## Back to the index

Return to [[crewai/00-index|CrewAI Learning Index]], then decide whether the project needs real Agents, Tasks, Crews, and a model provider.

## Primary references

Official documentation, <code>1.15.4</code> wheel API, and isolated runtime verification were checked on 2026-07-21.

- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Checkpointing](https://docs.crewai.com/en/concepts/checkpointing)
- [CrewAI Telemetry](https://docs.crewai.com/en/telemetry)
- [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing)
- [CrewAI 1.15.4 tracing-enablement source](https://github.com/crewAIInc/crewAI/blob/1.15.4/lib/crewai/src/crewai/events/listeners/tracing/utils.py)
- [CrewAI 1.15.4 Flow runtime source](https://github.com/crewAIInc/crewAI/blob/1.15.4/lib/crewai/src/crewai/flow/runtime/__init__.py)
- [CrewAI 1.15.4 source](https://github.com/crewAIInc/crewAI/tree/1.15.4)
- [PyPI: crewai 1.15.4](https://pypi.org/project/crewai/1.15.4/)
