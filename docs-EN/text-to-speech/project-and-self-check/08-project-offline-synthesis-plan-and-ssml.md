---
title: "Project: an offline synthesis plan and SSML"
tags:
  - ai-agent-engineer
  - tts
  - project
aliases:
  - TTS synthesis-plan project
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音合成/03-项目与自测/08-项目-离线合成计划与SSML.md
translation_source_hash: 05af0bed57d95ee3add327eb25599c1b2d03f1c31517b6391c5d0669996c301e
translation_route: zh-CN/语音合成/03-项目与自测/08-项目-离线合成计划与SSML
translation_default_route: zh-CN/语音合成/03-项目与自测/08-项目-离线合成计划与SSML
---

# Project: an offline synthesis plan and SSML

## Project goal

Create a structured “synthesis plan” from anonymized JSON requests and construct/validate basic SSML in memory. Validate the voice catalog, language–voice match, permitted purpose, in-policy authorization reference, structural presence of `acl_reference`, input length, and XML structure. The program explicitly gives every item a `not_generated` state: it calls no service, downloads no model, and produces no audio.

Assets:

- [[text-to-speech/project-and-self-check/examples/tts_requests.json|tts_requests.json]]
- [[text-to-speech/project-and-self-check/examples/build_tts_plan.py|build_tts_plan.py]]
- [[text-to-speech/project-and-self-check/examples/test_contract_and_cli.py|test_contract_and_cli.py]]

## Run it

Run the following commands from the project root, which contains `docs-CN/`, `docs-EN/`, and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\text-to-speech\project-and-self-check\examples'
python -B .\build_tts_plan.py .\tts_requests.json
python -B .\build_tts_plan.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
```

The program prints only redacted JSON to the terminal and has no write-file option. A plan contains only SHA-256 values and structural profiles for source text/SSML; it does not echo source text or complete SSML, avoiding sensitive-text copies during practice. The current regression suite has **73 cases**; normal, `-O`, and warnings-as-errors modes should all pass.

## Input and exit-code contract

Input must be strict UTF-8 JSON. Duplicate keys, `NaN`/`Infinity`, unknown fields, wrong types, and language tags outside this project's BCP 47 subset are rejected. Top-level `schema_version` is `"1.1"`; `policy` needs `policy_revision`, a nonempty `voice_catalog`, rate/emphasis allowlists, and `disclosure_required`. Every voice profile explicitly declares `voice_id`, supported languages, permitted purposes, and an in-policy authorization reference. Every request uses local `operation_id` and includes `source_revision`, `acl_reference`, purpose, and authorization reference. A real provider's `provider_request_id` is created by the provider response and should be recorded separately with the provider and response/receipt; it is not an input field for this project and cannot be used for local idempotency or deduplication. This teaching contract is not any vendor API, voice catalog, or rights-review system.

- Exit code `0`: structural contract and all policy checks pass.
- Exit code `1`: the structure is valid, but voice/language/purpose/in-policy authorization reference does not match, rate/emphasis is outside the allowlist, text is too long, or `operation_id` is duplicated.
- Exit code `2`: file, UTF-8, JSON, or structural-contract error.

## Security design

- User text is placed in nodes through `xml.etree.ElementTree`, which escapes special characters automatically.
- Language, voice, rate, and emphasis come from local policy; arbitrary XML is not accepted, and the language must match the selected voice profile's allowed set.
- Every request has `source_revision`, `acl_reference`, an authorization reference, and a purpose; missing values are contract errors. The script performs only a nonempty structural check of `acl_reference` and writes it into the plan; it **does not query, allowlist, or verify object-level ACL**. An external identity/authorization system must decide real object authorization before generation, reading, and release. The script likewise does not verify real contracts, consent, validity periods, or legal sufficiency.
- `source_text_sha256` supports association checks without retaining the complete text, but a digest can still be guessed from a dictionary and is not anonymization.
- Output includes `ssml_sha256` and `ssml_profile`, not complete SSML; the test fixture verifies complete XML behavior in unit tests.
- Output includes `generation_status: not_generated`, `audio_generated: false`, and `source_text_exposed: false`, preventing a plan from being misreported as generated audio or default terminal output from being treated as secure storage.

## Extension tasks

1. Remove `source_revision` or `acl_reference` and confirm that the script exits with a structural error; then replace it with any nonempty reference and observe that the offline project records it without claiming authorization passed.
2. Input `A&B <test>` and use unit tests to inspect safe escaping and parsed SSML rather than printing sensitive source text in the default CLI.
3. Change the Chinese voice to `en-US`, confirm the language–voice policy failure, then change purpose or in-policy authorization reference to observe different errors.
4. Before adding a vendor adapter, define core tags, output format, disclosure, fallback, and unknown-terminal-state behavior.
5. Add a policy-failure fixture. Create and clean up its temporary file in the test, then confirm exit code `1` and no audio or report file.

## Acceptance criteria

- [ ] The default fixture exits with `0`, a policy failure with `1`, and a structural-contract failure with `2`.
- [ ] All 73 tests pass in normal, `-O`, and warnings-as-errors modes, leaving no caches, reports, or audio files in the workspace.
- [ ] I can explain the SSML namespace, text escaping, and vendor-subset differences.
- [ ] I can distinguish “synthesis-plan validation passed” from “audio quality was validated”; this project proves only the former.
- [ ] I can add voice authorization, pronunciation rules, and an evaluation plan for a new language rather than merely changing a language code.

Return to [[text-to-speech/00-index|Text to Speech]], and connect authorization and evaluation to [[ai-governance/00-index|AI Governance]] and [[evaluation-framework/00-index|Evaluation Framework]].
