---
title: "Prompt Experiment Project and Self-Check"
tags:
  - prompt-engineering
  - project
  - self-test
aliases:
  - Prompt Engineering project
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
source_baseline:
  - Python 3.11 standard-library documentation
  - JSON Schema 2020-12 documentation
lang: en
translation_key: 提示词工程/07-提示词实验项目与自测.md
translation_source_hash: 2a3f20b89db10b43e3e0e5815260513e359da5be8e32267fe9ecd78512829a4a
translation_route: zh-CN/提示词工程/07-提示词实验项目与自测
translation_default_route: zh-CN/提示词工程/07-提示词实验项目与自测
---

# Prompt Experiment Project and Self-Check

## Project objective and evidence boundary

Build a ticket-classification prompt laboratory that does not call a real model. It renders role-separated messages, binds the prompt in code, cases, and schema by version, reads mock responses, and validates strict JSON, field contracts, business rules, grounded evidence, and expected labels in sequence. It then summarizes results by label, business slice, and risk. The report records SHA-256 hashes for all three asset types, avoiding version names that cannot identify the actual content.

This experiment can demonstrate that **local contracts and failure paths run correctly**. It cannot demonstrate that any online model will reach the same quality. **mock_response** is a test fixture, not model output. A real API integration requires separate repeated evaluation, cost validation, and safety validation.

## Project files

| File | Responsibility |
| --- | --- |
| [[prompt-engineering/examples/prompt_lab.py\|prompt_lab.py]] | Strictly loads cases, binds the prompt in code and schema, separates policy from untrusted input, validates responses, and creates a traceable report and exit codes. |
| [[prompt-engineering/examples/cases.json\|cases.json]] | Twelve versioned cases that record expected labels and annotation rationale, covering three labels, five slice types, and three risk levels. |
| [[prompt-engineering/examples/response.schema.json\|response.schema.json]] | A Draft 2020-12 teaching contract. The runtime checks that its key fields have not drifted from the handwritten validator, then applies business-semantic validation. |
| [[prompt-engineering/examples/test_prompt_lab.py\|test_prompt_lab.py]] | Nineteen unit tests covering success, malformed input, version mismatches, schema drift, result tampering, injection, CLI behavior, and safety under **-O**. |

The **slice** field classifies a failure scenario: **typical**, **boundary**, **insufficient**, **adversarial**, or **multilingual**. **risk** describes the business impact if the case fails, not model confidence. **annotation_reason** records the human rationale for the expected label and is not sent to the model.

**mock_response** deliberately stores a string that contains JSON rather than a nested object already parsed by the case file. A real model returns text first. The experiment must cover invalid JSON, duplicate keys, and wrong types; a case-file parser must not repair those errors before the model boundary.

## Runtime environment

The project uses only the Python standard library, so it requires neither third-party packages nor an API key. In PowerShell 7 on Windows 11, run the following blocks in order from the repository root that contains **docs-CN**, **docs-EN**, and **.website**. The report step returns to the repository root.

~~~powershell
Push-Location -LiteralPath 'docs-EN\prompt-engineering'  # Temporarily enter the course directory so relative paths point to examples.
py -3.11 --version  # Confirm that the Windows Python Launcher resolves the required Python 3.11.
py -3.11 -B -W error -m unittest discover -s .\examples -p 'test_prompt_lab.py' -v  # Run tests normally and treat warnings as errors.
py -3.11 -B -O -W error -m unittest discover -s .\examples -p 'test_prompt_lab.py' -v  # Repeat under -O to verify that essential checks do not depend on assert.
~~~

For ordinary projects, first learn the **venv + pip** isolation workflow in [[python-fundamentals/00-index|Python Fundamentals]]. This dependency-free exercise uses the installed Python directly to avoid creating a **.venv** inside the vault. To practice virtual environments, create one outside the vault, such as under **$env:TEMP**. Do not commit virtual environments, caches, or reports to the knowledge base.

## Step-by-step experiment

### 1. Inspect message boundaries

~~~powershell
py -3.11 .\examples\prompt_lab.py --show-prompt billing-refund-pending  # Render only the selected case's message boundary; do not score every case.
~~~

Inspect the printed message array. Stable classification policy is in the developer message, and the ticket is JSON-serialized in the user message. Then inspect **technical-injection-login**: its “ignore the rules” text still appears only as ticket data. This structure helps express a trust boundary and prevents string concatenation from damaging JSON syntax, but it is not security isolation. If a case's declared **prompt_version** differs from the version in code, the program stops before rendering.

### 2. Run all cases

~~~powershell
py -3.11 .\examples\prompt_lab.py  # Run all teaching cases and let the CLI return an exit status under the quality contract.
$LASTEXITCODE  # Read the previous external command's exit status; 0 means every case passed.
~~~

The current fixture should report **12/12 passed** and exit with **0**. At startup it checks case-declared prompt/schema versions and confirms that the teaching schema's root object, fields, and **anyOf** branches use only the exact keyword set implemented by the runtime. **pattern**, **allOf**, and other extra constraints are not silently ignored. The response validator rejects duplicate JSON keys, **NaN** or **Infinity**, unknown fields, invalid enum values, empty reasons, overlong text, and evidence absent from the original ticket. For **billing** and **technical**, **evidence** must be a literal substring of the original ticket. This is an additional business validation layer beyond parseable JSON.

