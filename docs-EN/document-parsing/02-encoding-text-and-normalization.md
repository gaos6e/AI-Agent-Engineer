---
title: "Encoding, text, and normalization"
tags:
  - ai-agent-engineer
  - document-parsing
  - Unicode
aliases:
  - Text encoding and normalization
source_checked: 2026-07-22
source_baseline:
  - Unicode 17.0.0 / UAX #15 revision 57
  - RFC 8259
  - Python 3.11 codecs and unicodedata
lang: en
translation_key: 文档解析/02-编码文本与规范化.md
translation_source_hash: 7831b60a772f89003b4ae9d2f09d0c2cab909cf6ca2852c13b07f035cc59b4f6
translation_route: zh-CN/文档解析/02-编码文本与规范化
translation_default_route: zh-CN/文档解析/02-编码文本与规范化
---

# Encoding, text, and normalization

## Goal

Understand the distinction among bytes, characters, encodings, and Unicode; process BOMs, line endings, and canonically equivalent characters with strict, auditable rules; and preserve both citable source text and retrieval-ready derived text.

## Bytes are not characters

Disks and networks store bytes. An encoding specifies how bytes map to characters; Unicode assigns code points to characters; a font then determines how those characters are displayed. UTF-8 is an encoding, not a language, and it does not guarantee that content is Chinese or English.

```python
raw = "Café Agent".encode("utf-8")
text = raw.decode("utf-8", errors="strict")
```

`strict` raises `UnicodeDecodeError` for an invalid sequence. A parsing entry point should not default to `errors="ignore"`: it silently deletes characters, potentially removing an amount, a negation, or a code character. `replace` inserts `U+FFFD`; use it only in an explicit degradation path that counts replacement positions, emits a quality warning, and preserves the raw bytes.

### Encoding detection is not magic

A BOM can conclusively indicate certain UTF encodings; an HTTP `charset` or document declaration is upstream evidence; statistical detectors provide only candidates and confidence signals. A recommended decision order is:

1. Read the encoding mandated by the protocol or format specification.
2. Use trusted metadata or a BOM.
3. Attempt strict decoding with an allowlist.
4. If uncertainty remains, send the input for human or specialized-detector review instead of iterating through every encoding until nothing errors.

The course project permits UTF-8, UTF-8 with a BOM, and UTF-16 with a BOM for plain text; for open interchange under RFC 8259, JSON accepts only UTF-8. This is an engineering policy, not a claim that all historical files use only those encodings.

## BOMs, line endings, and raw hashes

Windows text commonly uses CRLF (`\r\n`), whereas Unix commonly uses LF (`\n`). You may normalize internally to LF, but distinguish two hashes:

- `raw_sha256`: calculated from original bytes, for versioning and replay;
- `text_sha256`: calculated from normalized UTF-8 text under declared rules, for element comparison.

Normalizing before computing a “raw hash” incorrectly merges distinct inputs. Conversely, storing only a raw hash cannot explain why two visually identical elements behave differently during retrieval.

A UTF-8 BOM is `EF BB BF`. Python’s `utf-8-sig` consumes a BOM at the start of a file; adding it back casually during output makes cross-tool comparisons differ. Rules must be versioned and tested.

## An intuition for Unicode normalization

`é` can be a single precomposed character or an `e` followed by a combining accent. They look the same, but their bytes and `len()` can differ:

```python
import unicodedata

left = "é"
right = "e\u0301"
print(left == right)  # False
print(unicodedata.normalize("NFC", left) == unicodedata.normalize("NFC", right))  # True
```

Unicode UAX #15 defines four normalization forms:

| Form | Intuition | Usage caution |
| --- | --- | --- |
| NFC | Canonically decompose, then compose where possible | Common for general-text interoperability; used by this project. |
| NFD | Keep canonical decomposition | Appears in some file-system and text-processing contexts. |
| NFKC | Compatibility-decompose, then compose | Folds distinctions such as circled characters, width, and superscripts. |
| NFKD | Compatibility decomposition | Can likewise lose visually distinct but meaningful forms. |

