---
title: "Offline Monitoring Audit Project and Self-Check"
tags:
  - observability
  - project
aliases:
  - Runtime Monitoring Offline Project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
source_baseline: "Python 3 standard-library offline fixtures and 45 unittest
  cases; W3C, OpenTelemetry, and Google SRE materials checked through
  2026-07-22."
lang: en
translation_key: 运行监控/03-项目与自测/08-离线监控审计项目与自测.md
translation_source_hash: 88ab3330b1e1d9f4133862c7d278229c4257a3300ada455c27fc76f8c496e6e2
translation_route: zh-CN/运行监控/03-项目与自测/08-离线监控审计项目与自测
translation_default_route: zh-CN/运行监控/03-项目与自测/08-离线监控审计项目与自测
---

# Offline Monitoring Audit Project and Self-Check

## Project goal

Build a verifiable “telemetry contract → indicators → SLO/error budget → action” chain without connecting to a monitoring platform, cloud account, or real key. The project uses only Python 3's standard library:

- strictly validate structured-event, trace, metric-label, Collector, and telemetry-governance contracts;
- validate teaching W3C `traceparent` values, parent/child spans, and event-to-trace correlation;
- calculate RED, USE, p95, SLIs, short/long-window bad-event ratios, and error-budget burn rates;
- examine quality, safety, cost, Agent steps/tokens, and observability completeness together;
- emit `OK`, `TICKET`, or `PAGE`, a full SHA-256 monitoring-evidence digest, declared digest format, and a display-only short fingerprint;
- produce a no-raw-content regression candidate for human triage for every non-`OK` window;
- cover normal and incident cases, invalid input, release binding, full digests, digest format, business-event freshness, and CLI exit codes with 45 offline tests.

The project files use unambiguous relative links:

- [monitor_audit.py](runtime-monitoring/examples/monitor_audit.py) — contract validation, indicator calculation, and decision CLI.
- [telemetry_windows.json](runtime-monitoring/examples/telemetry_windows.json) — versioned teaching policy, SLO, and two windows.
- [test_monitor_audit.py](runtime-monitoring/examples/test_monitor_audit.py) — standard-library `unittest` tests.

## Environment setup

The primary environment is Windows 11, PowerShell 7, and a current stable Python 3. Learn the standard `venv + pip` flow first. This project has no third-party dependency, so it installs no package. Run the following blocks in order from the project root that contains both `docs-EN/` and `.website/`. Put the virtual environment in the system temporary directory to avoid creating `.venv` in the vault:

```powershell
$projectDir = (Resolve-Path -LiteralPath 'docs-EN\runtime-monitoring\examples').Path # Resolve the examples directory to an absolute path so the current directory cannot change the commands.
$venvDir = Join-Path $env:TEMP "ai-agent-engineer-monitoring-venv" # Keep the virtual environment in the system temporary directory, outside the vault.
python -m venv $venvDir # Create an isolated Python environment with the standard library.
& (Join-Path $venvDir "Scripts\Activate.ps1") # Activate it so subsequent python commands use the isolated interpreter.
Push-Location -LiteralPath $projectDir # Enter the script and fixture directory; this is restored at the end.
```

If local policy forbids activation scripts, call `& (Join-Path $venvDir "Scripts\python.exe") ...` directly. The project needs neither a network connection nor API key and writes no report file; do not copy the virtual environment into the knowledge base.

## Input contract

The top-level JSON contains `policy`, `slo`, and `scenarios`. The reader rejects duplicate JSON fields, nonstandard numbers, raw invalid UTF-8 bytes, and Unicode surrogates that cannot be encoded as strict UTF-8 scalar sequences. The validator then uses exact field sets: missing/unknown fields, wrong types, invalid enumerations, non-finite numbers, numbers that cannot be represented as finite `float` values, duplicate IDs, and unsorted timestamps all fail. This prevents a later duplicate field from silently replacing an earlier value, prevents uncontrolled encoding exceptions during full-digest calculation, and avoids silently accepting a typo. `slo.good_statuses` must also be a subset of the event `status` enumeration; otherwise a nonempty misspelled “good status” could count every event as bad.

