---
title: "Git Cheat Sheet: Remote Repository Synchronization"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - remote
lang: en
translation_key: Git/10-远程仓库同步.md
translation_source_hash: 74fefbc16ee9e70efe7d56856dd10f0f7b822f8d6bafecdf4fb957f3795994bc
translation_route: zh-CN/Git/10-远程仓库同步
translation_default_route: zh-CN/Git/10-远程仓库同步
---

# Remote Repository Synchronization

Remote commands connect a local repository to remote repositories and synchronize objects and references. `origin` is the most common remote name, but it is only a local configuration name—not the server itself. This page first provides a command reference, then connects the concepts in the [[git/10a-remote-collaboration-and-offline-two-clone-lab|Remote Collaboration Mental Model and Offline Lab]].

## Safety gate before any remote write

```powershell
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
git branch -vv
git remote
git log --oneline --decorate -5
```

Understand the repository root, current branch, upstream, remote names, and commits waiting to be pushed before considering a push or pull. `git remote -v`, `.git/config`, and complete configuration output can expose credentials embedded in URLs. Do not put a token in a URL or paste unredacted output into notes, logs, or tickets.

## `git remote add <name> <url>`

```powershell
git remote add origin https://github.com/example/project.git
```

Purpose: add a remote repository address to the current local repository.

First confirm the remote name:

```powershell
git remote
```

If you must inspect a URL, run `git remote get-url origin` locally. First confirm that it contains no userinfo, token, or private-server detail, then decide whether it is appropriate to record the output.

Notes:

- `<name>` is usually called `origin`, but it can also be `upstream` or another name.
- A repository can configure multiple remotes.

## `git push origin main`

```powershell
git push origin main
```

Purpose: push the local `main` branch to the remote named `origin`.

Appropriate when:

- local commits need to be synchronized to the remote main branch;
- you are pushing a specific branch for the first time and want to name both the remote and branch explicitly.

Note: if the remote branch contains commits absent locally, the push may be rejected. Fetch or pull first, then resolve the divergence.

## `git push`

```powershell
git push
```

Purpose: push references according to the repository's current push configuration. With the common `push.default=simple` setting, bare `git push` pushes the current branch to its corresponding upstream; settings such as `push.default` and `remote.*.push` can change the set of references pushed, so do not rely on memory alone.

Appropriate when:

- the current branch already has a tracking relationship set with `-u`;
- you are synchronizing the current branch after everyday development commits.

Check the upstream:

```powershell
git branch -vv
```

## `git push -u origin <name>`

```powershell
git push -u origin feature/demo
```

Purpose: push the current or named local branch to a remote for the first time and set its upstream.

Appropriate when:

- you are pushing a new feature branch for the first time;
- you want to use bare `git push` and `git pull` afterward.

Example:

```powershell
git push -u origin docs/git-cheat-sheet
```

## `git push --force-with-lease`

```text
git push --force-with-lease origin feature/demo
```

This is syntax reference, not a beginner exercise. Purpose: after rewriting local history, force-push with a protective check.

Appropriate when:

- a local rebase, amend, or squash requires updating the remote branch with the same name;
- you have confirmed that no one else's new remote commits would be overwritten.

> [!warning] It still rewrites history
> `--force-with-lease` is still a force push, not a concurrency-safety guarantee. When an explicit expected value is omitted, it normally depends on a local remote-tracking reference; an IDE or background fetch can update that reference and weaken the protection. In high-risk situations, constrain the remote, branch, and expected object ID, and follow the team process. Do not practice force pushes in beginner projects or shared main branches.

## `git push --tags`

```powershell
git push --tags
```

Purpose: push local tags to a remote.

Appropriate when:

- you created a tag after a release and need to synchronize it to the remote.

Common additions:

```powershell
git tag
git tag v1.0.0
git push origin v1.0.0
```

When pushing only one tag, prefer naming that tag explicitly instead of pushing every local tag at once.

## `git fetch origin`

```powershell
git fetch origin
```

Purpose: retrieve the latest commits and reference information from the remote (including information for `main`) without directly modifying the current local branch.

Appropriate when:

- you want to inspect what changed remotely before deciding whether to merge or rebase;
- you do not want `pull` to modify the current working branch automatically.

Follow-up inspection:

```powershell
git log --oneline HEAD..origin/main
git diff HEAD...origin/main
```

## `git pull --rebase`

```powershell
git pull --rebase
```

Purpose: fetch remote updates, then replay current local commits on top of the newest remote commits.

Appropriate when:

- you want to maintain linear history;
- a feature branch needs to catch up with its remote branch without creating a merge commit.

Note:

- Conflicts can occur during rebase. Resolve them, then continue:

```powershell
git rebase --continue
```

If you discover that the baseline or integration direction is wrong:

```powershell
git rebase --abort
```

## Choose the pull integration mode explicitly

```powershell
git pull --ff-only
git pull --rebase
git pull --no-rebase
```

`git pull` fetches first, then integrates according to an explicit option or configuration:

- `--ff-only`: permit only a fast-forward; reject the operation if history has diverged.
- `--rebase`: recreate local commits on top of the fetched baseline.
- `--no-rebase`: explicitly request a merge.

Git 2.55 documentation defines the default when no integration mode is selected as `--ff-only`, but repository or user configuration can select rebase, merge, or squash. Automation and teaching commands should state their intent explicitly; do not claim that bare `pull` necessarily merges.

Note: the integration stage of pull modifies the current branch and working tree. If you only want to inspect remote changes, `git fetch` is safer first.

## Authentication and practice boundary

Git for Windows can work with Git Credential Manager; different hosting platforms may use OAuth, a PAT, or an SSH key. Do not put an account password or token into a URL. Configure authentication according to the hosting platform's official documentation. The `example/project.git` address in this page is fictional and is not verified over the network.

For a complete account-free exercise, see [[git/10a-remote-collaboration-and-offline-two-clone-lab|Remote Collaboration and Offline Two-Clone Lab]]. It uses a local bare remote and two temporary clones; it does not touch real credentials or an online repository.

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git remote](https://git-scm.com/docs/git-remote)
- [git fetch](https://git-scm.com/docs/git-fetch)
- [git pull](https://git-scm.com/docs/git-pull)
- [git push](https://git-scm.com/docs/git-push)
- [gitcredentials](https://git-scm.com/docs/gitcredentials)
