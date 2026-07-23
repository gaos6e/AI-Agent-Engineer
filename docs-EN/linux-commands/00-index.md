---
title: "Linux Commands"
tags:
  - ai-agent-engineer
  - engineering-foundations
  - Linux
aliases:
  - Linux command learning path
  - Linux CLI introduction
source_checked: 2026-07-14
source_baseline:
  - GNU Coreutils 9.11
  - GNU Bash manual current at retrieval
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 8
ai_learning_schema: 2
ai_learning_id: linux-cli
ai_learning_domain: foundations
ai_learning_catalog_order: 800
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 70
ai_learning_track_agent_app_kind: optional
ai_learning_track_rag_order: 70
ai_learning_track_rag_kind: optional
ai_learning_track_agent_platform_order: 70
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 70
ai_learning_track_multimodal_realtime_kind: optional
lang: en
translation_key: Linux命令/00-目录.md
translation_source_hash: 36aacfaab951dd51d562b259c22823fe14dd137519571daa8667f6ae1e87d0c1
translation_route: zh-CN/Linux命令/00-目录
translation_default_route: zh-CN/Linux命令/00-目录
---

# Linux Commands

## Course overview

The Linux command line is foundational for deployments, containers, server troubleshooting, and remotely operated Agent services. This course retains its quick-reference layer and fills in the Shell mental model, services and logs, networking and ports, package management, and an integrated practice. It first teaches the safe habit of confirming the environment, identity, current directory, and target object before executing a command, then covers files, text, pipelines, permissions, processes, resources, services, networking, environment variables, and tmux.

The main local environment remains Windows 11 with PowerShell 7. Run Linux examples in WSL, a container, or an explicitly remote Linux shell; do not mix Bash and PowerShell syntax in the same command context.

> [!important] Four compatibility boundaries
> This course distinguishes portable POSIX syntax, GNU tool extensions, Linux-specific tools, and Bash builtins. `systemd`, `procps-ng`, `util-linux`, and `iproute2` are not present on every Unix system or minimal container, and macOS/BSD options may differ. Confirm the environment and local help before using an example.

## Where this fits in the overall path

This course belongs to the Engineering Foundations stage. Prefer PowerShell for routine local file work; use this course when a task moves into a Linux server, Docker container, or WSL. Later MLOps, LLMOps, runtime monitoring, and automation work depend on these capabilities.

## Learning objectives

- Identify the current shell, user, host, directory, and command source.
- Safely complete path, file, inspection, search, text-processing, and pipeline work.
- Understand standard input, standard output, standard error, and exit status.
- Read permissions, processes, disk, memory, and load information instead of guessing during troubleshooting.
- Manage sessions, environment variables, and long-running work without leaking credentials.
- Read evidence at the service, log, listening-port, DNS, TCP, TLS, and HTTP layers.
- Identify the distribution and package source instead of blindly downloading and executing software.
- Complete a controlled troubleshooting exercise for a local loopback Agent simulation service and produce an evidence report.

## Prerequisites

Knowing how to change directories in PowerShell and how to interpret paths is enough. Complete [[git/00-index|Git]] first if possible; no server experience is required. Perform every exercise only in your own WSL, container, or explicitly authorized Linux environment.

### Confirm the environment

Before entering WSL from PowerShell, check:

```powershell
wsl --status
wsl --list --verbose
```

After entering a Linux shell:

```bash
whoami
hostname
pwd
printf 'bash_version=%s\n' "${BASH_VERSION:-not-bash}"
ps -p "$$" -o comm=
```

`SHELL` commonly states the preferred shell configured for the login environment; it cannot reliably prove which shell is running now. WSL installation and arguments can change, so consult current Microsoft documentation when implementing it. A remote server also requires compliance with organizational access, audit, and change processes.

## Recommended order

