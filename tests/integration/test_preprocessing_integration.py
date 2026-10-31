"""Verify extraction output can be cleaned without losing page structure."""

from docintel.ingestion import load_txt
from docintel.preprocessing import clean_text


def test_text_loader_pages_feed_structure_aware_cleaning(tmp_path) -> None:
    source = tmp_path / "wrapped.txt"
    source.write_text(
        "# API Guide\nUse the exam-\nple safely.\n\n- Keep Case\n- Keep Tables\n",
        encoding="utf-8",
    )

    page = load_txt(source)[0]
    cleaned = clean_text(page.text)

    assert page.page_number == 1
    assert cleaned == "# API Guide\nUse the example safely.\n\n- Keep Case\n- Keep Tables"
