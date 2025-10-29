"""CSV-specific chunking strategy."""

from __future__ import annotations

from .base import BaseChunker
from .config import ChunkingConfig
from .metadata import ChunkMetadata
from .models import DocumentChunk
from .types import ChunkType


class CSVChunker(BaseChunker):
    """Chunk CSV data by row batches while keeping headers intact."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        lines = content.strip().split("\n")
        if not lines:
            return []

        header = lines[0]
        data_lines = lines[1:] if len(lines) > 1 else []
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for row_start in range(0, len(data_lines), self.config.csv_rows_per_chunk):
            row_end = min(row_start + self.config.csv_rows_per_chunk, len(data_lines))
            chunk_lines = data_lines[row_start:row_end]
            chunk_content = header + "\n" + "\n".join(chunk_lines)
            chunks.append(
                self._create_csv_chunk(
                    chunk_content,
                    document_id,
                    chunk_index,
                    row_start + 1,
                    row_end,
                )
            )
            chunk_index += 1

        return chunks

    def _create_csv_chunk(
        self,
        content: str,
        document_id: str,
        chunk_index: int,
        start_row: int,
        end_row: int,
    ) -> DocumentChunk:
        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=ChunkType.TABLE,
            chunk_index=chunk_index,
            start_position=start_row,
            end_position=end_row,
            section_title=f"Rows {start_row}-{end_row}",
            language=self.config.default_language,
        )

        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()
        return chunk


__all__ = ["CSVChunker"]
