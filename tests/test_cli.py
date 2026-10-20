import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from citation_reference_check.core import InputError, audit


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def invoke(*args, cwd=None):
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "citation_reference_check.cli", *map(str, args)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def test_membership_unknown_and_uncited_are_independent_and_ordered(tmp_path):
    docs = write(tmp_path, "docs", '{"id":"b"}\r\n{"id":"a"}\r{"id":"unused"}\n')
    answers = write(tmp_path, "answers", '{"id":"a","references":["a","missing"]}\n{"id":"b","references":["b","missing"]}')
    assert audit(str(docs), str(answers)) == {
        "status": "reference_issues",
        "document_count": 3,
        "answer_count": 2,
        "unknown_reference_lines": [1, 2],
        "uncited_document_lines": [3],
    }


def test_reuse_empty_references_and_independent_id_namespaces(tmp_path):
    docs = write(tmp_path, "d", '{"id":"x"}\n{"id":"z"}')
    answers = write(tmp_path, "a", '{"id":"x","references":[]}\n{"id":"x2","references":["x"]}\n{"id":"x3","references":["x"]}')
    result = audit(str(docs), str(answers))
    assert result["unknown_reference_lines"] == []
    assert result["uncited_document_lines"] == [2]


def test_empty_inputs_and_empty_reference_list(tmp_path):
    docs = write(tmp_path, "d", "")
    answers = write(tmp_path, "a", "")
    assert audit(str(docs), str(answers)) == {
        "status": "complete", "document_count": 0, "answer_count": 0,
        "unknown_reference_lines": [], "uncited_document_lines": [],
    }
    docs.write_text('{"id":"d"}', encoding="utf-8")
    answers.write_text('{"id":"a","references":[]}', encoding="utf-8")
    assert audit(str(docs), str(answers))["uncited_document_lines"] == [1]


def test_exact_unicode_case_sensitive_and_unicode_separators_not_delimiters(tmp_path):
    docs = write(tmp_path, "d", '{"id":"é"}\n{"id":"A"}')
    answers = write(tmp_path, "a", '{"id":"a","references":["é","a"]}')
    result = audit(str(docs), str(answers))
    assert result["unknown_reference_lines"] == [1]
    assert result["uncited_document_lines"] == [1, 2]
    write(tmp_path, "one", '{"id":"a"}\u2028{"id":"b"}')
    with pytest.raises(InputError):
        audit(str(tmp_path / "one"), str(answers))


@pytest.mark.parametrize("raw", [
    b'{"id":"x","id":"y"}', b'{"id":"x","extra":1}', b'{"id":"x"}\n\n',
    b'{"id":"x","n":NaN}', b'{"id":"x","n":Infinity}', b'{"id":"\\ud800"}',
    b'{"id":"x"}\xc3', b'{"id":"x"}\x00', b'{"id":"x"}\n{"id":"x"}',
])
def test_strict_document_inputs_rejected_without_echo(tmp_path, raw):
    docs = write(tmp_path, "d", raw)
    answers = write(tmp_path, "a", '{"id":"answer","references":[]}')
    result = invoke(docs, answers)
    assert result.returncode == 2
    assert result.stdout == '{"status":"invalid_input"}\n'
    assert result.stderr == ""
    assert "x" not in result.stdout


@pytest.mark.parametrize("raw", [
    b'{"id":"a","id":"b","references":[]}',
    b'{"id":"a","references":["x","x"]}', b'{"id":"a","references":[""]}',
    b'{"id":"a","references":[],"other":0}', b'{"id":"a","references":"x"}',
    b'{"id":"\\udfff","references":[]}', b'{"id":"a","references":["\\ud800"]}',
    b'{"id":"a","references":[],"n":-Infinity}',
])
def test_strict_answer_inputs_rejected(tmp_path, raw):
    docs = write(tmp_path, "d", '{"id":"x"}')
    answers = write(tmp_path, "a", raw)
    with pytest.raises(InputError):
        audit(str(docs), str(answers))


def test_both_files_attempted_even_when_first_invalid(tmp_path, monkeypatch):
    import citation_reference_check.core as core
    observed = []
    original = core._read_records

    def tracked(path, kind):
        observed.append(kind)
        if kind == "documents":
            raise InputError
        return original(path, kind)

    monkeypatch.setattr(core, "_read_records", tracked)
    with pytest.raises(InputError):
        core.audit(str(tmp_path / "missing-doc"), str(tmp_path / "missing-answer"))
    assert observed == ["documents", "answers"]


def test_no_partial_output_and_missing_or_extra_arguments(tmp_path):
    valid = write(tmp_path, "good.jsonl", '{"id":"ok"}')
    bad = write(tmp_path, "bad.jsonl", '{"id":"ok","references":["x","x"]}')
    result = invoke(valid, bad)
    assert (result.returncode, result.stdout, result.stderr) == (2, '{"status":"invalid_input"}\n', "")
    result = invoke("secret-path")
    assert (result.returncode, result.stdout, result.stderr) == (2, '{"status":"invalid_input"}\n', "")
    result = invoke(valid, valid, "third")
    assert (result.returncode, result.stdout, result.stderr) == (2, '{"status":"invalid_input"}\n', "")


def test_help():
    result = invoke("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert result.stderr == ""


def test_issue_cli_has_exact_machine_output(tmp_path):
    docs = write(tmp_path, "private-document-path.jsonl", '{"id":"d"}')
    answers = write(tmp_path, "private-answer-path.jsonl", '{"id":"a","references":["secret"]}')
    result = invoke(docs, answers)
    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "status": "reference_issues", "document_count": 1, "answer_count": 1,
        "unknown_reference_lines": [1], "uncited_document_lines": [1],
    }
    assert "secret" not in result.stdout
    assert "private-" not in result.stdout
    assert result.stderr == ""
