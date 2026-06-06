# tests/unit/test_chunker.py
# Tests for the CodeChunker — verifies splitting, overlap, and edge cases.

import pytest
from app.rag.chunker import CodeChunker


@pytest.fixture
def chunker():
    """Create a chunker with small settings for easy testing."""
    return CodeChunker(chunk_size=5, overlap=2, min_lines=2)


@pytest.fixture
def large_chunker():
    """Default-sized chunker matching production settings."""
    return CodeChunker()


def make_content(n_lines: int, prefix: str = "line") -> str:
    """Helper: create a file with n numbered lines."""
    return "\n".join(f"{prefix} {i+1}" for i in range(n_lines))


# ── Basic Chunking ────────────────────────────────────────────────────────────

class TestChunkFile:

    def test_small_file_becomes_one_chunk(self, chunker):
        content = make_content(2)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        assert len(chunks) == 1

    def test_large_file_splits_into_multiple_chunks(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        assert len(chunks) > 1

    def test_chunk_ids_are_unique(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_contains_session_id(self, chunker):
        content = make_content(10)
        chunks = chunker.chunk_file(content, "test.py", "mysession", "Python")
        for chunk in chunks:
            assert chunk.session_id == "mysession"

    def test_chunk_contains_filename(self, chunker):
        content = make_content(10)
        chunks = chunker.chunk_file(content, "main.py", "sess1", "Python")
        for chunk in chunks:
            assert chunk.filename == "main.py"

    def test_chunk_contains_language(self, chunker):
        content = make_content(10)
        chunks = chunker.chunk_file(content, "main.py", "sess1", "JavaScript")
        for chunk in chunks:
            assert chunk.language == "JavaScript"

    def test_total_chunks_field_is_correct(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)

    def test_chunk_indices_are_sequential(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


# ── Line Numbers ──────────────────────────────────────────────────────────────

class TestLineNumbers:

    def test_first_chunk_starts_at_line_1(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        assert chunks[0].start_line == 1

    def test_line_numbers_are_one_based(self, chunker):
        content = make_content(10)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        for chunk in chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_last_chunk_end_line_within_file(self, chunker):
        content = make_content(15)
        total_lines = 15
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        assert chunks[-1].end_line <= total_lines


# ── Overlap ───────────────────────────────────────────────────────────────────

class TestOverlap:

    def test_overlap_means_chunks_share_lines(self, chunker):
        """With chunk_size=5 overlap=2, chunk 0 lines 1-5, chunk 1 starts at line 4."""
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")

        if len(chunks) >= 2:
            # Chunk 1 start should be before chunk 0 end (overlap)
            assert chunks[1].start_line < chunks[0].end_line

    def test_no_chunk_is_empty(self, chunker):
        content = make_content(20)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        for chunk in chunks:
            assert len(chunk.content.strip()) > 0


# ── Multiple Files ────────────────────────────────────────────────────────────

class TestChunkMultipleFiles:

    def test_chunks_from_all_files(self, chunker):
        file_contents = {
            "a.py": make_content(10),
            "b.js": make_content(10),
        }
        language_map = {"a.py": "Python", "b.js": "JavaScript"}

        all_chunks = chunker.chunk_multiple_files(
            file_contents, "sess1", language_map
        )

        filenames_in_chunks = {c.filename for c in all_chunks}
        assert "a.py" in filenames_in_chunks
        assert "b.js" in filenames_in_chunks

    def test_empty_file_contents_returns_empty(self, chunker):
        all_chunks = chunker.chunk_multiple_files({}, "sess1", {})
        assert all_chunks == []


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_single_line_file(self, chunker):
        content = "print('hello')"
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        # Single line < min_lines=2, treated as single chunk
        assert len(chunks) == 1

    def test_content_preserved_in_chunks(self, chunker):
        content = make_content(5)
        chunks = chunker.chunk_file(content, "test.py", "sess1", "Python")
        # All original content should appear in at least one chunk
        all_chunk_content = "\n".join(c.content for c in chunks)
        for line in content.split("\n"):
            assert line in all_chunk_content

    def test_special_characters_in_filename(self, chunker):
        content = make_content(5)
        # Dots and slashes in filename should be handled
        chunks = chunker.chunk_file(content, "src/utils.helper.py", "sess1", "Python")
        assert len(chunks) > 0
        for chunk in chunks:
            assert "." not in chunk.chunk_id.replace("sess1", "")