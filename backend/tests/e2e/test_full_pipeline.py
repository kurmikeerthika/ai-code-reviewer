# tests/e2e/test_full_pipeline.py
# End-to-end test of the complete review pipeline.
# Uses mocked external services (OpenAI, ChromaDB) but tests the
# full request → response flow including all business logic.

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.e2e
class TestFullReviewPipeline:

    def test_upload_then_review_full_flow(
        self,
        client,
        sample_python_file,
        mock_rag_pipeline,
        mock_chat_openai,
    ):
        """
        Full flow test:
        1. Upload a file
        2. Get session_id
        3. Trigger review using session_id
        4. Verify structured report returned
        """

        # Step 1: Upload
        with open(sample_python_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/upload/",
                files={"files": ("test_code.py", f, "text/plain")},
            )

        assert upload_response.status_code == 201
        session_id = upload_response.json()["session_id"]
        assert session_id is not None

        # Step 2: Trigger Review (mock the heavy pipeline call)
        with patch(
            "app.api.endpoints.review.run_review_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = {
                "report_id": f"review_{session_id}",
                "session_id": session_id,
                "generated_at": "2025-01-01T00:00:00Z",
                "files_reviewed": ["test_code.py"],
                "languages": ["Python"],
                "summary": (
                    "The code contains a division by zero bug, "
                    "a hardcoded password, and a nested loop performance issue."
                ),
                "statistics": {
                    "total_issues": 3,
                    "severity_counts": {
                        "critical": 0, "high": 2, "medium": 1,
                        "low": 0, "info": 0
                    },
                    "by_category": {
                        "bugs": 1, "security": 1,
                        "complexity": 1, "optimization": 0
                    },
                },
                "issues": {
                    "bugs": [{
                        "issue_id": "BUG_001",
                        "category": "bug",
                        "severity": "high",
                        "title": "Division by zero",
                        "description": "The divide() function has no zero check.",
                        "filename": "test_code.py",
                        "line_start": 7,
                        "line_end": 8,
                        "code_snippet": "return a / b",
                        "suggestion": "if b == 0: raise ValueError('Cannot divide by zero')",
                        "confidence": 0.97,
                    }],
                    "security": [{
                        "issue_id": "SEC_001",
                        "category": "security",
                        "severity": "high",
                        "title": "Hardcoded password",
                        "description": "Password stored in plain text.",
                        "filename": "test_code.py",
                        "line_start": 10,
                        "line_end": 10,
                        "code_snippet": 'password = "admin123"',
                        "suggestion": "Use environment variables.",
                        "confidence": 0.99,
                    }],
                    "complexity": [{
                        "issue_id": "CPX_001",
                        "category": "complexity",
                        "severity": "medium",
                        "title": "O(n²) nested loop",
                        "description": "Nested loops result in quadratic complexity.",
                        "filename": "test_code.py",
                        "line_start": 12,
                        "line_end": 14,
                        "code_snippet": "for i in range(1000):\n    for j in range(1000):",
                        "suggestion": "Restructure to avoid nested iteration.",
                        "confidence": 0.9,
                    }],
                    "optimization": [],
                },
            }

            review_response = client.post(
                "/api/v1/review/",
                json={"session_id": session_id},
            )

        # Step 3: Verify report
        assert review_response.status_code == 200
        report = review_response.json()

        assert report["session_id"] == session_id
        assert "statistics" in report
        assert report["statistics"]["total_issues"] == 3
        assert len(report["issues"]["bugs"]) == 1
        assert len(report["issues"]["security"]) == 1
        assert len(report["issues"]["complexity"]) == 1
        assert report["issues"]["bugs"][0]["title"] == "Division by zero"
        assert report["issues"]["security"][0]["severity"] == "high"

        # Step 4: Fetch saved report
        get_response = client.get(f"/api/v1/review/{session_id}")
        assert get_response.status_code == 200
        saved_report = get_response.json()
        assert saved_report["session_id"] == session_id

    def test_upload_unsupported_file_never_reaches_review(
        self, client, sample_text_file
    ):
        """Uploading an unsupported file should fail at upload — review never runs."""
        with open(sample_text_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/upload/",
                files={"files": ("readme.txt", f, "text/plain")},
            )
        # Should fail at upload, never reach review
        assert upload_response.status_code == 400
        assert "session_id" not in upload_response.json()

    def test_review_store_persists_between_requests(
        self, client, sample_python_file, mock_rag_pipeline
    ):
        """Session data saved during upload must be retrievable in review."""
        with open(sample_python_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/upload/",
                files={"files": ("test_code.py", f, "text/plain")},
            )

        assert upload_response.status_code == 201
        session_id = upload_response.json()["session_id"]

        # Verify session is listed
        list_response = client.get("/api/v1/review/sessions/list")
        sessions = list_response.json()["sessions"]
        session_ids = [s["session_id"] for s in sessions]
        assert session_id in session_ids