"""Unit tests for structure-aware text cleaning."""

from docintel.preprocessing import (
    clean_text,
    collapse_whitespace,
    fix_hyphenation,
    join_wrapped_lines,
    normalize_unicode,
    remove_control_characters,
    standardize_punctuation,
)


def test_unicode_and_punctuation_normalization() -> None:
    assert normalize_unicode("Ａ café") == "A café"
    assert standardize_punctuation("“Hello”—it’s…") == '"Hello"-it\'s...'


def test_control_and_zero_width_characters_are_removed() -> None:
    assert remove_control_characters("A\x00B\u200bC\nD\tE") == "ABC\nD\tE"


def test_hyphenation_is_fixed_only_at_line_breaks() -> None:
    assert fix_hyphenation("exam-\nple and well-known") == "example and well-known"


def test_wrapped_prose_joins_and_structure_keeps_separate_lines() -> None:
    text = """# Heading
First wrapped
paragraph line.
- first item
- second item
| Name | Value |
| --- | --- |
"""

    assert join_wrapped_lines(text) == (
        "# Heading\nFirst wrapped paragraph line.\n- first item\n- second item\n"
        "| Name | Value |\n| --- | --- |"
    )


def test_paragraph_boundaries_and_whitespace_are_preserved_cleanly() -> None:
    assert collapse_whitespace("  one   two\n\n\n three  ") == "one two\n\nthree"
    assert join_wrapped_lines("First line\ncontinues.\n\nSecond paragraph.") == (
        "First line continues.\n\nSecond paragraph."
    )


def test_full_pipeline_handles_unicode_controls_case_and_empty_input() -> None:
    assert clean_text("ＡPI\u200b exam-\nple  “Case”\x00") == 'API example "Case"'
    assert clean_text("") == ""
    assert clean_text("API") == "API"
