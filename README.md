# Citation Reference Check

`citation-reference-check` is a Python 3.10+ standard-library CLI for checking
whether declared reference IDs exactly match IDs in a document fixture. It
reports answer lines that contain unknown references and document lines that
are never cited by a known reference. It reads synthetic JSONL fixtures only
and does not process answer text.

This is a set-membership audit. It does not assess whether a citation supports
an answer, whether citations are relevant or faithful, or the quality of a
retrieval or generation system.

## Install and run

```sh
python -m pip install .
citation-reference-check examples/documents.jsonl examples/answers.jsonl
```

The example intentionally reports `reference_issues`: the first answer names
an unknown reference, and the third document is unused. Exit status is `1` for
those issues, `0` when both findings lists are empty, and `2` for invalid input.
Use `citation-reference-check --help` for usage. Invalid input always produces
only `{"status":"invalid_input"}` on standard output, with no source values,
IDs, or paths in output.

## Input format

Documents contain one JSON object per physical line, exactly `{"id":"..."}`.
Answers contain exactly `{"id":"...","references":["..."]}`. IDs must be
nonempty strings and unique within their own file; a document ID may equal an
answer ID. Reference lists may be empty but may not repeat an exact value.
Matching is exact, case-sensitive, and performs no Unicode normalization or
trimming.

Files must be strict UTF-8 JSONL. CR, LF, and CRLF delimit records; a single
final line terminator is allowed. Blank records, duplicate JSON keys,
non-finite numbers, malformed JSON, invalid UTF-8, schema extras, and surrogate
code points are rejected. Empty files are valid. Both files are checked before
the CLI emits its one result, so invalid input never produces partial findings.

Output contains a status, record counts, and ascending 1-based physical line
numbers only. Unknown references do not count as known citations; a reference
may be reused in different answers. Every unused declared document is reported.

## Development

```sh
python -m pip install pytest
python -m pytest -q
```

The test suite uses generated temporary inputs and the synthetic files in
`examples/`; it makes no network calls and has no runtime dependencies.
