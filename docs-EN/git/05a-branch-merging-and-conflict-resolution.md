---
title: "Branch Merging and Conflict Resolution"
aliases:
  - Git merge introduction
  - Git conflict resolution
tags:
  - ai-agent-engineer
  - git
  - merge
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
lang: en
translation_key: Git/05A-分支合并与冲突处理.md
translation_source_hash: 5807be00fc95ea976a5aca24a3d0097c7348ac25b9fec266e5edd206605c4d54
translation_route: zh-CN/Git/05A-分支合并与冲突处理
translation_default_route: zh-CN/Git/05A-分支合并与冲突处理
---

# Branch Merging and Conflict Resolution

## Learning objective

Learn to distinguish fast-forward from three-way merge, start or abort a merge safely, and distinguish “the conflict file can commit” from “the business semantics are correct.” Practice all writes only in the [[git/12-version-control-practice-and-self-check|isolated experimental repository]].

## What merge solves

Branches let two work lines progress independently; a merge reunites them. Suppose `main` and `feature/summary` both start from commit B:

```text
        C ← D   feature/summary
       /
A ← B ← E       main, HEAD
```

Git finds common ancestor B, compares changes B→D and B→E, then attempts a common result. This is a three-way merge. If the current branch has no commits of its own, Git can simply move the branch reference forward: a fast-forward, with no new merge commit.

## Evidence before starting a merge

```powershell
git status --short --branch
git branch --show-current
git log --graph --oneline --decorate --all
git diff
git diff --staged
```

Confirm that the working tree has no unexplained change and that you understand “which branch goes into which”: switch to the receiver branch first, then give `git merge` the source branch.

```powershell
git switch main
git merge feature/summary
```

Do not reverse the direction verbally. The commands change `main`: it receives `feature/summary`’s reachable history.

## Three common outcomes

### 1. Already up to date

The source branch contains no commit absent from the current branch, so nothing changes.

### 2. Fast-forward

The current branch has not diverged, so its reference moves forward. History remains a single line.

### 3. Automatic or conflicting three-way merge

When both sides have advanced, Git attempts automatic merging. If changes do not conflict, it creates a merge commit. If it cannot decide the same content, the repository enters merging state and waits for human resolution.

## A conflict is not a random error

A conflict says Git lacks enough semantic information to choose final content. A text file may contain:

```text
<<<<<<< HEAD
Rule from the main branch
=======
Rule from the feature branch
>>>>>>> feature/summary
```

The `HEAD` side is the current receiver branch; the other side is the merged-in branch. Resolution is not mechanically deleting three types of markers. Read requirements, tests, and both intents, then write the content that should remain long-term.

List unresolved paths:

```powershell
git status
git diff --name-only --diff-filter=U
git diff
```

After editing and verification, add resolved paths to the index:

```powershell
git add -- prompts/summary.md
git diff --staged --check
git diff --staged
git merge --continue
```

`git merge --continue` may open a commit-message editor. After every conflict is resolved and staged, `git commit` is also possible. Run project tests before committing so “Git has no markers” and “the program behaves correctly” both hold.

## Abandon this merge

If the direction is wrong, requirements are missing, or the state should not proceed:

```powershell
git merge --abort
git status --short --branch
```

`--abort` attempts to restore state from before the merge. If complex uncommitted changes existed at the start, recovery may be incomplete; that is why the working tree must be understandable first. Do not use `reset --hard` instead of thinking.

## Merge, rebase, and cherry-pick

| Operation | Main effect | Commit-ID behavior | Typical use |
| --- | --- | --- | --- |
| `merge` | Reunites two histories, creating a multi-parent commit if needed | Existing commits unchanged; may add a merge commit | Preserve how the branch was formed |
| `rebase` | Recreates a series of commits on a new base | Replayed commits get new IDs | Clean a not-yet-shared feature branch |
| `cherry-pick` | Recreates selected changes on current branch | Source commit stays; current branch gets a different ID | Selectively transplant a fix |

The beginner path learns merge first. Do not casually rebase shared branches for “pretty history,” and do not use cherry-pick as a long-term branch-synchronization mechanism.

## Common errors and diagnosis

- **Merge on the wrong branch:** use `git branch --show-current` and the graph log to confirm direction; before completion, use `git merge --abort`.
- **Delete markers without reading semantics:** run tests and inspect documentation/evaluation cases before staging.
- **Unresolved files remain:** `git diff --name-only --diff-filter=U` should be empty.
- **No “new commit” after a merge:** it may have fast-forwarded; explain with `git log --graph --oneline --decorate --all`.
- **Confuse merge with pull:** pull fetches first, then integrates under explicit options or configuration; see the remote lesson.

## Exercise and mastery check

In the integrated project, have `main` and `experiment/short-output` modify the same line and resolve one definite conflict. Acceptance evidence:

- the diverged graph before merging;
- merging state and unresolved-path list;
- final file has no conflict markers and has a complete semantic explanation;
- `git diff --staged --check` and project-check results;
- graph after merging and merge-commit ID.

You should be able to answer: why does fast-forward have no multi-parent commit? What does `git add` express in a conflict flow? When should you continue, and when should you abort?

## Next step

Continue with [[git/06-diffing-and-commit-references|Diffing and Commit References]], then [[git/07-undoing-and-cleaning-up|Undoing and Cleaning Up]].

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git merge](https://git-scm.com/docs/git-merge)
- [Git User Manual: Merging](https://git-scm.com/docs/user-manual#merging)
- [git status](https://git-scm.com/docs/git-status)
- [git cherry-pick](https://git-scm.com/docs/git-cherry-pick)

