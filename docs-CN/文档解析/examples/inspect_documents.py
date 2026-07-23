"""离线文档清单检查器。

本项目只用 Python 标准库解析 UTF 文本、Markdown、HTML、CSV 与 JSON。
PDF、Office、图片和 OCR 需要受控的外部适配器；本程序只登记并停止。
"""

from __future__ import annotations

import argparse
import codecs
import csv
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Iterable, Sequence


PARSER_NAME = "stdlib-document-inspector"
PARSER_VERSION = "1.0.0"
SCHEMA_VERSION = "2.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
LINE_COORDINATE_SPACE = "normalized-text-lines-1-based-inclusive-v1"

EXTENSION_MEDIA_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".zip": "application/zip",
}

SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/html",
    "text/csv",
    "application/json",
}

ZIP_CONTAINER_TYPES = {
    "application/zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

EXTERNAL_ADAPTER_TYPES = {
    "application/pdf",
    "application/zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}


class DocumentError(ValueError):
    """可安全呈现给学习者的确定性文档错误。"""


@dataclass(frozen=True)
class Limits:
    max_files: int = 100
    max_file_bytes: int = 1_000_000
    max_total_bytes: int = 5_000_000

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} 必须是正整数")


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ParsedBlock:
    kind: str
    text: str
    line_start: int
    line_end: int
    section_path: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Element:
    element_id: str
    kind: str
    text: str
    text_sha256: str
    order: int
    location: dict[str, Any]
    section_path: list[str]
    attributes: dict[str, Any]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _digest_text(value: str) -> str:
    return _digest_bytes(value.encode("utf-8"))


def _parse_revision_sha256(
    raw_sha256: str,
    *,
    parser: str,
    parser_version: str,
    config_sha256: str,
) -> str:
    """Bind one successful parse to its raw bytes, parser, version, and config."""

    values = {
        "raw_sha256": raw_sha256,
        "parser": parser,
        "parser_version": parser_version,
        "config_sha256": config_sha256,
    }
    for name, value in values.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} 不是合法的 parse revision 输入")
        if name.endswith("sha256") and SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{name} 不是合法的 parse revision 输入")
    return _digest_text(_canonical_json(values))


def _normalise_text(value: str) -> str:
    normalised_newlines = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", normalised_newlines)


def _decode_text(raw: bytes) -> tuple[str, str, list[Issue]]:
    issues: list[Issue] = []
    if raw.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
        issues.append(Issue("bom_present", "warning", "检测到 UTF-8 BOM；已显式消费。"))
    elif raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        encoding = "utf-16"
        issues.append(Issue("utf16_bom", "warning", "检测到 UTF-16 BOM；跨系统交换优先使用 UTF-8。"))
    else:
        encoding = "utf-8"

    try:
        text = _normalise_text(raw.decode(encoding, errors="strict"))
    except UnicodeDecodeError as exc:
        raise DocumentError(
            f"strict 解码失败：字节区间 {exc.start}:{exc.end}；未使用 ignore/replace。"
        ) from exc
    if "\x00" in text:
        raise DocumentError("解码结果含 NUL；按二进制或损坏文本隔离。")
    other_controls = sum(
        ord(character) < 32 and character not in {"\n", "\t"}
        for character in text
    )
    if other_controls:
        issues.append(
            Issue(
                "control_characters_present",
                "warning",
                f"文本含 {other_controls} 个非换行/制表 C0 控制字符；需按领域复核。",
            )
        )
    return text, encoding, issues


def _reject_constant(value: str) -> Any:
    raise DocumentError(f"JSON 不允许非有限数值常量：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DocumentError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise DocumentError(
            f"JSON 语法错误：第 {exc.lineno} 行，第 {exc.colno} 列。"
        ) from exc


def _collapse_space(parts: Iterable[str]) -> str:
    return " ".join("".join(parts).split())