1. [[linux-commands/00b-linux-environment-and-shell-basics|Linux environment and Shell basics]]: distinguish PowerShell, a terminal, a Shell, Bash, WSL, containers, and remote hosts.
2. [[linux-commands/01-help-and-basics|Help and basics]]: inspect help, command sources, exit status, and history risks.
3. [[linux-commands/02-directories-and-paths|Directories and paths]]: always know where you are.
4. [[linux-commands/03-file-and-directory-operations|File and directory operations]]: create, copy, move, and remove safely.
5. [[linux-commands/04-viewing-file-content|Viewing file content]]: inspect complete files, beginnings, endings, and live appends.
6. [[linux-commands/05-searching-and-finding|Searching and finding]]: locate evidence by name and content.
7. [[linux-commands/07-pipelines-redirection-and-command-composition|Pipelines, redirection, and command composition]]: understand file descriptors, data flow, and pipeline status.
8. [[linux-commands/06-text-processing|Text processing]]: sort, deduplicate, extract fields, and batch safely.
9. [[linux-commands/08-permissions-and-users|Permissions and users]]: identify identities, ownership, and least privilege.
10. [[linux-commands/09-process-management|Process management]]: observe processes, verify PIDs, send signals, and manage background jobs.
11. [[linux-commands/10-system-information|System information]]: check disk, inodes, memory, CPU, and load.
12. [[linux-commands/11-services-and-logs|Services and logs]]: identify the service manager and safely read unit and journal evidence.
13. [[linux-commands/12-networking-and-ports|Networking and ports]]: investigate by address, route, listener, DNS, TCP, TLS, and HTTP layers.
14. [[linux-commands/13-archiving-and-extraction|Archiving and extraction]]: inspect archives and extract them safely into an empty directory.
15. [[linux-commands/14-package-management-and-safe-downloads|Package management and safe downloads]]: identify package managers, sources, and download-verification boundaries.
16. [[linux-commands/15-shell-environment-and-variables|Shell environment and variables]]: understand variables, quoting, environment scope, PATH, and configuration files.
17. [[linux-commands/16-tmux-terminal-multiplexing|tmux terminal multiplexing]]: preserve remote sessions and long-running jobs without treating tmux as a service manager.
18. [[linux-commands/17-agent-service-troubleshooting-practice-and-self-check|Agent service troubleshooting practice and self-check]]: complete the log and loopback-service troubleshooting loop in one unique temporary directory.

The original quick index remains at [[linux-commands/legacy-quick-reference-index|the legacy quick-reference index]], and scattered commands remain at [[linux-commands/00a-common-commands-legacy-quick-reference|legacy common commands]]. Neither retains an independent learning route; this page is the unified course entry point.

## Hands-on practice and project entry point

- Run file-modifying commands only in an experiment directory that you own.
- Before deletion, recursion, permission, or process-signal commands, print the resolved target and confirm it with read-only commands.
- See [[linux-commands/17-agent-service-troubleshooting-practice-and-self-check|Agent service troubleshooting practice and self-check]] for the integrated project; its core path requires no administrator privilege.

## Mastery criteria

- [ ] I can state whether a command runs in PowerShell, WSL, a container, or remote Linux.
- [ ] I can quote paths containing spaces, globs, or leading `-` correctly and use `--`.
- [ ] I can compose `find`/`grep`/`sort`/`uniq` and explain every pipeline stage.
- [ ] I can distinguish stdout, stderr, and exit status, including the caveats of pipeline failure propagation.
- [ ] I can investigate logs, processes, port-related clues, disk, and memory read-only before proposing an action.
- [ ] I do not use `sudo`, recursive deletion, permissive permissions, or forceful termination as a default repair.
- [ ] I can use environment variables and tmux safely without putting secrets into history or command output.

## Connections to other courses

| Later course | Connection |
| --- | --- |
| [[git/00-index\|Git]], [[python-fundamentals/00-index\|Python Fundamentals]] | Obtain source code on a server, create environments, and run scripts. |
| [[mlops/00-index\|MLOps]], [[llmops/00-index\|LLMOps]] | Deployment, logs, resources, and process management need Linux fundamentals. |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | The command line gathers evidence; long-term monitoring needs metrics and alerting systems. |
| [[ai-safety/00-index\|AI Safety]] | Permissions, secrets, command injection, and auditing are Agent-tool boundaries. |

## Primary references

Checked on **2026-07-14**. GNU Coreutils 9.11 was the current stable baseline in this review; distribution-packaged versions can be older. This round completed all Bash static syntax checks in Git Bash and actually ran the integrated script’s deterministic `--log-only` mode. No usable WSL distribution was available locally, so the Linux loopback, systemd, iproute2, and tmux projects were not executed on a live Linux system.

- [GNU Coreutils 9.11 Manual](https://www.gnu.org/software/coreutils/manual/coreutils.html)
- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html)
- [GNU grep Manual](https://www.gnu.org/software/grep/manual/grep.html)
- [GNU findutils Manual](https://www.gnu.org/software/findutils/manual/html_mono/find.html)
- [POSIX.1-2024 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/V3_chap02.html)
- [systemd systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [systemd journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [tmux documentation](https://github.com/tmux/tmux/wiki)
- [Microsoft: Basic commands for WSL](https://learn.microsoft.com/windows/wsl/basic-commands)

**Subject to change:** command options depend on distribution and tool version. Verify the current environment with `command --version`, `command --help`, or `man command` first.
