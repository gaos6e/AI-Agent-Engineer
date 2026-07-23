---
title: "Git Cheat Sheet: History Tracing and Code Archaeology"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - history
lang: en
translation_key: Git/09-历史追踪与代码考古.md
translation_source_hash: d1c60ea1eadc03f5d618953423f55231c6d5aeb3c5d35461b41c01f3df67cbca
translation_route: zh-CN/Git/09-历史追踪与代码考古
translation_default_route: zh-CN/Git/09-历史追踪与代码考古
---

# History Tracing and Code Archaeology

These commands answer “when did this change, who changed it, and why?” They are useful for investigating regressions, understanding older designs, and locating the commits that introduced a behavior.

## `git log main`

```powershell
git log main
```

Purpose: view the commit history of a branch.

Appropriate when:

- you want to see the most recent commits on the `main` branch;
- you need to confirm that a feature has reached its target branch.

Common variants:

```powershell
git log --oneline main
git log --graph main
git log --oneline --graph --decorate --all
```

Notes:

- `--oneline` displays one line per commit for a quick scan.
- `--graph` renders branch and merge relationships as an ASCII graph.
- `--decorate` shows references such as branch names and tags.

## `git log -- <file>`

```powershell
git log -- README.md
```

Purpose: view the history of commits that modified a file.

Appropriate when:

- you want to know which recent commits changed a file;
- you are tracing the source of a behavior change in that file.

Useful combinations:

```powershell
git log --oneline -- README.md
git log -p -- README.md
```

`-p` shows the patch for each commit, which is useful for closer investigation.

## `git log --follow <file>`

```powershell
git log --follow -- README.md
```

Purpose: view a file's history and, where possible, continue tracing it across renames.

Appropriate when:

- a file was moved or renamed and ordinary `git log -- <file>` does not show its earlier history.

Note:

- `--follow` is not guaranteed to resolve complex splits, merges, or large refactors perfectly. Use `git show` and path history together when interpreting its result.

## `git log -G <text>`

```powershell
git log -G banana
```

Purpose: find commits that added or removed lines of code matching text.

Appropriate when:

- you need to locate the first appearance or removal of a function call, configuration setting, or error message;
- you are investigating when a piece of logic changed.

Examples:

```powershell
git log -G "memory_gate"
git log -G "legacy_flag" -- src/
```

Notes:

- The value after `-G` is a regular expression.
- To search commit messages only, use `git log --grep <text>`. The two commands answer different questions.

## `git blame <file>`

```powershell
git blame -- README.md
```

Purpose: show the commit, author, and time that most recently changed each line of a file.

Appropriate when:

- you want to find the commit that introduced a line of code or configuration;
- you need to inspect the wider context of that commit.

Recommended combination:

```powershell
git blame -- README.md
git show HEAD~1
```

Notes:

- `blame` identifies the person who last changed a line, not necessarily the root cause of a problem.
- Formatting-only edits, reordering, and large migrations can make blame less informative. Interpret it with the historical context.

## Restore a file from an earlier version

```powershell
git restore --source=HEAD~1 -- README.md
```

Older syntax:

```powershell
git checkout HEAD~1 -- README.md
```

Purpose: retrieve a version of one file from an earlier commit into the current working tree.

Appropriate when:

- the new version of a file has a problem and you want an earlier version for comparison or temporary restoration;
- you need to restore one file rather than roll back the entire repository.

Note: this modifies the file in the current working tree. After confirming the result, you still need `git add` and `git commit` to record it in history.

## Code-archaeology exercise

In an isolated project, choose a sentence that you know exists. First use `git log -G "length" --all -- prompts/summary.md` to find candidate commits, then use `git show` to verify the patch, and finally use `git blame -- prompts/summary.md` to identify the commit that last changed the current line. Record the “candidate evidence” separately from the “final conclusion”; do not treat the last editor as the root cause by default.
