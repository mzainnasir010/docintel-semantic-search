"""Structure-aware text preprocessing helpers."""

from quillseek.preprocessing.boilerplate import (
    BoilerplateReport,
    iter_preprocessed_pages,
)

from quillseek.preprocessing.cleaning import (
    clean_text,
    collapse_whitespace,
    fix_hyphenation,
    join_wrapped_lines,
    normalize_unicode,
    remove_control_characters,
    standardize_punctuation,
)

__all__ = [
    "clean_text",
    "BoilerplateReport",
    "collapse_whitespace",
    "fix_hyphenation",
    "join_wrapped_lines",
    "iter_preprocessed_pages",
    "normalize_unicode",
    "remove_control_characters",
    "standardize_punctuation",
]
