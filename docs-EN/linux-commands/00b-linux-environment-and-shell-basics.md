---
title: "Linux Environment and Shell Basics"
aliases:
  - Linux command-line introduction
  - Bash and a safe lab environment
tags:
  - AI-Agent-Engineer
  - Linux
  - Bash
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/00B-Linux环境与Shell基础.md
translation_source_hash: 21b85f1f6b1baab9645d7f9b4118b1ab7524a9013f26a10a88976dd4ea690d9f
translation_route: zh-CN/Linux命令/00B-Linux环境与Shell基础
translation_default_route: zh-CN/Linux命令/00B-Linux环境与Shell基础
---

# Linux Environment and Shell Basics

## Goal

Before learning commands, distinguish where a command runs, what interprets it, and which machine it affects. You will learn about terminals, Shells, Bash, distributions, WSL, containers, and remote hosts; understand commands, options, operands, quoting, expansion, `--`, and exit status; and create a controlled temporary lab directory.

## A terminal is not a Shell, and a Shell is not Linux

| Concept | Role | Common examples |
| --- | --- | --- |
| Terminal | Displays input/output and hosts an interactive session | Windows Terminal, SSH client |
| Shell | Parses command syntax, expands variables, and starts programs | PowerShell, Bash, zsh |
| Operating system/environment | Provides a kernel, filesystem, processes, and tools | Ubuntu, Debian, container image, WSL |
| Command | A Shell builtin, function, alias, or external program | `cd`, `printf`, `grep`, `python3` |

PowerShell’s `$env:PATH`, object pipeline, and quoting rules are not Bash’s `$PATH`, text pipeline, and expansion rules. When a code fence says `powershell` or `bash`, switch to that environment first.

## Which Linux environment might you be in?

- **WSL**: runs a Linux distribution on Windows. Windows paths are commonly mounted under `/mnt/c`, where permission and I/O semantics can differ from a native Linux filesystem.
- **Container**: process, network, filesystem, and resource views are limited by namespaces and cgroups. The image may lack `man`, systemd, procps, or an editor.
- **Remote host**: commands affect the remote system, so access, audit, change, and data boundaries apply.
- **Native Linux**: still confirm the distribution, Shell, permissions, and tool version. An Ubuntu tutorial is not automatically correct for every system.

Read-only WSL checks from PowerShell:

```powershell
wsl --status
wsl --list --verbose
```

If no distribution is installed, do not pretend Linux commands have been verified. Installing or enabling WSL changes local state, so follow current Microsoft documentation and device-management policy.

## Establish an environment fingerprint first

```bash
id
hostname
pwd
uname -srm
cat -- /etc/os-release
printf 'bash_version=%s\n' "${BASH_VERSION:-not-bash}"
ps -p "$$" -o pid=,comm=,args=
```

- `$SHELL` commonly comes from the login environment or account configuration and cannot reliably prove the Shell currently executing.
- A nonempty `$BASH_VERSION` proves the process has a Bash variable. `ps -p "$$"` observes the current Shell process but depends on procps.
- `/etc/os-release` describes the distribution user space, while `uname` primarily describes the kernel. Their sources can differ in WSL and containers.

## What makes up one command?

```text
command [options] [operands]
grep    -n       'ERROR' service.log
```

- **command**: the builtin, function, or program to run.
- **option**: changes behavior; common forms are short `-n` and long `--line-number`.
- **operand/argument**: the actual object, such as a file, text, or PID.
- **`--`**: many tools interpret it as “options end here,” so a following `-report.txt` is handled as a path. Not every command supports it; consult help first.

Confirm what the Shell will finally resolve:

```bash
command -v -- grep
type -a -- grep
type -a -- cd
```

`command -v` is a comparatively portable query for scripts. Bash `type -a` can additionally show aliases, functions, builtins, and multiple paths. `which` does not fully represent the Shell’s real resolution result.

## Quoting and expansion: what the Shell does before starting a program

```bash
name='Agent log'
printf '%s\n' "$name"
printf '%s\n' '$name'
printf '%s\n' "home=$HOME"
```

