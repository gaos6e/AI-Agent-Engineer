"""LCEL composition example that needs langchain-core but no model key."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def build_pipeline() -> Any:
    from langchain_core.runnables import RunnableLambda, RunnableParallel

    normalize = RunnableLambda(lambda text: " ".join(text.strip().split()))
    features = RunnableParallel(
        text=RunnableLambda(lambda text: text),
        length=RunnableLambda(len),
        words=RunnableLambda(lambda text: len(text.split())),
    )
    return normalize | features


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", default="  hello   agent  ")
    args = parser.parse_args(argv)
    try:
        result = build_pipeline().invoke(args.text)
    except ImportError:
        print(
            json.dumps(
                {
                    "status": "dependency_missing",
                    "required": "langchain-core",
                    "note": "create a venv, install a locked compatible version, then rerun",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 4
    print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


