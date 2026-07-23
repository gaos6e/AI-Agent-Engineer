---
title: "05 Searching and Finding"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux search and find commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/05 搜索与查找.md
translation_source_hash: 1c52c86cf723f9952e1873607954ed86db38cc3373e08a1e97d757d961047f01
translation_route: zh-CN/Linux命令/05-搜索与查找
translation_default_route: zh-CN/Linux命令/05-搜索与查找
---

# 05 Searching and Finding

## Learning objectives

- Find files by name, type, and time.
- Search for keywords in file content.
- Locate the path of a command program.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `find` | Find files and directories | Recursively finds paths under a specified directory | `find path conditions` | `find . -name "*.log"` |
| `grep` | Search text content | Matches text in a file or input stream | `grep [options] pattern file` | `grep "error" app.log` |
| `command -v` | Inspect command resolution | POSIX Shell query for how a command name resolves | `command -v name` | `command -v python3` |
| `type -a` | Inspect a Bash command source | Shows aliases, functions, builtins, and multiple file locations | `type -a name` | `type -a python3` |
| `which` | Legacy path-query tool | Implementations vary and can omit aliases/functions/builtins | `which name` | `which python3` |
| `whereis` | Find command-related files | Finds binary, source, and manual locations | `whereis command` | `whereis bash` |
| `locate` | Find files quickly | Finds paths using a system index | `locate keyword` | `locate nginx.conf` |

## Common scenarios

Find files by name:

```bash
find . -name "*.log"
find ./logs -type f -name "*.log"
```

Find recently changed files:

```bash
find . -type f -mtime -7
```

Search file content:

```bash
grep "error" app.log
grep -r "deprecated_flag" ./src
grep -n "failed" app.log
```

Locate a command:

```bash
command -v -- python3
type -a -- python3
whereis bash
```

## Notes for beginners

- `find .` starts at the current directory.
- `find /` scans the entire system. It can be slow, cross mount points, and collect irrelevant paths; practice only in a lab directory.
- `grep -r` recursively searches a directory and is useful for finding a keyword in a project.
- `grep -n` shows line numbers for easier location.
- `locate` depends on an index, so it may not find a newly created file; `find` is more reliable in that situation.
- `find -mtime -7` uses rounded 24-hour periods, not the preceding seven calendar days.
- Use `grep -F` for literal text and `grep -E` or default BRE for regular expressions. In a regular expression, `.` matches any single character.

## Safe filenames and restricted scope

When passing find results to another command, prefer `-exec ... {} +`:

```bash
find ./logs -type f -name '*.log' -exec wc -l -- {} +
```

It does not split legal file names on newlines. GNU/Linux also supports `-print0 | xargs -0`; see [[linux-commands/06-text-processing|Text processing]].

## Exercise

In a lab directory, create three `.log` files and one log whose name contains a space. Complete four kinds of query: name, modification time, fixed string, and regular expression. For acceptance, record the starting path, hit count, and exit status; do not scan `/` or a real `/var/log`.

## References

- [GNU Findutils](https://www.gnu.org/software/findutils/manual/html_mono/find.html)
- [GNU grep](https://www.gnu.org/software/grep/manual/grep.html)
- [POSIX command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html)
