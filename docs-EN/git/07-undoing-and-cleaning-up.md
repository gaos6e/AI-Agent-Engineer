---
title: "Git Cheat Sheet: Undoing and Cleaning Up"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - restore
lang: en
translation_key: Git/07-撤销与清理.md
translation_source_hash: 9d64cd47cd0c7050a89673658ea6cb07283dec858e7e0625a58cc29cbe866be7
translation_route: zh-CN/Git/07-撤销与清理
translation_default_route: zh-CN/Git/07-撤销与清理
---

# Undoing and Cleaning Up

Some commands in this group move only the index; others delete local changes. Before execution, determine whether you intend to undo “staging state” or file content itself.

## `git restore <file>`

```powershell
git restore -- README.md
```

Purpose: restore a specified working-tree path from index contents. It is equivalent to restoring from `HEAD` only when index and `HEAD` are identical.

To explicitly ignore the index and restore from the current commit:

```powershell
git restore --source=HEAD -- README.md
```

Legacy form:

```powershell
git checkout -- README.md
```

> [!warning] Local content can be lost
> If this file contains modifications not saved in a commit or stash, running the command overwrites them.

Inspect first:

```powershell
git diff -- README.md
```

## `git restore --staged --worktree <file>`

```powershell
git restore --staged --worktree -- README.md
```

Purpose: undo both staged content and working-tree content for the file, returning it to current `HEAD`.

Legacy form:

```powershell
git checkout HEAD -- README.md
```

Appropriate when:

- a file has been staged, but you have confirmed none of its changes are wanted.

This is stronger than `git reset -- README.md` because it changes working-tree content.

## `git revert`: undo a commit while preserving history

```powershell
git revert --no-edit HEAD
```

Purpose: generate inverse changes for a target commit and create a new commit. It does not delete the original commit, so it suits ordinary commits in shared history.

Before using it:

- inspect the target with `git show HEAD`; in practice, revert only a dedicated ordinary test commit;
- keep the working tree clean; if inverse changes conflict, resolve them and continue, or abort with `git revert --abort`;
- a merge commit requires selection of a mainline parent, so beginners should not casually revert a merge commit;
- `--no-edit` keeps the auto-generated message so practice does not get blocked by an unfamiliar editor. In real projects, still review the message under team policy.

## `git reset --hard`

```powershell
git reset --hard
```

Purpose: reset current branch, staging area, and working tree to `HEAD`, discarding all local modifications to tracked files.

> [!danger] High-risk operation
> This deletes uncommitted modifications to tracked files. To write its target commit, it can also delete untracked files/directories that obstruct tracked paths. Reflog cannot recover working-tree content that was never committed. Use only in a disposable isolated repository, after `git status --short`, `git diff`, and `git diff --staged`.

Common safer alternative:

```powershell
git stash
git status --short
```

If you only need to unstage content, do not use `--hard`:

```powershell
git reset
```

## `git clean`

```powershell
git clean
```

Purpose: delete files not tracked by Git. Real use normally needs `-f` because Git protectively refuses direct deletion by default.

Recommended flow:

```powershell
git clean -n -d
git clean -fd
```

- `-n` is a dry run that lists what would be deleted.
- `-f` confirms execution.
- `-d` includes untracked directories.
- Ignored paths are not deleted by default; `-x` includes them, and this beginner route does not practice that option.
- Nested Git repositories have extra protection. Do not stack `-f` flags to bypass a boundary you do not understand.

> [!warning] It will not enter commit history
> Git has not saved untracked files. After deletion, Git usually cannot recover them.

## `git stash`

```powershell
git stash
```

Purpose: temporarily save staged and unstaged modifications to currently tracked files, then clean those modifications. If untracked or ignored paths remain, the working tree may not be completely clean.

Appropriate when:

- you need to switch branches temporarily but current work is not ready to commit;
- you want to move local modifications aside before pulling updates or reproducing an issue.

Useful supplementary commands:

```powershell
git stash list
git stash pop
git stash apply
```

- `pop` applies the most recent stash and deletes it after success.
- `apply` applies it but retains the stash record.
- Default `git stash` does not include untracked or ignored files; `-u` includes untracked files, while `-a` includes ignored files too. Inspect first to avoid putting credentials into a stash.

## Decision table for an undo command

| Goal | History impact | Suitable for shared history? | Recommended command |
| --- | --- | --- | --- |
| Unstage only; retain file contents | Unchanged | Yes | `git restore --staged -- README.md` |
| Overwrite working-tree file from index | Unchanged | Yes, but loses local content | `git restore -- README.md` |
| Overwrite index and worktree from `HEAD` | Unchanged | Yes, but loses local content | `git restore --source=HEAD --staged --worktree -- README.md` |
| Inversely undo a shared ordinary commit | Adds inverse commit | Usually | `git revert --no-edit HEAD` |
| Move local branch while retaining file changes | Rewrites current branch entry | Consider only if not shared | `git reset --mixed HEAD~1` |
| Discard all tracked local changes | Branch target can change; files are lost | No; isolated repository only | `git reset --hard HEAD` |
| Delete untracked files | Not in history; normally unrecoverable | History-independent but high risk | First `git clean -n -d`, then consider `git clean -fd` only in an isolated repository |
| Temporarily move tracked changes aside | History unchanged; adds stash reference | Local operation | `git stash push -m "wip: explain purpose"` |

## Minimum exercise

In the isolated repository from [[git/12-version-control-practice-and-self-check|Version-Control Practice and Self-Check]], verify separately “restore working tree,” “unstage,” and “revert a dedicated ordinary commit.” At each step record `status`, `diff`, `diff --staged`, and `log` before/after, then state whether content, index, history, and branch pointer changed.

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git restore](https://git-scm.com/docs/git-restore)
- [git revert](https://git-scm.com/docs/git-revert)
- [git reset](https://git-scm.com/docs/git-reset)
- [git clean](https://git-scm.com/docs/git-clean)
- [git stash](https://git-scm.com/docs/git-stash)
