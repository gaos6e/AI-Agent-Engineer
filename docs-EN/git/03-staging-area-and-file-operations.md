---
title: "Git Cheat Sheet: Staging Area and File Operations"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - staging
lang: en
translation_key: Git/03-暂存区与文件操作.md
translation_source_hash: 14e5db5c797259e664f0caf0c539d6613ad3d22843b6297a06a012815d10a8cf
translation_route: zh-CN/Git/03-暂存区与文件操作
translation_default_route: zh-CN/Git/03-暂存区与文件操作
---

# Staging Area and File Operations

A Git commit does not write every change directly into history. First place the intended content in the staging area. Treat it as the candidate manifest for the next commit.

## `git add <file>`

```powershell
git add -- README.md
```

Purpose: add new contents of the specified file to the staging area. It can add a new file or stage modifications to a tracked file.

Appropriate when:

- you want to commit one file rather than every change;
- you want to split one piece of work into several commits and stage only related files each time.

Examples:

```powershell
git add README.md
git add src/app.py
```

Inspect:

```powershell
git status
git diff --staged
```

## `git add .`

```powershell
git add .
```

Purpose: stage additions, modifications, and deletions in the path scope of `.`. It means the current directory and descendants, not necessarily the entire repository.

Appropriate when:

- you have confirmed that the working tree contains only changes for this commit;
- a small project or one-off cleanup needs all changes staged quickly.

Notes:

- Run `git status` first to avoid committing temporary files, logs, or generated artifacts.
- Current Git `git add <pathspec>` records additions, modifications, and deletions in the given path scope; very old Git behavior differed. To explicitly cover the whole repository, return to its root, inspect status, and then use `git add -A`.

## `git add -p`

```powershell
git add -p
```

Purpose: interactively choose parts of a file’s changes to stage. Git divides changes into hunks so you can select each section.

Appropriate when:

- one file contains multiple logical changes and only some belong in the next commit;
- you want precise control of commit scope.

Common choices:

- `y`: stage this hunk.
- `n`: skip this hunk.
- `s`: split this hunk further.
- `q`: quit interaction.

Use `git diff --staged` to review the final staged content and avoid omissions or unintended selections.

## `git mv <old> <new>`

```powershell
git mv old-name.md new-name.md
```

Purpose: move or rename a file and stage deletion of the old path plus addition of the new path. A commit still saves before/after snapshots; rename is inferred from similarity when history is viewed.

Appropriate when:

- renaming source files, documentation, or files inside a directory;
- you want one command to move the file and stage the path change.

`git mv` moves a file and stages the path change. Git does not preserve a permanent “rename record”; it infers a rename from content similarity when showing history. A manual move followed by `git add -A` can be recognized too.

## `git rm <file>`

```powershell
git rm -- obsolete.md
```

Purpose: delete a file from the working tree and stage the deletion.

Appropriate when:

- the file is truly no longer needed and the next commit should record its removal.

This deletes the local file. To stop tracking a file while retaining it locally, use `git rm --cached <file>`.

## `git rm --cached <file>`

```powershell
git rm --cached -- .env
```

Purpose: stop tracking a file without deleting the local file.

Appropriate when:

- local configuration, cache, or generated output was committed by mistake and should leave version control;
- you are about to add it to `.gitignore` but still need it locally.

Common combination:

```powershell
git rm --cached .env
Add-Content .gitignore ".env"
git status
```

If sensitive information has entered history, removing it only from the latest commit does not erase historical exposure. Clean Git history further and rotate credentials.

## `git reset <file>`

```powershell
git reset -- README.md
```

Purpose: unstage the specified file while retaining its actual working-tree modification.

Appropriate when:

- after `git add`, you realize a file should not enter the next commit;
- you want to split commit scope again.

Modern alternative:

```powershell
git restore --staged -- README.md
```

## `git reset`

```powershell
git reset
```

Purpose: unstage all content while retaining working-tree modifications.

Appropriate when:

- undoing the result of `git add .` in one step;
- reorganizing files for the next commit.

Without `--hard`, `git reset` normally does not delete working-tree files. The truly risky command is `git reset --hard`; see [[git/07-undoing-and-cleaning-up|Undoing and Cleaning Up]].

## `git status`

```powershell
git status
```

Purpose: view working-tree and staging-area state. It reports untracked, modified, and staged files.

Habit:

- inspect once before committing;
- inspect once after undo, move, or delete commands;
- when a file is uncertain, do not immediately run `git add .`.

Compact output:

```powershell
git status --short
```

## Minimum exercise

In an isolated experimental repository, modify `README.md` and run, in order, `git add -- README.md`, `git diff --staged`, and `git restore --staged -- README.md`. Explain in your own words whether file content, staging area, and history changed.
