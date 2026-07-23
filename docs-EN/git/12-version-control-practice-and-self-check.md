---
title: "Version-Control Practice and Self-Check"
tags:
  - AI-Agent-Engineer
  - Git
  - integrated-practice
aliases:
  - Git Integrated Project
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
lang: en
translation_key: Git/12-版本控制实战与自测.md
translation_source_hash: e4de1bba27cf3bda28cb331ec4aceac50a625b0c6e7ab67d111fbae6445e294f
translation_route: zh-CN/Git/12-版本控制实战与自测
translation_default_route: zh-CN/Git/12-版本控制实战与自测
---

# Version-Control Practice and Self-Check

## Project objective

Manage “prompt experiment records” in a fresh isolated repository under the system temporary directory. Leave auditable evidence of at least three content commits, one baseline-evidence commit, branch divergence, conflict resolution, three kinds of undo, and history tracing. The core project has no remote, uses no real data, and does not practice `reset --hard`, `clean -fd`, rebase, or force pushes.

> [!info] Actual verification boundary for this knowledge base
> This knowledge-base update did not execute the project below, because it would create nested repositories and Git commits, conflicting with the current constraint not to create commits. The PowerShell fences received AST syntax checks, and Git command semantics were cross-checked against the 2.55.0 official documentation. Learners must still inspect actual output step by step when running the lab.

## Lab tiers

| Environment | Permitted actions | Required safeguards | Acceptance |
| --- | --- | --- | --- |
| Current real repository | Read-only review such as `status`, `diff`, `log`, and `show` | Do not add, commit, switch branches, or access a network | State is unchanged before and after |
| Core temporary repository | init, add, commit, branch, merge, restore, revert | Fresh empty directory under `%TEMP%`; equal root paths; no remote | At least three content commits, one merge, three kinds of undo |
| Offline remote lab | Bare remote, two local clones, fetch/push | A separate unique temporary directory; no account or credentials | Can explain a push rejection and remote-tracking references |
| Optional high risk | Recover after `branch -D` with reflog; hard reset, clean, rebase, force-with-lease | Disposable copy only; each action needs independent safeguards | Only branch-entry recovery is optional; the rest is outside core acceptance |

## Phase 0: create and prove the isolation boundary

### 0.1 Create a unique empty directory

Copy the entire block below rather than starting with `git init` alone:

```powershell
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$labPath = Join-Path $tempRoot ("git-core-lab-" + [Guid]::NewGuid().ToString("N"))
if (Test-Path -LiteralPath $labPath) {
    throw "The lab directory already exists; stopping."
}
New-Item -ItemType Directory -Path $labPath | Out-Null
$resolvedLab = (Resolve-Path -LiteralPath $labPath).Path
if (-not $resolvedLab.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "The lab directory is not under the system temporary directory; stopping."
}
if (@(Get-ChildItem -LiteralPath $resolvedLab -Force).Count -ne 0) {
    throw "The lab directory is not empty; stopping."
}
Set-Location -LiteralPath $resolvedLab
git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "The lab directory is already inside another Git worktree; stopping."
}
$resolvedLab
```

The last line must print a fresh absolute path under the system temporary directory. If any `throw` is triggered, do not bypass it.

### 0.2 Initialize a known default branch and verify the repository root

```powershell
git init --initial-branch=main
if ($LASTEXITCODE -ne 0) { throw "Could not initialize the lab repository; stopping." }
git config set user.name "Git Learner"
git config set user.email "learner@example.test"
if ($LASTEXITCODE -ne 0) { throw "Could not set the repository-local identity; stopping." }
$gitRoot = [IO.Path]::GetFullPath((git rev-parse --show-toplevel).Trim())
if (-not [String]::Equals($gitRoot, $resolvedLab, [StringComparison]::OrdinalIgnoreCase)) {
    throw "The Git root and lab directory do not match; stopping."
}
$remoteNames = @(git remote)
if ($remoteNames.Count -ne 0) {
    throw "The core lab must not configure a remote; stopping."
}
git config get user.name
git config get user.email
git status --short --branch
```

