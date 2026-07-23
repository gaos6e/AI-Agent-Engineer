---
title: "01 Help and Basics"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux help and basic commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/01 帮助与基础.md
translation_source_hash: af74352dc6d922868e3da1af0719da1e68068093c8cdf302988fd4a49c6014d6
translation_route: zh-CN/Linux命令/01-帮助与基础
translation_default_route: zh-CN/Linux命令/01-帮助与基础
---

# 01 Help and Basics

## Learning objectives

- Know how to query command help.
- Inspect and reuse command history safely.
- Clear a terminal and print text and variables.
- Determine whether a command comes from an alias, function, builtin, or external program, and preserve its exit status.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `man` | Read a command manual | Short for manual; shows a complete command description | `man command_name` | `man ls` |
| `--help` | Read brief help | Many GNU and third-party external commands support it; it is not a uniform POSIX requirement | `command --help` | `cp --help` |
| `history` | View command history | Lists commands executed by the current shell | `history` or `history count` | `history 20` |
| `clear` | Clear the screen | Clears the current terminal display | `clear` | `clear` |
| `printf` | Print formatted output | More predictable behavior than `echo` | `printf 'format' arguments` | `printf '%s\n' "$HOME"` |
| `command -v` | Query command resolution | Returns the location or type clue the Shell will use | `command -v name` | `command -v python3` |
| `type` | Inspect Bash command type | Shows an alias, function, builtin, or file | `type -a name` | `type -a cd` |

## Common scenarios

Find out how to use a command:

```bash
man tar
tar --help
```

Show recently executed commands:

```bash
history 30
```

Print text and an environment-variable fact:

```bash
printf '%s\n' 'hello linux'
printf 'path_entries_are_set=%s\n' "${PATH:+yes}"
```

Clear the terminal screen:

```bash
clear
```

## Notes for beginners

- In a `man` page, press `/` to search and `q` to quit.
- Many GNU and third-party external commands use `--help` for a quick option list, but POSIX does not standardize it. For Bash builtins, prefer `help name` or the Shell manual; on BSD/macOS, follow the local `man` page.
- `history` only displays history; it does not automatically run it. Confirm safety before rerunning a historical command.
- History can include URLs, arguments, and accidentally entered secrets. Do not put tokens directly on a command line or publicly paste complete history.
- Query only variables that are safe to disclose. Bare `env` or printing a full PATH/proxy configuration can expose local information.
- `$?` preserves only the most recent foreground pipeline’s status. Copy it into a variable immediately before another command runs.

## Minimal exercise

```bash
type -a -- cd
command -v -- grep
grep -q -- 'needle' /dev/null
grep_rc=$?
printf 'grep_rc=%s\n' "$grep_rc"
```

Explain what kind of command `cd` and `grep` are, and use GNU grep documentation to explain exit status 1. Complete [[linux-commands/00b-linux-environment-and-shell-basics|Linux environment and Shell basics]] first for environment, quoting, and expansion.

## References

- [GNU Bash Builtins](https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html)
- [POSIX command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html)