- Single quotes preserve an almost literal value; `'$name'` does not expand a variable.
- Double quotes allow expansions such as `$name` and `$(command)` while retaining the result as one argument.
- An unquoted variable expansion undergoes field splitting and pathname expansion again, so paths and external input normally must be written as `"$value"`.
- `*`, `?`, and `[...]` are globs expanded by the Shell against file names; they are not regular expressions. By default, Bash can leave an unmatched pattern as its literal text.

A minimal experiment for argument boundaries:

```bash
value='one two'
printf '<%s>\n' "$value"
printf '<%s>\n' $value
```

The first command receives one argument; the second commonly receives two. Real scripts should quote variables unless field splitting is specifically intended.

## Exit status is not screen text

Programs use 0 for success and nonzero values for different error or unmet-condition categories; consult each tool’s documentation for the exact meaning.

```bash
grep -q -- 'needle' /dev/null
status=$?
printf 'grep_status=%s\n' "$status"
```

GNU grep uses 1 for “no match” and 2 for an error. `$?` holds only the most recent foreground pipeline’s status and is overwritten after another command. [[linux-commands/07-pipelines-redirection-and-command-composition|Pipelines, redirection, and command composition]] explains propagation of intermediate pipeline failures in detail.

## Create a controlled lab directory

The following code applies only to GNU/Linux or an environment with GNU `realpath`. It creates a unique directory and does not remove it automatically:

```bash
lab_root=${TMPDIR:-/tmp}
lab_root_real=$(realpath -e -- "$lab_root") || exit 1
lab_dir=$(mktemp -d "$lab_root_real/agent-shell-lab.XXXXXX") || exit 1
lab_real=$(realpath -e -- "$lab_dir") || exit 1
case "$lab_real" in
  "$lab_root_real"/agent-shell-lab.*) ;;
  *) printf 'unexpected lab path: %s\n' "$lab_real" >&2; exit 1 ;;
esac
if [ ! -O "$lab_real" ] || [ -L "$lab_real" ]; then
  printf 'lab ownership or symlink check failed\n' >&2
  exit 1
fi
cd -- "$lab_real" || exit 1
printf 'lab=%s\n' "$PWD"
```

`mktemp -d` avoids name collisions. Checks of `realpath`, ownership, and symbolic links constrain the boundary of later write operations. Do not substitute `/`, a home directory, or a real project for these variables. The course intentionally does not run `rm -rf` automatically; decide on cleanup only after learning the deletion guardrails.

## Hands-on exercise

In the directory above, run:

```bash
touch -- 'report one.txt' '--literal-name'
printf '%s\n' ./*
printf 'line one\nline two\n' > 'report one.txt'
wc -l -- 'report one.txt'
command -v -- wc
printf 'last_status=%s\n' "$?"
```

Explain why `--` is required when creating `--literal-name`, why a path containing spaces must be quoted, who expands `./*`, and which command the final `$?` actually corresponds to.

## Common misconceptions

- **“The code is on my computer, so it affects only local Windows.”** Commands in an SSH or container terminal can affect a remote system or mounted volume.
- **“Linux commands can be copied directly to macOS.”** GNU and BSD options frequently differ.
- **“If I have sudo, I may execute it.”** Possessing permission is not the same as having authorization; elevation expands the incident blast radius.
- **“No command output means success.”** Check exit status and the expected side effect.
- **“A secret in an environment variable cannot leak.”** Process environments, debug output, history, and crash material can all expose it.

## Mastery check

- [ ] I can distinguish a terminal, Shell, Bash, WSL, container, and remote host.
- [ ] I can explain why POSIX, GNU extensions, and Linux-specific tools are different layers.
- [ ] I can identify a command source with `command -v` and `type -a`.
- [ ] I can explain the difference among single quotes, double quotes, unquoted variables, and globs.
- [ ] I can complete the exercise in a unique temporary directory and explain why it is not automatically deleted.

Next: [[linux-commands/01-help-and-basics|Help and basics]].

## References

Retrieved on **2026-07-14**.

- [GNU Bash Manual: Shell Expansions](https://www.gnu.org/software/bash/manual/html_node/Shell-Expansions.html)
- [GNU Bash Manual: Bash Variables](https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html)
- [POSIX.1-2024 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/V3_chap02.html)
- [POSIX command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html)
- [Microsoft WSL basic commands](https://learn.microsoft.com/windows/wsl/basic-commands)
