---
title: "SKILL.md Frontmatter and Progressive Disclosure"
aliases:
  - SKILL.md frontmatter
tags:
  - agent-skills
  - context-engineering
source_checked: 2026-07-22
lang: en
translation_key: Agent Skills/学习路线/02-SKILL前置元数据与渐进披露.md
translation_source_hash: 0635256b1fd311f8f6d4a59430b5489107e63f977847df73c482abef16a7356b
translation_route: zh-CN/Agent-Skills/学习路线/02-SKILL前置元数据与渐进披露
translation_default_route: zh-CN/Agent-Skills/学习路线/02-SKILL前置元数据与渐进披露
---

# SKILL.md Frontmatter and Progressive Disclosure

## Goal

Write valid frontmatter and explain why metadata, full instructions, and resources load in three different layers.

## Two parts of the file

`SKILL.md` consists of YAML frontmatter between the first two `---` delimiters and the Markdown body that follows:

```markdown
--- # Start of YAML frontmatter: the client reads this small metadata block first to decide whether to load the Skill
name: text-statistics # A stable lowercase-hyphen name, normally identical to the Skill directory name
description: "Count words, characters, and lines. Use when a user needs deterministic text-size statistics." # States capability, trigger signals, and output boundary to reduce over-triggering
compatibility: "Requires Python 3; no network access." # Describes required host environment and the no-network constraint
--- # End of YAML frontmatter: the body can be read only when needed

# Text Statistics <!-- The task title visible after a user or agent opens the Skill -->

Follow the workflow below... <!-- The body holds working steps instead of putting long instructions in the always-visible description -->
```

YAML is not arbitrary `key: value` text. Quote values that contain colons or other special syntax, or use an appropriate YAML multiline form. Validate it with a real parser or the official validator.

Do not use this course's simplified parser to prove arbitrary YAML valid. Anchors, multiline blocks, escapes, booleans, and nested structures may fall outside its support. Before publication, run the official `skills-ref validate` and then test discovery, activation, and resource loading in the target client.

## Field constraints

According to the official specification checked on 2026-07-22:

- `name` is required and has 1–64 characters. The specification describes its allowed characters as lowercase alphanumerics (examples show `a-z` and `0-9`) plus hyphens. For cross-client portability, this course's example and validator use the explicit ASCII subset `[a-z0-9-]`. It cannot begin or end with a hyphen, cannot have two consecutive hyphens, and must match its parent directory.
- `description` is required and has 1–1024 characters. It states both what the Skill does and when to use it, including concrete discovery keywords.
- `license` is optional and gives a license name or refers to a license file in the package.
- `compatibility` is optional and has 1–500 characters. Use it only when there are environment requirements such as products, system packages, or network access.
- `metadata` is optional and maps string keys to string values. Avoid keys likely to collide with other implementations.
- `allowed-tools` is optional and remains experimental. Support differs across implementations and it cannot serve as a general security guarantee.

## Three layers of progressive disclosure

1. **Discovery layer** — Implementations of progressive disclosure commonly first provide each Skill's `name` and `description`, at the cost of only a small amount of metadata per item.
2. **Activation layer** — On a task match, those implementations load the complete `SKILL.md` body. Official guidance recommends keeping the main file under 500 lines and treating fewer than roughly 5,000 tokens as a context-economy target. This is engineering guidance, not a specification claim that a longer file is incompatible.
3. **Resource layer** — Scripts, `references`, and `assets` should be read or executed only when the instructions explicitly require them.

For a host that uses this loading model, `description` determines whether a Skill can be discovered, the body determines how to work after activation, and resources hold conditional detail. Putting a long API reference in the body makes every activation pay the context cost; leaving only a path in a directory leaves the agent unsure when to read it. If a target client preloads Skills for a custom agent or permits explicit invocation, measure its real loading path rather than treating the three-layer model as a universal runtime guarantee.

## Splitting example

For a Skill that handles payment-API errors:

- Keep the standard workflow, retry boundary, and “never log the token” gotcha in `SKILL.md`.
- Store error-code detail in `references/api-errors.md` and state “read this only when the response is non-2xx.”
- Use `scripts/validate_payload.py` for deterministic schema validation.
- Store the final audit-report template in `assets/report-template.md`.

Any safety restriction that must be known before execution belongs in `SKILL.md`, not in a reference that might never be read.

## Exercises and self-check

1. Identify the invalid names: `PDF-tools`, `-pdf`, `pdf--tools`, and `pdf-tools`. Only the last is valid, and it must still match the directory name.
2. Split a 700-line error-code document into a body and a reference, then write one exact condition for loading the reference.
3. Self-check: why does `allowed-tools` not prove a script is safe or user-authorized? The field is experimental, and client support, actual script behavior, identity scope, user intent, and confirmation policy require independent verification.

## Next step

Continue with [[agent-skills/learning-route/03-trigger-descriptions-and-scope-boundaries|Trigger Descriptions and Scope Boundaries]].

## References

- [Agent Skills Specification](https://agentskills.io/specification) — checked 2026-07-22.
- [Adding skills support: progressive disclosure](https://agentskills.io/client-implementation/adding-skills-support) — checked 2026-07-22; used to explain client-side three-layer loading, not as this tree's upstream translation.
- [GitHub Copilot SDK: Custom skills](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/skills) — a client-specific preloading example; checked 2026-07-22.
