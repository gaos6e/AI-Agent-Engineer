---
title: "Git Learning Path"
aliases:
  - Git learning path
  - Git Cheat Sheet
  - Quick Reference for Common Git Commands
source: https://git-scm.com/cheat-sheet
source_pdf: https://git-scm.com/cheat-sheet.pdf
source_install_windows: https://git-scm.com/install/windows
retrieved: 2026-07-14
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
tested_environment:
  - Windows 11
  - PowerShell 7
  - Git 2.54.0.windows.1
tags:
  - git
  - version-control
  - cheat-sheet
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 7
ai_learning_schema: 2
ai_learning_id: git
ai_learning_domain: foundations
ai_learning_catalog_order: 700
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 60
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 60
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 60
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 60
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: Git/00-目录.md
translation_source_hash: 12ba14eb0ea812d75c46c9f19ef8eb08ec248f52de074efd05b65a8968e28975
translation_route: zh-CN/Git/00-目录
translation_default_route: zh-CN/Git/00-目录
---

# Git

## About this knowledge base

This directory is organized from the official Git cheat sheet and adds local installation guidance, usage scenarios for each command category, common risks, and more modern alternatives. Commands remain in English; the explanations are localized.

Git is a distributed version-control system. Alongside the existing command tutorials, this knowledge base provides an AI Agent Engineer learning route from zero: first build a mental model of snapshots, objects, and references; then understand the working tree, staging area, and `HEAD`; then learn branches, diffs, recovery, and remote collaboration; finally complete a project in an isolated experimental repository. Do not run cleanup, hard resets, history rewrites, or force pushes in a real working tree until you understand their impact.

