---
title: "07 Pipelines, Redirection, and Command Composition"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux pipelines, redirection, and command composition
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/07 管道重定向与命令组合.md
translation_source_hash: 1b0d81761730f0eeecc637c31b2c34a3e5c5361c105f24a7b6dfd98c8e95454e
translation_route: zh-CN/Linux命令/07-管道重定向与命令组合
translation_default_route: zh-CN/Linux命令/07-管道重定向与命令组合
---

# 07 Pipelines, Redirection, and Command Composition

## Learning objectives

- Pass one command’s output to another command.
- Save output to a file.
- Decide whether to continue based on the preceding command’s success or failure.
- Distinguish stdin, stdout, stderr, and file descriptors, and verify intermediate pipeline failures.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `\|` | Pipeline | Passes standard output from the left command to the right command | `command1 \| command2` | `ls -lah \| grep -F '.log'` |
| `>` | Overwrite a file | Writes standard output to a file and replaces existing content | `command > file` | `echo hello > a.txt` |
| `>>` | Append to a file | Appends standard output to a file | `command >> file` | `echo world >> a.txt` |
| `<` | Read input from a file | Uses file contents as command input | `command < file` | `sort < names.txt` |
| `2>` | Redirect error output | Writes standard error to a file | `command 2> file` | `find . -name a 2> errors.txt` |
| `&&` | Run after success | Runs the right command only when the left succeeds | `command1 && command2` | `mkdir test && cd test` |
| `\|\|` | Run after failure | Runs the right command only when the left fails | `command1 \|\| command2` | `cd project \|\| echo "directory does not exist"` |
| `tee` | Display and write simultaneously | Copies stdin to stdout and a file | `command \| tee file` | `printf '%s\n' ok \| tee result.txt` |

## Common scenarios

Filter command output:

```bash
ls -lah -- . | grep -F '.log'
pgrep -a -u "$(id -u)" -f 'python3'
```

The first command demonstrates text filtering only. Process discovery uses `pgrep` so that `ps | grep` does not mistake grep’s own command line for a target process.

Save output to a file:

```bash
echo "hello" > message.txt
echo "world" >> message.txt
```

Save error output separately:

```bash
find . -name '*.conf' > find_results.txt 2> find_errors.txt
```

Continue only after success:

```bash
mkdir project && cd project
```

Print a message after failure:

```bash
cd project || echo "project directory does not exist"
```

## Notes for beginners

- `>` overwrites a file; use `>>` when original content must be retained.
- A pipeline `|` passes output text, not the file itself.
- `2>` redirects only error output and does not affect normal output.
- `&&` is commonly used to avoid continuing when a preceding command failed.
- Command composition is powerful. Preview with non-destructive commands before deleting or overwriting files.

## The three standard streams and redirection order

Linux processes normally read stdin from file descriptor 0, write stdout to 1, and write stderr to 2. Redirections are processed left to right:

```text
command_that_may_fail > combined.log 2>&1
command_that_may_fail 2>&1 > stdout-only.log
```

The two commands are not equivalent. The first makes fd 2 follow fd 1 after fd 1 points to the file; the second first points fd 2 at the original terminal and then moves fd 1 separately. The command name is only a signature explanation; do not execute it unchanged.

> [!danger] Redirection truncates first
> `sort data.txt > data.txt` can truncate the input file before `sort` reads it. Write output to a new file, validate it, and then replace it in a controlled way.

## Pipeline exit status

By default, Bash uses the last command’s status as the whole pipeline status:

```bash
false | true
pipeline_rc=$?
printf 'pipeline_rc=%s\n' "$pipeline_rc"
```

Assigning `$?` also overwrites `PIPESTATUS`, so rerun the pipeline and save the parts immediately:

```bash
false | true
parts=("${PIPESTATUS[@]}")
printf 'left=%s right=%s\n' "${parts[0]}" "${parts[1]}"
```

When Bash `pipefail` is enabled, a pipeline returns the status of its rightmost nonzero command; only a fully successful pipeline returns 0:

```bash
set -o pipefail
false | true
pipeline_rc=$?
printf 'pipeline_rc=%s\n' "$pipeline_rc"
```

`PIPESTATUS` and `pipefail` are Bash capabilities, not features of every POSIX Shell. A script also cannot rely only on `set -e` instead of explicit error handling because its behavior is context-sensitive in conditionals, subshells, and compound commands.

## Controlled exercise

Create `input.txt` in a lab directory, write stdout, stderr, and combined output to three new files, then construct `grep 'missing' input.txt | wc -l`. Compare its default status, `${PIPESTATUS[@]}`, and `pipefail`. Explain in the report why “0 lines” cannot prove that grep succeeded.

## References

- [GNU Bash: Redirections](https://www.gnu.org/software/bash/manual/html_node/Redirections.html)
- [GNU Bash: Pipelines](https://www.gnu.org/software/bash/manual/html_node/Pipelines.html)
- [POSIX Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/V3_chap02.html)