UAX #15 explicitly warns against blindly applying NFKC/NFKD to arbitrary text, because distinctions involving mathematical symbols, superscripts, fractions, and full-width forms can matter. NFC is not “removing all unusual characters”; it handles only the canonically equivalent relationships defined by the standard.

## A four-layer text model

To satisfy auditing, display, and retrieval at the same time, store:

1. **raw bytes**: an immutable source version protected by permissions;
2. **parser raw text**: with page, line, or coordinate data for reviewing parsing behavior;
3. **normalized text**: line-ending and Unicode rules are fixed while semantics remain intact; and
4. **retrieval-derived text**: may apply case folding, table-row descriptions, or whitespace policy, but must not impersonate citable source text.

Record a rule version and parent hash for every layer. When an agent cites text to a user, it should return to locatable parser raw text or the source page, rather than show only a derivative string optimized for recall.

## Control characters, zero-width characters, and whitespace

“Invisible” does not mean “meaningless.” A non-breaking space affects line wrapping, a zero-width joiner affects some writing systems, and tabs and newlines carry structure in code and tables. A safe approach is to:

- detect and count code-point categories before removing anything;
- create small allow/deny rules for explicit risks;
- handle code, natural language, and identifiers separately;
- retain a change log and source coordinates; and
- regress against real language, formula, and code samples.

Mojibake in a terminal does not by itself prove that a file is corrupt. Also inspect the terminal font, output encoding, and pipe encoding.

## JSON, CSV, and HTML differ

- JSON: use a real JSON parser; production entry points should consider duplicate keys and non-standard extensions such as `NaN`/`Infinity`. This project rejects those values strictly.
- CSV: RFC 4180 describes a common format, but real separators, encodings, and dialects still require an explicit contract. Fields containing commas or newlines must be handled by the `csv` module.
- HTML: hand entities, nesting, and visible structure to an HTML parser. Removing tags with regular expressions mixes scripts, styles, cells, and paragraph boundaries.

## Common mistakes and troubleshooting

- **“If it decodes, the encoding is correct.”** Many wrong encoding combinations still produce legal characters; use protocol, metadata, and sample validation.
- **“NFKC always improves search.”** It can fold meaningful formatting distinctions; use it only on explicit fields or a derived retrieval layer.
- **“Removing all whitespace is cleaner.”** Words, code indentation, paragraphs, and cells become stuck together.
- **“After normalization, the source is unnecessary.”** Without it, you cannot cite precisely, investigate problems, or change rules.
- **“A JSON library always rejects `NaN`.”** Implementations and defaults differ; make the contract an explicit test.

## Exercises

1. Compare the code points, UTF-8 bytes, raw hashes, and NFC text hashes of `"é"` and `"e\u0301"`.
2. Construct an invalid UTF-8 sequence, run `strict`, `replace`, and `ignore`, and record what each mode loses.
3. Parse a CSV field containing commas, double quotes, and embedded newlines with `csv`; explain why `split(',')` fails.
4. Write allowed normalization rules for evidence-citation text and search text, and identify irreversible steps.

## Self-check

- [ ] I can explain mojibake at the levels of bytes, code points, and fonts.
- [ ] I know the relative evidentiary strength of BOMs, declared encodings, and statistical detection.
- [ ] I can explain the distinct risks of NFC and NFKC.
- [ ] I preserve both raw versions and rule-governed derived versions.
- [ ] I do not present search text directly as a source citation.

## References and next step

- [Unicode Standard Annex #15: Normalization Forms](https://www.unicode.org/reports/tr15/)
- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 4180: CSV](https://www.rfc-editor.org/rfc/rfc4180.html)
- [Python `codecs`](https://docs.python.org/3.11/library/codecs.html)
- [Python `unicodedata`](https://docs.python.org/3.11/library/unicodedata.html)

Sources retrieved on 2026-07-22. Next: [[document-parsing/03-structure-headings-lists-and-tables|Structure, headings, lists, and tables]].
