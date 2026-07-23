---
title: "Git Cheat Sheet: Diffing and Commit References"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - diff
lang: en
translation_key: Git/06-差异对比与提交引用.md
translation_source_hash: e348bd0953513209a86fade91f569a8dd4892d084b60fc643f664f5610ccb3e4
translation_route: zh-CN/Git/06-差异对比与提交引用
translation_default_route: zh-CN/Git/06-差异对比与提交引用
---

# Diffing and Commit References

`diff` answers “what changed?” In Git, first distinguish three states: the working tree, staging area, and most recent commit.

## Working-tree and staging-area differences

### `git diff`

```powershell
git diff
```

Purpose: view working-tree modifications not yet staged.

Appropriate when:

- inspecting what you changed before `git add`;
- quickly confirming a local difference after code changes.

### `git diff --staged`

```powershell
git diff --staged
```

Purpose: view staged changes that will enter the next commit.

Equivalent common form:

```powershell
git diff --cached
```

Appropriate when:

- reviewing commit content before `git commit`;
- confirming selections after `git add -p`.

### `git diff HEAD`

```powershell
git diff HEAD
```

Purpose: view tracked-path differences from the most recent commit to the current working tree, including staged and unstaged content. Ordinary untracked files do not appear, so still inspect `git status --short`.

Appropriate when:

- you want a single overview of “everything in the current directory versus the last commit”;
- doing a total review before a commit.

## Differences between commits

### `git show <commit>`

```powershell
git show HEAD~1
```

Purpose: view a commit’s metadata and the difference it introduced relative to its parent.

Appropriate when:

- reviewing what a particular commit actually changed;
- understanding one commit’s concrete content before code review.

### `git diff <commit> <commit>`

```powershell
git diff main feature/demo
```

Purpose: compare content differences between two commits.

Examples:

```powershell
git diff main feature-branch
git diff HEAD~3 HEAD
```

Order affects display direction. Usually read it as “change from the first commit to the second.”

### `git diff <commit> -- <file>`

```powershell
git diff HEAD~1 -- README.md
```

Purpose: view how one file changed from a specified commit to current state.

Appropriate when:

- you care about one file, not the entire repository;
- confirming how one configuration or document differs from an older version.

### `git diff <commit> --stat`

```powershell
git diff HEAD~1 --stat
git show HEAD~1 --stat
```

Purpose: view a difference summary instead of a complete patch.

Appropriate when:

- judging change scale quickly;
- summarizing touched files for handoff notes.

## What `<commit>` can mean

When a command contains `<commit>`, several reference forms are available.

| Form | Meaning | Example |
|---|---|---|
| Branch name | Commit currently targeted by that branch | `main` |
| Tag name | A release or marked location | `v0.1` |
| Commit ID | Hash prefix or complete hash for one commit | `3e887ab` |
| Remote branch | Current remote-tracking branch target | `origin/main` |
| `HEAD` | The currently checked-out commit | `HEAD` |
| `HEAD^` | Parent of the current commit | `HEAD^` |
| `HEAD~3` | Three first-parent steps before the current commit | `HEAD~3` |

Notes:

- `HEAD^^^` and `HEAD~3` are common ways to trace three parent generations back.
- A merge commit has multiple parents, so `^` can take a number to choose a parent, such as `HEAD^2`.
- Before using an unfamiliar reference, inspect a graph with `git log --oneline --graph --decorate`.
- `--` clearly separates commit/options from paths and avoids ambiguity when a branch and file share a name.

## Minimum self-check

1. Which two layers do `git diff`, `git diff --staged`, and `git diff HEAD` compare?
2. Why preserve `--` in `git diff HEAD~1 -- README.md`?
3. Why can `HEAD^1` and `HEAD^2` of a merge commit target different parents?
