# tests/unit/test_schemas.py
# Tests for Pydantic schemas — validation, enum values, defaults.

import pytest
from pydantic import ValidationError
from app.models.schemas import (
    FileInfo,
    UploadResponse,
    ReviewStatus,
    SeverityLevel,
    IssueCategory,
    CodeChunk,
    RAGSearchResult,
)


class TestReviewStatus:

    def test_all_valid_statuses(self):
        for status in ["pending", "processing", "completed", "failed"]:
            assert ReviewStatus(status) is not None

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            ReviewStatus("unknown_status")


class TestSeverityLevel:

    def test_all_valid_severities(self):
        for sev in ["critical", "high", "medium", "low", "info"]:
            assert SeverityLevel(sev) is not None

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError):
            SeverityLevel("extreme")


class TestFileInfo:

    def test_valid_file_info(self):
        info = FileInfo(
            filename="main.py",
            file_size=1024,
            file_extension=".py",
            language="Python",
            line_count=50,
            char_count=1024,
            content_preview="def main(): pass",
        )
        assert info.filename == "main.py"
        assert info.language == "Python"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            FileInfo(
                filename="main.py",
                # Missing all other required fields
            )


class TestUploadResponse:

    def test_valid_upload_response(self):
        info = FileInfo(
            filename="main.py",
            file_size=100,
            file_extension=".py",
            language="Python",
            line_count=10,
            char_count=100,
            content_preview="def foo(): pass",
        )
        response = UploadResponse(
            session_id="abc123",
            message="Uploaded successfully",
            total_files=1,
            files=[info],
        )
        assert response.status == ReviewStatus.PENDING
        assert response.rag_chunks_stored == 0

    def test_default_status_is_pending(self):
        info = FileInfo(
            filename="x.py",
            file_size=1,
            file_extension=".py",
            language="Python",
            line_count=1,
            char_count=1,
            content_preview="x",
        )
        response = UploadResponse(
            session_id="s1",
            message="ok",
            total_files=1,
            files=[info],
        )
        assert response.status == ReviewStatus.PENDING


class TestCodeChunk:

    def test_valid_code_chunk(self):
        chunk = CodeChunk(
            chunk_id="sess1_main_py_chunk_0",
            session_id="sess1",
            filename="main.py",
            language="Python",
            content="def foo(): pass",
            start_line=1,
            end_line=1,
            chunk_index=0,
            total_chunks=1,
        )
        assert chunk.chunk_id == "sess1_main_py_chunk_0"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            CodeChunk(
                chunk_id="id",
                # Missing all other required fields
            )


class TestRAGSearchResult:

    def test_valid_search_result(self):
        result = RAGSearchResult(
            chunk_id="chunk_1",
            filename="main.py",
            language="Python",
            content="def foo(): pass",
            start_line=1,
            end_line=1,
            similarity_score=0.95,
        )
        assert result.similarity_score == 0.95

    def test_similarity_score_is_float(self):
        result = RAGSearchResult(
            chunk_id="c1",
            filename="f.py",
            language="Python",
            content="x",
            start_line=1,
            end_line=1,
            similarity_score=0.5,
        )
        assert isinstance(result.similarity_score, float)