This uses a repository-level identity and does not modify global Git configuration. `example.test` is a reserved test domain, not a real email address.

## Phase 1: establish a minimal project, three content commits, and baseline evidence

### 1.1 File structure

Create the following fictional assets:

```text
README.md
.gitignore
prompts/
  summary.md
eval/
  cases.json
evidence.md
```

Use PowerShell to create the directories and initial files:

```powershell
New-Item -ItemType Directory -Path prompts, eval | Out-Null
Set-Content -LiteralPath README.md -Encoding utf8 -Value @(
    "# Prompt history lab"
    ""
    "Only fictional data is allowed."
)
Set-Content -LiteralPath .gitignore -Encoding utf8 -Value @(
    ".env"
    ".venv/"
    "__pycache__/"
)
Set-Content -LiteralPath prompts/summary.md -Encoding utf8 -Value @(
    "# Summary prompt"
    ""
    "Return a concise summary in no more than 120 Chinese characters."
)
Set-Content -LiteralPath eval/cases.json -Encoding utf8 -Value @(
    "["
    "  {`"input`": `"Fictional meeting note A`", `"expected`": [`"decision`", `"owner`"]},"
    "  {`"input`": `"Fictional meeting note B`", `"expected`": [`"risk`", `"deadline`"]}"
    "]"
)
Set-Content -LiteralPath evidence.md -Encoding utf8 -Value "# Evidence log"
```

First verify the JSON and secret boundary:

```powershell
Get-Content -LiteralPath eval/cases.json -Raw | ConvertFrom-Json | Out-Null
git status --short
git check-ignore -v -- .env
git ls-files -- .env
```

The final command should produce no output because `.env` must not be tracked.

### 1.2 Three atomic content commits

Commit the initial structure first:

```powershell
git add -- README.md .gitignore prompts/summary.md eval/cases.json evidence.md
git diff --staged
git diff --staged --check
git commit -m "docs: initialize prompt history lab"
if ($LASTEXITCODE -ne 0) { throw "The initial commit failed; stopping." }
git rev-parse HEAD
```

For the second commit, add only one fictional evaluation case, verify the JSON, and commit it. For the third, change only the README's lab explanation and commit it. Before each commit, run:

```powershell
git status --short
git diff
git diff --staged
git diff --check
git diff --staged --check
git log --oneline --decorate -3
```

Record the three commit IDs, intentions, and validation results in `evidence.md`. Preserve the baseline evidence in a fourth documentation-only commit. If unrelated files were modified at the same time, split the staging area again first:

```powershell
git add -- evidence.md
git diff --staged --check
git commit -m "docs: record baseline evidence"
if ($LASTEXITCODE -ne 0) { throw "The baseline-evidence commit failed; stopping." }
$pending = @(git status --porcelain)
if ($pending.Count -ne 0) {
    throw "The working tree must be clean before the branch exercise; stopping."
}
```

## Phase 2: deliberately create and resolve a conflict

### 2.1 Create divergence

Create a feature branch, change the length rule in `prompts/summary.md` to 80 characters, and commit:

```powershell
git switch -c experiment/short-output
git add -- prompts/summary.md
git diff --staged
git commit -m "experiment: shorten summary limit"
```

Switch back to the known `main` branch, change the same line to 200 characters, and commit:

```powershell
git switch main
git add -- prompts/summary.md
git diff --staged
git commit -m "experiment: expand summary limit"
git log --graph --oneline --decorate --all
```

### 2.2 Merge, inspect, and exit

```powershell
git merge experiment/short-output
if ($LASTEXITCODE -eq 0) {
    throw "The expected text conflict did not occur; stop and check whether both branches changed the same line."
}
git status
$unmerged = @(git diff --name-only --diff-filter=U)
if ($unmerged.Count -ne 1 -or $unmerged[0] -ne "prompts/summary.md") {
    if (Test-Path -LiteralPath .git/MERGE_HEAD) { git merge --abort }
    throw "The unresolved path does not match the expectation; a merge abort was attempted."
}
git diff
```

Only `prompts/summary.md` should be unresolved. If the branch direction, file, or precondition is not as expected, immediately run:

```powershell
git merge --abort
git status --short --branch
```

To continue, manually change the length rule to a justified final value and explain both sides' intent in `evidence.md`. Confirm that conflict markers are gone:

```powershell
$markers = Select-String -LiteralPath prompts/summary.md -Pattern '^(<<<<<<<|=======|>>>>>>>)'
if ($markers) {
    throw "Conflict markers remain; do not commit."
}
git add -- prompts/summary.md evidence.md
git diff --staged --check
git diff --staged
git commit -m "merge: reconcile summary length rules"
git log --merges --oneline
git log --graph --oneline --decorate --all
```

“No conflict markers” only means the syntax is complete. The final rule must also agree with `eval/cases.json` and the lab description.

## Phase 3: verify three kinds of undo

### 3.1 Discard an unstaged working-tree modification

Add a fictional sentence to the end of `README.md`, inspect it, then restore it:

```powershell
git diff -- README.md
git restore -- README.md
git status --short
```

Note: by default, `restore` restores the working tree from the index. At this point the index equals `HEAD`, so the outcome also equals the current committed version.

### 3.2 Unstage while retaining content

Modify `README.md` again:

```powershell
git add -- README.md
git diff --staged -- README.md
git restore --staged -- README.md
git diff -- README.md
git diff --staged -- README.md
```

The working-tree modification should remain and the staged diff should be empty. Preserve the output first, then clean this experimental change with `git restore -- README.md`. You may consolidate evidence in a later documentation commit, but do not enter the revert exercise with an uncommitted `evidence.md` change.

### 3.3 Undo a dedicated ordinary commit with revert

First create a dedicated non-merge commit that is explicitly wrong, then revert it:

```powershell
$pending = @(git status --porcelain)
if ($pending.Count -ne 0) {
    throw "The working tree must be clean before the revert exercise; stopping."
}
Add-Content -LiteralPath prompts/summary.md -Encoding utf8 -Value "Temporary wrong rule: expose secret tokens."
git add -- prompts/summary.md
git commit -m "experiment: add intentionally wrong rule"
if ($LASTEXITCODE -ne 0) { throw "The wrong-rule commit failed; stopping." }
$revertTarget = (git rev-parse HEAD).Trim()
git show --stat --oneline $revertTarget
git revert --no-edit $revertTarget
if ($LASTEXITCODE -ne 0) {
    git status
    git revert --abort
    throw "The revert did not finish as expected; an abort was attempted."
}
git log --oneline --decorate -3
```

Verify that both the original commit and its inverse commit appear in history, while the wrong content is absent from the current file. If you selected a merge commit by mistake or encounter a conflict you do not understand, use `git revert --abort`; do not guess the `-m` argument.

## Phase 4: history tracing and a recovery entry point

```powershell
git log -- prompts/summary.md
git blame -- prompts/summary.md
git log -G "summary" --all -- prompts/summary.md
git log --graph --oneline --decorate --all
git reflog
```

In `evidence.md`, answer: which commit introduced the 80-character rule, which introduced the 200-character rule, which resolved the conflict, and which was reverted? Include patch evidence for each conclusion.

The optional reflog recovery exercise runs only in this isolated repository. This step force-deletes an experimental branch with a unique commit to create a “lost branch entry” situation; do not reproduce it in a real repository:

```powershell
$pending = @(git status --porcelain)
if ($pending.Count -ne 0) { throw "The working tree must be clean before the reflog exercise; stopping." }
git switch -c recovery/demo
Set-Content -LiteralPath recovery-note.md -Encoding utf8 -Value "Recover this fictional commit."
git add -- recovery-note.md
git commit -m "experiment: create recovery target"
if ($LASTEXITCODE -ne 0) { throw "The recovery-target commit failed; stopping." }
$lostCommit = (git rev-parse HEAD).Trim()
git switch main
git branch -D recovery/demo
git reflog
$headReflog = @(git reflog --format='%H')
if ($lostCommit -notin $headReflog) {
    throw "The target commit is not in the HEAD reflog; stopping."
}
git branch recovery/found $lostCommit
git show --stat --oneline recovery/found
```

`git branch -D` is deliberately confined here to the temporary repository because it is high risk. Deleting a branch deletes that branch's own reflog; recovery evidence comes from the `HEAD` reflog created when switching and committing. Do not hard-reset: the goal is to recreate a reference, not move the current branch. Reflog is local and expires; it is not a permanent backup.

## Read-only real-repository review task

If you have a real project, run only the read-only commands below and write a review conclusion that does not change state:

```powershell
git rev-parse --show-toplevel
git status --short --branch
git diff --stat
git diff --staged --stat
git branch -vv
git remote
git log --graph --oneline --decorate -10
```

Do not add, commit, switch branches, pull, or clean merely to make the output look tidy. If you need to inspect a URL, first confirm that it cannot leak a token or private-server information.

## Remote extension project

The core project intentionally has no remote. After completion, continue to the [[git/10a-remote-collaboration-and-offline-two-clone-lab|Remote Collaboration and Offline Two-Clone Lab]] to simulate fetch, push rejection, and integration with a local bare remote and two clones. It requires no account, network access, or real credentials.

## Pre-commit checklist for real work

```text
□ Every item in git status --short is understood
□ git diff reviews unstaged changes
□ git diff --staged reviews content to be committed
□ No credentials, personal information, large files, caches, or environment directories are present
□ The commit scope has one clear intent
□ The commit message says “what”; its body explains “why” when needed
□ Relevant tests or documentation checks have run and their results are recorded
```

`.gitignore` affects only the selection of untracked paths; it does not remove committed files from history. If you find a committed credential, stop sharing it, rotate the credential, and assess history cleanup under your organization's process. Do not merely add an ignore rule.

## Self-check

1. What are the working tree, index, object database, and `HEAD` respectively?
2. What distinct evidence do `git diff`, `git diff --staged`, and `git status` provide?
3. Why is a branch better understood as a movable reference than as a directory copy?
4. How do fast-forward and three-way merge differ in history structure?
5. Why does conflict resolution require business judgment and testing?
6. Which layer does each of `restore`, `revert`, and `reset` primarily affect?
7. Why does this project require reverting a dedicated ordinary commit?
8. What can reflog help recover, and why is it not a permanent backup?
9. What kind of secret leak cannot be solved by `.gitignore`?
10. Why is `origin/main` not the server's real-time state?
11. Why cannot a push rejection simply be “solved” with a force push?
12. After an agent generates code, who is responsible for checking scope, credentials, tests, and the final commit?

## Scoring and acceptance

| Item | Points | Passing evidence |
| --- | ---: | --- |
| Isolation and secret boundary | 20 | Temporary absolute path, equal root paths, no remote, fictional data, and a local identity |
| Atomic commits | 15 | At least three clear commits, each with staged diff and validation records |
| Branches and conflict | 20 | Deterministic divergence, one merge conflict, semantic resolution, and a merge commit |
| Three kinds of undo | 20 | Before-and-after evidence for working-tree restore, staged restore, and reverting an ordinary commit |
| History tracing | 15 | log, blame, `-G`, and reflog answer concrete questions |
| Retrospective quality | 10 | Can explain results, limits, and unverified items with the state model |

Score at least **80/100** and receive full credit for “Isolation and secret boundary” to complete the lab. Safety items cannot be offset by other points.

When finished, return to the [[git/00-index|Git Index]].

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [Git Tutorial](https://git-scm.com/docs/gittutorial)
- [Git Glossary](https://git-scm.com/docs/gitglossary)
- [git merge](https://git-scm.com/docs/git-merge)
- [git restore](https://git-scm.com/docs/git-restore)
- [git revert](https://git-scm.com/docs/git-revert)
- [git reflog](https://git-scm.com/docs/git-reflog)
