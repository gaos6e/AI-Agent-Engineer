---
title: "Project: Offline Transcript Evaluation"
tags:
  - ai-agent-engineer
  - asr
  - project
aliases:
  - ASR offline evaluation project
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音识别/03-项目与自测/08-项目-离线转录评估.md
translation_source_hash: cb2c595aad58ccc97bb7a5abd75c918e54556131931683582a59e4529f32a620
translation_route: zh-CN/语音识别/03-项目与自测/08-项目-离线转录评估
translation_default_route: zh-CN/语音识别/03-项目与自测/08-项目-离线转录评估
---

# Project: Offline Transcript Evaluation

## Project objective

Use a manually written synthetic transcript fixture to validate format/time-reference contracts, committed transcript revisions, anonymous speaker fields, WER/CER, and slice differences offline. The project contains no audio and performs no model inference, so its metric convention can be reproduced in any Python 3 environment.

Assets:

- [[speech-recognition/project-and-self-check/examples/asr_fixture.json|asr_fixture.json]]
- [[speech-recognition/project-and-self-check/examples/evaluate_transcript.py|evaluate_transcript.py]]
- [[speech-recognition/project-and-self-check/examples/test_contract_and_cli.py|test_contract_and_cli.py]]

## Run it

Run these commands from the project root that contains both **docs-EN/** and **.website/**:

~~~powershell
Push-Location -LiteralPath 'docs-EN\speech-recognition\project-and-self-check\examples'
python -B .\evaluate_transcript.py .\asr_fixture.json
python -B .\evaluate_transcript.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
~~~

The script calculates teaching-scale WER using NFKC, **casefold()**, punctuation removal, and whitespace tokens, and CER using non-whitespace characters. It records the rule in its report; changing the rule requires a new evaluation version. WER/CER for an empty reference is **undefined_no_reference_units**, never falsely reported as zero. The current regression suite has **69 tests**; normal, **-O**, and warnings-as-errors modes should all pass.

## Input and exit-code contract

Input must be strict UTF-8 JSON. Duplicate keys, **NaN/Infinity**, unknown fields, and wrong types are rejected. The top level contains exactly **schema_version: "1.1"**, **session_id**, **source_audio**, **transcript_revision**, **transcript_state**, **normalization**, and **segments**. **source_audio** declares stable **asset_id**, **source_revision**, a time reference relative to **asset_start**, original/analysis formats, and **audio_available: false**. These are **synthetic metadata**; the script does not read or validate real media. **transcript_state** is fixed as **committed** because the project does not simulate streaming partial/revision events. Each segment contains exactly an ID, start/end time, speaker, slice, reference text, and predicted text. **speaker** may be **null** to indicate that no anonymous speaker label was supplied.

- Exit code **0**: the structural contract is valid and has no duplicate-ID or timeline error.
- Exit code **1**: the structural contract is valid but contains duplicate IDs, negative time, invalid intervals, or overlap.
- Exit code **2**: a file, UTF-8, JSON, or structural-contract error occurred.

## Report interpretation

- **micro_wer/micro_cer**: pooled edit count divided by reference length.
- **rate_status**: **defined** or **undefined_no_reference_units**. Explain the latter's errors separately with no-reference-segment metrics.
- **by_slice**: grouped by synthetic scenario labels in the fixture; labels do not represent real populations.
- **timestamp_errors**: contract problems such as an end not after a start, out-of-order segments, or overlap.
- **audit_errors**: cross-segment consistency errors such as duplicate **segment_id**.
- **speaker_coverage**: fraction of segments with an anonymous speaker label; it does not evaluate identity correctness.
- **source_audio / transcript_revision**: associate a report with synthetic asset, format contract, and transcript version; they do not prove real audio was examined.

## Extension tasks

1. Move the second segment's start into the first segment and confirm an overlap error.
2. Add synonymous number forms to a Chinese segment and compare normalization behavior.
3. Add device/noise slices; report reference-word count for every slice to avoid strong conclusions from small samples.
4. Add a no-speech case with an empty reference, observe undefined WER, and design an independent false-trigger metric.
5. To permit overlapping speech, extend the schema and timeline semantics first instead of simply disabling every overlap check.

## Acceptance criteria

- [ ] The default fixture returns **0**; a deliberately introduced timeline/duplicate-ID error returns **1**; a broken structural contract returns **2**.
- [ ] All 69 tests pass in normal, **-O**, and warnings-as-errors modes without generating caches.
- [ ] I can calculate WER for one segment by hand and verify it against the script.
- [ ] I can explain that the script does not validate real audio quality, VAD, timestamp precision, or speaker correctness.
- [ ] I can explain why a synthetic **slice** result must not be presented as a real fairness conclusion.

After finishing, return to the [[speech-recognition/00-index|Speech Recognition index]], then connect the metric ideas to [[benchmark-design/00-index|Benchmark Design]].
