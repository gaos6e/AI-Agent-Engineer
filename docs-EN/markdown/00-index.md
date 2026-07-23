---
title: "Markdown"
tags:
  - ai-agent-engineer
  - engineering-foundations
  - markdown
aliases:
  - Markdown learning path
  - Introduction to writing in Obsidian
ai_learning_stage: "1. Engineering foundations"
ai_learning_order: 6
ai_learning_schema: 2
ai_learning_id: markdown
ai_learning_domain: foundations
ai_learning_catalog_order: 600
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 50
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 50
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 50
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 50
ai_learning_track_multimodal_realtime_kind: recommended
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/00-目录.md"
translation_source_hash: e6694456d18452745c02250a106aef7a82b4ab7c4c7bde5edefd1ca58f01cb7b
translation_route: zh-CN/Markdown/00-目录
translation_default_route: zh-CN/Markdown/00-目录
---

# Markdown

## About this knowledge base

Markdown is a lightweight markup format for expressing headings, paragraphs, lists, links, code, and tables in plain text. AI Agent Engineer uses it to maintain README files, runbooks, tool contracts, prompt documentation, experiment records, and Obsidian knowledge bases. The real goal is not memorizing symbols. It is writing engineering documents whose source is readable, whose target host renders predictably, whose links remain maintainable, whose steps are executable, and whose evidence boundaries are clear.

This knowledge base separates a seven-lesson core path from three reference materials. [[markdown/markdown-tutorial|The Complete Markdown Tutorial]] and [[markdown/mermaid-tutorial|The Complete Mermaid Tutorial]] are retained as large reference layers. Follow the short lessons first, then look up the section that answers a concrete problem. Dynamic-version facts and compatibility notes for the larger tutorials are collected in [[markdown/references-versions-and-compatibility|References, versions, and compatibility notes]].

## Place in the overall path

This knowledge base belongs to the Engineering Foundations domain. Across the four role tracks, it commonly follows JSON and leads into [[git/00-index|Git]]. Later prompt-engineering, RAG, Agent, evaluation, and production courses reuse the writing habits for structure, links, evidence, and safety established here, but the complete Markdown course is not a hard prerequisite.

## Learning objectives

- Use headings, paragraphs, lists, quotations, tables, links, images, and nested code fences.
- Explain line breaks, indentation, fences, and compatibility differences through the chain “source text → parser → host rendering.”
- Distinguish CommonMark 0.31.2, GFM 0.29-gfm, Obsidian extensions, and platform features.
- Use full-path wikilinks, heading and block links, embeds, and the adjacent-attachment convention.
- Design Properties with clear types, no duplicate keys, and no sensitive information.
- Use callouts and Mermaid to express necessary semantics without letting visual elements replace the prose contract.
- Write Agent-engineering documents that beginners can execute and review, distinguishing expectations, measured facts, recommendations, inferences, and unknowns.

## Prerequisites

You only need a text editor and folders; programming is not required. Observe Obsidian source mode alongside Live Preview or Reading View when possible. Command exercises use Windows 11 and PowerShell 7, but this course does not create virtual environments, install dependencies, or call external APIs.

## Recommended order

| Order | Lesson | Problem it solves |
| --: | --- | --- |
| 1 | [[markdown/01-markdown-basics-and-readable-source-files\|Markdown basics and readable source files]] | How does Markdown turn plain text into structure, and how can a document stay readable before rendering? |
| 2 | [[markdown/02-commonmark-gfm-and-obsidian-syntax-boundaries\|CommonMark, GFM, and Obsidian syntax boundaries]] | Which features are a portable core, GFM extensions, Obsidian-only syntax, or host behavior? |
| 3 | [[markdown/03-obsidian-links-attachments-and-embeds\|Obsidian links, attachments, and embeds]] | How do you avoid ambiguous same-name targets and maintain heading, block, and attachment embeds? |
| 4 | [[markdown/04-properties-callouts-and-reusable-notes\|Properties, callouts, and reusable notes]] | How do you design searchable metadata and semantically meaningful callout blocks? |
| 5 | [[markdown/05-structured-technical-writing-for-agent-engineering\|Structured technical writing for Agent engineering]] | How do README files, runbooks, experiment records, and tool contracts become executable and reviewable? |
| 6 | [[markdown/06-integrated-writing-practice-and-mermaid-debugging\|Integrated writing practice and Mermaid debugging]] | How do small tasks exercise structure, links, Properties, diagrams, and minimal debugging? |
| 7 | [[markdown/07-knowledge-base-runbook-project-and-self-test\|Knowledge-base runbook project and self-test]] | How do you deliver a complete runbook with a contract, failure paths, safety boundaries, and reader tests? |

