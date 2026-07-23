---
title: "Remote Collaboration and an Offline Two-Clone Lab"
aliases:
  - Git Remote Collaboration Mental Model
  - Git Offline Remote Lab
tags:
  - AI-Agent-Engineer
  - Git
  - remote
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
lang: en
translation_key: Git/10A-远程协作与离线双克隆实验.md
translation_source_hash: 3471b9a1499843284e47090893f3d4c351b91394d4a4a476f5f19782ff09d666
translation_route: zh-CN/Git/10A-远程协作与离线双克隆实验
translation_default_route: zh-CN/Git/10A-远程协作与离线双克隆实验
---

# Remote Collaboration and an Offline Two-Clone Lab

## Objectives

Distinguish a remote, remote-tracking reference, upstream, and server-side branch; understand the boundary between fetch, integration, and push; and simulate two collaborators in a temporary local directory without an account, network access, or real credentials.

## Do not confuse these four names

| Name | Where it exists | Example | Meaning |
| --- | --- | --- | --- |
| remote | Local configuration | `origin` | A shorthand for a set of URLs and fetch/push rules |
| server branch | Remote repository | `main` on the server | The actual current reference on the remote |
| remote-tracking ref | Local repository | `origin/main` | The local record of remote state from the last fetch |
| upstream | Local branch configuration | `main` tracks `origin/main` | The default correspondence used by bare `pull`, `status`, and similar commands |

`origin/main` is not a live view of the network. It reflects newly fetched state only after fetch, pull, or certain background tools update it.

## Fetch, integration, and push

```text
server reference ── fetch ──▶ local remote-tracking ref
                                      │
                                 merge / rebase
                                      ▼
                                  local branch ── push ──▶ server reference
```

- `git fetch` obtains objects and updates remote-tracking refs; it normally does not change the current working tree.
- `git merge origin/main` or `git rebase origin/main` is what integrates fetched history into the current branch.
- `git push` asks the remote to move a reference. The remote can reject it because it is not fast-forward, permissions or protection rules prohibit it, or a hook rejects it.
- `git pull` is fetch plus a subsequent integration step. Its integration mode depends on explicit options and configuration; do not treat it as an indivisible action.

## A reviewable collaboration flow

1. Run `git fetch origin` to obtain facts.
2. Inspect the difference with `git log --oneline HEAD..origin/main` and `git diff HEAD...origin/main`.
3. Choose merge or rebase on a local feature branch, resolve conflicts, and run tests.
4. Push the feature branch rather than directly rewriting a protected main branch.
5. Use a pull request / merge request on the hosting platform for review, checks, and approval.

Pull requests, protected branches, and approval are hosting-platform and organizational-governance capabilities, not part of Git's object model itself. Consult the platform's official documentation and your team's rules for concrete buttons and permissions.

## Credential boundary

- HTTPS and SSH are distinct transport and authentication paths; Git alone does not unify hosting-platform sign-in rules.
- Git for Windows commonly works with Git Credential Manager; a platform may also require OAuth, a PAT, or an SSH key.
- Do not put a token in the userinfo portion of a URL, or write it to a script, remote configuration, note, or command output.
- Before publishing `git remote -v`, `.git/config`, or complete configuration output, inspect it for userinfo, proxy settings, and custom headers.
- This lesson's core experiment uses a local-path remote and needs neither a network nor credentials.

## Offline two-clone lab

### Safety boundary

The following lab creates commits and a local bare remote. Run it only in a new unique directory under `%TEMP%`; never run it in the current vault or a real project. During development of this knowledge base, only the code-block syntax was checked; these write operations were not executed.

Create and verify an isolated root:

