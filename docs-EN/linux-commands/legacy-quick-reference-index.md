---
title: "Legacy Linux Command Quick-Reference Index"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux command introduction index
lang: en
translation_key: Linux命令/目录.md
translation_source_hash: 8be0d1b52750534387b9221ce822926624a152d6ba7be0800bf1515a25ece25a
translation_route: zh-CN/Linux命令/目录
translation_default_route: zh-CN/Linux命令/目录
---

# Legacy Linux Command Quick-Reference Index

> [!note] Legacy quick-reference index
> This page retains the original course order to make historical material easy to find, but it is no longer a complete learning route. Beginners should start at [[linux-commands/00-index|the unified Linux Commands entry point]], which adds Shell foundations, services and logs, networking, package safety, and the integrated project.

These notes are for quickly looking up common Linux commands. They focus on completing daily file operations, viewing logs, searching text, managing processes, and using tmux in a terminal. Each category documents command purpose, meaning, basic usage, and examples.

## Recommended order

1. [[linux-commands/00b-linux-environment-and-shell-basics|Linux environment and Shell basics]]
2. [[linux-commands/01-help-and-basics|Help and basics]]
3. [[linux-commands/02-directories-and-paths|Directories and paths]]
4. [[linux-commands/03-file-and-directory-operations|File and directory operations]]
5. [[linux-commands/04-viewing-file-content|Viewing file content]]
6. [[linux-commands/05-searching-and-finding|Searching and finding]]
7. [[linux-commands/07-pipelines-redirection-and-command-composition|Pipelines, redirection, and command composition]]
8. [[linux-commands/06-text-processing|Text processing]]
9. [[linux-commands/08-permissions-and-users|Permissions and users]]
10. [[linux-commands/09-process-management|Process management]]
11. [[linux-commands/10-system-information|System information]]
12. [[linux-commands/11-services-and-logs|Services and logs]]
13. [[linux-commands/12-networking-and-ports|Networking and ports]]
14. [[linux-commands/13-archiving-and-extraction|Archiving and extraction]]
15. [[linux-commands/14-package-management-and-safe-downloads|Package management and safe downloads]]
16. [[linux-commands/15-shell-environment-and-variables|Shell environment and variables]]
17. [[linux-commands/16-tmux-terminal-multiplexing|tmux terminal multiplexing]]
18. [[linux-commands/17-agent-service-troubleshooting-practice-and-self-check|Agent service troubleshooting practice and self-check]]

## Quick entry points

| Category | Best for |
|---|---|
| [[linux-commands/00b-linux-environment-and-shell-basics\|Shell basics]] | Distinguish terminal, Shell, and Linux; understand command structure and exit status. |
| [[linux-commands/01-help-and-basics\|Help and basics]] | Find help, clear the screen, inspect history, and print text. |
| [[linux-commands/02-directories-and-paths\|Directories and paths]] | Know where you are, change directory, and inspect directory structure. |
| [[linux-commands/03-file-and-directory-operations\|File and directory operations]] | Create, copy, move, rename, and remove files. |
| [[linux-commands/04-viewing-file-content\|Viewing file content]] | View text, page through it, and inspect beginnings and endings. |
| [[linux-commands/05-searching-and-finding\|Searching and finding]] | Find files, text, and command locations. |
| [[linux-commands/06-text-processing\|Text processing]] | Sort, deduplicate, process fields, and replace text. |
| [[linux-commands/07-pipelines-redirection-and-command-composition\|Pipelines and redirection]] | Compose commands, save output, and distinguish standard output from error output. |
| [[linux-commands/08-permissions-and-users\|Permissions and users]] | Inspect identity, understand permissions, and apply least privilege. |
| [[linux-commands/09-process-management\|Process management]] | Inspect, start, and stop processes in a controlled way. |
| [[linux-commands/10-system-information\|System information]] | Inspect system, memory, disk, CPU, and load. |
| [[linux-commands/11-services-and-logs\|Services and logs]] | Inspect systemd services and journal data read-only. |
| [[linux-commands/12-networking-and-ports\|Networking and ports]] | Locate issues across addresses, listening ports, DNS, TLS, and HTTP. |
| [[linux-commands/13-archiving-and-extraction\|Archiving and extraction]] | Package, compress, and safely inspect archives. |
| [[linux-commands/14-package-management-and-safe-downloads\|Package management]] | Identify a package manager, verify downloads, and avoid high-risk installation pipelines. |
| [[linux-commands/15-shell-environment-and-variables\|Shell environment and variables]] | Manage variables, child-process environments, aliases, and Shell configuration. |
| [[linux-commands/16-tmux-terminal-multiplexing\|tmux terminal multiplexing]] | Restore sessions after disconnects, split panes, and preserve an interactive terminal. |
| [[linux-commands/17-agent-service-troubleshooting-practice-and-self-check\|Integrated project]] | Complete log, resource, port, and process troubleshooting in a controlled temporary directory. |

## Minimal must-know commands

The following is a list of command names, not a directly pasteable script. For deletion, elevation, or process termination, return to the relevant lesson to verify target, permissions, and exit status.

```text
pwd
ls -lah
cd
mkdir
touch
cp
mv
rm -- file_name
cat
less
tail -f
grep
find
chmod
ps
kill -TERM controlled_process_PID
df -h
tar
tmux
```
