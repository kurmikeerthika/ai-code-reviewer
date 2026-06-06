# tests/integration/test_upload_api.py
# Integration tests for the /upload endpoint.
# Uses TestClient — real HTTP requests, real validation, mocked external services.

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestUploadEndpoint:

    def test_upload_python_file_succeeds(
        self, client, sample_python_file, mock_rag_pipeline, mock_review_store
    ):
        """Uploading a valid .py file should return 201 with session_id."""
        with open(sample_python_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("test_code.py", f, "text/plain")},
            )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 16
        assert data["total_files"] == 1
        assert data["files"][0]["filename"] == "test_code.py"
        assert data["files"][0]["language"] == "Python"
        assert data["status"] == "pending"

    def test_upload_javascript_file_succeeds(
        self, client, sample_javascript_file, mock_rag_pipeline, mock_review_store
    ):
        with open(sample_javascript_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("test_code.js", f, "text/plain")},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["files"][0]["language"] == "JavaScript"

    def test_upload_txt_file_rejected(self, client, sample_text_file):
        """Text files should be rejected with 400."""
        with open(sample_text_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("readme.txt", f, "text/plain")},
            )
        assert response.status_code == 400
        assert ".txt" in response.json()["detail"]

    def test_upload_empty_file_rejected(self, client, empty_python_file):
        """Empty files should be rejected with 400."""
        with open(empty_python_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("empty.py", f, "text/plain")},
            )
        assert response.status_code == 400

    def test_upload_no_files_rejected(self, client):
        """Request with no files should be rejected."""
        response = client.post("/api/v1/upload/")
        assert response.status_code == 422  # Unprocessable entity

    def test_upload_multiple_files(
        self, client, sample_python_file, sample_javascript_file,
        mock_rag_pipeline, mock_review_store
    ):
        """Multiple files should all be processed."""
        with open(sample_python_file, "rb") as py_f, \
             open(sample_javascript_file, "rb") as js_f:
            response = client.post(
                "/api/v1/upload/",
                files=[
                    ("files", ("test.py", py_f, "text/plain")),
                    ("files", ("test.js", js_f, "text/plain")),
                ],
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_files"] == 2

    def test_upload_response_includes_preview(
        self, client, sample_python_file, mock_rag_pipeline, mock_review_store
    ):
        """Response should include a content preview."""
        with open(sample_python_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("test.py", f, "text/plain")},
            )
        data = response.json()
        assert len(data["files"][0]["content_preview"]) > 0

    def test_upload_response_includes_line_count(
        self, client, sample_python_file, mock_rag_pipeline, mock_review_store
    ):
        with open(sample_python_file, "rb") as f:
            response = client.post(
                "/api/v1/upload/",
                files={"files": ("test.py", f, "text/plain")},
            )
        data = response.json()
        assert data["files"][0]["line_count"] > 0


class TestSupportedLanguagesEndpoint:

    def test_returns_language_list(self, client):
        response = client.get("/api/v1/upload/supported-languages")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert ".py" in data["languages"]
        assert ".js" in data["languages"]
        assert data["total_supported"] > 0

    def test_python_maps_to_correct_language(self, client):
        response = client.get("/api/v1/upload/supported-languages")
        data = response.json()
        assert data["languages"][".py"] == "Python"