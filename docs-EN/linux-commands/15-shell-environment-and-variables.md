---
title: "15 Shell Environment and Variables"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux Shell environment and variable commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/15 Shell 环境与变量.md
translation_source_hash: 0588cccaa69eaf9d0ed15633accd3f54d14eb62b9016dbbe9721291d4ec394a7
translation_route: zh-CN/Linux命令/15-Shell-环境与变量
translation_default_route: zh-CN/Linux命令/15-Shell-环境与变量
---

# 15 Shell Environment and Variables

## Learning objectives

- Inspect and set environment variables.
- Create command aliases.
- Reload Shell configuration files.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `env` | Inspect or construct a child-process environment | Does not include all Shell variables and can contain secrets | `env` | `env -i PATH=/usr/bin /usr/bin/env` |
| `export` | Mark an environment variable | Makes it inheritable by later child commands; does not affect parent or existing processes | `export name=value` | `export APP_ENV=dev` |
| `alias` | Set a command alias | Gives a common command a shorter name | `alias name='command'` | `alias ll='ls -lah'` |
| `source` | Reload a script | Executes script contents in the current Shell | `source file` | `source ~/.bashrc` |
| `type` | Inspect a command type | Determines whether a command is a builtin, alias, function, or executable file | `type command` | `type cd` |
| `bash` | Enter a Bash Shell | Starts the Bash command interpreter | `bash` | `bash` |
| `zsh` | Enter a zsh Shell | Starts the zsh command interpreter | `zsh` | `zsh` |

## Common scenarios

Inspect only variables that may be disclosed:

```bash
printf 'home=%s\n' "$HOME"
printf 'app_env=%s\n' "${APP_ENV:-unset}"
```

Set a temporary variable:

```bash
export APP_ENV=dev
printf '%s\n' "$APP_ENV"
```

Add a directory to PATH:

```bash
export PATH="$PATH:$HOME/bin"
```

Set aliases:

```bash
alias ll='ls -lah'
alias gs='git status'
```

Loading configuration executes code in the current Shell, so these are syntax reference for trusted files only:

```text
. "$HOME/.bashrc"
source "$HOME/.bashrc"
```

Inspect a command source:

```bash
type cd
type ll
type python3
```

## Notes for beginners

- A variable set directly with `export` generally lasts only for the current terminal session.
- A Shell variable enters later child processes only after export; `env` does not list every unexported Shell variable.
- Bash login/non-login and interactive/non-interactive modes read different startup files. zsh rules differ too, so do not always write to `~/.bashrc`.
- `source` is Bash syntax; `.` is the POSIX form. Both execute arbitrary code in the current Shell, so load only trusted, reviewed files.
- An `alias` normally needs a Shell configuration file to persist.
- `type cd` shows that `cd` is a Shell builtin, which is why `which cd` can be counterintuitive.

## Single quotes, double quotes, and secrets

```bash
value='one two'
printf '<%s>\n' "$value"
printf '%s\n' 'literal $value'
printf '%s\n' "expanded $value"
```

Variable expansions should normally be in double quotes. Even in environment variables, secrets can appear in process environments, debug logs, crash dumps, or child processes. Do not use bare `env`, `set`, or `export -p` to gather troubleshooting evidence.

## PATH safety

- PATH is searched left to right. An empty component or untrusted writable directory can enable command hijacking.
- Before adding a directory, inspect its canonical path, owner, and permissions; do not put `.` at the front of PATH.
- A script can record a critical tool’s source with `command -v` first. High-security situations use controlled absolute paths and a minimal environment.

```bash
command -v -- python3
printf '%s\n' "$PATH" | tr ':' '\n' | nl -ba
```

Remove private paths and internal mount information before publishing a report.

## Exercise

Create an ordinary Shell variable `LOCAL_ONLY` and an exported `CHILD_VISIBLE`, then compare them in a child Bash:

```bash
LOCAL_ONLY='local'
export CHILD_VISIBLE='child'
bash -c 'printf "local=%s child=%s\n" "${LOCAL_ONLY:-unset}" "${CHILD_VISIBLE:-unset}"'
```

The expected result is that the child process cannot see the unexported variable. The exercise uses no real token and modifies no startup file.

## References

- [GNU Bash: Bourne Shell Builtins](https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html)
- [GNU Bash: Startup Files](https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html)
- [GNU Bash: Quoting](https://www.gnu.org/software/bash/manual/html_node/Quoting.html)
