"""Unit tests for the SQLite-backed document store chunking integration."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from core.document_store import DocumentStore


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Return a path for a throwaway SQLite database."""

    return tmp_path / "documents.db"


def _fetch_chunk_rows(db_path: Path, document_id: str) -> list[tuple[str, str]]:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content, metadata FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        )
        return cursor.fetchall()


def test_add_document_persists_chunk_records(temp_db_path: Path) -> None:
    store = DocumentStore(db_path=str(temp_db_path))

    document_id = store.add_document("Sample paragraph content." * 10, title="Doc")

    stored_chunks = _fetch_chunk_rows(temp_db_path, document_id)
    assert stored_chunks, "Expected at least one chunk to be persisted"
    assert store.chunk_manager.get_chunks(document_id), "Chunk manager should index chunks"


def test_short_document_uses_fallback_chunk(temp_db_path: Path) -> None:
    store = DocumentStore(db_path=str(temp_db_path))

    document_id = store.add_document("short text", title="Tiny Doc")

    stored_chunks = _fetch_chunk_rows(temp_db_path, document_id)
    assert len(stored_chunks) == 1, "Fallback chunk should be the only record"
    content, metadata_raw = stored_chunks[0]
    metadata = json.loads(metadata_raw)
    assert content == "short text"
    assert metadata["chunk_index"] == 0


def test_csv_documents_mark_chunks_as_table(temp_db_path: Path) -> None:
    store = DocumentStore(db_path=str(temp_db_path))

    document_id = store.add_document(
        "header1,header2\nvalue1,value2",
        title="CSV Doc",
        doc_type="csv",
        metadata={"file_extension": "csv"},
    )

    stored_chunks = _fetch_chunk_rows(temp_db_path, document_id)
    assert stored_chunks, "CSV document should be chunked"
    _, metadata_raw = stored_chunks[0]
    metadata = json.loads(metadata_raw)
    assert metadata["chunk_type"] == "table"
