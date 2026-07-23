---
title: "Structured Technical Writing for Agent Engineering"
tags:
  - ai-agent-engineer
  - markdown
  - technical-writing
  - engineering-documentation
aliases:
  - Agent engineering documentation
  - Structured technical writing
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/05-面向Agent工程的结构化技术写作.md"
translation_source_hash: 2f9bf8d01490cbaad52f1ba4d72261ae886078d1dff2777305a4c43778671c4c
translation_route: zh-CN/Markdown/05-面向Agent工程的结构化技术写作
translation_default_route: zh-CN/Markdown/05-面向Agent工程的结构化技术写作
---

# Structured Technical Writing for Agent Engineering

## Lesson goal

Documents written by an AI Agent engineer are read jointly by people, scripts, and models. This lesson is not about making prose “formal.” It is about enabling readers to execute, review, and reproduce: goals are clear, input and output are checkable, commands and evidence are separate, and risks and unverified items are not hidden.

## Start from the reader's task

Before writing, answer four questions:

1. **Who will read it?** A learner new to the project, a maintainer, or an on-call operator?
2. **What should they complete after reading?** Understand a concept, run a command, diagnose a fault, or make a decision?
3. **What are they allowed to do?** Read-only inspection, local writes, external API calls, or production changes?
4. **What counts as completion?** A file created, tests passing, human approval, or a metric reaching a threshold?

If those questions have no answer, adding headings and callouts only makes ambiguous content look better formatted.

## Minimal structure of an executable document

| Section | Must answer | Common failure |
| --- | --- | --- |
| Goal and non-goals | what to do and not do | leave scope for readers to guess |
| Prerequisites | how to confirm environment, permission, and version | say only “install Python” |
| Input/output contract | format, size, sensitivity, failure form | give only one successful example |
| Procedure | current directory, purpose, command, stop condition | paste unexplained commands |
| Verification | what evidence proves success | present expected output as measured |
| Troubleshooting | symptom, cause, diagnosis, safe recovery | say only “retry” |
| Safety boundaries | credentials, privacy, external side effects | expose real data in examples |
| Sources and versions | basis, check date, volatile items | use memory instead of current documentation |

## Separate commands, output, and evidence

The following is a teaching command, not a record actually executed by this knowledge base:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

It must be followed by boundaries:

- Working directory: example project root.
- Side effects: creates a local `.venv` and installs dependencies.
- Repository rule: do not commit `.venv`.
- Expected result: command exit code is `0`.
- Measured result: **not run by this course**, because no corresponding example project or dependency file exists.

If it is actually run, write separate evidence: date, environment, complete command, exit code, and necessary redacted output. Do not replace a reviewable record with “it should be fine” or “verified to work.”

## Placeholders need syntax

Placeholders must be recognizable and must not be executed by accident:

~~~text
<PROJECT_ROOT>      absolute project directory supplied by the reader
<YOUR_API_KEY>      identifies a required key; documentation must not fill a real value
example.invalid     a domain reserved for documentation examples
~~~

State substitution rules before the command. Do not mix `{path}`, `YOUR_PATH`, and `xxx` without explanation. Do not feed angle-bracket placeholders straight to PowerShell because `<` and `>` can have syntactic meanings.

When a key is needed, provide `.env.example`:

~~~dotenv
MODEL_API_KEY=replace-with-your-own-key
~~~

This is only a field template. A real `.env` must be ignored and access controlled, and an example must not contain a usable token, its length characteristics, or an internal address.

## State inputs, instructions, and tool boundaries for an Agent

Markdown headings and fences can help people and models recognize regions:

~~~~markdown
## Task

Extract action items from user-provided meeting text.

## Not allowed

- Do not send email.
- Do not access the network.
- Do not write text to long-term storage.

## User data

```text
Place untrusted input here.
```

## Output contract

Return `owner`, `action`, and `due_date`; use `null` when a value cannot be determined.
~~~~

But a fence only expresses structure; it is **not a security boundary**. Untrusted input can also contain headings, backticks, or instruction-like language. Actual protections come from least privilege, schema validation, tool allowlists, human approval, and side-effect control. Detailed approaches belong in [[prompt-engineering/00-index|Prompt Engineering]], [[context-engineering/00-index|Context Engineering]], and [[agent-core/00-index|Agent Core]].

## Five high-frequency document types

### README: help people find the right entry point

A README should answer project purpose, quick start, minimal example, directory entry points, and support boundaries first. Do not put the full design history on the home page; link to dedicated documents.

### Runbook: help people complete an operation safely

Write a runbook in dependency order, including stop conditions, rollback or safe recovery, verification, and an escalation path. If an operation sends messages, deletes data, or creates cost, say so before the command and require appropriate confirmation.

### ADR / design decision: make a choice traceable

