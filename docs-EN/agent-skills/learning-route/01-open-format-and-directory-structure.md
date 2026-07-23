---
title: "Agent Skills Open Format and Directory Structure"
aliases:
  - Agent Skill structure
tags:
  - agent-skills
  - open-format
source_checked: 2026-07-22
lang: en
translation_key: Agent Skills/学习路线/01-开放格式与目录结构.md
translation_source_hash: 9d4123b27610eb26bae153d4404aff71bbf2de13173e978c00f9dd8172d171a8
translation_route: zh-CN/Agent-Skills/学习路线/01-开放格式与目录结构
translation_default_route: zh-CN/Agent-Skills/学习路线/01-开放格式与目录结构
---

# Agent Skills Open Format and Directory Structure

## Goal

Distinguish specification requirements, recommended conventions, and client implementations, then design a minimal Skill directory.

## What a Skill solves

A normal prompt can say what to do this time, while real team work also depends on project conventions, repeatable steps, validation scripts, templates, and lessons from failure. Agent Skills package that material in a version-controlled folder so compatible clients can discover it and provide detailed guidance when appropriate.

An open format means different products can read the same basic structure. It does **not** mean their install locations, callable tools, authorization, conflict priority, sub-agent inheritance, or trigger probability are identical. Some hosts select Skills from their descriptions, some allow explicit selection, and some configurations preload the full body. Read the target client's official documentation and test before moving a Skill; see [[agent-skills/learning-route/00-positioning-client-differences-and-permission-boundaries|Positioning, Client Differences, and Permission Boundaries]].

Each Skill should cover one coherent capability boundary rather than packing an entire team handbook into one bundle. Extract it from stable practice, failure records, templates, and verifiable scripts in real projects. Split two tasks when their inputs, risks, or acceptance criteria are genuinely different. Source, license, version, and compatibility information are also part of the maintainability contract.

## Minimal and extended layout

```text
text-statistics/
├── SKILL.md          # Required: YAML frontmatter plus Markdown instructions
├── scripts/          # Optional: executable scripts
├── references/       # Optional: reference material loaded when needed
├── assets/           # Optional: templates, static assets, lookup tables
└── evals/            # Common evaluation folder used by the official authoring guidance
```

The minimum specification requirement is a `SKILL.md` file inside the Skill folder. `scripts/`, `references/`, and `assets/` are optional directories described by the specification. `evals/` is a working structure used by the official evaluation guidance; do not call it a required format field.

## Deciding where content belongs

- Put steps, boundaries, and important gotchas needed on every activation in `SKILL.md`.
- Put long explanations needed only for a particular error or subtask in `references/`, and state in `SKILL.md` exactly when to read each file.
- Put repeated calculations, format conversions, and deterministic validation in `scripts/` so the model does not reinvent code each time.
- Put long templates, example material, and static schemas in `assets/`.

Use paths relative to the Skill root and keep references about one level deep where practical. A chain in which documents repeatedly point to other documents makes it unclear when the agent should continue loading material and increases the risk of omissions.

## The boundary between specification and client

| Question | The open format defines | A particular client decides |
| --- | --- | --- |
| Required file | `SKILL.md` | Which directories it scans |
| Core metadata | `name` and `description` | How it matches and displays them |
| Instructions and resources | Markdown body and optional directories | Which tools read or execute them |
| Permissions | `allowed-tools` is experimental; `compatibility` can only describe environment needs | Whether it is supported, how a user is confirmed, and how identity and scope are verified |
| Triggering | `description` is important discovery information | Actual matching by the model and harness |

## Common misconceptions

- Calling every long document a Skill: without a clear task, trigger, and executable workflow, its value is limited.
- Presenting a product-specific installation command as part of the open specification: identify the client, version, and retrieval date.
- Putting all knowledge in `SKILL.md`: all of it enters context on activation and can distract from the work.
- Creating many directories without saying when to read them: a resource's presence does not ensure correct use, and certainly does not make its content trustworthy.
- Treating a Skill as authorization: it can shape the context for choosing a tool, but cannot prove user consent, correct token scope, or business approval.

## Exercises and self-check

1. Design a folder for “review this repository's Python CLI.” List only its files and their purposes, then explain why the capability is coherent.
2. Decide where an API error-code table, a safety check required every time, an output-report template, and a deterministic schema validator belong.
3. Self-check: is `evals/` required by the specification? No. It is a working structure recommended in the official evaluation guidance.

## Next step

Continue with [[agent-skills/learning-route/02-skill-frontmatter-and-progressive-disclosure|SKILL.md Frontmatter and Progressive Disclosure]].

## References

- [Agent Skills Specification](https://agentskills.io/specification) — checked 2026-07-22.
- [GitHub Copilot: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) — a client implementation example; checked 2026-07-22.