Each scenario fixes its observation endpoint with a time-zone-bearing `window_end` and derives its start from `window_minutes`; every event must be within that window. `event_data_age_seconds` is the age of the latest business event relative to that endpoint and is separate from the Collector's latest-export age: a Collector can successfully export an already-stalled business stream. Exceeding `policy.max_event_age_seconds` produces a `PAGE` rather than treating old data as the current short window. `window_end` is the declared time of an offline fixture, not a trusted time service.

Every scenario also has strict `release_evidence` fields: `release_id`, `release_manifest_sha256`, `candidate_gate_evidence_sha256`, and `candidate_gate_evidence_digest_format`. Both digests must be full **64-character lowercase hexadecimal strings (256-bit SHA-256 digests)**, and the format field must be the versioned teaching profile currently supported by this repository. Every event's `release` must equal `release_id`. The fixture's two release-evidence sets are independent teaching examples; they do not claim direct interchangeability with fixed LLMOps-project values. A production system must validate semantics, byte representation, and digest end to end against the same release manifest.

`evaluate_scenario()` also returns `evidence_digest_format` in every `Decision`. A non-`OK` `regression_handoff` carries the upstream `candidate_gate_evidence_digest_format` and this window's `monitor_evidence_digest_format` separately. All three use the controlled local-Python teaching format `python-json-sorted-utf8-v1`, and a fixed golden vector constrains byte representation; an unknown format is rejected. This only tells a recipient how to recompute, not the provenance, artifact integrity, or approval authenticity of release evidence. Cross-language hashing/signing still needs verified bytes or an explicitly specified and interoperability-tested standard such as [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html).

### Event and Agent signals

Each event contains:

- `request_id`, a time-zone-bearing timestamp, `service`, `release`, and controlled `intent`;
- technical `status`, `latency_ms`, and `trace_id`;
- provider, model snapshot, model/tool-call counts, Agent steps, and input/output tokens;
- a quality label that may be `true/false/null`, where `null` explicitly means ground truth is unknown;
- safety-check status, violation outcome, and estimated cost.

The script rejects contradictions such as “a violation was found although no safety check ran.” Provider/model fields are local contract examples and do not claim to match a current SDK field for any vendor.

### Traces and propagation

Each trace contains deliberately constructed teaching IDs and a span tree. The validator checks:

- W3C version-`00` shape, a 32-character lowercase hexadecimal nonzero trace ID, a 16-character lowercase hexadecimal nonzero parent-span ID, and `00/01` flags;
- matching trace ID in `traceparent` and the record;
- exactly one root span, unique span IDs, real parent spans, and no cycle;
- a root span whose service, release, status, and duration correlate with its event.

These IDs do not originate from real users or production systems. `traceparent` is for propagation correlation only; it is not an authentication credential.

### Telemetry and Collector governance

`metric_label_keys` must come from a finite allowlist. High-cardinality values such as `request_id`, a full release digest, or a gate digest are rejected and may appear only in controlled traces or audit logs for handoff. The telemetry policy checks that raw-content capture is off, redaction checks pass, and retention is bounded. Collector signals cover accepted, refused, sent, failed, queue, and latest-export age. Resource signals use USE to inspect CPU utilization, queue saturation, and resource errors.

## Indicator and action definitions

| Definition | Project meaning | Interpretation boundary |
| --- | --- | --- |
| RED Rate | Events in the declared window ÷ `window_minutes` | Teaching event rate, not traffic forecasting |
| RED Errors | Proportion with `status == error` | Technical failure, not task quality |
| RED Duration | Nearest-rank p95 of all teaching events | Does not represent a particular monitoring-platform algorithm |
| SLI good event | Eligible `status` and latency no greater than SLO objective | Event definition and latency objective are versioned |
| Bad-event ratio | Share of events other than SLI-good events | Direct measurement for one observation window |
| Burn rate | Bad-event ratio ÷ `(1 - SLO target)` | `1x` consumes allowed budget evenly; it is not remaining budget |
| Business-event age | `window_end` − latest event timestamp | Checked separately from Collector export age; too large may mean a stalled business stream |
| Trace completeness | Proportion of events with a verifiably correlated trace | Missing evidence does not mean the request did not exist |
| Quality pass rate | Pass share among labeled events | Must accompany label coverage |
| Safety-violation rate | Violation share among checked events | Must accompany safety-check coverage |
| Cost/Agent structure | Estimated cost per request, mean steps, mean tokens | Teaching estimate, not a real invoice |

