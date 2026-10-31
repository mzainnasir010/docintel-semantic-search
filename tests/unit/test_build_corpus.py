"""Unit tests for source-page text extraction."""

from backend.scripts.build_corpus import html_to_text


def test_html_to_text_preserves_content_and_removes_navigation() -> None:
    html = """
    <html><nav>Home | Previous</nav><div role="navigation">index | modules</div><main>
    <h1>JSON encoding</h1><p>Use json.dumps() to serialize objects.</p>
    <ul><li>Lists are supported.</li></ul></main><script>ignore me</script></html>
    """
    extracted = html_to_text(html)

    assert "JSON encoding" in extracted
    assert "json.dumps()" in extracted
    assert "Lists are supported." in extracted
    assert "Home | Previous" not in extracted
    assert "index | modules" not in extracted
    assert "ignore me" not in extracted
