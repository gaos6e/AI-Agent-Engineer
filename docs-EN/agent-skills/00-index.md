---
title: "Agent Skills Learning Path"
aliases:
  - Agent Skills Open Format
  - Agent Skills Course Index
tags:
  - ai-agent-engineer
  - agent-skills
  - learning-path
source_url: https://agentskills.io/llms.txt
source_path: /llms.txt
fetched_at: 2026-05-12T14:48:55+08:00
source_checked: 2026-07-22
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: CC-BY-4.0
ai_learning_stage: 5. Single-Agent Systems and Tools
ai_learning_order: 33
ai_learning_schema: 2
ai_learning_id: agent-skills
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3300
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 675
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 675
ai_learning_track_agent_platform_kind: optional
lang: en
translation_key: Agent Skills/00-目录.md
translation_source_hash: 1b2b7c5cbb0f0334b6af3349c76ad9bd36786c7b036f162aaf2521211942d76b
translation_route: zh-CN/Agent-Skills/00-目录
translation_default_route: zh-CN/Agent-Skills/00-目录
---

# Agent Skills

## Course overview

Agent Skills are an open format for giving an AI agent reusable specialist capabilities through a folder containing a `SKILL.md` file, scripts, and supporting resources. They package the procedural knowledge needed for a recurring class of work into something discoverable, selectively loaded, versioned, and testable. This course first establishes the boundaries between the format, clients, and authorization; it then covers triggering, progressive disclosure, safety, and evaluation. The eight pre-existing official materials remain available as an upstream-reference layer.

