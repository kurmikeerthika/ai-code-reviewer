# app/api/endpoints/rag.py
# HTTP endpoints for interacting with the RAG pipeline directly.
# Useful for testing and debugging the vector store.

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.models.schemas import RAGSearchResponse, RAGStoreResponse
from app.rag.rag_pipeline import rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG Pipeline"],
)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Request body for semantic code search."""
    query: str = Field(
        ...,
        min_length=3,
        description="What to search for, e.g. 'SQL injection vulnerability'",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Limit search to this session's files (recommended)",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return",
    )
    filename_filter: Optional[str] = Field(
        default=None,
        description="Limit search to this specific filename",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="Semantic search over stored code chunks",
)
async def search_code(request: SearchRequest):
    """
    Search the ChromaDB vector store for code chunks similar to your query.

    This is a semantic search — it finds code by meaning, not exact keywords.

    **Example queries:**
    - "SQL injection vulnerability"
    - "hardcoded password or secret"
    - "nested loops with high complexity"
    - "missing input validation"
    - "functions that could raise exceptions"
    """
    results = await rag_pipeline.search(
        query=request.query,
        session_id=request.session_id,
        top_k=request.top_k,
        filename_filter=request.filename_filter,
    )

    return RAGSearchResponse(
        query=request.query,
        session_id=request.session_id or "all_sessions",
        results=results,
        total_results=len(results),
    )


@router.get(
    "/stats",
    summary="ChromaDB collection statistics",
)
async def get_rag_stats():
    """
    Returns the current state of the ChromaDB vector store:
    - Collection name
    - Total documents stored
    - Storage directory
    """
    return rag_pipeline.get_stats()


@router.delete(
    "/session/{session_id}",
    summary="Delete all chunks for a session",
)
async def delete_session_chunks(session_id: str):
    """
    Delete all stored code chunks for a specific upload session.
    Useful for cleanup or re-uploading the same files.
    """
    from app.rag.chroma_client import chroma_client

    deleted = await chroma_client.delete_session(session_id)

    return {
        "session_id": session_id,
        "chunks_deleted": deleted,
        "message": f"Deleted {deleted} chunks for session '{session_id}'",
    }