"""Command line interface with deliberately fixed invalid-input output."""

from __future__ import annotations

import json
import sys

from .core import InputError, audit

HELP = """usage: citation-reference-check DOCUMENTS.jsonl ANSWERS.jsonl

Audit exact reference membership in synthetic JSONL fixtures. The tool reports
physical line numbers and aggregate counts; it does not assess citation quality.
"""


def main() -> int:
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        sys.stdout.write(HELP)
        return 0
    if len(args) != 2:
        sys.stdout.write('{"status":"invalid_input"}\n')
        return 2
    try:
        result = audit(args[0], args[1])
    except InputError:
        sys.stdout.write('{"status":"invalid_input"}\n')
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