The short window is the five minutes before declared `window_end`; the long window covers the full sixty minutes. Therefore, the last event cannot quietly redefine both windows. The project intentionally does **not** emit `error_budget_remaining_ratio`: remaining budget requires consumed budget, population, and exclusion rules over the full SLO compliance window and cannot be derived from this 60-minute teaching window. The priority is `OK < TICKET < PAGE`. Sustained fast short/long burn, failed safety/privacy policy, Collector blindness, stale business events, or insufficient trace completeness can escalate to PAGE; latency, label, quality, cost, Agent structure, and USE investigation lines can create a TICKET. Thresholds belong to the `local-monitor-policy-v3` teaching policy, not universally recommended Google, Prometheus, or OpenTelemetry values.

## Run scenarios

Run the healthy window first:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1" # Do not create __pycache__, keeping the teaching directory free of cache files.
python .\monitor_audit.py --scenario stable-window # Run the healthy window with sufficient evidence.
if ($LASTEXITCODE -ne 0) { throw "stable-window did not return 0 as expected" } # A healthy scenario completes with OK and exit code 0.
```

The first line should be `OK: stable-window`, with short/long burn rates `0.00/0.00` and `event_age=60s`. Then run the incident window:

```powershell
python .\monitor_audit.py --scenario incident-window # Run an incident window containing SLO, safety, and Collector problems.
if ($LASTEXITCODE -ne 1) { throw "incident-window did not return 1 as expected" } # PAGE is a controlled action, so it returns 1 rather than crashing.
```

The first line should be `PAGE: incident-window`. The local fixture's short/long burn rates are `5.00/2.50`; the output then lists SLO, safety, Collector, trace, quality, cost, and resource decision reasons and emits `regression_candidate=needs_human_triage`. The candidate contains only release evidence and limited trace references, with `raw_content_included=false`. It is not an automatic write to a frozen dataset.

`evaluate_scenario()` returns `Decision.evidence_sha256` and `Decision.evidence_digest_format`: the full runtime summary and its byte profile. Only when non-`OK`, `regression_handoff` carries that same value as `monitor_evidence_sha256` and `monitor_evidence_digest_format` to the human-triage candidate while retaining the candidate-gate format it received. The CLI intentionally prints only a 16-character `evidence_fingerprint`, which is readable by people but insufficient for cross-system handoff. A real integration should retain full value, format, provenance verification, and approval boundary in a controlled record or API.

CLI exit-code contract:

- `0` — selected scenario is `OK`.
- `1` — at least one scenario needs `TICKET` or `PAGE`.
- `2` — file, JSON, or data-contract error.

This makes the script suitable for offline checks, but a real page still requires an owner, runbook, routing, suppression, and end-to-end notification verification.

## Run tests and syntax checks

The four groups below cover the normal interpreter, disabled assertions, warnings as errors, and both interpreter switches together. Tests do not rely on production-code `assert`:

```powershell
python -m unittest -v test_monitor_audit # Run all unit tests with the normal interpreter.
if ($LASTEXITCODE -ne 0) { throw "normal tests failed" } # Stop verification immediately if normal mode fails.

python -O -m unittest -v test_monitor_audit # Verify production validation does not depend on a bare assert removed by -O.
if ($LASTEXITCODE -ne 0) { throw "optimized tests failed" } # Optimized mode must yield the same regression result.

python -W error -m unittest -v test_monitor_audit # Promote warnings to errors so compatibility problems are not ignored.
if ($LASTEXITCODE -ne 0) { throw "warnings-as-errors tests failed" } # Strict warning mode must pass.

