# tests/integration/test_rag_api.py
# Integration tests for the /rag endpoint.

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.integration
class TestRAGSearchEndpoint:

    def test_search_too_short_query_rejected(self, client):
        """Query shorter than 3 chars should fail validation."""
        response = client.post(
            "/api/v1/rag/search",
            json={"query": "ab"},
        )
        assert response.status_code == 422

    def test_search_returns_results_structure(self, client):
        """Search endpoint should always return the correct response structure."""
        with patch(
            "app.api.endpoints.rag.rag_pipeline",
        ) as mock_pipeline:
            mock_pipeline.search = AsyncMock(return_value=[])

            response = client.post(
                "/api/v1/rag/search",
                json={
                    "query": "SQL injection vulnerability",
                    "session_id": "test-session",
                    "top_k": 3,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert data["query"] == "SQL injection vulnerability"

    def test_stats_endpoint_returns_collection_info(self, client):
        with patch(
            "app.api.endpoints.rag.rag_pipeline"
        ) as mock_pipeline:
            mock_pipeline.get_stats = MagicMock(return_value={
                "collection_name": "code_reviews",
                "total_documents": 42,
                "persist_directory": "/tmp/chroma",
            })

            response = client.get("/api/v1/rag/stats")

        assert response.status_code == 200
        data = response.json()
        assert "collection_name" in data
        assert "total_documents" in data

    def test_delete_session_endpoint(self, client):
        with patch(
            "app.api.endpoints.rag.chroma_client"
        ) as mock_chroma:
            mock_chroma.delete_session = AsyncMock(return_value=5)

            response = client.delete("/api/v1/rag/session/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert "chunks_deleted" in data