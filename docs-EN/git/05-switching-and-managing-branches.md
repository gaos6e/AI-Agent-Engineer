---
title: "Git Cheat Sheet: Switching and Managing Branches"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - branch
lang: en
translation_key: Git/05-分支切换与分支管理.md
translation_source_hash: 6f6200b246ce73ddc88682b741132ebf9cecf357918061fb516f42e8aedd296c
translation_route: zh-CN/Git/05-分支切换与分支管理
translation_default_route: zh-CN/Git/05-分支切换与分支管理
---

# Switching and Managing Branches

A branch is a movable reference to a commit that isolates different lines of work. This course uses the single-purpose `git switch` for branch switching while retaining compatible `git checkout` forms. Automation should still verify Git version and project conventions in the target environment. See [[git/02a-git-state-model-and-commit-graph|Git State Model and Commit Graph]] for the state model.

## `git switch <name>`

```powershell
git switch feature/demo
```

Purpose: switch to an existing branch.

Legacy form:

```powershell
git checkout feature/demo
```

Appropriate when:

- switching from the current branch to `main`, `develop`, or a feature branch;
- inspecting code state on another branch.

If the working tree has uncommitted changes, Git may refuse to switch to avoid overwriting your work. Run `git status --short` first.

## `git switch -c <name>`

```powershell
git switch -c feature/demo
```

Purpose: create a branch from the current commit and immediately switch to it.

Legacy form:

```powershell
git checkout -b feature/demo
```

Appropriate when:

- starting a feature, fix, or documentation-cleanup task;
- isolating experimental work from the main branch.

Example:

```powershell
git switch -c docs/git-cheat-sheet
```

Before creation, use `git branch --show-current` to confirm the actual baseline branch name. `git init` default depends on version, installer, or config; a clone’s initial branch comes from remote `HEAD`, so it is not always `main`.

## `git branch`

```powershell
git branch
```

Purpose: list local branches; the current branch normally has a marker.

Common extensions:

```powershell
git branch -a
git branch -vv
```

- `-a` also shows remote-tracking branches.
- `-vv` shows upstream and ahead/behind information for local branches.

## `git branch --sort=-committerdate`

```powershell
git branch --sort=-committerdate
```

Purpose: list branches descending by latest commit time.

Appropriate when:

- finding recently active feature branches;
- determining which branches have been inactive before cleanup.

## `git branch -d <name>`

```powershell
git branch -d feature/demo
```

Purpose: delete a local branch. Git checks whether the branch was merged into its upstream; if it has no upstream, it checks whether it was merged into current `HEAD`. It refuses when those protection conditions are not met.

Appropriate when:

- a feature branch is merged;
- a local temporary branch is no longer needed.

You cannot delete the current branch; switch elsewhere first.

## `git branch -D <name>`

```powershell
git branch -D feature/demo
```

Purpose: force-delete a local branch even when Git considers it unmerged.

> [!warning] High-risk operation
> `-D` removes the branch reference to unmerged commits. Before running it, use `git log --oneline HEAD..feature/demo` to view commits unique to the target branch, then `git branch --contains feature/demo` to see which branches contain its tip. If still uncertain, do not force-delete.

Recovery idea:

- If it was deleted recently by mistake, use `git reflog` to locate a commit ID and create the branch again.

## Next: merge branches

Creating and switching solves isolation, not reconciliation. Continue with [[git/05a-branch-merging-and-conflict-resolution|Branch Merging and Conflict Resolution]] for fast-forward, three-way merge, conflict markers, `git merge --continue`, and `git merge --abort`.