> [!info] Source and scope
> The official documentation index is [agentskills.io/llms.txt](https://agentskills.io/llms.txt); the specification and authoring guidance were checked on 2026-07-22. `name` and `description` remain required. `license`, `compatibility`, and `metadata` are optional, while `allowed-tools` is still explicitly experimental. Install locations, trigger behavior, tool authorization, and confirmation prompts remain client-specific. Do not mistake one product's behavior for a universal guarantee. In particular, the presence or loading of a Skill, or the `allowed-tools` field, does not constitute user authorization, identity verification, or evidence that a script is safe.
>
> The licensing boundary was rechecked on 2026-07-20: the upstream repository code uses Apache-2.0, while its `docs/` directory and website documentation use **CC BY 4.0**. They are not interchangeable. Before public release, every upstream-reference page must retain Agent Skills attribution, its original link, and a notice of Chinese translation, editorial organization, and formatting changes. If those fields are absent, publish only a source-link page. An example Skill that independently declares CC0-1.0 follows its own declaration.

## Where this course fits

This course belongs to the “Single-Agent Systems and Tools” stage. After learning the task loop in [[agent-core/00-index|Agent Core]] and the action contract in [[tool-calling-function-calling/00-index|Tool Calling]], you can package stable workflows as Skills. When external tools or data are involved, pair them with [[mcp/00-index|MCP]]. A Skill does not replace Tool Calling, MCP, or an authorization system: it supplies workflow context, while effective permission is enforced by the host, tool service, and business system. This is a capability dependency after choosing this branch, not a requirement that every role finish every linked course; if you have no reusable workflow, you can defer Agent Skills.

## Learning objectives

- Explain the boundary between the open format and a particular agent client.
- Distinguish Skills, persistent instructions, Tool Calling, MCP, and effective authorization.
- Create a specification-aligned folder and `SKILL.md` YAML frontmatter.
- Control context cost with the metadata → instructions → resources layers of progressive disclosure.
- Write a `description` that covers genuine intent without over-triggering.
- Design non-interactive, safe-by-default scripts with structured output, and organize references and assets only when needed.
- Establish source, version, diff-review, and isolated-trial boundaries for third-party Skills and updates.
- Improve quality with format validation, trigger tests, with/without-Skill baselines, and observable assertions.

## Prerequisites

- Read and write Markdown and simple YAML frontmatter.
- Run Python 3 scripts in PowerShell 7 and inspect exit codes.
- Understand an agent context window, Tool Calling, and least privilege.
- No prior knowledge of a specific client is required; read that client's current official documentation before installing anything.

## Recommended sequence

1. [[agent-skills/learning-route/00-positioning-client-differences-and-permission-boundaries|Positioning, Client Differences, and Permission Boundaries]] — establish the responsibility boundary between the format, tool protocols, and authorization.
2. [[agent-skills/learning-route/01-open-format-and-directory-structure|Open Format and Directory Structure]] — separate the specification core from each client's implementation choices.
3. [[agent-skills/learning-route/02-skill-frontmatter-and-progressive-disclosure|SKILL.md Frontmatter and Progressive Disclosure]] — write accurate frontmatter and split context on demand.
4. [[agent-skills/learning-route/03-trigger-descriptions-and-scope-boundaries|Trigger Descriptions and Scope Boundaries]] — calibrate a `description` with realistic positive and negative cases.
5. [[agent-skills/learning-route/04-scripts-resources-and-safety|Scripts, Resources, and Safety]] — design executable resources, supply-chain review, and least-privilege boundaries.
6. [[agent-skills/learning-route/05-testing-evaluation-and-iteration|Testing, Evaluation, and Iteration]] — compare against a baseline and improve from evidence.
7. [[agent-skills/learning-route/06-project-create-and-validate-an-agent-skill|Project: Create and Validate an Agent Skill]] — run a complete, offline example.

## Hands-on entry points

- Main project: [[agent-skills/learning-route/06-project-create-and-validate-an-agent-skill|Create and validate the text-statistics Skill]].
- Trigger exercise: write eight to ten realistic positive requests and the same number of negative requests for your own Skill. Prefer nearby tasks that are easy to trigger by mistake, then reserve a separate validation set.
- Evaluation exercise: write an assertion for one mechanically verifiable outcome, and compare it with the baseline where the Skill is not loaded.

## Mastery checklist

- [ ] I can create a valid folder with `SKILL.md` from scratch and explain why `name` must match its parent directory.
- [ ] I can explain how a target client discovers, selects, or preloads Skills without treating progressive disclosure as a guarantee for every host.
- [ ] I can write a `description` that says both what the Skill does and when to use it, then test its boundary with near-miss negative cases.
- [ ] I can review a script's network, file, command, credential, and output boundaries, and review a third-party Skill's source, revision, and update diff.
- [ ] I can explain why a Skill, `allowed-tools`, and an MCP resource do not prove user intent or authorization.
- [ ] I can run the local example validator and scripts, and understand both their coverage and their limits.
- [ ] I can use a with-Skill/without-Skill baseline, concrete assertions, and human review to decide whether to revise a Skill.

## Relationships to other courses

- [[prompt-engineering/00-index|Prompt Engineering]] focuses on one-off or templated instructions. A Skill packages a stable workflow, scripts, and reference material, and is selected through its description.
- [[context-engineering/00-index|Context Engineering]] explains why information should load only when needed; progressive disclosure is a concrete engineering application.
- [[tool-calling-function-calling/00-index|Tool Calling]] defines the parameter, result, and error contract for one action. A Skill provides the workflow context for when to call it, how to verify it, and when to stop.
- [[mcp/00-index|MCP]] exposes tools, resources, and prompts. A Skill can teach an agent when and how to use them safely, but grants no access and does not replace server-side validation.
- [[evaluation-framework/00-index|Evaluation Framework]] supplies broader methods for experimental design, metrics, and error analysis once its full course is available.

## Primary references

All sources below are first-party materials, retrieved or checked on 2026-07-22:

- [Agent Skills Specification](https://agentskills.io/specification)
- [Agent Skills repository](https://github.com/agentskills/agentskills)
- [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices)
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts)
- [GitHub Copilot: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) — used to illustrate client differences.
- [GitHub Copilot: Adding agent skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) — used to illustrate directory and pre-approved-tool boundaries.

## Official-documentation reference layer

The files below are pre-existing Chinese editorial versions of official documentation. Their body text, provenance data, and layer status are intentionally retained. Their client lists and product-specific operations represent a captured snapshot only: current installation instructions, commands, permissions, and support must be checked against the target client's official documentation and local verification. The learning route above adds the operational boundary around that reference layer.

### 01 — Overview

- [[agent-skills/upstream-references/overview/agent-skills-overview|Agent Skills Overview]] — the format's concept, value, and working model.
- [[agent-skills/upstream-references/overview/specification|Specification]] — folders, frontmatter, resources, and validation rules.
- [[agent-skills/upstream-references/overview/client-showcase|Client Showcase]] — clients in the ecosystem; support status changes over time.

### 02 — Skill authors

- [[agent-skills/upstream-references/skill-authors/quickstart|Quickstart]] — build the smallest first Skill.
- [[agent-skills/upstream-references/skill-authors/best-practices|Best practices]] — derive workflows from real practice while controlling context.
- [[agent-skills/upstream-references/skill-authors/optimizing-descriptions|Optimizing descriptions]] — improve should-trigger and should-not-trigger behavior.
- [[agent-skills/upstream-references/skill-authors/evaluating-skills|Evaluating skills]] — design tests, assertions, baselines, and iterations.
- [[agent-skills/upstream-references/skill-authors/using-scripts|Using scripts]] — write agent-friendly script interfaces.
