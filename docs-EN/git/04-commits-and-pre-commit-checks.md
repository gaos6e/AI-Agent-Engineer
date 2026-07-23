---
title: "Git Cheat Sheet: Commits and Pre-Commit Checks"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - commit
lang: en
translation_key: Git/04-提交与提交前检查.md
translation_source_hash: f98539d475333f8490d18682d8c0e3d827377e5d5e76149731e4724d56fb2341
translation_route: zh-CN/Git/04-提交与提交前检查
translation_default_route: zh-CN/Git/04-提交与提交前检查
---

# Commits and Pre-Commit Checks

A commit writes the directory tree selected by the staging area as a new snapshot and records its parent, author, time, and message. It is not “saving the whole working tree.” See [[git/02a-git-state-model-and-commit-graph|Git State Model and Commit Graph]] for the full structure. A good commit has clear scope, a readable message, and no unrelated files.

## `git commit`

```powershell
git commit
```

Purpose: create a commit and open the default editor for its message.

Appropriate when:

- the explanation is long enough to need a subject and body;
- a team expects a message to explain context, risk, or verification.

Suggested messages:

- Put a short subject on the first line, such as `fix: handle empty config path`.
- If needed, add a blank line, then explain reason, impact, and verification.

## `git commit -m "message"`

```powershell
git commit -m "message"
```

Purpose: create a commit with an inline command-line message.

Appropriate when:

- the change is small or its explanation short;
- an automation script or quick local snapshot needs a message.

Example:

```powershell
git commit -m "docs: add git cheat sheet notes"
```

Notes:

- In Windows PowerShell, both single and double quotes express strings, but a double-quoted message interpolates PowerShell variables or escape sequences.
- Still inspect `git diff --staged` before committing; do not rely only on the commit message.

## `git commit -am "message"`

```powershell
git commit -am "message"
```

Purpose: stage modifications to all tracked files, then commit.

Appropriate when:

- every modification is to an already tracked file;
- no new file is involved.

Limits:

- It does not automatically include untracked new files.
- It can combine unrelated modifications across tracked files. Before running it, inspect:

```powershell
git status --short
git diff
```

## Pre-commit check flow

A recommended minimum flow:

```powershell
git status --short
git diff
git add -- README.md
git diff --staged
git commit -m "type: short message"
```

- `git status --short` quickly confirms the change list.
- `git diff` shows unstaged content.
- `git diff --staged` shows what will enter the commit.
- If the project provides tests, lint, or formatting commands, run the relevant validation before committing.

## Correct a message or add a missed file

If you immediately find a wrong message or missed staging a file, use:

```powershell
git commit --amend
```

See [[git/08-history-rewriting-and-failure-recovery|History Rewriting and Failure Recovery]] for details. If others already use the commit, be cautious before altering history.

## Completion check

- Every line in `git diff --staged` belongs to one clear intent.
- `git status --short` has no unexpected credentials, caches, lock files, or large files.
- After committing, `git show --stat --oneline HEAD` explains what the snapshot did.
- Required project tests, lint, or document checks actually ran and their results were recorded honestly.
