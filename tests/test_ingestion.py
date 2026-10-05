from ingestion import chunks_from_sections


def test_chunk_metadata_is_preserved():
    chunks = chunks_from_sections(
        [("Page 3", "retrieval augmented generation uses relevant context")],
        "source-1", "notes.pdf", "pdf"
    )
    assert len(chunks) == 1
    metadata = chunks[0].metadata()
    assert metadata["source_name"] == "notes.pdf"
    assert metadata["location"] == "Page 3"
    assert metadata["chunk_id"] == chunks[0].id


def test_empty_text_produces_no_chunks():
    assert chunks_from_sections([("Page 1", "   ")], "s", "empty.pdf", "pdf") == []