```powershell
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$labPath = Join-Path $tempRoot ("git-remote-lab-" + [Guid]::NewGuid().ToString("N"))
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

Create a bare remote and the first collaborator:

```powershell
git init --bare --initial-branch=main remote.git
if ($LASTEXITCODE -ne 0) { throw "Could not create the bare remote; stopping." }
git clone "$resolvedLab/remote.git" alice
if ($LASTEXITCODE -ne 0) { throw "Could not clone Alice's repository; stopping." }
Set-Location -LiteralPath "$resolvedLab/alice"
git config set user.name "Alice Learner"
git config set user.email "alice@example.test"
Set-Content -LiteralPath README.md -Encoding utf8 -Value "# Offline remote lab"
git add -- README.md
git commit -m "docs: initialize offline lab"
if ($LASTEXITCODE -ne 0) { throw "Alice's initial commit failed; stopping." }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw "Alice's initial push failed; stopping." }
```

Clone the second collaborator:

```powershell
Set-Location -LiteralPath $resolvedLab
git clone "$resolvedLab/remote.git" bob
if ($LASTEXITCODE -ne 0) { throw "Could not clone Bob's repository; stopping." }
Set-Location -LiteralPath "$resolvedLab/bob"
git config set user.name "Bob Learner"
git config set user.email "bob@example.test"
git status --short --branch
git remote
```

First, let Alice create a local commit that has not been pushed:

```powershell
Set-Location -LiteralPath "$resolvedLab/alice"
Set-Content -LiteralPath alice.md -Encoding utf8 -Value "Alice local change"
git add -- alice.md
git commit -m "docs: add Alice note"
if ($LASTEXITCODE -ne 0) { throw "Alice's local commit failed; stopping." }
```

Then let Bob create another commit and push it first:

```powershell
Set-Location -LiteralPath "$resolvedLab/bob"
Set-Content -LiteralPath bob.md -Encoding utf8 -Value "Bob remote change"
git add -- bob.md
git commit -m "docs: add Bob note"
if ($LASTEXITCODE -ne 0) { throw "Bob's commit failed; stopping." }
git push
if ($LASTEXITCODE -ne 0) { throw "Bob's push failed; stopping." }
```

Return to Alice and try to push. It should encounter a non-fast-forward rejection:

```powershell
Set-Location -LiteralPath "$resolvedLab/alice"
git push
if ($LASTEXITCODE -eq 0) {
    throw "The expected non-fast-forward rejection did not occur; stop and inspect the lab order."
}
```

Do not treat the rejection as an error to eliminate. Alice next only fetches and inspects:

```powershell
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Alice's fetch failed; stopping." }
git log --graph --oneline --decorate --all
git log --oneline HEAD..origin/main
git diff HEAD...origin/main
```

Choose merge or rebase according to the experiment's intent, resolve conflicts, run checks, and push only afterward. Do not bypass the rejection with `--force`; the rejection is evidence of concurrency protection.

This set of files should not conflict, so complete the exercise explicitly with rebase:

```powershell
git rebase origin/main
if ($LASTEXITCODE -ne 0) {
    git status
    git rebase --abort
    throw "Alice's rebase did not finish as expected; an abort was attempted."
}
git log --graph --oneline --decorate --all
git push
if ($LASTEXITCODE -ne 0) { throw "Alice's final push failed; stopping." }
```

Finally, have Bob fetch and fast-forward, then assert that both `main` branches point to the same commit:

```powershell
Set-Location -LiteralPath "$resolvedLab/bob"
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Bob's final fetch failed; stopping." }
git merge --ff-only origin/main
if ($LASTEXITCODE -ne 0) { throw "Bob could not fast-forward; stopping." }
$aliceTip = (git -C "$resolvedLab/alice" rev-parse main).Trim()
$bobTip = (git rev-parse main).Trim()
if ($aliceTip -ne $bobTip) {
    throw "Alice's and Bob's main branches are not synchronized yet."
}
git log --graph --oneline --decorate --all
```

### Acceptance evidence

- `git remote` contains only the expected `origin`; the remote URL is the local lab path.
- Both clones can explain their local branch, `origin/main`, and upstream.
- Preserve the category of one push rejection, without recording credentials or private paths.
- Before and after fetch, explain how `origin/main` changed and whether the working tree changed.
- After integration, both collaborators can see the same reachable commit graph.

## Why `--force-with-lease` is still dangerous

It is still a force push. When an explicit expected value is omitted, the lease normally relies on a local remote-tracking ref; an IDE or background fetch can update that ref, making the protection weaker than the user expects. In high-risk situations, restrict the remote, branch, and expected object ID and follow team policy. Do not practice force pushes in a beginner's main project, and do not use them on protected main branches.

## Self-check

1. Why is `origin/main` not the server's real-time state?
2. Why do current files normally remain unchanged after fetch?
3. When a push is rejected, why is fetching and reviewing first more reasonable than force-pushing?
4. Why can the set of references pushed by bare `git push` be affected by `push.default` and remote configuration?
5. Does pull-request approval belong to Git core or to hosting-platform governance?

## Next steps

For the command reference, see [[git/10-remote-repository-synchronization|Remote Repository Synchronization]]. For configuration and the boundary around sensitive output, see [[git/11-git-configuration-and-key-files|Git Configuration and Key Files]]. For the integrated project, see [[git/12-version-control-practice-and-self-check|Version-Control Practice and Self-Check]].

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git fetch](https://git-scm.com/docs/git-fetch)
- [git pull](https://git-scm.com/docs/git-pull)
- [git push](https://git-scm.com/docs/git-push)
- [gitcredentials](https://git-scm.com/docs/gitcredentials)
- [Git URL protocols](https://git-scm.com/docs/git-clone#_git_urls)