> [!info] Sources
> Original page: [Git Cheat Sheet](https://git-scm.com/cheat-sheet); PDF: [cheat-sheet.pdf](https://git-scm.com/cheat-sheet.pdf); Windows installation page: [Installing Git](https://git-scm.com/install/windows).

> [!important] Command placeholders
> `<path>`, `<commit>`, `<branch>`, and `<url>` in headings or inline commands mean “replace this with a real value”; do not type the angle brackets literally into PowerShell. To prevent accidental copy/paste, this course’s PowerShell blocks use parseable examples such as `README.md`, `HEAD~1`, and `feature/demo`. A path argument prefixed with `--` makes the end of options explicit.

## Where this course fits in the overall route

This course is in the Engineering Foundations stage. It builds on Markdown and command-line basics, providing reviewable and recoverable change history for later Python projects, Agent tools, evaluation assets, and production configuration. Git tracks versions only; it does not replace tests, artifact storage, secret management, or deployment approval.

## Learning objectives

- Explain the relationship among a working tree, staging area, commits, and branches.
- Inspect status, diffs, untracked files, and sensitive-information risk before a commit.
- Use branches to isolate Agent code, prompts, configuration, and evaluation changes.
- Choose among `restore`, `revert`, `reset`, and `reflog` recovery approaches.
- Synchronize remote repositories safely and understand the risk of rewriting shared history.
- Complete an isolated-repository practice from initialization through conflict resolution, rollback, and review.

## Prerequisites

The primary environment is Windows 11 with PowerShell 7. You only need to know how to change directories and edit text. It is recommended to complete [[markdown/00-index|Markdown]] first; installation and identity configuration begin in lesson 1.

## Recommended order

- [[git/01-install-git-on-windows|01 Install Git Locally]] — installation, verification, and minimum identity configuration.
- [[git/02-getting-started-and-creating-a-repository|02 Getting Started and Creating a Repository]] — recognize repositories and initialize or clone safely.
- [[git/02a-git-state-model-and-commit-graph|02A Git State Model and Commit Graph]] — build a model of snapshots, objects, index, `HEAD`, references, and commit graph.
- [[git/03-staging-area-and-file-operations|03 Staging Area and File Operations]] — choose precisely what belongs in a commit.
- [[git/04-commits-and-pre-commit-checks|04 Commits and Pre-Commit Checks]] — build reviewable commit habits.
- [[git/05-switching-and-managing-branches|05 Switching and Managing Branches]] — use references to isolate lines of task work.
- [[git/05a-branch-merging-and-conflict-resolution|05A Branch Merging and Conflict Resolution]] — understand fast-forward, three-way merge, conflict resolution, and safe abort.
- [[git/06-diffing-and-commit-references|06 Diffing and Commit References]] — use evidence to understand actual changes.
- [[git/07-undoing-and-cleaning-up|07 Undoing and Cleaning Up]] — determine state before selecting a recovery command.
- [[git/08-history-rewriting-and-failure-recovery|08 History Rewriting and Failure Recovery]] — use only after understanding shared history.
- [[git/09-history-tracing-and-code-archaeology|09 History Tracing and Code Archaeology]] — locate the commit that introduced a line or behavior.
- [[git/10-remote-repository-synchronization|10 Remote Repository Synchronization]] — understand fetch, pull, push, and conflict.
- [[git/10a-remote-collaboration-and-offline-two-clone-lab|10A Remote Collaboration and Offline Two-Clone Lab]] — distinguish remote references and simulate two collaborators offline.
- [[git/11-git-configuration-and-key-files|11 Git Configuration and Key Files]] — manage configuration, ignores, and key repository files.
- [[git/12-version-control-practice-and-self-check|12 Version-Control Practice and Self-Check]] — finish the integrated task in an isolated experimental repository.

## Quick entry points

- Git is not installed locally: [[git/01-install-git-on-windows|Install Git Locally]].
- Creating or obtaining a repository: [[git/02-getting-started-and-creating-a-repository|Getting Started and Creating a Repository]].
- Commands are all blending together: [[git/02a-git-state-model-and-commit-graph|Git State Model and Commit Graph]].
- Preparing a commit: [[git/03-staging-area-and-file-operations|Staging Area and File Operations]], then [[git/04-commits-and-pre-commit-checks|Commits and Pre-Commit Checks]].
- Branch work: [[git/05-switching-and-managing-branches|Switching and Managing Branches]].
- Merge and conflict: [[git/05a-branch-merging-and-conflict-resolution|Branch Merging and Conflict Resolution]].
- Inspecting changes: [[git/06-diffing-and-commit-references|Diffing and Commit References]].
- Undo or cleanup: [[git/07-undoing-and-cleaning-up|Undoing and Cleaning Up]] for high-risk-command guidance.
- Altering commit history: [[git/08-history-rewriting-and-failure-recovery|History Rewriting and Failure Recovery]], only after understanding the impact.
- Tracking history and finding responsible lines: [[git/09-history-tracing-and-code-archaeology|History Tracing and Code Archaeology]].
- Syncing a remote: [[git/10-remote-repository-synchronization|Remote Repository Synchronization]].
- Practicing remote collaboration without an account: [[git/10a-remote-collaboration-and-offline-two-clone-lab|Remote Collaboration and Offline Two-Clone Lab]].
- User name, aliases, and ignored files: [[git/11-git-configuration-and-key-files|Git Configuration and Key Files]].

## Hands-on work and project entry

See [[git/12-version-control-practice-and-self-check|Version-Control Practice and Self-Check]] for the integrated task. All destructive exercises belong in a newly created isolated experimental repository. Preserve evidence with `git status`, `git diff`, and `git log` before executing a recovery command.

## Mastery checklist

- [ ] Can draw the working-tree → staging-area → commit flow and verify it with commands.
- [ ] Before every commit, inspect staged and unstaged diffs, untracked files, and credential risk.
- [ ] Can create a branch, create and resolve a text conflict, and explain the resulting content.
- [ ] Can distinguish undoing uncommitted changes, creating an inverse commit, and moving a branch pointer.
- [ ] Can recover a locally unreachable commit with `reflog`.
- [ ] Do not casually rewrite shared branches; when force pushing is necessary, first understand and prefer `--force-with-lease`.
- [ ] Can explain why `.gitignore` cannot protect credentials that have already entered history.

## Relationship to other knowledge bases

| Next knowledge base | Connection |
| --- | --- |
| [[markdown/00-index\|Markdown]] | Documentation and prompts are textual assets with readable diffs. |
| [[python-fundamentals/00-index\|Python Fundamentals]] | Source code, tests, and dependency declarations should form reproducible commits. |
| [[linux-commands/00-index\|Linux Commands]] | Server-side Git operations rely on reliable command-line and path judgment. |
| [[mlops/00-index\|MLOps]], [[llmops/00-index\|LLMOps]] | Git records code version; data, models, prompts, evaluation, and deployment need additional tracking. |
| [[agent-skills/00-index\|Agent Skills]], [[mcp/00-index\|MCP]] | Tool contracts and configuration changes should be reviewable and reversible. |

## Primary references

Checked **2026-07-14**. The current official stable-documentation baseline was Git 2.55.0; this machine’s available syntax was checked under Windows 11, PowerShell 7, and `git version 2.54.0.windows.1`. They are recorded separately: a local version is not a global latest version. Options evolve by Git version; before execution, use a focused command such as `git help status` to consult local documentation.

- [Git Reference](https://git-scm.com/docs)
- [Pro Git](https://git-scm.com/book/en/v2)
- [Git Glossary](https://git-scm.com/docs/gitglossary)
- [Git Cheat Sheet](https://git-scm.com/cheat-sheet)
- [Git User Manual](https://git-scm.com/docs/user-manual)
- [Git for Windows installation page](https://git-scm.com/install/windows)