python -O -W error -m unittest -v test_monitor_audit # Re-run with optimization and warnings-as-errors together.
if ($LASTEXITCODE -ne 0) { throw "optimized warnings-as-errors tests failed" } # Local verification completes only when all four modes pass.
```

Then perform a minimum syntax check without writing `.pyc`:

```powershell
python -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ('monitor_audit.py', 'test_monitor_audit.py'))]" # Compile implementation and tests in memory without writing .pyc.
if ($LASTEXITCODE -ne 0) { throw "syntax check failed" } # A syntax failure must not be hidden by later directory restoration.
Pop-Location # Restore the terminal directory from before this project was run.
```

Tests cover strict schemas, observation-window boundaries, business-event age, non-finite numbers, numbers not representable as finite `float`, raw invalid UTF-8, UTF-8-unencodable surrogates, a fixed digest golden vector, Trace Context, parent/child spans, cycles, event correlation, high-cardinality labels, Collector/safety contradictions, release evidence, full SHA-256, human-triage candidates, decision priority, and CLI exit codes. Passing proves only agreement between the local contract and implementation; it does not prove that a real monitoring backend or notification path works.

## Hands-on exercises and extensions

1. Add `ticket-window` so the long window exceeds its threshold but the short one does not cross PAGE; assert `TICKET`.
2. Add a valid window whose quality labels are all `null`. Verify that output explicitly says “task quality unknown,” not quality zero.
3. Add a teaching `link` field for an asynchronous tool span: write a failing test first, then extend the exact schema and cycle detection.
4. Serialize decision output as stdout JSON, preserving policy/SLO version and evidence fingerprint without overwriting inputs or creating historical artifacts.
5. Move the stable window's last event two minutes earlier while keeping the Collector fresh. Confirm stale business events still PAGE, and explain why the two ages cannot replace each other.
6. Build an offline runbook mapping for every PAGE reason and test that missing owner, runbook, or recovery condition cannot enter real notification routing.

## Self-check questions

1. Why cannot an HTTP-success request with a missing quality label be counted as a quality success?
2. Why are a falling trace sampling rate and growing metric-label cardinality different problems?
3. Why is simultaneous short- and long-window crossing better suited to PAGE than one instantaneous threshold?
4. Why are otherwise “normal” metrics untrustworthy when Collector export age is too high?
5. Why does valid `traceparent` syntax still fail to prove a request is authorized?
6. Why does a fresh Collector export still fail to prove the business event stream is current?
7. Why is exit code `1` for the incident window successful test verification rather than a script crash?

## Mastery checklist

- [ ] I can explain every denominator, unknown value, and version field in the JSON contract.
- [ ] I can drill from a RED symptom to USE resources, traces, and structured events.
- [ ] I can calculate an SLI, error budget, and short/long-window burn rate by hand.
- [ ] I can distinguish quality, safety, cost, Collector health, and observability completeness.
- [ ] I can run the 45 tests and explain the risks checked by `-O`, `-W error`, and their combination.
- [ ] I can explain the boundaries between burn rate, remaining error budget, a full evidence digest, and a display fingerprint.
- [ ] I can state that all IDs, thresholds, and model fields are offline teaching-contract values.
- [ ] I can list the collection, propagation, backend, notification, privacy, and compliance boundaries a real system still must verify.

## Project boundary and next step

This project proves that input contracts, correlation, indicator definitions, and local decisions can be verified deterministically. The current `slo` is only a Layer A teaching contract—`target + latency_objective_ms + good_statuses`—and does not yet make service population, exclusion rules, a complete compliance window, data source, or change approval into an auditable SLO object. It can neither treat a fixture window's burn rate as production SLO-compliance evidence nor calculate production remaining error budget. `window_end` and age checks prove only time relationships inside the fixture, not trusted time, complete real traffic, or correct end-to-end collection. A regression candidate is likewise a restricted audit artifact. It is admitted only after human triage, redaction, deduplication, and reproduction through [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]]. The project connects no real SDK, Collector, monitoring backend, provider billing, notification path, or user ground truth, and it has no Obsidian Reading View verification. In production, first connect the [[runtime-monitoring/foundations/02-instrumentation-collector-and-correlation|Instrumentation, Collectors, and Correlation]] pipeline in a sandbox, then use [[runtime-monitoring/production-monitoring/07-incident-response-and-postmortems|Incident Response and Postmortems]] to exercise the full path from symptom through containment and recovery.

## References

- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — W3C Recommendation, checked 2026-07-22.
- [OpenTelemetry Collector internal telemetry](https://opentelemetry.io/docs/collector/internal-telemetry/) — checked 2026-07-22.
- [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/) — checked 2026-07-22.
- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — checked 2026-07-22.
- [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) — checked 2026-07-22; numerical thresholds were not copied directly.
- [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/) — checked 2026-07-22; this project uses custom nearest-rank, not Prometheus query behavior.

