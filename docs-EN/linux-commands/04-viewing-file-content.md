---
title: "04 Viewing File Content"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux commands for viewing file content
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/04 查看文件内容.md
translation_source_hash: 06dd90361d405429b087ff93f56e06eccc7f4eb0e0da0e24b76f1e58ba42560c
translation_route: zh-CN/Linux命令/04-查看文件内容
translation_default_route: zh-CN/Linux命令/04-查看文件内容
---

# 04 Viewing File Content

## Learning objectives

- View a text file directly.
- Page through large files.
- View a file’s beginning, end, and live appended content.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `cat` | Print an entire file | Short for concatenate; commonly prints a small file directly | `cat file` | `cat README.md` |
| `less` | Page through a file | Suitable for browsing a large file, with scrolling and search | `less file` | `less app.log` |
| `head` | View a file’s beginning | Shows the first 10 lines by default | `head [options] file` | `head -n 20 app.log` |
| `tail` | View a file’s end | Shows the final 10 lines by default and can follow changes | `tail [options] file` | `tail -f app.log` |
| `wc` | Count newlines, words, bytes, or characters | By default shows newline, word, and byte counts; `-m` counts characters | `wc [options] file` | `wc -l app.log` |

## Common scenarios

View a small file:

```bash
cat config.txt
```

Page through a large log:

```bash
less app.log
```

View the beginning and end:

```bash
head -n 20 app.log
tail -n 50 app.log
```

Follow newly appended log content:

```bash
tail -F -- app.log
```

Count lines in a file:

```bash
wc -l app.log
```

## Notes for beginners

- `cat` is not suitable for opening a very large log directly because it can flood the terminal.
- In `less`, press `/keyword` to search, `n` for the next match, and `q` to quit.
- `tail -f` occupies the terminal continuously; press `Ctrl-c` to stop it.
- GNU `tail -F` retries by name and handles common log rotation. Options are not identical on every platform.
- `wc -l` counts newline characters; the final text segment without a trailing newline does not increase that count. `wc -c` counts bytes and `wc -m` counts characters.
- Logs can contain user input, tokens, internal addresses, and command lines. Do not publish an entire log directly.

## Log-viewing exercise

On the fictional log from the integrated project, compare `head -n 2`, `tail -n 2`, `wc -l`, and `less`. State what range each command reads, whether it keeps running, and whether its output belongs in a report.

## References

- [GNU Coreutils wc](https://www.gnu.org/software/coreutils/wc)
- [GNU Coreutils tail](https://www.gnu.org/software/coreutils/manual/html_node/tail-invocation.html)
