---
title: "Git Cheat Sheet: Install Git Locally"
source: https://git-scm.com/install/windows
retrieved: 2026-06-04
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - installation
  - windows
lang: en
translation_key: Git/01-本机安装 Git.md
translation_source_hash: a7db54cd520b89141e37e027be3ea01a44bbb22fa0bec4fecd1d6cb3fff8e8f8
translation_route: zh-CN/Git/01-本机安装-Git
translation_default_route: zh-CN/Git/01-本机安装-Git
---

# Install Git Locally

This lesson installs Git locally on Windows and confirms that PowerShell can invoke `git` directly. Later lessons assume installation and basic configuration are complete.

## Recommended method: use `winget`

```powershell
winget install --id Git.Git -e --source winget
```

Purpose: install Git for Windows through the Windows package manager. After installation, it normally provides `git.exe`, Git Bash, and common credential-management components.

> [!warning] This changes local machine state
> Installation, upgrades, and `--global` configuration affect the current Windows user or the whole machine; they are not isolated-repository exercises. Confirm device-management policy first. On a corporate device, do not bypass administrator restrictions.

Appropriate when:

- Windows already has App Installer / winget.
- You want command-line installation and convenient later upgrades.
- You do not want to download an `.exe` installer manually.

If winget sources have not refreshed recently, run:

```powershell
winget source update
```

Notes:

- After installation, close and reopen PowerShell so the new `PATH` takes effect.
- If a corporate computer restricts winget or Store sources, use the official installer below.
- If the system requests elevation, rerun in an administrator PowerShell only in accordance with the actual security policy.

## Alternative: download the installer

Open the official Git for Windows installation page:

<https://git-scm.com/install/windows>

Download and run the Git for Windows installer. With no special requirement, the installer’s default options are normally suitable.

Options worth checking:

- **PATH environment variable:** choose an option that makes Git available in PowerShell / CMD, rather than Git Bash only.
- **Default editor:** if you do not know Vim, choose VS Code, Notepad, or another familiar editor.
- **Line-ending handling:** default choices are normally fine for a Windows-only learning environment; use project policy for cross-platform work.
- **Terminal emulator and credential management:** normally leave defaults.

## Verify installation

After reopening PowerShell, run:

```powershell
git --version
Get-Command git
```

Normally, `git --version` prints the installed Git version and `Get-Command git` shows the actual path to `git.exe`.

If PowerShell cannot find the command:

- close and reopen PowerShell first;
- check that Git actually finished installing;
- check whether the installer added Git to `PATH`;
- if it still fails, rerun the installer and repair the PATH-related option.

## First-use configuration

Git commits require a user name and email. After first installation, configure them:

```powershell
git config set --global user.name "Your Name"
git config set --global user.email "you@example.com"
```

View only the fields configured for this lesson:

```powershell
git config get --global user.name
git config get --global user.email
```

Notes:

- `user.name` and `user.email` become commit-author information; they need not match the operating-system login.
- An email address may be personal information. Confirm platform privacy-email options or team identity policy before public commits.
- If corporate and personal projects require different identities, set repository-level configuration in the particular repository; see [[git/11-git-configuration-and-key-files|Git Configuration and Key Files]].
- To connect GitHub, GitLab, or another remote repository, choose HTTPS sign-in, a credential manager, or an SSH key according to the platform.
- Do not put tokens in a remote URL or paste full `git config --list` / credential-manager output into notes, logs, or support requests.

## Lesson completion check

```powershell
git --version
Get-Command git
git config get --global user.name
git config get --global user.email
```

If you can explain that the four outputs come respectively from the Git program, PowerShell command resolution, and user-level configuration, move on. If identity fields are empty, set them now or set repository-only identity later in an isolated experimental repository.

> [!note] Legacy forms
> `git config --global user.name "Your Name"` and `git config --global --get user.name` remain compatible, but the Git 2.55 documentation marks the no-subcommand form as deprecated. This course uses `set`, `get`, and `list` subcommands in its primary examples.

## Further reading

After installation, continue with [[git/02-getting-started-and-creating-a-repository|Getting Started and Creating a Repository]] to initialize a local repository or clone a remote one.
