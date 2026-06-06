# app/rag/chunker.py
# Splits source code files into overlapping chunks for vector storage.
#
# Why chunk? LLMs and embedding models have token limits.
# Instead of sending 1000-line files, we send 40-line windows.
# Overlap ensures a function split at a boundary isn't lost.

import logging
from typing import List
from app.models.schemas import CodeChunk
from app.core.constants import (
    CHUNK_SIZE_LINES,
    CHUNK_OVERLAP_LINES,
    MIN_CHUNK_LINES,
    MAX_CHUNK_CHARS,
)

logger = logging.getLogger(__name__)


class CodeChunker:
    """
    Splits source code into overlapping line-based chunks.

    Example with CHUNK_SIZE_LINES=5, CHUNK_OVERLAP_LINES=2:

    File lines: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    Chunk 0: lines 1–5
    Chunk 1: lines 4–8   ← overlaps by 2 lines
    Chunk 2: lines 7–10  ← overlaps by 2 lines
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE_LINES,
        overlap: int = CHUNK_OVERLAP_LINES,
        min_lines: int = MIN_CHUNK_LINES,
        max_chars: int = MAX_CHUNK_CHARS,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_lines = min_lines
        self.max_chars = max_chars

        # Step size = how many lines to advance between chunks
        # With size=40, overlap=8 → step=32
        self.step = max(1, chunk_size - overlap)

    def chunk_file(
        self,
        content: str,
        filename: str,
        session_id: str,
        language: str,
    ) -> List[CodeChunk]:
        """
        Split a single file's content into overlapping CodeChunk objects.

        Args:
            content:    Full text content of the file
            filename:   Original filename (used in chunk IDs)
            session_id: Upload session ID (used in chunk IDs)
            language:   Detected programming language

        Returns:
            List of CodeChunk objects ready to store in ChromaDB
        """
        # Split file into individual lines (preserve empty lines)
        lines = content.splitlines()
        total_lines = len(lines)

        if total_lines < self.min_lines:
            logger.warning(
                f"File '{filename}' has only {total_lines} lines "
                f"(minimum {self.min_lines}). Storing as single chunk."
            )
            # Store tiny files as one chunk
            return self._make_single_chunk(
                content, filename, session_id, language, total_lines
            )

        chunks: List[CodeChunk] = []
        chunk_index = 0

        # Slide a window of `chunk_size` lines, advancing by `step` each time
        start = 0
        while start < total_lines:
            end = min(start + self.chunk_size, total_lines)

            # Extract the lines for this chunk
            chunk_lines = lines[start:end]
            chunk_content = "\n".join(chunk_lines)

            # Skip if chunk is too short (can happen at end of file)
            if len(chunk_lines) < self.min_lines:
                break

            # Truncate if somehow over character limit
            if len(chunk_content) > self.max_chars:
                chunk_content = chunk_content[: self.max_chars]
                logger.debug(f"Chunk truncated to {self.max_chars} chars")

            # Build a unique, readable chunk ID
            # e.g. "abc123_main_py_chunk_0"
            safe_filename = filename.replace(".", "_").replace("/", "_")
            chunk_id = f"{session_id}_{safe_filename}_chunk_{chunk_index}"

            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    session_id=session_id,
                    filename=filename,
                    language=language,
                    content=chunk_content,
                    start_line=start + 1,    # 1-based line numbers
                    end_line=end,
                    chunk_index=chunk_index,
                    total_chunks=0,          # Filled in after loop
                )
            )

            chunk_index += 1

            # If we've reached the end, stop
            if end >= total_lines:
                break

            # Advance window
            start += self.step

        # Now that we know the total, fill it in on every chunk
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks

        logger.info(
            f"Chunked '{filename}': "
            f"{total_lines} lines → {total_chunks} chunks "
            f"(size={self.chunk_size}, overlap={self.overlap})"
        )

        return chunks

    def _make_single_chunk(
        self,
        content: str,
        filename: str,
        session_id: str,
        language: str,
        total_lines: int,
    ) -> List[CodeChunk]:
        """Helper: wrap an entire small file as one chunk."""
        safe_filename = filename.replace(".", "_").replace("/", "_")
        chunk_id = f"{session_id}_{safe_filename}_chunk_0"
        return [
            CodeChunk(
                chunk_id=chunk_id,
                session_id=session_id,
                filename=filename,
                language=language,
                content=content[: self.max_chars],
                start_line=1,
                end_line=total_lines,
                chunk_index=0,
                total_chunks=1,
            )
        ]

    def chunk_multiple_files(
        self,
        file_contents: dict,
        session_id: str,
        file_language_map: dict,
    ) -> List[CodeChunk]:
        """
        Chunk all files in an upload session.

        Args:
            file_contents:     dict mapping filename → full content string
            session_id:        Upload session ID
            file_language_map: dict mapping filename → language string

        Returns:
            Flat list of all CodeChunk objects across all files
        """
        all_chunks: List[CodeChunk] = []

        for filename, content in file_contents.items():
            language = file_language_map.get(filename, "Unknown")
            file_chunks = self.chunk_file(content, filename, session_id, language)
            all_chunks.extend(file_chunks)

        logger.info(
            f"Session {session_id}: chunked {len(file_contents)} file(s) "
            f"into {len(all_chunks)} total chunks"
        )

        return all_chunks


# Shared singleton instance
code_chunker = CodeChunker()