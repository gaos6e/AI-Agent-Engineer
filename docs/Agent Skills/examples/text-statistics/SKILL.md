---
title: "Text Statistics"
name: text-statistics
description: Count word-like tokens, Unicode characters, and logical lines with
  deterministic JSON output. Use when a user asks for text-size statistics, word
  or line counts, or a machine-readable count summary; do not use for rewriting,
  translation, sentiment, token billing, or semantic analysis.
license: CC0-1.0
compatibility: Requires Python 3; reads only an explicit UTF-8 input and does
  not access the network.
metadata:
  version: 1.0.0
  source: ai-agent-engineer-course
---

# Text Statistics

## Workflow

1. Confirm that the requested result is a count. Do not substitute this Skill for rewriting, translation, sentiment, model-token billing, or semantic summarization.
2. Prefer `scripts/text_stats.py --input <UTF8_FILE>` for file content. Both input forms reject UTF-8 payloads over 1 MiB; use `--text <TEXT>` only for short, non-secret text because command histories can retain arguments.
3. Parse the JSON written to stdout. Treat a nonzero exit code or stderr as a failure; do not invent missing counts.
4. Explain the counting rule if the result will be compared with an editor, tokenizer, or language-specific tool.

## Commands

```powershell
python -B scripts/text_stats.py --text "Hello Agent 世界" # 直接传入短文本；-B 防止产生 Python 字节码缓存
python -B scripts/text_stats.py --input .\sample.txt # 从 UTF-8 文件读取；脚本会限制为 1 MiB 并拒绝目录/无效编码
```

The input file must be valid UTF-8 and no larger than 1,000,000 bytes. The script never writes a file and never accesses the network.

## Output contract

Successful stdout is exactly one JSON object containing integer `words`, `characters`, and `lines` fields. Diagnostics go to stderr and failures return a nonzero exit code. The input text is never echoed.

## Counting rules and gotchas

- A Latin letter, digit, or underscore run counts as one word-like token; each Han character counts as one. This is a teaching rule, not a universal linguistic definition.
- `characters` counts Python Unicode code points, including whitespace and newline characters. It is not a byte count or a model tokenizer count.
- CRLF, LF, and CR are treated as line separators. Empty text has zero logical lines; a trailing separator introduces a final empty logical line.
- Do not promise equality with Microsoft Word, an IDE, or an LLM tokenizer unless their rules have been separately checked.
