
# tests/conftest.py
# Shared pytest fixtures for the AI Code Reviewer project
# Updated for OFFLINE Ollama + Qwen setup

import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

# ─────────────────────────────────────────────────────────────
# Test Environment Variables
# ─────────────────────────────────────────────────────────────

# Offline model config
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:1.5b")

# Optional GitHub token for tests
os.environ.setdefault("GITHUB_TOKEN", "ghp_test-fake-token")

# Debug mode
os.environ.setdefault("DEBUG", "true")

# Chroma test DB
os.environ.setdefault(
    "CHROMA_PERSIST_DIRECTORY",
    "/tmp/test_chroma_db"
)

# Import app AFTER environment setup
from app.main import app


# ─────────────────────────────────────────────────────────────
# FastAPI Test Client
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """
    Shared FastAPI test client.
    """
    with TestClient(app) as test_client:
        yield test_client


# ─────────────────────────────────────────────────────────────
# Sample Code Strings
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_python_code():
    return '''
# Sample Python file with intentional issues

def divide(a, b):
    return a / b

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return query

password = "admin123"

def slow_search(items, target):
    results = []
    for item in items:
        for check in items:
            if item == target:
                results.append(item)
    return results

def process_data(data):
    result = ""
    for item in data:
        result = result + str(item)
    return result
'''


@pytest.fixture
def sample_javascript_code():
    return '''
// JavaScript file with issues

function getUserData(userId) {
    const query = "SELECT * FROM users WHERE id = " + userId;
    return db.execute(query);
}

const API_KEY = "sk-hardcoded-key";

function divide(a, b) {
    return a / b;
}
'''


# ─────────────────────────────────────────────────────────────
# Temporary Test Files
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_python_file(sample_python_code, tmp_path):
    file_path = tmp_path / "test_code.py"
    file_path.write_text(sample_python_code, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_javascript_file(sample_javascript_code, tmp_path):
    file_path = tmp_path / "test_code.js"
    file_path.write_text(sample_javascript_code, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_text_file(tmp_path):
    file_path = tmp_path / "readme.txt"
    file_path.write_text(
        "This is not valid source code.",
        encoding="utf-8"
    )
    return file_path


@pytest.fixture
def empty_python_file(tmp_path):
    file_path = tmp_path / "empty.py"
    file_path.write_text("", encoding="utf-8")
    return file_path


# ─────────────────────────────────────────────────────────────
# Mock Ollama Embeddings
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ollama_embeddings(monkeypatch):
    """
    Mock embedding model for offline tests.
    """

    mock = AsyncMock()

    # Fake embeddings
    mock.aembed_documents = AsyncMock(
        return_value=[
            [0.1] * 384,
            [0.2] * 384
        ]
    )

    mock.aembed_query = AsyncMock(
        return_value=[0.1] * 384
    )

    monkeypatch.setattr(
        "app.rag.embeddings.embedding_model",
        mock
    )

    return mock


# ─────────────────────────────────────────────────────────────
# Mock ChatOllama LLM
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_chat_ollama(monkeypatch):
    """
    Replace real Ollama calls with fake responses.
    """

    mock_llm = MagicMock()

    fake_response = MagicMock()

    fake_response.content = '''
{
    "issues": [
        {
            "issue_id": "TEST_001",
            "title": "Division by zero risk",
            "description": "No validation before division",
            "filename": "test_code.py",
            "line_start": 5,
            "line_end": 5,
            "code_snippet": "return a / b",
            "suggestion": "Check if b == 0 before division",
            "severity": "high",
            "confidence": 0.95
        }
    ]
}
'''

    mock_llm.ainvoke = AsyncMock(
        return_value=fake_response
    )

    monkeypatch.setattr(
        "app.agents.base_agent.ChatOllama",
        lambda **kwargs: mock_llm
    )

    monkeypatch.setattr(
        "app.agents.synthesizer.ChatOllama",
        lambda **kwargs: mock_llm
    )

    return mock_llm


# ─────────────────────────────────────────────────────────────
# Mock RAG Pipeline
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_rag_pipeline(monkeypatch):
    """
    Mock vector DB + RAG system.
    """

    mock = MagicMock()

    mock.store_files = AsyncMock(
        return_value=MagicMock(
            total_chunks_stored=3,
            files_processed=["test_code.py"],
            message="Stored 3 chunks"
        )
    )

    mock.search = AsyncMock(return_value=[])

    mock.build_context_for_review = AsyncMock(
        return_value="""
## Mock RAG Context

No real vector search used in tests.
"""
    )

    mock.get_stats = MagicMock(
        return_value={
            "collection_name": "test_collection",
            "total_documents": 0,
            "persist_directory": "/tmp/test_chroma",
        }
    )

    monkeypatch.setattr(
        "app.api.endpoints.upload.rag_pipeline",
        mock
    )

    monkeypatch.setattr(
        "app.agents.graph.rag_pipeline",
        mock
    )

    return mock


# ─────────────────────────────────────────────────────────────
# Mock Review Store
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_review_store(monkeypatch):
    """
    Fake in-memory review store.
    """

    from app.services.review_store import ReviewStore

    store = ReviewStore()

    store.save_session(
        session_id="test-session-123",
        filenames=["test_code.py"],
        language_map={"test_code.py": "Python"},
        file_contents={
            "test_code.py": "def foo(): pass"
        },
    )

    monkeypatch.setattr(
        "app.api.endpoints.review.review_store",
        store
    )

    monkeypatch.setattr(
        "app.api.endpoints.upload.review_store",
        store
    )

    return store

