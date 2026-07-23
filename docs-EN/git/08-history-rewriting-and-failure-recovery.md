---
title: "Git Cheat Sheet: History Rewriting and Failure Recovery"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - rebase
lang: en
translation_key: Git/08-历史改写与故障恢复.md
translation_source_hash: 1b5199fe515c0c4e12e5b73ded0efabd45ac36488f31f85845027a31942b1c7e
translation_route: zh-CN/Git/08-历史改写与故障恢复
translation_default_route: zh-CN/Git/08-历史改写与故障恢复
---

# History Rewriting and Failure Recovery

This command group moves commit history or modifies existing commits. It suits cleaning local-branch history, but before changing commits that are pushed and used by others, confirm collaboration impact.

## `git reset HEAD~1`

```powershell
git reset --mixed HEAD~1
```

Purpose: undo the most recent commit while retaining file modifications in the working tree.

Appropriate when:

- you just committed but the commit scope is wrong and you want to split/recommit;
- the message or file combination is poor, while the changes must remain.

Notes:

- `HEAD~1` means one first-parent step backward.
- `--mixed` moves the branch pointer and resets the index while retaining working-tree modifications. It is the default if omitted, but is explicit here for reviewability.

Common follow-up:

```powershell
git status
git add -p
git commit -m "new message"
```

## `git rebase -i HEAD~N`

```powershell
git rebase -i HEAD~5
```

Purpose: interactively edit the most recent N commits—reorder, combine, reword, or remove them.

The official cheat sheet uses:

```powershell
git rebase -i HEAD~6
```

for a squash example. Choose N based on the commits you intend to edit. To process the newest five commits, `HEAD~5` is common. To include an earlier baseline commit in the editor list, expand the range.

Common verbs:

| Verb | Meaning |
|---|---|
| `pick` | Keep the commit |
| `reword` | Keep content but edit the message |
| `edit` | Stop at the commit and allow content changes |
| `squash` | Merge into the preceding commit and allow message editing |
| `fixup` | Merge into the preceding commit and discard current message |
| `drop` | Delete the commit |

> [!warning] Commit IDs will be rewritten
> Rebase generates new commit IDs. If the commits were pushed to a shared branch, confirm the team process before rewriting.

Conflict loop:

```powershell
git status
git add -- resolved-file.md
git rebase --continue
```

If the base, order, or target was wrong, abort instead of layering more fixes:

```powershell
git rebase --abort
git status --short --branch
```

## Squash several recent commits

After interactive rebase opens, normally leave the first record as `pick` and change later commits that belong with it to `fixup` or `squash`.

```text
pick 1111111 first change
fixup 2222222 small fix
fixup 3333333 typo fix
```

When finished, Git combines these commits into fewer commits.

## `git reflog BRANCHNAME`

```powershell
git reflog BRANCHNAME
```

Purpose: view commits a branch reference previously targeted. It is commonly used to recover a position before rebase, reset, or accidental branch deletion.

Appropriate when:

- a rebase failed or its result is wrong and you need an earlier commit;
- a branch was accidentally deleted and you need its last commit ID.

Examples:

```powershell
git reflog main
git reflog
```

- Without a branch name, `git reflog` normally shows moves of current `HEAD`.
- Reflog is local, not remote-repository history.
- Reflog entries expire and may be pruned. Typical defaults expire reachable entries after about 90 days and unreachable entries after about 30 days, though configuration can change.
- Deleting a branch also deletes that branch’s own reflog. The `HEAD` reflog may still supply a clue, but cannot guarantee permanent recovery.

Create a recovery reference before deciding whether to move the current branch:

```powershell
git reflog
git branch recovery/before-rewrite 'HEAD@{1}'
git show recovery/before-rewrite
```

This is easier to review than immediately hard-resetting and preserves the current-branch scene.

## Three common reset modes

| Mode | Moves current branch | Resets index | Overwrites working tree | Typical boundary |
| --- | --- | --- | --- | --- |
| `--soft` | Yes | No | No | Reorganize recent commits that are not shared |
| `--mixed` | Yes | Yes | No | Uncommit and stage again |
| `--hard` | Yes | Yes | Yes | Disposable isolated repository only; loses uncommitted content |

`reset` behavior also depends on target commit and path form. Do not memorize only “undo”; first determine whether you need to move a reference, index, or working tree.

## `git reset --hard <commit>`

```powershell
git reset --hard 'HEAD@{1}'
```

Purpose: force the current branch, staging area, and working tree to a specified commit.

Typical recovery flow:

```powershell
git reflog
git branch recovery/before-hard-reset 'HEAD@{1}'
git reset --hard 'HEAD@{1}'
```

> [!danger] High-risk operation
> This discards current working-tree and staging-area modifications and may delete untracked paths blocking the target tree. Use only in a disposable isolated repository after creating a recovery reference and confirming current local changes are unneeded.

## `git commit --amend`

```powershell
git commit --amend
```

Purpose: change the most recent commit. It can correct its message or add newly staged files to it.

Appropriate when:

- a message is wrong immediately after committing;
- one file was missed and the commit is not pushed or can be safely rewritten.

Add a missed file:

```powershell
git add forgotten-file.md
git commit --amend
```

To change only the message:

```powershell
git commit --amend -m "new message"
```

Amend replaces the most recent commit, changing its commit ID.

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git reset](https://git-scm.com/docs/git-reset)
- [git rebase](https://git-scm.com/docs/git-rebase)
- [git reflog](https://git-scm.com/docs/git-reflog)
- [git commit --amend](https://git-scm.com/docs/git-commit)
