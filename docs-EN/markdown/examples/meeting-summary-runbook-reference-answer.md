---
title: "Meeting-Summary Runbook Reference Answer"
tags:
  - ai-agent-engineer
  - markdown
  - reference-answer
aliases:
  - Markdown integrated-project reference answer
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/examples/会议摘要运行手册-参考答案.md"
translation_source_hash: 31a63f21da1c9f5a11a8bba51960dc75cc004db1484bb680e8bb66e85691df3e
translation_route: zh-CN/Markdown/examples/会议摘要运行手册-参考答案
translation_default_route: zh-CN/Markdown/examples/会议摘要运行手册-参考答案
---

# Local Meeting-Summary Script Runbook (Reference Answer)

> [!warning] Teaching scenario
> This document demonstrates a runbook structure. The current knowledge base has no `summarize_meeting.py`, the commands below were not run, and every output is labeled as expected. Do not treat this page as a runnable software delivery.

## Goal and non-goals

This runbook explains how to run a **fictional** local script on Windows 11 and PowerShell 7. It reads UTF-8 meeting text and a local JSON configuration and produces a Markdown summary draft.

Boundaries:

- It does not connect to a meeting platform or external API.
- It does not send email, messages, or calendar invitations.
- It does not read recordings.
- It does not process real customer, patient, student, or account data.
- Output requires human confirmation and cannot become an execution instruction directly.

## Prerequisites

The reader needs a teaching-project directory that is assumed to contain `summarize_meeting.py`. Replace the string below with your own safe practice path:

~~~powershell
$ProjectRoot = 'C:\path\to\meeting-summary-demo'
Set-Location -LiteralPath $ProjectRoot
python --version
Test-Path -LiteralPath '.\summarize_meeting.py' -PathType Leaf
~~~

Expected:

- `python --version` displays the local Python 3 version.
- `Test-Path` returns `True`.
- Stop if either condition fails; do not download a same-named script from the network at random.

This document did not run these commands and did not confirm a fixed Python patch version.

## Input/output contract

| File | Format and required content | Sensitivity | Retention policy |
| --- | --- | --- | --- |
| `meeting.txt` | UTF-8 text with at least one line of fictional meeting content | fictional data only | may be deleted after practice |
| `config.json` | JSON object with `language` and `max_bullets` | non-sensitive teaching configuration | retain with the practice |
| `summary.md` | Markdown draft with a heading and action-items list | determined by input; this exercise is fictional only | decide after human review |

Minimal `meeting.txt`:

~~~text
Example meeting: Alex will prepare a fully fictional demonstration checklist by 2026-07-20.
~~~

Minimal `config.json`:

~~~json
{
  "language": "en-US",
  "max_bullets": 5
}
~~~

Expected `summary.md`:

~~~markdown
# Meeting Summary Draft

## Action items

- Owner: Alex; task: prepare the demonstration checklist; due date: 2026-07-20.
~~~

The name and task above are fully fictional.

## Procedure

### 1. Confirm the current directory and input files

~~~powershell
Get-Location
Get-Item -LiteralPath '.\meeting.txt', '.\config.json' | Select-Object Name, Length
~~~

Expected: both files exist and have a size greater than `0`. Stop if a file is missing or the path is outside the teaching directory.

### 2. Validate JSON syntax only

~~~powershell
python -m json.tool '.\config.json' > $null
if ($LASTEXITCODE -ne 0) { throw 'config.json is invalid JSON' }
~~~

Expected: exit code `0`. This proves only that JSON syntax can be parsed; it does not prove field values meet a business contract.

### 3. Run the fictional script

~~~powershell
python '.\summarize_meeting.py' --input '.\meeting.txt' --config '.\config.json' --output '.\summary.md'
~~~

Expected: exit code `0` and a nonempty `summary.md`. This course has no such script, so there is no actual run result.

### 4. Local human confirmation

~~~powershell
Get-Item -LiteralPath '.\summary.md' | Select-Object Name, Length
Get-Content -LiteralPath '.\summary.md' -Encoding utf8
~~~

Review the owner, task, and date manually. If hallucinated, omitted, or sensitive content appears, delete the draft and record the issue. There is no automatic sending step.

## Control flow

~~~mermaid
flowchart TD
    Read["Read local text and configuration"] --> Validate{"Files, encoding, and JSON valid?"}
    Validate -->|no| Stop["Stop and report a local error"]
    Validate -->|yes| Draft["Generate a local Markdown draft"]
    Draft --> Review{"Human confirmation?"}
    Review -->|no| Remove["Delete the draft and record the issue"]
    Review -->|yes| End["Keep the local draft and end"]
~~~

The diagram has no network, sending, or external-write branch.

## Troubleshooting

| Observable symptom | Likely cause | Diagnosis | Safe recovery |
| --- | --- | --- | --- |
| `meeting.txt` is missing | wrong directory or input not created | `Test-Path`, `Get-Location` | stop; return to the teaching directory |
| decoding error | file is not UTF-8 | check editor save encoding; do not print real full text | save fictional data again as UTF-8 |
| `json.tool` errors | comma, quote, or bracket error | read the line/column error; do not output sensitive configuration | correct a copy and validate again |
| `summary.md` is missing or empty | script failed, input empty, or output path wrong | check exit code and file size | stop; do not treat an empty file as success |

Do not mask a deterministic input error through unlimited retries, and do not use administrator privileges to “solve” an ordinary path problem.

## Acceptance record

| Check | Current state | Evidence |
| --- | --- | --- |
| Document structure complete | checked | this page contains boundaries, contract, procedure, failures, and acceptance |
| Internal links exist | statically checked | targets back to the course and index exist |
| Example data is fictional | checked | this page explicitly labels teaching content |
| Commands can actually run | unverified | the repository lacks the fictional script |
| Obsidian Reading View | needs human review | static text inspection cannot replace the UI |

## Changes and sources

- 2026-07-14: created the teaching reference answer; did not run the fictional script or make network calls.
- PowerShell command syntax: [Microsoft PowerShell documentation](https://learn.microsoft.com/powershell/).
- JSON syntax validation: [Python `json` documentation](https://docs.python.org/3/library/json.html).
- Markdown structure: [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/).

Return to [[markdown/07-knowledge-base-runbook-project-and-self-test|Knowledge-base runbook project and self-test]] or [[markdown/00-index|Markdown index]].
