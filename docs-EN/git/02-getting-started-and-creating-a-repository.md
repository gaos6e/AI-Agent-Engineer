---
title: "Git Cheat Sheet: Getting Started and Creating a Repository"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - repository
lang: en
translation_key: Git/02-入门与仓库创建.md
translation_source_hash: 9532a113a9b675d3f8890b50c149ff519ccfe6b237ce803e52923dd579efe3e6
translation_route: zh-CN/Git/02-入门与仓库创建
translation_default_route: zh-CN/Git/02-入门与仓库创建
---

# Getting Started and Creating a Repository

This command group starts a Git repository: either initialize the current directory or copy an existing remote repository locally. This page recognizes the two entry points first. Before staging and committing, continue to [[git/02a-git-state-model-and-commit-graph|Git State Model and Commit Graph]] to build a mental model of snapshots, index, `HEAD`, and branches.

## `git init`

```powershell
git init
```

Purpose: create a new Git repository in the current directory. It creates a `.git/` directory where Git stores commit history, branch references, configuration, and staging-area state.

Appropriate when:

- the current directory already contains files but is not yet managed by Git;
- you want to start a local project from scratch before deciding whether to add a remote.

Notes:

- Run it at a project root, not accidentally in an unrelated parent directory.
- Re-running it in an existing Git repository normally does not destroy history, but is unnecessary.
- `git init` creates only a local repository; it does not automatically connect GitHub, GitLab, or another remote.
- The default branch name depends on Git version, installer, and `init.defaultBranch` configuration. When an experiment needs a definite name, run:

```powershell
git init --initial-branch=main
```

Git 2.55’s built-in default remains `master`, and the official plan is to switch it to `main` in Git 3.0. An environment may already override that, so always gather evidence with `git branch --show-current`.

Common next commands:

```powershell
git status
git branch --show-current
git remote
```

At this stage, observe only. Staging, committing, and pushing are covered later; do not treat `git add .`, `commit`, and `push` as a fixed initialization bundle when scope is uncertain.

## `git clone <url>`

```powershell
git clone https://github.com/example/project.git
```

Purpose: copy a complete project from a remote repository, including file contents, commit history, branch references, and remote-address configuration.

Appropriate when:

- you already have a remote repository address, such as a GitHub repository URL;
- you want to develop, read, or run an existing project locally.

Common forms:

```powershell
git clone https://github.com/example/project.git
git clone git@github.com:example/project.git
```

Notes:

- HTTPS addresses are usually easier to use directly; SSH addresses require an SSH key first.
- The initial cloned branch is set by remote `HEAD`, so do not assume it is always `main`.
- Git creates a directory matching the repository name by default. To choose a local directory name:

```powershell
git clone https://github.com/example/project.git project-local
```

Verify with:

```powershell
git status
git remote -v
```

`git status` confirms working-tree state; `git remote -v` confirms remote addresses.

> [!warning] Remote addresses can leak secrets
> Teaching examples use public fictional addresses. Do not put a token, password, or userinfo credential in a URL. Before publishing `git remote -v` output, inspect and redact it.

## Read-only observation exercise

In an existing repository whose purpose you clearly know, run only:

```powershell
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
git log -1 --oneline --decorate
git remote
```

Answer: where is the repository root, what is the current branch, is the working tree clean, what is the latest commit, and which remote names are configured? Do not run `init`, `add`, `commit`, or `push` in a real repository merely to practice. For write operations, enter the [[git/12-version-control-practice-and-self-check|isolated integrated project]].

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git init](https://git-scm.com/docs/git-init)
- [git clone](https://git-scm.com/docs/git-clone)
- [Git Tutorial](https://git-scm.com/docs/gittutorial)
