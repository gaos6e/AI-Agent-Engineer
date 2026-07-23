---
title: "Quality, Safety, and Cost Signals"
tags:
  - observability
  - ai-monitoring
aliases:
  - Multidimensional Monitoring for AI Applications
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "OpenAI, NIST, and OpenTelemetry primary materials checked
  through 2026-07-22; the GenAI semantic-convention migration, schema-version
  boundary, and component-stability boundary were reviewed."
lang: en
translation_key: 运行监控/02-生产监控/03-质量、安全与成本信号.md
translation_source_hash: 7c56e19cf83b8a66f1bafc5dad24ad161b24c9f663724f38e6266cc29f4a22e9
translation_route: zh-CN/运行监控/02-生产监控/03-质量、安全与成本信号
translation_default_route: zh-CN/运行监控/02-生产监控/03-质量、安全与成本信号
---

# Quality, Safety, and Cost Signals

## Goal

Build task-quality, safety-outcome, cost, and observability-completeness signals for an AI application alongside availability and latency, and distinguish ground truth, proxies, and unknowns.

## Several meanings of “service success”

One request can be HTTP 200, valid against a schema, factually wrong, cause a tool side effect, and exceed the cost budget at the same time. Do not flatten these meanings into one `success=true` field.

| Layer | Example | Data timeliness |
| --- | --- | --- |
| Technical | Not timed out, not 5xx, schema valid | Usually immediate |
| Process | Retrieval has evidence, tool parameters are valid, loop stays within its limit | Immediate or shortly delayed |
| Task quality | Classification is correct, answer is grounded, task is completed | May be immediate; ground truth may arrive days later |
| Safety/authorization | No unauthorized action, leakage, or high-loss side effect | Detection may be immediate; complete investigation is often delayed |
| Business outcome | User does not reopen a ticket, a decision is adopted, no reversal occurs | Usually delayed and affected by external factors |

Record status and evidence source for each layer separately. Do not fill an unknown with “success” before ground truth returns.

## Levels of quality signals

1. **Deterministic checks** — output schema, numerical range, cited-ID presence, required tool invocation.
2. **Proxy signals** — user retry/reversal, human handoff, no retrieval result, rule conflict. They arrive quickly but are not ground truth.
3. **Automated scoring** — task functions or versioned graders. Record the grader version and calibrate it against human judgment.
4. **Human review** — sampling, expert review, and disputed-case review. Report sampling rules and agreement; do not assume the reviewed subset represents the full population.
5. **Delayed ground truth** — correlate a later outcome with the release, input snapshot, and prediction at the time using a stable entity ID.

Every quality curve should show its denominator, label coverage, and freshness. “90% quality” based on only 5% coverage of easy samples is weak evidence.

## Safety-signal denominator and coverage

Zero recorded security events can mean three things: none occurred, detection had no coverage, or the observability pipeline lost data. At minimum, report:

- policy rejects/passes/check failures by policy version and task type;
- audited unauthorized actions, leaks, successful prompt injections, or high-loss side effects;
- the share of requests covered by safety checks and the fail-open/fail-closed state;
- human-review sample size, wait time, and conclusion-revision rate;
- time from occurrence to detection and from detection to containment for severe events.

Do not place raw attack text or user information in metric labels. Investigation evidence needs access control, redaction, a retention period, and auditability.

## Cost is a function of traffic and structure

Total cost alone mixes “more users” with “one task is out of control.” Show these together:

- total or estimated cost attributed by project, release, and task type;
- cost per request, per successful task, and per business outcome;
- input, cache-read/write, and output-token distributions;
- model, retrieval, tool, and retry call counts;
- price-list version, currency, discount/contract assumptions, and whether a value is an estimate or a bill.

Before an invoice arrives, a token-and-price-list figure is an estimate. Mark it as such; do not claim exact equality with billing.

## LLM and Agent runtime signals

Without recording sensitive content, a versioned event or trace contract can include:

| Category | Controlled signal | Question answered |
| --- | --- | --- |
| Release identity | Provider, model snapshot, release/prompt/policy version | Which release unit changed behavior? |
| Model use | Model-call count; input/output tokens; cache tokens when the provider actually supplies them | Is cost or latency driven by traffic or per-task structure? |
| Agent process | Steps, tool calls/failures, loop-termination cause, human handoff | Is there a retry storm or runaway loop? |
| RAG/tools | Retrieval, reranking, model, tool, and policy-check spans with status | In which stage did time or an error occur? |
| Outcome | Technical status; quality status and coverage; safety status and coverage; estimated cost | Is HTTP success hiding task failure? |

Fields must come from a current SDK/provider response or the team's own contract. Preserve missing values as unknown rather than converting them to zero. Semantic-convention stability is declared for specific OpenTelemetry components and signals; as of 2026-07-21, the core semantic-conventions page was 1.43.0 and GenAI conventions had moved to a separate repository. Pin the actual revision and schema/contract identifier, verify stability for the components used, and write contract tests. Do not treat a core-page version or a changing field name as a permanent fact across systems. A full release-manifest or gate SHA-256 is likewise a trace/control-audit field, never a metric label.

## Monitoring completeness is a first-class signal

The following gaps can make every quality and safety curve look “better”:

- Trace or log export failure;
- a safety classifier timing out and the system failing open;
- the ground-truth feedback job stopping;
- a new release omitting version fields;
- a data definition changing without dashboard annotation.

Monitor event count, version-field completeness, trace-propagation rate, label coverage, and end-to-end collection delay too. The Collector's most recent successful export does not replace business-event age: they respectively tell you whether the transport chain is alive and whether the observed business stream is progressing.

## Exercise and self-check

For a RAG customer-support Agent, design a signal table with at least two signals in each category: technical, process, quality, safety, cost, and observability completeness. For each signal, state denominator, timeliness, ground truth/proxy, slice, and owner. Answer:

1. Why does no recorded safety violation fail to prove there is no safety problem?
2. Why must task-success rate be read with label coverage?
3. When total cost rises, how do you separate traffic growth, model change, longer outputs, and retry storms?

## Summary and next step

AI runtime health is a combination of multidimensional evidence and unknowns, not one availability curve. [[runtime-monitoring/production-monitoring/04-alert-design-and-on-call-operations|Alert Design and On-Call Operations]] determines which signals merit waking a person.

## References

- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-21; task-specific evaluation and human calibration.
- [NIST AI RMF: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — checked 2026-07-21.
- [OpenTelemetry Generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — checked 2026-07-21; the core page notes that the content moved and the prior location is no longer maintained.
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai) — checked 2026-07-21; pin the actual revision/schema URL and verify the components in use.
- [OpenTelemetry Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/) — checked 2026-07-21.

