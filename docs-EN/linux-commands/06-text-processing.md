---
title: "06 Text Processing"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux text-processing commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/06 文本处理.md
translation_source_hash: 3615fe3e892fca9fee101350fe0f631fede746d5868563ea94b681050c816af3
translation_route: zh-CN/Linux命令/06-文本处理
translation_default_route: zh-CN/Linux命令/06-文本处理
---

# 06 Text Processing

## Learning objectives

- Sort, deduplicate, and count text.
- Extract fields by delimiter.
- Perform simple text replacement and batch processing.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `sort` | Sort text lines | Sorts lexically or numerically | `sort file` | `sort names.txt` |
| `uniq` | Remove adjacent duplicate lines | Short for unique; usually used with `sort` | `uniq file` | `sort names.txt \| uniq` |
| `cut` | Extract text columns | Selects fields by character position or delimiter | `cut [options] file` | `cut -d ":" -f 1 /etc/passwd` |
| `awk` | Analyze text and process columns | Suitable for field-oriented text processing | `awk 'rules' file` | `awk '{print $1}' app.log` |
| `sed` | Stream text editor | Commonly replaces, removes, or prints lines | `sed 'expression' file` | `sed 's/old/new/g' file.txt` |
| `tr` | Translate or delete characters | Performs character-level transformations | `tr 'old_chars' 'new_chars'` | `printf '%s\n' abc \| tr '[:lower:]' '[:upper:]'` |
| `xargs` | Turn NUL-delimited input into arguments | Ordinary newlines cannot represent every legal filename; on GNU/Linux use with `-print0`/`-0` | `find ... -print0 \| xargs -0 command` | `find . -type f -name '*.log' -print0 \| xargs -0 -- wc -l` |

## Common scenarios

Sort and deduplicate:

```bash
sort names.txt | uniq
sort names.txt | uniq -c
```

Extract the first field of a colon-separated file:

```bash
cut -d ":" -f 1 /etc/passwd
```

Extract the first log field:

```bash
awk '{print $1}' app.log
```

Replace text in output:

```bash
sed 's/error/ERROR/g' app.log
```

Turn lowercase into uppercase:

```bash
printf '%s\n' 'linux' | LC_ALL=C tr '[:lower:]' '[:upper:]'
```

Pass found files safely to another command:

```bash
find . -type f -name '*.log' -exec wc -l -- {} +
find . -type f -name '*.log' -print0 | xargs -0 -- wc -l
```

## Notes for beginners

- `uniq` removes only adjacent duplicate lines, so use `sort` before `uniq` in the usual case.
- `sed 's/old/new/g' file` prints a transformed result by default; it does not modify the source file.
- `sed -i` is not POSIX. GNU and BSD/macOS differ on `-i` and backup-suffix syntax. This course first writes to a new file and compares it instead of editing in place.
- `awk` splits fields on whitespace by default; `$1` is the first field and `$2` is the second.
- An ordinary newline pipeline cannot safely represent every legal filename. The portable first choice is `find -exec ... {} +`; GNU/Linux can use `-print0 | xargs -0`.
- Sorting, case conversion, and character classes depend on locale. Set `LC_ALL=C` explicitly when reproducible byte order is required.

## Replacement exercise without overwriting a source file

```bash
sed 's/error/ERROR/g' -- app.log > app.log.new
cmp --silent -- app.log app.log.new
cmp_rc=$?
printf 'content_changed=%s\n' "$cmp_rc"
```

Inspect `app.log.new` first, then decide whether to replace the original with a controlled `mv`. Do not redirect output back into the input file.

## Mastery check

- [ ] I can explain why `uniq` usually requires sorted input.
- [ ] I can handle filenames containing spaces and newlines without bare `find | xargs`.
- [ ] I know that sed in-place editing and locales have platform differences.

## References

- [GNU Findutils: Security Considerations](https://www.gnu.org/software/findutils/manual/html_node/find_html/Security-Considerations.html)
- [POSIX sed](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/sed.html)
- [GNU gawk](https://www.gnu.org/software/gawk/manual/gawk.html)