class StructuredHTMLParser(HTMLParser):
    """提取少量显式 HTML 块；不尝试浏览器级容错或 CSS 布局。"""

    BLOCK_TAGS = {
        "p": "paragraph",
        "li": "list_item",
        "pre": "code_block",
        "caption": "caption",
        "h1": "heading",
        "h2": "heading",
        "h3": "heading",
        "h4": "heading",
        "h5": "heading",
        "h6": "heading",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[ParsedBlock] = []
        self._active_tag: str | None = None
        self._active_kind: str | None = None
        self._active_parts: list[str] = []
        self._active_start = 1
        self._skip_depth = 0
        self._row_start: int | None = None
        self._row_cells: list[str] = []
        self._cell_tag: str | None = None
        self._cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        line = self.getpos()[0]
        if tag in {"script", "style", "template"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "tr":
            self._row_start = line
            self._row_cells = []
            return
        if tag in {"td", "th"} and self._row_start is not None:
            self._cell_tag = tag
            self._cell_parts = []
            return
        if tag == "br" and self._active_tag is not None:
            self._active_parts.append("\n")
            return
        if self._active_tag is None and tag in self.BLOCK_TAGS:
            self._active_tag = tag
            self._active_kind = self.BLOCK_TAGS[tag]
            self._active_parts = []
            self._active_start = line

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._cell_tag is not None:
            self._cell_parts.append(data)
        elif self._active_tag is not None:
            self._active_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        line = self.getpos()[0]
        if tag in {"script", "style", "template"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if self._cell_tag == tag:
            self._row_cells.append(_collapse_space(self._cell_parts))
            self._cell_tag = None
            self._cell_parts = []
            return
        if tag == "tr" and self._row_start is not None:
            if any(self._row_cells):
                self.blocks.append(
                    ParsedBlock(
                        "table_row",
                        _canonical_json({"cells": self._row_cells}),
                        self._row_start,
                        line,
                        attributes={"cell_count": len(self._row_cells)},
                    )
                )
            self._row_start = None
            self._row_cells = []
            return
        if self._active_tag == tag and self._active_kind is not None:
            if tag == "pre":
                text = _normalise_text("".join(self._active_parts)).strip("\n")
            else:
                text = _collapse_space(self._active_parts)
            if text:
                attributes: dict[str, Any] = {}
                if tag.startswith("h") and len(tag) == 2:
                    attributes["level"] = int(tag[1])
                self.blocks.append(
                    ParsedBlock(
                        self._active_kind,
                        text,
                        self._active_start,
                        line,
                        attributes=attributes,
                    )
                )
            self._active_tag = None
            self._active_kind = None
            self._active_parts = []


def _attach_section_paths(blocks: Sequence[ParsedBlock]) -> list[ParsedBlock]:
    headings: list[str] = []
    result: list[ParsedBlock] = []
    for block in blocks:
        if block.kind == "heading":
            level = int(block.attributes.get("level", 1))
            headings = headings[: max(level - 1, 0)]
            while len(headings) < level - 1:
                headings.append("(未命名层级)")
            headings.append(block.text)
            path = tuple(headings)
        else:
            path = tuple(headings)
        result.append(
            ParsedBlock(
                block.kind,
                block.text,
                block.line_start,
                block.line_end,
                path,
                dict(block.attributes),
            )
        )
    return result


def parse_html(text: str) -> list[ParsedBlock]:
    parser = StructuredHTMLParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise DocumentError(f"HTML 解析失败：{type(exc).__name__}") from exc
    return _attach_section_paths(parser.blocks)


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LIST_RE = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})([^`]*)$")


def parse_markdown(text: str) -> list[ParsedBlock]:
    lines = text.split("\n")
    blocks: list[ParsedBlock] = []
    headings: list[str] = []
    paragraph: list[str] = []
    paragraph_start = 1
    code_lines: list[str] = []
    code_start = 1
    fence_marker: str | None = None
    code_language = ""

    def flush_paragraph(end_line: int) -> None:
        nonlocal paragraph
        text_value = _collapse_space(paragraph)
        if text_value:
            blocks.append(
                ParsedBlock(
                    "paragraph",
                    text_value,
                    paragraph_start,
                    end_line,
                    tuple(headings),
                )
            )
        paragraph = []

    for line_number, line in enumerate(lines, start=1):
        if fence_marker is not None:
            if line.strip().startswith(fence_marker):
                blocks.append(
                    ParsedBlock(
                        "code_block",
                        "\n".join(code_lines),
                        code_start,
                        line_number,
                        tuple(headings),
                        {"language": code_language},
                    )
                )
                fence_marker = None
                code_lines = []
            else:
                code_lines.append(line)
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            flush_paragraph(line_number - 1)
            fence_marker = fence_match.group(1)[0] * len(fence_match.group(1))
            code_language = fence_match.group(2).strip()
            code_start = line_number
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush_paragraph(line_number - 1)
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip().rstrip("#").rstrip()
            headings = headings[: max(level - 1, 0)]
            while len(headings) < level - 1:
                headings.append("(未命名层级)")
            headings.append(title)
            blocks.append(
                ParsedBlock(
                    "heading",
                    title,
                    line_number,
                    line_number,
                    tuple(headings),
                    {"level": level},
                )
            )
            continue

        list_match = LIST_RE.match(line)
        if list_match:
            flush_paragraph(line_number - 1)
            blocks.append(
                ParsedBlock(
                    "list_item",
                    list_match.group(2),
                    line_number,
                    line_number,
                    tuple(headings),
                    {"indent_spaces": len(list_match.group(1))},
                )
            )
            continue

        if not line.strip():
            flush_paragraph(line_number - 1)
        else:
            if not paragraph:
                paragraph_start = line_number
            paragraph.append(line)

    if fence_marker is not None:
        raise DocumentError(f"Markdown 代码围栏未闭合：起始行 {code_start}")
    flush_paragraph(len(lines))
    return blocks


def parse_plain_text(text: str) -> list[ParsedBlock]:
    lines = text.split("\n")
    blocks: list[ParsedBlock] = []
    parts: list[str] = []
    start = 1
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if not parts:
                start = line_number
            parts.append(line)
        elif parts:
            blocks.append(
                ParsedBlock("paragraph", _collapse_space(parts), start, line_number - 1)
            )
            parts = []
    if parts:
        blocks.append(ParsedBlock("paragraph", _collapse_space(parts), start, len(lines)))
    return blocks


def parse_csv(text: str) -> list[ParsedBlock]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise DocumentError("CSV 为空，缺少表头。") from exc
    except csv.Error as exc:
        raise DocumentError(f"CSV 表头解析失败：{exc}") from exc
    if not header or any(not name.strip() for name in header):
        raise DocumentError("CSV 表头不得为空。")
    if len(set(header)) != len(header):
        raise DocumentError("CSV 表头字段必须唯一。")

    blocks: list[ParsedBlock] = []
    previous_end = reader.line_num
    try:
        for record_index, row in enumerate(reader, start=1):
            start_line = previous_end + 1
            end_line = reader.line_num
            previous_end = end_line
            if len(row) != len(header):
                raise DocumentError(
                    f"CSV 第 {record_index} 条记录有 {len(row)} 列，预期 {len(header)} 列。"
                )
            data = dict(zip(header, row, strict=True))
            blocks.append(
                ParsedBlock(
                    "table_row",
                    _canonical_json(data),
                    start_line,
                    end_line,
                    attributes={"record_index": record_index, "column_count": len(header)},
                )
            )
    except csv.Error as exc:
        raise DocumentError(f"CSV 解析失败：{exc}") from exc
    return blocks


def parse_json(text: str) -> list[ParsedBlock]:
    value = strict_json_loads(text)
    top_level = "array" if isinstance(value, list) else "object" if isinstance(value, dict) else "scalar"
    return [
        ParsedBlock(
            "json_document",
            _canonical_json(value),
            1,
            max(1, text.count("\n") + 1),
            attributes={"top_level": top_level},
        )
    ]


def _parse_blocks(media_type: str, text: str) -> list[ParsedBlock]:
    if media_type == "text/plain":
        return parse_plain_text(text)
    if media_type == "text/markdown":
        return parse_markdown(text)
    if media_type == "text/html":
        return parse_html(text)
    if media_type == "text/csv":
        return parse_csv(text)
    if media_type == "application/json":
        return parse_json(text)
    raise DocumentError(f"没有为 {media_type} 配置标准库解析器。")


def _signature_media_type(prefix: bytes) -> tuple[str | None, str]:
    if prefix.startswith(b"%PDF-"):
        return "application/pdf", "magic-bytes"
    if prefix.startswith(b"PK\x03\x04") or prefix.startswith(b"PK\x05\x06"):
        return "application/zip", "container-signature"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "magic-bytes"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "magic-bytes"
    probe = prefix.lstrip().lower()
    if probe.startswith(b"<!doctype html") or probe.startswith(b"<html"):
        return "text/html", "content-sniff"
    return None, "none"


def _classify(path: Path, raw: bytes) -> tuple[str | None, str | None, str, bool]:
    declared = EXTENSION_MEDIA_TYPES.get(path.suffix.lower())
    signature, method = _signature_media_type(raw[:1024])
    if signature is None:
        return declared, declared, "extension-only", False
    if signature == "application/zip" and declared in ZIP_CONTAINER_TYPES:
        return declared, declared, "container-signature+extension", False
    mismatch = declared is not None and signature != declared
    return declared, signature, method, mismatch


def _make_elements(
    parse_revision_sha256: str, blocks: Sequence[ParsedBlock]
) -> list[Element]:
    if not isinstance(parse_revision_sha256, str) or not SHA256_PATTERN.fullmatch(
        parse_revision_sha256
    ):
        raise ValueError("parse_revision_sha256 必须是完整小写 SHA-256")
    result: list[Element] = []
    for order, block in enumerate(blocks, start=1):
        text = _normalise_text(block.text)
        text_sha256 = _digest_text(text)
        location = {
            "coordinate_space": LINE_COORDINATE_SPACE,
            "line_start": block.line_start,
            "line_end": block.line_end,
        }
        identity = {
            "kind": block.kind,
            "location": location,
            "parse_revision_sha256": parse_revision_sha256,
            "text_sha256": text_sha256,
        }
        result.append(
            Element(
                element_id=f"elm_{_digest_text(_canonical_json(identity))}",
                kind=block.kind,
                text=text,
                text_sha256=text_sha256,
                order=order,
                location=location,
                section_path=list(block.section_path),
                attributes=dict(block.attributes),
            )
        )
    return result


def _record_base(relative_path: str, size_bytes: int) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "source_id": f"unread:{relative_path}",
        "raw_sha256": None,
        "size_bytes": size_bytes,
        "extension_media_type": None,
        "detected_media_type": None,
        "detection_method": "not-read",
        "encoding": None,
        "status": "rejected",
        "parser": None,
        "parser_version": None,
        "parse_revision_sha256": None,
        "elements": [],
        "issues": [],
    }


def _read_bounded_bytes(path: Path, maximum: int) -> bytes:
    """Read at most one byte past a budget so a changed file cannot bypass it."""

    if maximum < 0:
        raise ValueError("读取字节上限不得为负数")
    with path.open("rb") as handle:
        raw = handle.read(maximum + 1)
    if len(raw) > maximum:
        raise DocumentError(
            f"读取时文件超过 {maximum} 字节预算；已停止继续读取并拒绝该文件。"
        )
    return raw


def inspect_file(
    path: Path,
    root: Path,
    limits: Limits,
    remaining_bytes: int,
    config_sha256: str,
) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    if path.is_symlink():
        record = _record_base(relative_path, 0)
        record["issues"] = [
            asdict(Issue("symlink_rejected", "error", "符号链接未被跟随。"))
        ]
        return record

    try:
        size = path.stat().st_size
    except OSError as exc:
        record = _record_base(relative_path, 0)
        record["issues"] = [
            asdict(Issue("stat_failed", "error", f"无法读取文件元数据：{type(exc).__name__}"))
        ]
        return record

    record = _record_base(relative_path, size)
    if size > limits.max_file_bytes:
        record["issues"] = [
            asdict(
                Issue(
                    "file_too_large",
                    "error",
                    f"文件大小 {size} 超过单文件上限 {limits.max_file_bytes}。",
                )
            )
        ]
        return record
    if size > remaining_bytes:
        record["issues"] = [
            asdict(
                Issue(
                    "total_budget_exceeded",
                    "error",
                    f"读取该文件会超过总字节上限 {limits.max_total_bytes}。",
                )
            )
        ]
        return record

    max_read_bytes = min(limits.max_file_bytes, remaining_bytes)
    try:
        raw = _read_bounded_bytes(path, max_read_bytes)
    except OSError as exc:
        record["issues"] = [
            asdict(Issue("read_failed", "error", f"读取失败：{type(exc).__name__}"))
        ]
        return record
    except DocumentError as exc:
        record["issues"] = [
            asdict(Issue("read_budget_exceeded", "error", str(exc)))
        ]
        return record

    raw_hash = _digest_bytes(raw)
    source_id = f"sha256:{raw_hash}"
    declared, detected, method, mismatch = _classify(path, raw)
    record.update(
        {
            "source_id": source_id,
            "raw_sha256": raw_hash,
            "extension_media_type": declared,
            "detected_media_type": detected,
            "detection_method": method,
        }
    )

    if declared is None:
        record["issues"] = [
            asdict(Issue("unknown_extension", "error", "扩展名不在允许清单中；未猜测解析器。"))
        ]
        return record
    if mismatch:
        record["issues"] = [
            asdict(
                Issue(
                    "media_type_mismatch",
                    "error",
                    f"扩展名声明 {declared}，内容检测为 {detected}；文件已隔离。",
                )
            )
        ]
        return record
    if detected in EXTERNAL_ADAPTER_TYPES:
        record["status"] = "external_adapter_required"
        record["issues"] = [
            asdict(
                Issue(
                    "external_adapter_required",
                    "warning",
                    "该格式需要隔离的外部解析/OCR 适配器；本程序未展开或执行内容。",
                )
            )
        ]
        return record
    if detected not in SUPPORTED_TEXT_TYPES:
        record["issues"] = [
            asdict(Issue("unsupported_type", "error", f"不支持的媒体类型：{detected}"))
        ]
        return record

    try:
        text, encoding, decode_issues = _decode_text(raw)
        if detected == "application/json" and encoding == "utf-16":
            raise DocumentError("开放系统交换的 JSON 应使用 UTF-8；拒绝 UTF-16 输入。")
        blocks = _parse_blocks(detected, text)
        if not blocks:
            raise DocumentError("解析结果没有可发布元素。")
        parse_revision_sha256 = _parse_revision_sha256(
            raw_hash,
            parser=PARSER_NAME,
            parser_version=PARSER_VERSION,
            config_sha256=config_sha256,
        )
        elements = _make_elements(parse_revision_sha256, blocks)
    except DocumentError as exc:
        record["issues"] = [asdict(Issue("parse_rejected", "error", str(exc)))]
        return record

    record.update(
        {
            "encoding": encoding,
            "status": "parsed",
            "parser": PARSER_NAME,
            "parser_version": PARSER_VERSION,
            "parse_revision_sha256": parse_revision_sha256,
            "elements": [asdict(element) for element in elements],
            "issues": [asdict(issue) for issue in decode_issues],
        }
    )
    return record


def _discover(root: Path) -> tuple[list[Path], list[Issue]]:
    files: list[Path] = []
    issues: list[Issue] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        except OSError as exc:
            issues.append(
                Issue(
                    "directory_read_failed",
                    "error",
                    f"无法枚举目录 {directory.relative_to(root).as_posix() or '.'}：{type(exc).__name__}",
                )
            )
            continue
        for entry in entries:
            if entry.is_symlink():
                if entry.is_dir():
                    issues.append(
                        Issue(
                            "directory_symlink_rejected",
                            "error",
                            f"未跟随目录符号链接：{entry.relative_to(root).as_posix()}",
                        )
                    )
                else:
                    files.append(entry)
            elif entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                files.append(entry)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix().casefold()), issues


def scan_root(root: Path, limits: Limits = Limits()) -> dict[str, Any]:
    limits.validate()
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("输入路径必须是目录")

    files, global_issues = _discover(resolved_root)
    discovered_file_count = len(files)
    if not files:
        global_issues.append(Issue("no_files", "error", "输入目录中没有可检查文件。"))
    if len(files) > limits.max_files:
        global_issues.append(
            Issue(
                "file_limit_exceeded",
                "error",
                f"发现 {len(files)} 个文件，超过上限 {limits.max_files}；只检查排序后的前 {limits.max_files} 个。",
            )
        )
        files = files[: limits.max_files]

    config = {
        "limits": asdict(limits),
        "normalization": "newline-to-LF+Unicode-NFC",
        "supported_media_types": sorted(SUPPORTED_TEXT_TYPES),
    }
    config_sha256 = _digest_text(_canonical_json(config))
    records: list[dict[str, Any]] = []
    consumed = 0
    for path in files:
        record = inspect_file(
            path,
            resolved_root,
            limits,
            limits.max_total_bytes - consumed,
            config_sha256,
        )
        records.append(record)
        if record["raw_sha256"] is not None:
            consumed += int(record["size_bytes"])

    status_counts = {
        status: sum(record["status"] == status for record in records)
        for status in ("parsed", "external_adapter_required", "rejected")
    }
    error_count = sum(issue.severity == "error" for issue in global_issues) + sum(
        issue["severity"] == "error"
        for record in records
        for issue in record["issues"]
    )
    warning_count = sum(issue.severity == "warning" for issue in global_issues) + sum(
        issue["severity"] == "warning"
        for record in records
        for issue in record["issues"]
    )
    if error_count:
        gate = "fail"
    elif status_counts["external_adapter_required"] or warning_count:
        gate = "review_required"
    else:
        gate = "pass"

    return {
        "schema_version": SCHEMA_VERSION,
        "parser": {"name": PARSER_NAME, "version": PARSER_VERSION},
        "config": config,
        "config_sha256": config_sha256,
        "root": ".",
        "documents": records,
        "summary": {
            "gate": gate,
            "discovered_file_count": discovered_file_count,
            "processed_file_count": len(records),
            "consumed_bytes": consumed,
            "status_counts": status_counts,
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": [asdict(issue) for issue in global_issues],
    }


def _output_is_inside_root(output: Path, root: Path) -> bool:
    try:
        output.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except ValueError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成只读、确定性的离线文档解析清单")
    parser.add_argument("root", type=Path, help="待检查目录")
    parser.add_argument("--output", type=Path, help="可选输出 JSON；必须位于输入目录之外")
    parser.add_argument("--max-files", type=int, default=Limits.max_files)
    parser.add_argument("--max-file-bytes", type=int, default=Limits.max_file_bytes)
    parser.add_argument("--max-total-bytes", type=int, default=Limits.max_total_bytes)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    limits = Limits(args.max_files, args.max_file_bytes, args.max_total_bytes)
    try:
        if args.output is not None and _output_is_inside_root(args.output, args.root):
            raise ValueError("--output 必须位于输入目录之外，避免输出被下一次扫描当成输入")
        manifest = scan_root(args.root, limits)
        rendered = json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.output is None:
            sys.stdout.write(rendered)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0 if manifest["summary"]["gate"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
