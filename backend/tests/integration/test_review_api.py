# tests/integration/test_review_api.py
# Integration tests for the /review endpoint.

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
class TestReviewEndpoint:

    def test_review_unknown_session_returns_404(self, client):
        """Reviewing a nonexistent session should return 404."""
        response = client.post(
            "/api/v1/review/",
            json={"session_id": "nonexistent-session-xyz"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_review_valid_session_returns_report(
        self, client, mock_review_store, mock_rag_pipeline, mock_chat_openai
    ):
        """A valid session_id should trigger the pipeline and return a report."""
        with patch(
            "app.api.endpoints.review.run_review_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = {
                "report_id": "review_test-session-abc123",
                "session_id": "test-session-abc123",
                "generated_at": "2025-01-01T00:00:00Z",
                "files_reviewed": ["test_code.py"],
                "summary": "Mock review complete.",
                "statistics": {
                    "total_issues": 2,
                    "severity_counts": {
                        "critical": 0, "high": 1, "medium": 1,
                        "low": 0, "info": 0
                    },
                    "by_category": {
                        "bugs": 1, "security": 1,
                        "complexity": 0, "optimization": 0
                    },
                },
                "issues": {
                    "bugs": [], "security": [],
                    "complexity": [], "optimization": []
                },
            }

            response = client.post(
                "/api/v1/review/",
                json={"session_id": "test-session-abc123"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-abc123"
        assert "statistics" in data
        assert data["statistics"]["total_issues"] == 2

    def test_get_report_after_review(self, client, mock_review_store):
        """GET /review/{session_id} should return the saved report."""
        # Pre-save a report in the store
        mock_review_store.save_report("test-session-abc123", {
            "report_id": "review_test-session-abc123",
            "session_id": "test-session-abc123",
            "summary": "Review complete.",
        })

        response = client.get("/api/v1/review/test-session-abc123")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-abc123"

    def test_get_report_no_review_yet_returns_404(self, client, mock_review_store):
        """GET report for session without review should return 404."""
        response = client.get("/api/v1/review/test-session-abc123")
        assert response.status_code == 404

    def test_list_sessions_returns_all(self, client, mock_review_store):
        response = client.get("/api/v1/review/sessions/list")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total_sessions"] >= 1

    def test_review_missing_session_id_returns_422(self, client):
        """Request body without session_id should fail validation."""
        response = client.post(
            "/api/v1/review/",
            json={},  # Missing session_id
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestHealthEndpoints:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_returns_healthy(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_info_returns_app_info(self, client):
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data