Record context, constraints, options, decision, rationale, consequences, and conditions for re-evaluation. Do not write “the team decided” as a technical fact; label it as a judgment when evidence is incomplete.

### Experiment record: make conclusions reproducible

Record hypothesis, data version, configuration, commands, randomness, metric definition, result files, and failed attempts. Posting only the final score hides selection bias and run conditions.

### Tool contract: prevent an Agent from guessing

For a Tool Calling or MCP tool, state purpose, input schema, output schema, errors, idempotency, side effects, authorization, and examples. Documentation examples do not replace runtime validation. Continue with MCP materials and [[agent-skills/00-index|Agent Skills]].

## Give diagrams, tables, and prose their own jobs

- **Flows or call relationships:** Mermaid.
- **Fields, versions, or option comparisons:** tables.
- **Dependency order:** numbered lists.
- **Causality, boundaries, and trade-offs:** full paragraphs.
- **Content that must be copied and run:** code fences.

Do not fill a diagram node with a full explanation, and do not use a table for long narrative. Visual structure must help a reader answer a question, not display tool fluency.

## Writing by evidence level

| Statement | Evidence state | Appropriate wording |
| --- | --- | --- |
| Executed | command, environment, time, and result exist | “Twelve tests ran under Python 3.11.9 and exited with code 0.” |
| Official fact | current primary source exists | “The official documentation states as of the check date…” |
| Engineering recommendation | a choice based on constraints | “This project recommends full-path links because entry-point names repeat.” |
| Reasonable inference | evidence is incomplete | “The logs only support inferring that the timeout occurred during the request phase.” |
| Unknown | not yet checked | “Not verified in Obsidian Reading View.” |

Precise wording is normally more credible than absolute wording. Do not turn “current tests pass” into “will never fail,” or generalize one platform's behavior to every Markdown renderer.

## Review an Agent-engineering document

Review in this order:

1. **Scope:** do the title and first screen clearly state task and non-goals?
2. **Executability:** can a beginner identify the directory and permissions needed to run it?
3. **Contract:** are input, output, failure, and side effects checkable?
4. **Evidence:** are measured facts, expectations, recommendations, and unknowns separate?
5. **Safety:** are credentials exposed, or external writes, cost, or approval hidden?
6. **Navigation:** are all active links real, clear, and unambiguous?
7. **Maintenance:** are versions, sources, changes, and recheck conditions present?
8. **Rendering:** have source text, target Reading View, and export environment each been spot-checked?

Fix errors and omissions before optimizing wording and style.

## Hands-on practice: write one tool description

Write one page for a fictional `extract_actions` tool:

- Input: untrusted local meeting text.
- Output: action-item JSON.
- Limits: no network, no sending, no long-term storage.
- Errors: empty input, oversized input, date cannot be parsed.
- Side effects: none.
- Human confirmation: output is a draft only.

It must contain a goal/non-goals section, input/output table, one success example, two failure examples, a security warning, self-check questions, and a source date. Exchange it with another reader, who should answer from the document alone: “Can the tool send email? When does it return an error? Can its output be executed directly?” If they cannot, keep revising.

## Common misconceptions

- **Writing only the happy path:** real maintenance cost is commonly in error and recovery paths.
- **Putting every detail in one table:** long steps and reasons lose hierarchy.
- **Using “obvious” or “simple” to skip prerequisites:** beginners cannot fill in implicit steps.
- **Equating Markdown sections with prompt security:** structured display cannot replace permission control.
- **Assuming more copied logs means stronger evidence:** retain necessary evidence and remove sensitive information and noise.
- **Assuming a source link stays accurate forever:** dynamic technology needs a recorded check date and applicable version.

## Self-check and mastery criteria

1. What makes a runbook executable rather than merely readable?
2. Why must placeholders define substitution rules?
3. Why are Markdown fences not security boundaries?
4. How should measured facts, official facts, engineering recommendations, and inferences be distinguished?
5. What problems do README files, runbooks, ADRs, experiment records, and tool contracts each solve?

- [ ] I can write goals, prerequisites, procedures, verification, and troubleshooting for a beginner.
- [ ] I can define inputs, outputs, failures, side effects, and approval boundaries.
- [ ] I can distinguish expected results from measured results in documentation.
- [ ] I can review active links, credentials, versions, and unverified items.

Previous: [[markdown/04-properties-callouts-and-reusable-notes|Properties, callouts, and reusable notes]].  
Next: [[markdown/06-integrated-writing-practice-and-mermaid-debugging|Integrated writing practice and Mermaid debugging]].

## References

Checked: **2026-07-14**.

- [Google Technical Writing One](https://developers.google.com/tech-writing/one)
- [Microsoft Writing Style Guide](https://learn.microsoft.com/style-guide/welcome/)
- [Obsidian Help Style Guide](https://obsidian.md/help/style-guide)
- [CommonMark Specification 0.31.2](https://spec.commonmark.org/0.31.2/)
