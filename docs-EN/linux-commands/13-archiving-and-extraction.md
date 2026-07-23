---
title: "13 Archiving and Extraction"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux archive and extraction commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/13 压缩与解压.md
translation_source_hash: e87241cb6f66cc9c3af0445c14cfb06fd844d861c90a2bc9587b514a6e8ff9fc
translation_route: zh-CN/Linux命令/13-压缩与解压
translation_default_route: zh-CN/Linux命令/13-压缩与解压
---

# 13 Archiving and Extraction

## Learning objectives

- Package a directory.
- Compress and extract common `.tar.gz`, `.gz`, and `.zip` files.
- Distinguish packaging from compression.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `tar` | Archive and extract | Tape archive; commonly handles `.tar` and `.tar.gz` | `tar [options] archive path` | `tar -czf archive.tar.gz folder/` |
| `gzip` | gzip compression | Compresses one file to `.gz` | `gzip file` | `gzip app.log` |
| `gunzip` | gzip extraction | Extracts a `.gz` file | `gunzip file.gz` | `gunzip app.log.gz` |
| `zip` | zip compression | Creates a `.zip` archive | `zip [options] archive path` | `zip -r archive.zip folder/` |
| `unzip` | zip extraction | Extracts a `.zip` archive | `unzip archive` | `unzip archive.zip` |

## Common scenarios

Package a directory as `.tar.gz`:

```bash
tar -czf project.tar.gz -- project/
```

Extract `.tar.gz`:

```bash
mkdir -- extract-target
tar -xzf project.tar.gz -C extract-target
```

List archive contents without extracting:

```bash
tar -tzf project.tar.gz
```

Compress and extract an individual gzip file:

```bash
gzip app.log
gunzip app.log.gz
```

Create a zip archive in a unique lab directory and extract it into a new empty directory:

```bash
zip_lab=$(mktemp -d "${TMPDIR:-/tmp}/zip-lab.XXXXXX") || exit 1
if [ ! -O "$zip_lab" ] || [ -L "$zip_lab" ]; then
  printf 'zip lab ownership or symlink check failed\n' >&2
  exit 1
fi
mkdir -- "$zip_lab/project"
printf 'fixture\n' > "$zip_lab/project/README.txt"
(cd -- "$zip_lab" && zip -rq project.zip project) || exit 1
unzip -l "$zip_lab/project.zip"
zip_dest=$(mktemp -d "$zip_lab/extract.XXXXXX") || exit 1
unzip -q "$zip_lab/project.zip" -d "$zip_dest"
find "$zip_dest" -maxdepth 2 -print
```

## Notes for beginners

- Common `tar` options: `c` creates, `x` extracts, `t` lists, `z` uses gzip, and `f` names the file.
- `.tar` is mainly packaging, `.gz` is mainly compression, and `.tar.gz` packages first then compresses.
- `gzip file` normally replaces the original with `file.gz`; the original file is not retained.
- Before extraction, use `tar -tzf` or `unzip -l` to see what is inside.
- Extract an unknown archive into an empty directory first to avoid scattering files or overwriting existing ones.

## Additional risks from untrusted archives

“List first + use a new empty directory” is only a minimum starting point. A malicious archive can contain absolute paths, `..` path traversal, symbolic/hard links, special files, unusual permissions, or ownership information. Do not extract an unknown archive as root, directly into a project, home directory, or system path.

A controlled GNU tar check flow:

```bash
archive=$(realpath -e -- project.tar.gz) || exit 1
tar -tzf "$archive"
dest=$(mktemp -d "${TMPDIR:-/tmp}/archive-lab.XXXXXX") || exit 1
dest_real=$(realpath -e -- "$dest") || exit 1
printf 'archive=%s\ndestination=%s\n' "$archive" "$dest_real"
tar --extract --gzip --file="$archive" \
  --directory="$dest_real" \
  --no-same-owner \
  --no-same-permissions
find "$dest_real" -mindepth 1 -maxdepth 3 -print
```

You must still inspect absolute paths, `..`, and intended links in the listing. GNU tar and the common macOS bsdtar/libarchive differ in options and default protections; read the manual for the actual implementation.

## Exercise and mastery check

In a lab directory, create two small text files, archive them, list the contents, extract them into a brand-new directory, and compare with `cmp`. Completion requires explaining packaging vs. compression, whether the original remains, the extraction destination, and the untrusted-archive boundary.

## References

- [GNU tar manual](https://www.gnu.org/software/tar/manual/tar.html)
- [GNU tar: Extracting Archives from Untrusted Sources](https://www.gnu.org/software/tar/manual/html_node/extracting-untrusted-archives.html)
