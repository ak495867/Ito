#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOTS = ("apps", "cpp", "rust", "ocaml", "rtl", "python", "tests")
EXTENSIONS = {".cpp", ".hpp", ".h", ".rs", ".ml", ".mli", ".sv", ".v", ".py"}
PATTERNS = {
    ".cpp": re.compile(r"//|/\*|\*/"),
    ".hpp": re.compile(r"//|/\*|\*/"),
    ".h": re.compile(r"//|/\*|\*/"),
    ".rs": re.compile(r"//|/\*|\*/"),
    ".ml": re.compile(r"\(\*|\*\)"),
    ".mli": re.compile(r"\(\*|\*\)"),
    ".sv": re.compile(r"//|/\*|\*/"),
    ".v": re.compile(r"//|/\*|\*/"),
    ".py": re.compile(r"^\s*#"),
}


def main() -> int:
    failures: list[str] = []
    for root_name in ROOTS:
        root = Path(root_name)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix not in EXTENSIONS
                or "_build" in path.parts
                or "build" in path.parts
            ):
                continue
            pattern = PATTERNS[path.suffix]
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if pattern.search(line):
                    failures.append(f"{path}:{line_number}")
    if failures:
        print("source_comments_found")
        print("\n".join(failures))
        return 1
    print("no_source_comments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
