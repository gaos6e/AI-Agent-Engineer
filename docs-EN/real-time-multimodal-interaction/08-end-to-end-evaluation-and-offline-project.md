---
title: "End-to-End Evaluation and the Offline Project"
tags:
  - ai-agent-engineer
  - realtime
  - evaluation
  - project
aliases:
  - Real-time session simulator project
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 实时多模态交互/08-端到端评测与离线项目.md
translation_source_hash: 533dd38793653c4eec3444838088946759bdcfc8a3e74e51ef4c73a76e0e0b29
translation_route: zh-CN/实时多模态交互/08-端到端评测与离线项目
translation_default_route: zh-CN/实时多模态交互/08-端到端评测与离线项目
---

# End-to-End Evaluation and the Offline Project

## Why it matters

ASR word error rate, TTS naturalness, and a model's text accuracy cannot independently prove that a real-time agent is usable. A system can hear and answer correctly but continue playing an old answer after interruption, or execute a tool twice. The evaluation unit should be a trial with an initial environment, event trace, side effects, and final outcome.

## How to implement it

### Evaluation targets and metrics

Each \`task\` fixes an initial state, user script/media, allowed tools, risk, and grader; each \`trial\` retains media/network conditions, the event trace, tool receipts, final state, cost, and latency. Run stochastic components at least several times and report distributions and failure slices.

| Layer | Example metrics | Does not replace |
| --- | --- | --- |
| Perception | ASR WER/CER, dropped audio frames, visual localization | User intent/task correctness |
| Turns | Turn taking, false/missed interruption, old-playback-stop latency | Factual correctness of the answer |
| Tools | Schema, correlation, parameters, success, side-effect count | Whether the user is satisfied |
| Outcomes | Final external state, constraints, safety, human handoff | Trajectory diagnosis |
| System | p50/p95/p99 latency, timeouts, recovery, cost | Quality and risk |

A baseline suite should at least include quiet/noise/echo, accents/languages, short pauses, overlap, backchannels, self-corrections, long-tail tools, disconnects, late events, duplicate events, permission denial, and malicious audio. A release gate should jointly cover task success, safety-critical failures, duplicate side effects, p95/p99 latency, and recovery rate.

[Full-Duplex-Bench](https://arxiv.org/abs/2503.04721) provides an open research framework for pauses, backchannels, turn taking, and interruption. [Full-Duplex-Bench v3](https://arxiv.org/abs/2604.04847) further includes natural disfluent speech and multi-step tool calls, but as of 2026-07-18 it remained a recent preprint. Use it for observation and supplementary testing rather than direct production conclusions or model rankings.

### Offline project

[[real-time-multimodal-interaction/examples/realtime_session.py|\`realtime_session.py\`]] is a pure-standard-library event/session simulator. Its fixture parser rejects duplicate JSON keys and non-standard constants such as \`NaN\`/\`Infinity\`; events and nested tool arguments also accept only finite, JSON-compatible values. It enforces these invariants:

- Audio frames are contiguous from sequence 0, and only a turn containing speech may commit.
- The same event ID with the same content is ignored idempotently; the same ID with different content is rejected.
- Barge-in cancels the old response and clears the playback queue.
- A tool result must match an existing \`call_id + response_id\`; it validates offline correlation only, while actual authorization, idempotency receipts, and business reconciliation belong to the production execution ledger.
- \`WaitingTool\` pauses input/output for the current response until every declared tool has a result or the user interrupts.
- A disconnect saves a checkpoint, and only the correct resume token can recover it; when an old write call needs reconciliation, recovery may receive only its result/receipt before new work.
- Timeout/completed are terminal states; after termination, only exact duplicate events may be ignored.
- Unknown events, fields, error types, reverse-ordered time, and unresolved tools are rejected.

Run it with:

\`\`\`powershell
Set-Location ".\docs-EN\real-time-multimodal-interaction" # Enter the course project so fixture and example paths are stable
$env:PYTHONDONTWRITEBYTECODE = "1" # Do not create local Python bytecode cache files
python -B .\examples\realtime_session.py .\examples\session_fixture.json --pretty # Run the offline session fixture and print a formatted event/state summary
python -B -W error .\examples\test_realtime_session.py # Run tests at the normal optimization level, treating warnings as failures
python -B -O -W error .\examples\test_realtime_session.py # Verify under optimization/strict-warning mode that safety logic does not rely on bare assert
\`\`\`

Expected result: **33 tests / OK** in both normal and \`-O\` modes, with no network access, third-party dependencies, credentials, or file output. The [[real-time-multimodal-interaction/examples/session_fixture.json|fixture]] shows “old answer interrupted → new turn calls a tool → disconnect recovery → normal terminal state.” The regression suite also verifies duplicate JSON keys/non-standard numeric values, the tool-wait gate, and the requirement to reconcile an old write call before accepting new work after recovery.

> [!warning] What the simulator does not prove
> It does not capture or play real audio, nor validate codecs, echo cancellation, NAT, jitter buffers, telephony gateways, model quality, cloud-service session behavior, production authorization, or real tool receipts. It proves that the application event contract remains coherent at deterministic boundaries. A real rollout still needs device, network, media, execution-ledger, and provider-integration testing.

## Common failures

- Inspecting only the final transcript, not whether old audio leaked or a tool ran twice.
- Replacing distributions from multiple trials with one demo, so averages hide tail failures.
- Claiming production quality even though benchmark audio differs greatly from real devices/languages.
- Letting a grader read only the model answer rather than query the external final state.
- Testing only a happy path with no disconnect, late event, duplicate, \`unknown\`, or human handoff.

## How to validate

Run the offline contract tests first, then connect the same event schema to a real media adapter while preserving deterministic replay. Locate every failure in perception, turn handling, model, tool, playback, transport, or state recovery rather than vaguely attributing it to “the model.” Before rollout, place the critical suite in the release gate; production samples should retain only minimum necessary data and remain correlatable with the same grader.

## Practice tasks

1. Add a second audio frame to the fixture while preserving its contiguous sequence number, then confirm that the tests still pass.
2. Add a test for “disconnect while a tool is pending, then receive its receipt after recovery,” and explain why the old write request cannot be replayed automatically.
3. Design 20 tasks for a real target scenario, covering at least four networks, four turn behaviors, and three security failures.
4. State the new unknowns and acceptance gates when moving from the offline simulator to WebRTC/telephony.

## Completion checklist

- [ ] I can explain every ID, event, state, and terminal state.
- [ ] Normal/\`-O\`, warnings-as-errors tests both pass.
- [ ] Evaluation includes initial/final environment, side effects, traces, cost, and latency.
- [ ] Text/button fallback and a human-handoff path exist.
- [ ] Dynamic product facts have been checked against official documentation on the integration date.
