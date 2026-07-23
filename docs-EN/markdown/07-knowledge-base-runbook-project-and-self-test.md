---
title: "Knowledge-Base Runbook Project and Self-Test"
tags:
  - ai-agent-engineer
  - markdown
  - integrated-practice
aliases:
  - Markdown integrated project
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/07-知识库运行手册项目与自测.md"
translation_source_hash: 86d29f8e5300775fddc93ee19688a1645c1a65da39c7a15ce801c7c4fdfb4bf9
translation_route: zh-CN/Markdown/07-知识库运行手册项目与自测
translation_default_route: zh-CN/Markdown/07-知识库运行手册项目与自测
---

# Knowledge-Base Runbook Project and Self-Test

## Project goal

Write a runbook for a fictional “local meeting-summary script.” The project assesses document quality only; it does not require you to create or run a script. A reader should be able to judge the environment, procedure, expected result, failure handling, and safety boundaries from scratch. Work independently first, then view the [[markdown/examples/meeting-summary-runbook-reference-answer|reference answer]]. Commands in the reference answer are teaching scenarios too; they do not imply a corresponding script exists in the repository.

## Task scenario and deliverable

- Scenario: the script reads only local UTF-8 meeting text and a local `config.json`, then writes a local Markdown summary draft. It does not access the network or send messages.
- Deliverable: one note named `meeting-summary-runbook.md`. Do not write the exercise file into this knowledge base's formal course directory.
- Audience: a beginner who can open PowerShell but does not understand Python projects.
- Evidence boundary: you may write “expected output,” but must not label an unrun command “verified passing.”
- Safety boundary: use only fictional meeting content and placeholder paths; do not use real recordings, client information, or credentials.

## Required structure

### Metadata

Frontmatter contains at least `title`, `tags`, and `aliases`. Put only searchable metadata in Properties and place detailed explanation in the body.

### Overview and boundaries

State that the script transforms local fictional meeting text into a summary draft; it does not connect to a real meeting system, send automatically, or read real credentials.

### Prerequisites

List Windows 11, PowerShell 7, and Python 3, including commands that verify them. Do not promise a particular version that has not been checked.

### Procedure

Number commands in order. For each section, state purpose, current directory, command, expected output, and a stop condition on failure. Use different language fences for commands and output.

### Input/output contract

Use a table for filename, format, required content, sensitivity level, and retention policy. Define at least `meeting.txt`, `config.json`, and `summary.md`, and give a fully fictional minimal input, configuration, and expected output.

### Acceptance and troubleshooting

Include at least four failures: missing file, encoding error, JSON syntax error, and empty output. For each, state an observable symptom, diagnostic command, and safe recovery.

### Mermaid flowchart

Draw “read → validate → summarize → human confirmation → end.” Clearly state that there are no external side effects before human confirmation.

### Sources and change record

Use standard links for external materials and record their retrieval date. The change record states what changed and what was verified; do not write an unprovable “fully usable.”

## Quality check

| Dimension | Failing | Passing |
| --- | --- | --- |
| Structure | stacked headings with no order | reader can locate the task by hierarchy |
| Commands | no directory or expectation | commands, output, and placeholders are clearly separate |
| Links | ambiguous or broken | internal paths are clear and external links have descriptions |
| Evidence | expectations written as measurements | executed and unexecuted work are clearly distinct |
| Safety | examples include real data or credentials | only fictional data and explicit dangerous boundaries |
| Rendering | fences and diagram not checked | both editor and Reading View are reviewed |

## Real-task acceptance

Ask a reader with no background to answer these questions using only the runbook:

1. From which directory do I run it?
2. How do I confirm that Python is available?
3. What does the input contain, and which data is prohibited?
4. What result counts as success?
5. Which errors require stopping?
6. Will the output be sent automatically?

If the reader needs the author to explain verbally, the runbook is still missing information. Record their questions as document-test results, then revise.

## Scoring rules

The total is 20 points, with each item worth 0–2:

1. audience, goal, and non-goals are clear;
2. prerequisites include verification commands;
3. every step states working directory, command, and stop condition;
4. input/output contract is checkable;
5. expected result and actual verification are separate;
6. all four failure types have observable symptoms and safe recovery;
7. internal links target real full paths and external links have descriptions;
8. Mermaid expresses only the key control flow;
9. there is no real sensitive information or destructive command;
10. sources date, changes, and unverified items are recorded.

Completion requires at least 16 points and no safety item scored 0. If another reader still needs verbal supplementation, the maximum score is 15.

## Knowledge-base self-test

1. How are Markdown and a renderer related?
2. Why must CommonMark, GFM, and Obsidian extensions not be conflated?
3. Why is heading hierarchy more important than font size?
4. How do you choose between fenced code and inline code?
5. How do you avoid link ambiguity when internal files share a name?
6. Why should an external URL not use a wikilink?
7. When is a table worse than a list?
8. What kind of relationship is Mermaid suitable for expressing?
9. How does a document distinguish expected output from actual verification?
10. Why does documentation need a safety review too?

## Mastery check

- [ ] I completed one runbook with metadata, procedures, a table, code fences, links, and Mermaid.
- [ ] Every internal link resolves to a real file and every external link has descriptive text.
- [ ] I checked layout in Obsidian Editor View and Reading View.
- [ ] Another reader completed a paper walkthrough using the runbook.
- [ ] I recorded unverified items and did not present sample output as measured evidence.
- [ ] The document contains no real credential, sensitive data, or unsafe bulk-delete command.

Previous: [[markdown/06-integrated-writing-practice-and-mermaid-debugging|Integrated writing practice and Mermaid debugging]].  
After finishing, compare item by item with the [[markdown/examples/meeting-summary-runbook-reference-answer|reference answer]], then return to the [[markdown/00-index|Markdown index]].

## References

Retrieved: **2026-07-14**.

- [CommonMark Specification 0.31.2](https://spec.commonmark.org/0.31.2/)
- [GitHub Flavored Markdown Specification](https://github.github.com/gfm/)
- [Obsidian Help](https://obsidian.md/help/)
- [Mermaid documentation](https://mermaid.js.org/intro/)
