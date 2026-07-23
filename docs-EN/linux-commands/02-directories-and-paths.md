---
title: "02 Directories and Paths"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux directory and path commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/02 目录与路径.md
translation_source_hash: ddb74f33f84116ef2fbd0c606392d5191d04c9eab0acbc3bacfe3ffae042934b
translation_route: zh-CN/Linux命令/02-目录与路径
translation_default_route: zh-CN/Linux命令/02-目录与路径
---

# 02 Directories and Paths

## Learning objectives

- Determine the current directory.
- List a directory’s contents and change directories.
- Understand absolute paths, relative paths, a home directory, and a parent directory.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `pwd` | Show the current directory | Print working directory | `pwd` | `pwd` |
| `ls` | List files and directories | List directory contents | `ls [options] [path]` | `ls -lah` |
| `cd` | Change directories | Change the current directory | `cd path` | `cd /var/log` |
| `tree` | Show a directory tree | Displays contents hierarchically | `tree [path]` | `tree .` |
| `dirname` | Get a path’s directory part | Removes the final file or directory component | `dirname path` | `dirname /tmp/a.txt` |
| `basename` | Get a path’s file-name part | Returns the last path component | `basename path` | `basename /tmp/a.txt` |
| `realpath` | Normalize and resolve a path | Outputs a canonical absolute path on GNU/Linux | `realpath [options] path` | `realpath -e -- .` |
| `readlink` | Read a symbolic link | Shows a link target; options vary by implementation | `readlink path` | `readlink /proc/self/exe` |

## Common scenarios

Show the current location and files:

```bash
pwd
ls -lah -- .
```

Change to common directories:

```bash
cd ~
cd ..
cd /var/log
cd -
```

Show directory hierarchy:

```bash
tree .
tree -L 2 .
```

Split and resolve paths:

```bash
dirname /home/user/project/app.py
basename /home/user/project/app.py
realpath -e -- .
```

## Notes for beginners

- A path beginning with `/` is absolute, for example `/home/user`.
- A path not beginning with `/` is relative, for example `./data` or `../logs`.
- `~` is the current user’s home directory.
- `.` is the current directory and `..` is the parent directory.
- `ls -lah` is common: `-l` shows details, `-a` includes hidden files, and `-h` uses readable sizes.
- Some systems do not install `tree` by default; use `ls` first when it is absent.
- The path shown by a symbolic link can differ from its final object. Resolve and verify an absolute path before writes, deletion, or recursive operations.
- In WSL, `/mnt/c/...` points to the Windows filesystem; permissions, case behavior, and I/O performance can differ from a Linux home directory.
- Quote variables and paths with spaces, for example `cd -- "$HOME/My Project"`.

## Temporary-directory exercise

First use [[linux-commands/00b-linux-environment-and-shell-basics|the safe lab environment]] to create a unique directory, then run:

```bash
path_lab=$(mktemp -d "$lab_real/path-lab.XXXXXX") || exit 1
mkdir -- "$path_lab/real dir"
ln -s -- "$path_lab/real dir" "$path_lab/link dir"
cd -- "$path_lab/link dir"
printf 'logical=%s\n' "$PWD"
printf 'physical=%s\n' "$(pwd -P)"
realpath -e -- .
cd -- "$lab_real"
```

Explain the difference among a logical path, physical path, and symbolic-link resolution. Inspect the target text stored in the link with `readlink -- "$path_lab/link dir"`. `$lab_real` comes from the introduction; do not assume it still exists in a newly opened Shell. Keep the lab directory for manual inspection; do not remove it recursively automatically.

## References

- [GNU Coreutils: Working context](https://www.gnu.org/software/coreutils/manual/html_node/Working-context.html)
- [GNU Coreutils realpath](https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html)
