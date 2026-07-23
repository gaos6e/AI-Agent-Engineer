---
title: "Git Cheat Sheet: Git Configuration and Key Files"
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - config
lang: en
translation_key: Git/11-Git 配置与关键文件.md
translation_source_hash: 78a0eac4d29a395eb13113ffe8d0fc59454aad437b41b38619f317bf178f485a
translation_route: zh-CN/Git/11-Git-配置与关键文件
translation_default_route: zh-CN/Git/11-Git-配置与关键文件
---

# Git Configuration and Key Files

Git configuration controls behavior such as user name, email address, default branch, aliases, line-ending handling, and merge tools. Configuration can be repository-level, user-level, or system-level.

## `git config set user.name 'Your Name'`

```powershell
git config set user.name "Your Name"
```

Purpose: set the commit author name for the current repository.

Appropriate when:

- one repository needs a different identity;
- work and personal projects need different author information.

Common companion:

```powershell
git config set user.email "you@example.com"
```

Check the current repository configuration:

```powershell
git config get --local user.name
git config get --local user.email
```

## `git config --global ...`

```powershell
git config set --global user.name "Your Name"
git config set --global user.email "you@example.com"
```

Purpose: set global Git configuration for the current user, which affects all of that user's repositories by default.

Appropriate when:

- setting a default identity after installing Git for the first time;
- configuring a global editor, default branch name, or frequently used aliases.

Examples:

```powershell
git config set --global init.defaultBranch main
git config set --global core.editor "code --wait"
```

Note: repository-level configuration takes precedence over global configuration.

## `git config alias.st status`

```powershell
git config set alias.st status
```

Purpose: create a Git command alias. You can then use `git st` instead of `git status`.

Common aliases:

```powershell
git config set --global alias.st status
git config set --global alias.co checkout
git config set --global alias.br branch
git config set --global alias.cm commit
git config set --global alias.lg "log --oneline --graph --decorate"
```

Notes:

- Short aliases suit high-frequency commands.
- Avoid very short aliases for high-risk commands such as `reset --hard` or force pushes.

## `man git-config`

```powershell
man git-config
```

Purpose: view the manual for Git configuration.

Windows note:

- If `man` is unavailable locally, use:

```powershell
git help config
git config -h
```

Appropriate when:

- you need the precise definition of a configuration key;
- you need to confirm the values a configuration key supports.

## `.git/config`

```text
.git/config
```

Purpose: the local configuration file for the current repository.

Characteristics:

- It affects only the current repository.
- It commonly stores remote addresses, branch upstreams, and repository-level user names.
- It is normally not committed because it resides inside `.git/`.

Inspect it with:

```powershell
git config get --local --regexp '^(user|core|branch)\.'
```

## `~/.gitconfig`

```text
~/.gitconfig
```

Purpose: the global Git configuration file for the current user.

Characteristics:

- It affects most repositories of the current user.
- It commonly stores the global user name, email address, aliases, default editor, and similar settings.

Inspect it with:

```powershell
git config get --global user.name
git config get --global user.email
```

On Windows, `~` normally refers to the user home directory, such as `C:\Users\<username>`.

## `.gitignore`

```text
.gitignore
```

Purpose: declare which untracked files Git should ignore.

Appropriate when:

- ignoring caches, logs, build output, local configuration, and dependency directories;
- preventing accidental commits of temporary files.

Example:

```gitignore
__pycache__/
.env
*.log
dist/
node_modules/
```

Notes:

- `.gitignore` affects only untracked files. Files Git already tracks remain tracked after they are added to `.gitignore`.
- To stop tracking an already committed file while retaining the local file, use:

```powershell
git rm --cached -- .env
```

## `.gitattributes`

`.gitattributes` stores path-attribute rules shared with the repository. It can declare text normalization, diff drivers, and export behavior. For collaboration across Windows and Linux, start with conservative rules:

```gitattributes
* text=auto
*.sh text eol=lf
*.ps1 text eol=crlf
```

It does not automatically repair every historical line-ending issue. Before adding rules, align with the project convention and verify with `git diff --check` and actual tests, so one commit does not introduce unrelated whole-file line-ending changes.

## `.gitmodules` and the submodule boundary

A submodule is itself an independent Git repository. Its parent records the submodule URL configuration and one specific commit pointer; it does not merge the submodule's internal history into the parent repository. Inspect and commit the two layers separately:

```powershell
git status --short
git submodule status
git diff --submodule=short
```

After committing inside a submodule, the parent repository sees only the pointer change. Do not mistake a clean parent repository for proof that every submodule has no local modifications.

## Configuration precedence

Common precedence, from highest to lowest:

1. Command-line arguments.
2. Optional worktree-level configuration.
3. Repository-level configuration: `.git/config`.
4. User-level configuration: `~/.gitconfig`.
5. System-level configuration.

Trace a configuration source:

```powershell
git config list --show-origin --show-scope
```

> [!warning] Output can contain sensitive information
> Remote URLs, proxy settings, credential-helper configuration, or custom headers can appear in `.git/config` and complete configuration output. When troubleshooting, prefer `git config get <specific-key>`. Do not paste complete output directly into public notes, logs, or tickets, and do not embed a token in a URL.

> [!note] Compatibility note
> Older forms such as `git config user.name "Your Name"` and `git config --get user.name` remain compatible at present, but Git 2.55 documentation marks them deprecated. New lesson examples use the `set`, `get`, and `list` subcommands. If a subcommand is unavailable in an older Git installation, consult the local `git config -h` first.

## References

Checked against Git 2.55.0 official documentation, obtained **2026-07-14**.

- [git config](https://git-scm.com/docs/git-config)
- [gitignore](https://git-scm.com/docs/gitignore)
- [gitattributes](https://git-scm.com/docs/gitattributes)
- [gitmodules](https://git-scm.com/docs/gitmodules)
