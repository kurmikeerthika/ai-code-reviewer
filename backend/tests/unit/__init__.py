# tests/unit/test_file_service.py
# Tests for FileService — file validation, reading, and metadata extraction.
# These are pure unit tests — no HTTP, no database, no external APIs.

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.services.file_service import FileService


@pytest.fixture
def service():
    """Create a fresh FileService for each test."""
    return FileService()


# ── Extension Detection ───────────────────────────────────────────────────────

class TestGetFileExtension:

    def test_python_extension(self, service):
        assert service.get_file_extension("main.py") == ".py"

    def test_javascript_extension(self, service):
        assert service.get_file_extension("app.js") == ".js"

    def test_uppercase_extension_is_lowercased(self, service):
        assert service.get_file_extension("App.PY") == ".py"

    def test_dotfile_with_no_extension(self, service):
        assert service.get_file_extension(".gitignore") == ""

    def test_nested_extension(self, service):
        # index.test.ts → should return .ts
        assert service.get_file_extension("index.test.ts") == ".ts"

    def test_path_with_directories(self, service):
        assert service.get_file_extension("src/components/App.tsx") == ".tsx"


# ── Language Detection ────────────────────────────────────────────────────────

class TestDetectLanguage:

    def test_python(self, service):
        assert service.detect_language("script.py") == "Python"

    def test_javascript(self, service):
        assert service.detect_language("app.js") == "JavaScript"

    def test_typescript(self, service):
        assert service.detect_language("types.ts") == "TypeScript"

    def test_java(self, service):
        assert service.detect_language("Main.java") == "Java"

    def test_go(self, service):
        assert service.detect_language("main.go") == "Go"

    def test_unknown_extension(self, service):
        assert service.detect_language("file.xyz") == "Unknown"

    def test_no_extension(self, service):
        assert service.detect_language("Makefile") == "Unknown"


# ── Extension Validation ──────────────────────────────────────────────────────

class TestValidateFileExtension:

    def test_valid_python_passes(self, service):
        # Should not raise
        service.validate_file_extension("main.py")

    def test_valid_javascript_passes(self, service):
        service.validate_file_extension("app.js")

    def test_txt_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_extension("readme.txt")
        assert exc_info.value.status_code == 400
        assert ".txt" in exc_info.value.detail

    def test_pdf_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_extension("document.pdf")
        assert exc_info.value.status_code == 400

    def test_no_extension_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_extension("Makefile")
        assert exc_info.value.status_code == 400
        assert "no extension" in exc_info.value.detail.lower()

    def test_exe_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_extension("program.exe")
        assert exc_info.value.status_code == 400


# ── File Count Validation ─────────────────────────────────────────────────────

class TestValidateFileCount:

    def test_single_file_passes(self, service):
        files = [MagicMock()]
        service.validate_file_count(files)  # Should not raise

    def test_max_files_passes(self, service):
        files = [MagicMock() for _ in range(10)]
        service.validate_file_count(files)  # 10 is the max, should pass

    def test_too_many_files_raises_400(self, service):
        files = [MagicMock() for _ in range(11)]
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_count(files)
        assert exc_info.value.status_code == 400
        assert "10" in exc_info.value.detail

    def test_empty_list_raises_400(self, service):
        with pytest.raises(HTTPException) as exc_info:
            service.validate_file_count([])
        assert exc_info.value.status_code == 400
        assert "no files" in exc_info.value.detail.lower()


# ── File Content Reading ──────────────────────────────────────────────────────

class TestReadFileContent:

    @pytest.mark.asyncio
    async def test_reads_valid_utf8_file(self, service):
        mock_file = AsyncMock()
        mock_file.filename = "main.py"
        mock_file.read = AsyncMock(return_value=b"def hello(): pass\n")

        raw, content = await service.read_file_content(mock_file)

        assert raw == b"def hello(): pass\n"
        assert content == "def hello(): pass\n"

    @pytest.mark.asyncio
    async def test_empty_file_raises_400(self, service):
        mock_file = AsyncMock()
        mock_file.filename = "empty.py"
        mock_file.read = AsyncMock(return_value=b"")

        with pytest.raises(HTTPException) as exc_info:
            await service.read_file_content(mock_file)
        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_file_too_large_raises_400(self, service):
        mock_file = AsyncMock()
        mock_file.filename = "huge.py"
        # 2MB — over the 1MB limit
        mock_file.read = AsyncMock(return_value=b"x" * (2 * 1024 * 1024))

        with pytest.raises(HTTPException) as exc_info:
            await service.read_file_content(mock_file)
        assert exc_info.value.status_code == 400
        assert "large" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_binary_file_raises_422(self, service):
        mock_file = AsyncMock()
        mock_file.filename = "binary.py"
        # Invalid UTF-8 bytes
        mock_file.read = AsyncMock(return_value=b"\xff\xfe binary content")

        with pytest.raises(HTTPException) as exc_info:
            await service.read_file_content(mock_file)
        assert exc_info.value.status_code == 422


# ── Metadata Extraction ───────────────────────────────────────────────────────

class TestExtractFileMetadata:

    def test_line_count(self, service):
        content = "line1\nline2\nline3\n"
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("main.py", raw, content)
        assert info.line_count == 4  # 3 newlines + 1

    def test_char_count(self, service):
        content = "hello"
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("main.py", raw, content)
        assert info.char_count == 5

    def test_preview_truncated(self, service):
        content = "x" * 500  # Longer than CONTENT_PREVIEW_LENGTH (300)
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("main.py", raw, content)
        assert len(info.content_preview) <= 304  # 300 + "..."
        assert info.content_preview.endswith("...")

    def test_short_content_not_truncated(self, service):
        content = "def foo(): pass"
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("main.py", raw, content)
        assert not info.content_preview.endswith("...")
        assert info.content_preview == content

    def test_language_detected(self, service):
        content = "def foo(): pass"
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("script.py", raw, content)
        assert info.language == "Python"

    def test_file_size_in_bytes(self, service):
        content = "hello"
        raw = content.encode("utf-8")
        info = service.extract_file_metadata("main.py", raw, content)
        assert info.file_size == 5


# ── Session ID Generation ─────────────────────────────────────────────────────

class TestGenerateSessionId:

    def test_session_id_is_string(self, service):
        sid = service.generate_session_id()
        assert isinstance(sid, str)

    def test_session_id_is_16_chars(self, service):
        sid = service.generate_session_id()
        assert len(sid) == 16

    def test_session_ids_are_unique(self, service):
        ids = {service.generate_session_id() for _ in range(100)}
        assert len(ids) == 100  # All 100 should be unique