"""Tests for evals/tooling/fuzzy/fuzzy_replace (Codex seek_sequence-style)."""

from __future__ import annotations

from fuzzy.fuzzy_replace import fuzzy_replace_once, seek_sequence


def test_seek_sequence_exact() -> None:
    lines = ["foo", "bar", "baz"]
    assert seek_sequence(lines, ["bar", "baz"]) == [1]


def test_seek_sequence_trim_end() -> None:
    lines = ["foo ", "bar\t\t"]
    assert seek_sequence(lines, ["foo", "bar"]) == [0]


def test_seek_sequence_trim_both() -> None:
    lines = [" foo ", " bar\t"]
    assert seek_sequence(lines, ["foo", "bar"]) == [0]


def test_seek_sequence_pattern_longer_than_input() -> None:
    lines = ["one line"]
    assert seek_sequence(lines, ["too", "many", "lines"]) == []


def test_fuzzy_replace_exact_substring() -> None:
    content = "alpha\nbeta\ngamma\n"
    new, err = fuzzy_replace_once(content, "beta", "BETA")
    assert err is None
    assert new is not None
    assert "BETA" in new
    assert "beta" not in new


def test_fuzzy_replace_ambiguous_exact() -> None:
    content = "x\nx\n"
    _, err = fuzzy_replace_once(content, "x", "y")
    assert err is not None
    assert "2 times" in err


def test_fuzzy_replace_fuzzy_indent() -> None:
    content = 'def main():\n    message = "Hi"\n'
    old = '    message = "Hi"'
    new = '    message = "Hello"'
    result, err = fuzzy_replace_once(content, old, new)
    assert err is None
    assert result is not None
    assert "Hello" in result
