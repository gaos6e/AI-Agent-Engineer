---
title: "03 File and Directory Operations"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux file and directory commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/03 文件和目录操作.md
translation_source_hash: 9532dd5951bc4125c62861dd4be2655174798296c2e9aca5af7c992cd4cbd82a
translation_route: zh-CN/Linux命令/03-文件和目录操作
translation_default_route: zh-CN/Linux命令/03-文件和目录操作
---

# 03 File and Directory Operations

## Learning objectives

- Create files and directories.
- Copy, move, rename, and remove files.
- Inspect file type and detailed file status.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `touch` | Create an empty file or update timestamps | Creates a missing file; otherwise updates its timestamp | `touch file_name` | `touch notes.txt` |
| `mkdir` | Create a directory | Make directory | `mkdir [options] directory_name` | `mkdir -p logs/2026` |
| `cp` | Copy a file or directory | Copies a source to a destination | `cp source destination` | `cp a.txt b.txt` |
| `mv` | Move or rename | Moves a source to a destination and can rename it | `mv source destination` | `mv old.txt new.txt` |
| `rm` | Remove a file or directory | Removes a specified path | `rm file` | `rm old.txt` |
| `file` | Determine file type | Identifies a format from its contents | `file file` | `file app.log` |
| `stat` | Inspect detailed file status | Shows metadata such as size, permissions, and time | `stat file` | `stat app.log` |

## Common scenarios

The following complete controlled lab does not rely on an existing directory named `project`. It creates a unique temporary directory, verifies the absolute path and ownership, then creates, copies, moves, and removes one explicit file:

```bash
if [ "$(id -u)" -eq 0 ]; then
  printf 'do not run this lab as root\n' >&2
  exit 1
fi

lab_root=$(realpath -e -- "${TMPDIR:-/tmp}") || exit 1
home_real=$(realpath -e -- "${HOME:?HOME is required}") || exit 1
current_real=$(pwd -P)
paths_overlap_tree() {
  if [ "$1" = '/' ] || [ "$2" = '/' ]; then
    return 0
  fi
  case "$1/" in "$2/"*) return 0 ;; esac
  case "$2/" in "$1/"*) return 0 ;; esac
  return 1
}
if [ "$lab_root" = '/' ] \
    || paths_overlap_tree "$lab_root" "$home_real" \
    || paths_overlap_tree "$lab_root" "$current_real"; then
  printf 'unsafe lab root overlaps home or working tree: %s\n' "$lab_root" >&2
  exit 1
fi

work=$(mktemp -d "$lab_root/file-ops.XXXXXX") || exit 1
work_real=$(realpath -e -- "$work") || exit 1
case "$work_real" in
  "$lab_root"/file-ops.*) ;;
  *) printf 'unexpected work path: %s\n' "$work_real" >&2; exit 1 ;;
esac
if [ ! -O "$work" ] || [ -L "$work" ]; then
  printf 'work ownership or symlink check failed\n' >&2
  exit 1
fi

cd -- "$work_real" || exit 1
[ "$(pwd -P)" = "$work_real" ] || exit 1
mkdir -p -- project/data/raw project/data/processed project/logs
touch -- project/README.md
cp -- project/README.md project/README.bak.md
cp -R -- project/data project/data_backup
mv -- project/README.bak.md project/backup.md
mv -- project/backup.md project/logs/

target=$(realpath -e -- "$work_real/project/logs/backup.md") || exit 1
case "$target" in
  "$work_real"/project/logs/backup.md) ;;
  *) printf 'unexpected target: %s\n' "$target" >&2; exit 1 ;;
esac
printf 'delete=%s\n' "$target"
rm -- "$target"
file -- project/README.md
stat -- project/README.md
find . -maxdepth 3 -print
```

The recursive-deletion signature is for reference only: `rm -r -- "$directory"`. This course does not offer directly copyable `rm -rf` because it bypasses some interactive and missing-file warnings. Its default `--preserve-root` gives special protection only to `/`; it does not protect a home directory, mount point, or incorrect variable. Keep the lab directory for inspection; do not remove it recursively automatically.

## Notes for beginners

- `rm` usually does not move files to a recycle bin, so confirm the path before execution.
- `rm -rf` is extremely dangerous. Never use it for `/`, `~`, or a path assembled from an empty variable.
- `cp -R` is the portable POSIX option for copying a directory. GNU `-r` is common, but scripts should check the target platform.
- `mv` both moves and renames; when the destination is an existing directory, it moves the source into it.
- Quote filenames with spaces, for example `mv "old name.txt" "new name.txt"`.
- `--` ends option parsing and protects a path beginning with `-`; variables must still be double-quoted.
- Recursive operations also require checks of symbolic links, mount points, and the expected root. Do not assume `sudo`.

## Safe exercise and acceptance

Run the complete lab above. Verify that the output path matches `$TMPDIR/file-ops.*`, the target belongs to the current user, and it is not a symbolic link. Retain `pwd -P`, `find . -maxdepth 3 -print`, and exit statuses. Confirm that only `project/logs/backup.md` was removed; do not practice recursive deletion.

## References

- [GNU Coreutils rm](https://www.gnu.org/software/coreutils/manual/html_node/rm-invocation.html)
- [GNU Coreutils cp](https://www.gnu.org/software/coreutils/manual/html_node/cp-invocation.html)
- [POSIX cp](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/cp.html)
