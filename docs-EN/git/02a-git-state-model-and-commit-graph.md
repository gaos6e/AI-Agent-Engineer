---
title: "Git State Model and Commit Graph"
aliases:
  - Git mental model
  - Working tree, staging area, and HEAD
tags:
  - ai-agent-engineer
  - git
  - version-control
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
lang: en
translation_key: Git/02A-Git 状态模型与提交图.md
translation_source_hash: b36d9bf3684a5ec25256ba5bff471b03f51e70f4f8b9c42b08cd0937f59fe10c
translation_route: zh-CN/Git/02A-Git-状态模型与提交图
translation_default_route: zh-CN/Git/02A-Git-状态模型与提交图
---

# Git State Model and Commit Graph

## Learning objective

After this lesson, you can explain what Git stores, which layer one `add` and one `commit` change, and the relationship among `HEAD`, branches, and the commit graph. Build the model before memorizing commands so undo or conflict handling does not become guesswork.

## Start with an analogy

Imagine a technical manual that is repeatedly published:

- **Working tree:** the manuscript currently being edited on your desk.
- **Index / staging area:** the directory tree prepared for the next edition.
- **Commit:** a numbered, archived version snapshot.
- **Branch:** a movable bookmark attached to a commit.
- **`HEAD`:** which bookmark is currently in use; in detached HEAD state, it points directly to a commit.

`git add` does not merely “tell Git a file exists”; it copies the selected path’s current contents into the index. `git commit` then creates a new commit from the index and moves the current branch bookmark forward. Unstaged working-tree content does not enter that commit.

## Git primarily stores snapshots, not recordings of operations

From a user’s perspective, every commit describes one complete directory tree. Git reuses unchanged objects and compresses storage/transfer, so it does not mechanically duplicate every file each time. The key point is that a commit records “what the tree is at this moment,” not a sequence of editing actions that must be replayed in order.

Common objects:

| Object | What it stores | Why it matters |
| --- | --- | --- |
| blob | File content, without a filename | Identical content can be reused |
| tree | File names, directory structure, and object references | Represents a directory-tree snapshot |
| commit | Tree, parent commit(s), author, time, and message | Connects a snapshot to the history graph |
| annotated tag | Object, tag author, message, and more | Gives a release point an explained stable name |

Object names are computed from content. Changed content gets a different object ID, helping Git detect object corruption. Git itself is not access control or a secret vault.

## How the three states compare

| Question | Objects compared | Common command |
| --- | --- | --- |
| What changed in the working tree relative to the index? | Working tree ↔ index | `git diff` |
| What will the index add over `HEAD`? | Index ↔ `HEAD` | `git diff --staged` |
| What differs overall from `HEAD` in tracked content? | Working tree + index ↔ `HEAD` | `git diff HEAD` |
| Which files are untracked? | Git state database ↔ working-tree paths | `git status --short` |

Ordinary untracked files do not appear in `git diff HEAD`. Before a commit, inspect both `status` and diffs.

```text
edit a file                git add                  git commit
working tree ─────────────▶ index ───────────────────▶ new commit
  ▲                           │                         │
  └──── git restore ──────────┘                         └── current branch moves forward
```

## `HEAD`, branches, and the commit graph

In a normal state, `HEAD` is a symbolic reference—such as one pointing to `refs/heads/main`—and `main` then points to a commit. When you create a commit, Git gives it the old commit as a parent and moves `main`.

```text
A ← B ← C   main, HEAD
         \
          D ← E   feature/demo
```

When two branches add commits independently, history forks. It is not a simple list, but a directed acyclic graph (DAG) formed by parent-commit relations. A merge commit can have two or more parents.

Two easy-to-confuse states:

- **Unborn branch:** immediately after `git init`, before the first commit, a branch name exists as intent but has no commit to point to.
- **Detached HEAD:** `HEAD` points directly to a commit instead of a local branch. You can commit, but without creating a branch, later checkout can leave those commits difficult to find.

Inspect the current state:

```powershell
git branch --show-current
git status --short --branch
git symbolic-ref --short HEAD
```

The third command fails in detached HEAD state. That is evidence; do not create or switch a branch merely to suppress the error.

## Observe objects with read-only commands

In an isolated repository with at least one commit, run:

```powershell
git rev-parse --show-toplevel
git rev-parse HEAD
git cat-file -t HEAD
git cat-file -p HEAD
git ls-files --stage
git log --graph --oneline --decorate --all
```

Observe:

1. `cat-file -p HEAD` shows a tree, parent (except for the first commit), author, committer, and message.
2. `ls-files --stage` shows index entries; the index is not an ordinary directory and is not the working tree.
3. `log --graph` shows references and parent-child relations; a branch name is not a permanent part of a commit.

## Common misconceptions

- **“A commit saves everything in the current directory”:** false. It saves the tree represented by the index; untracked and unstaged content may be absent.
- **“A branch copies a whole set of files”:** false. A branch is normally a small reference; file content comes from its target commit tree.
- **“Git records a rename event”:** commits store before/after snapshots; history viewers infer renames from similarity.
- **“A hash protects a secret”:** false. Credentials entering the object database can still be read from history; rotate them and clean them by process.
- **“Reflog is a permanent backup”:** false. It is local and expires; it does not replace remote backup or artifact archiving.

## Exercise and self-check

For each action below, state what changes in the working tree, index, `HEAD`, and current branch:

1. Edit `README.md` without `add`.
2. Run `git add -- README.md`.
3. Run `git commit -m "docs: update readme"`.

Then answer: why should `git restore --staged -- README.md` not delete the working-tree edit? Why does a new detached-HEAD commit need a branch to retain an easy long-term entry point?

For hands-on verification, use [[git/12-version-control-practice-and-self-check|Version-Control Practice and Self-Check]], not a real project where you create commits merely to learn.

## Summary and next step

Git’s core is not command count but “objects + references + three states.” Next, study [[git/03-staging-area-and-file-operations|Staging Area and File Operations]] to map the model to precise path selection.

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [Git Glossary](https://git-scm.com/docs/gitglossary)
- [Git User Manual: The Object Database](https://git-scm.com/docs/user-manual#the-object-database)
- [Git Repository Layout](https://git-scm.com/docs/gitrepository-layout)
- [git status](https://git-scm.com/docs/git-status)
- [git diff](https://git-scm.com/docs/git-diff)

