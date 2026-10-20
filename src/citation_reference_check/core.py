"""Strict, privacy-preserving JSONL parsing and reference membership audit."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class InputError(Exception):
    """An input file cannot be audited under the documented schema."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValueError


def _contains_surrogate(value: Any) -> bool:
    if isinstance(value, str):
        return any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    if isinstance(value, list):
        return any(_contains_surrogate(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_surrogate(key) or _contains_surrogate(item) for key, item in value.items())
    return False


def _physical_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = re.split(r"\r\n|\r|\n", text)
    if text.endswith(("\r", "\n")):
        lines.pop()
    return lines


def _read_records(path: str, kind: str) -> list[tuple[int, dict[str, Any]]]:
    try:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8", errors="strict")
        lines = _physical_lines(text)
        records: list[tuple[int, dict[str, Any]]] = []
        seen: set[str] = set()
        for number, line in enumerate(lines, 1):
            if not line:
                raise InputError
            try:
                item = json.loads(
                    line,
                    object_pairs_hook=_unique_object,
                    parse_constant=_reject_constant,
                )
            except (ValueError, json.JSONDecodeError, RecursionError):
                raise InputError from None
            if not isinstance(item, dict) or _contains_surrogate(item):
                raise InputError
            if kind == "documents":
                valid = set(item) == {"id"} and isinstance(item.get("id"), str) and bool(item["id"])
                identifier = item.get("id")
            else:
                refs = item.get("references")
                valid = (
                    set(item) == {"id", "references"}
                    and isinstance(item.get("id"), str)
                    and bool(item["id"])
                    and isinstance(refs, list)
                    and all(isinstance(ref, str) and bool(ref) for ref in refs)
                    and len(refs) == len(set(refs))
                )
                identifier = item.get("id")
            if not valid or identifier in seen:
                raise InputError
            seen.add(identifier)
            records.append((number, item))
        return records
    except InputError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        raise InputError from None


def audit(document_path: str, answer_path: str) -> dict[str, Any]:
    """Read both inputs and return only counts, status, and physical line numbers."""
    docs: list[tuple[int, dict[str, Any]]] | None = None
    answers: list[tuple[int, dict[str, Any]]] | None = None
    try:
        docs = _read_records(document_path, "documents")
    except InputError:
        pass
    try:
        answers = _read_records(answer_path, "answers")
    except InputError:
        pass
    if docs is None or answers is None:
        raise InputError

    document_ids = {item["id"] for _, item in docs}
    cited_known: set[str] = set()
    unknown_lines: list[int] = []
    for line, answer in answers:
        refs = answer["references"]
        if any(ref not in document_ids for ref in refs):
            unknown_lines.append(line)
        cited_known.update(ref for ref in refs if ref in document_ids)
    uncited_lines = [line for line, doc in docs if doc["id"] not in cited_known]
    result = {
        "status": "reference_issues" if unknown_lines or uncited_lines else "complete",
        "document_count": len(docs),
        "answer_count": len(answers),
        "unknown_reference_lines": unknown_lines,
        "uncited_document_lines": uncited_lines,
    }
    return result
