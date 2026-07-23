"""Return deterministic text statistics without network or file writes."""

from __future__ import annotations  # Keep annotations stable across Python versions and permit forward references.

import argparse  # Parse the mutually exclusive --text and --input forms.
import json  # Serialize statistics as machine-readable JSON.
import re  # Recognize Latin/numeric token runs and individual Han characters.
import sys  # Send expected input errors to stderr.
from pathlib import Path  # Represent the input path safely across platforms.


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u4dbf\u4e00-\u9fff]")  # Each Latin/numeric run and Han character is one teaching token.
MAX_INPUT_BYTES = 1024 * 1024  # Apply the shared 1 MiB ceiling before processing user content.


def logical_line_count(text: str) -> int:  # Count lines consistently across Windows and Unix newline forms.
    """Count logical lines after normalizing common newline sequences."""
    if text == "":
        return 0
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.count("\n") + 1


def calculate(text: str) -> dict[str, int]:  # Return three deterministic, offline text metrics.
    """Count Latin/numeric runs and individual Han characters as word-like tokens."""
    return {
        "words": len(TOKEN_PATTERN.findall(text)),
        "characters": len(text),
        "lines": logical_line_count(text),
    }


def require_bounded_utf8_text(text: str, *, source: str) -> str:  # Share one UTF-8 byte contract between direct and file input.
    """Reject text that cannot fit the shared 1 MiB UTF-8 input contract."""
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError(f"{source} must be valid UTF-8 text") from exc
    if size > MAX_INPUT_BYTES:
        raise ValueError(f"{source} exceeds {MAX_INPUT_BYTES} UTF-8 bytes (1 MiB): {size}")
    return text


def read_utf8_file(path: Path) -> str:  # Read bounded bytes first so a changing file cannot bypass the limit.
    """Read at most 1 MiB of UTF-8 input without trusting a pre-read file size."""
    if not path.is_file():
        raise ValueError(f"input path is not a file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} UTF-8 bytes (1 MiB): at least {len(raw)}")
    try:
        return require_bounded_utf8_text(raw.decode("utf-8"), source="input")
    except UnicodeDecodeError as exc:
        raise ValueError("input file must be valid UTF-8") from exc


def build_parser() -> argparse.ArgumentParser:  # Build a reusable parser so tests can provide their own argv.
    parser = argparse.ArgumentParser(
        description="Count word-like tokens, Unicode code points, and logical lines."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Literal UTF-8 text (maximum 1 MiB); avoid this option for secrets")
    source.add_argument("--input", type=Path, help="Path to a UTF-8 text file (maximum 1 MiB)")
    return parser


def main(argv: list[str] | None = None) -> int:  # Return a shell-friendly status for one command invocation.
    args = build_parser().parse_args(argv)
    try:
        text = (
            require_bounded_utf8_text(args.text, source="--text")
            if args.text is not None
            else read_utf8_file(args.input)
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(calculate(text), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # Do not run the CLI when the module is imported by tests.
    raise SystemExit(main())
