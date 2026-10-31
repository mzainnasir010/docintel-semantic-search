"""Unit tests for file routing and stable ingestion identities."""

from quillseek.ingestion import detect_file_type, stable_document_id


def test_file_type_uses_signatures_and_supported_extensions(pdf_factory, tmp_path) -> None:
    pdf_path = pdf_factory("misnamed.txt", page_specs=("text",))
    text_path = tmp_path / "notes.TXT"
    text_path.write_text("plain text", encoding="utf-8")
    unsupported = tmp_path / "archive.bin"
    unsupported.write_bytes(b"random bytes")

    assert detect_file_type(pdf_path) == "pdf"
    assert detect_file_type(text_path) == "txt"
    assert detect_file_type(unsupported) is None


def test_stable_document_id_is_content_based_and_short(tmp_path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "renamed.txt"
    first.write_bytes(b"same content")
    second.write_bytes(b"same content")

    first_id = stable_document_id(first)
    assert first_id == stable_document_id(second)
    assert len(first_id) == 16
    second.write_bytes(b"different content")
    assert first_id != stable_document_id(second)


def test_ingestion_reports_unsupported_input_without_raising(tmp_path) -> None:
    from quillseek.ingestion import ingest_files

    unsupported = tmp_path / "data.csv"
    unsupported.write_text("a,b", encoding="utf-8")
    result = ingest_files([unsupported])

    assert result.succeeded == 0
    assert len(result.failed) == 1
    assert result.failed[0].file_type == "unsupported"
    assert "Unsupported document type" in result.failed[0].error_message
    assert result.page_counts[result.failed[0].doc_id] == 0