The project does not include a third-party JSON Schema implementation, so it cannot claim to execute all Draft 2020-12 semantics. It validates only the finite set of keywords used by the current teaching schema and checks that set against the runtime code. A real application should use a well-maintained schema validator and translate API parameters to the subset supported by its provider.

### 3. Produce an auditable report

~~~powershell
$report = Join-Path $env:TEMP "prompt-lab-report.json"  # Create the report under the system temp directory without polluting the vault.
py -3.11 .\examples\prompt_lab.py --json-report $report  # Write the current case results as an auditable JSON report.
Get-Content -LiteralPath $report -Raw -Encoding utf8  # Read the report unchanged as UTF-8 to inspect fields and failure details.
Pop-Location  # Return to the repository root where the paired Push-Location began.
~~~

The report records **dataset_version**, **prompt_id**, **prompt_version**, **schema_version**, SHA-256 hashes for the three asset types, total passed cases, results by label/slice/risk, and failure details with metadata. It does not write prompt text, keys, or real customer data. **build_report()** recalculates every complete **CaseResult** from the fixture, then compares each ID, label, slice, risk, error content, pass state, and **prompt_chars** before it calculates statistics. Any tampering fails before aggregation.

### 4. Prove that tests really fail

The suite's **test_cli_returns_failure_for_broken_mock_response** temporarily constructs a bad response and requires the CLI to return a nonzero status. The temporary file is outside the repository and does not modify the official cases. You can also copy **cases.json** outside the vault, intentionally change one **mock_response.label**, and run with **--cases <copy-path>**. Do not corrupt the official fixture, which is the regression baseline.

The exit-code contract is:

- **0:** every case passes.
- **1:** a case response fails the quality contract.
- **2:** the case/schema file is malformed, versions mismatch, **--show-prompt** receives an unknown ID, or report writing fails.

Input errors go to stderr without a Python traceback, allowing CI to distinguish a model-quality regression from an invalid experiment configuration.

## Local verification record

On **2026-07-21**, verification completed with Python 3.11.9:

- **py -3.11 -m py_compile:** both script and tests passed.
- **Normal mode:** all 19 tests passed with warnings treated as errors.
- **python -O mode:** the same 19 tests passed, demonstrating that essential validation does not depend on bare **assert** statements removed by optimization.
- **CLI:** all 12 cases passed across five slice types and three risk levels.
- The normal and **-O** CLI text and JSON report were byte-for-byte identical.

These results cover only offline fixtures. They did not call an external API or validate Obsidian Reading view.

## Extension tasks

1. Add 12 cases while keeping labels balanced. State slice, risk, and **annotation_reason** for each, and increment **dataset_version** after changing data.
2. Copy the prompt as v2 and change one rule only. Update **PROMPT_VERSION** in code and the case declarations together, preserve the evaluation set, and generate a case-by-case difference report. Version mismatches should remain fail-closed.
3. Design a separate refusal or clarification state for insufficient information. Update the schema, validator, cases, and tests, and observe why a contract must migrate as a whole.
4. After [[llm-api-integration/00-index|LLM API Integration]], add a separate adapter. It must obtain keys only from environment variables and record provider, model configuration, prompt version, and request ID. Offline tests must remain independently runnable.
5. After [[evaluation-framework/00-index|Evaluation Framework]], add repeated sampling, precision/recall, release thresholds for critical slices, and human-review records.

## Self-check questions

1. Why can twelve passing mocks not prove online-model quality?
2. What errors do strict JSON, schema, business rules, and action authorization each block?
3. Why does putting a ticket in a user JSON field still not eliminate prompt injection?
4. What attribution problem arises if you change prompt, model, and retrieval together?
5. Why cannot a global average “offset” a high-risk slice?
6. Why should a production adapter not rewrite or replace the offline test path?

## Mastery check

- [ ] I can run normal and **-O** test suites and explain the failure types covered by the 19 tests.
- [ ] I can make an intentionally broken temporary case fail correctly with a nonzero status.
- [ ] I can explain the separate responsibilities of template, cases, schema, business rules, and authorization.
- [ ] I can read the JSON report by slice and risk and locate a failing case.
- [ ] I do not write real keys, customer data, virtual environments, or full prompt logs into the vault.
- [ ] I can state which evidence remains missing between offline contract validation and online-model evaluation.

## Primary references

- [Python 3.11: unittest](https://docs.python.org/3.11/library/unittest.html) (accessed 2026-07-21)
- [Python 3.11: json](https://docs.python.org/3.11/library/json.html) (accessed 2026-07-21)
- [JSON Schema Draft 2020-12: Validation](https://json-schema.org/draft/2020-12/json-schema-validation) (accessed 2026-07-21)

## Return to the course

Return to the [[prompt-engineering/00-index|Prompt Engineering course index]], or continue to [[context-engineering/00-index|Context Engineering]].