Use the reference layer when needed:

- [[markdown/markdown-tutorial|The Complete Markdown Tutorial]]: 17 topics and a quick reference for looking up individual syntax.
- [[markdown/mermaid-tutorial|The Complete Mermaid Tutorial]]: many diagram types and project examples; read the compatibility notes first, then consult it as needed.
- [[markdown/references-versions-and-compatibility|References, versions, and compatibility notes]]: current version facts, primary sources, and host differences.

## Hands-on practice and project entry points

- Rendering, links, Properties, and Mermaid practice: [[markdown/06-integrated-writing-practice-and-mermaid-debugging|Integrated writing practice and Mermaid debugging]].
- A real link and embed target: [[markdown/examples/link-and-embed-practice-target|Link and embed practice target]].
- Complete delivery: [[markdown/07-knowledge-base-runbook-project-and-self-test|Knowledge-base runbook project and self-test]].
- Review after finishing the project: [[markdown/examples/meeting-summary-runbook-reference-answer|Meeting-summary runbook reference answer]].

For every exercise, inspect the source file first and Reading View second; both should be understandable. If another reader is unavailable, wait a day and do a paper walkthrough using only your own runbook, recording the information that is still missing.

## Mastery criteria

- [ ] I can organize a long document with heading levels, paragraphs, and lists instead of using bold text or spaces to manufacture structure.
- [ ] I can explain block and inline structure and repair line-break, indentation, and nested-fence problems.
- [ ] I can label common syntax as CommonMark, GFM, Obsidian, or platform-layer behavior.
- [ ] I can create unambiguous full-path note, heading, and block links, and embed a real target.
- [ ] I can write Properties with no duplicate keys, stable types, and no secrets.
- [ ] I can verify Mermaid in the current Obsidian Reading View and record host-version unknowns.
- [ ] I can write a runbook with a goal, contract, steps, failures, safety, validation, and sources.
- [ ] I can let another beginner answer “where do I start, when do I stop, and what counts as success?” using only the document.

## Relationship to other knowledge bases

| Knowledge base | Connection |
| --- | --- |
| [[git/00-index\|Git]] | Plain-text diffs, renames, conflicts, and review. |
| [[prompt-engineering/00-index\|Prompt Engineering]] and [[context-engineering/00-index\|Context Engineering]] | Use a clear hierarchy to distinguish tasks, data, examples, and output; do not treat fences as a security boundary. |
| MCP and [[agent-skills/00-index\|Agent Skills]] | Tool and skill documentation needs inputs, outputs, errors, side effects, approval, and versioning. |
| Evaluation and runtime-monitoring knowledge bases | Test plans, event records, and retrospectives need traceable evidence. |

## Acceptance record for this revision

Acceptance date: **2026-07-14**.

- Actual structure: 13 Markdown files: seven core-path lessons, three reference materials, two real exercise artifacts, and this index.
- All rendered internal links, heading fragments, block IDs, and one real embed were statically parsed with zero broken links; newly created or changed content has no ambiguous short link.
- All 137 top-level code fences are closed; all 62 Mermaid blocks have a recognizable diagram-type declaration.
- Eight PowerShell fences passed syntax parsing; Python, JSON, and JavaScript examples passed their respective static syntax checks.
- Twenty-nine unique external URLs returned HTTP 200 during acceptance; dynamic facts were also checked against primary documentation.
- 'git diff --check' passed, with no cache, virtual environment, large data, model artifact, or apparent real credential found.
- Obsidian Reading View was not manually verified, and Mermaid CLI was not used. The final UI behavior of callouts, Properties, real block embeds, and Mermaid should still be spot-checked in the current Obsidian version.

## Primary references

Checked: **2026-07-14**. Dynamic versions and corrections are detailed in [[markdown/references-versions-and-compatibility|References, versions, and compatibility notes]].

- [CommonMark Specification 0.31.2](https://spec.commonmark.org/0.31.2/)
- [GitHub Flavored Markdown Specification 0.29-gfm](https://github.github.com/gfm/)
- [Obsidian Flavored Markdown](https://obsidian.md/help/obsidian-flavored-markdown)
- [Obsidian: Internal links](https://obsidian.md/help/links)
- [Obsidian: Properties](https://obsidian.md/help/properties)
- [Mermaid documentation](https://mermaid.js.org/intro/)

**May change:** extensions supported by different renderers vary. Recheck the concrete behavior of Mermaid, Properties, and Obsidian in the target version. This revision completed static checks of files, frontmatter, fences, and internal links; a manual Obsidian Reading View check can only be marked complete after it has actually been performed.
