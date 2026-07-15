"""Return deterministic text statistics without network or file writes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u4dbf\u4e00-\u9fff]")
MAX_INPUT_BYTES = 1_000_000


def logical_line_count(text: str) -> int:
    """Count logical lines after normalizing common newline sequences."""
    if text == "":
        return 0
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.count("\n") + 1


def calculate(text: str) -> dict[str, int]:
    """Count Latin/numeric runs and individual Han characters as word-like tokens."""
    return {
        "words": len(TOKEN_PATTERN.findall(text)),
        "characters": len(text),
        "lines": logical_line_count(text),
    }


def read_utf8_file(path: Path) -> str:
    """Read a bounded UTF-8 file and reject directories or oversized inputs."""
    if not path.is_file():
        raise ValueError(f"input path is not a file: {path}")
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes: {size}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("input file must be valid UTF-8") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count word-like tokens, Unicode code points, and logical lines."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Literal text; avoid this option for secrets")
    source.add_argument("--input", type=Path, help="Path to a UTF-8 text file (maximum 1 MB)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = args.text if args.text is not None else read_utf8_file(args.input)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(calculate(text), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
