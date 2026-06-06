# app/models/schemas.py
# All Pydantic data models for request/response validation.

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReviewStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLEXITY = "complexity"
    OPTIMIZATION = "optimization"


# ---------------------------------------------------------------------------
# File Upload Schemas
# ---------------------------------------------------------------------------

class FileInfo(BaseModel):
    filename: str
    file_size: int
    file_extension: str
    language: str
    line_count: int
    char_count: int
    content_preview: str


class UploadResponse(BaseModel):
    session_id: str
    message: str
    total_files: int
    files: List[FileInfo]
    status: ReviewStatus = ReviewStatus.PENDING
    rag_chunks_stored: int = Field(
        default=0,
        description="Number of code chunks stored in ChromaDB vector store"
    )


# ---------------------------------------------------------------------------
# RAG / ChromaDB Schemas  ← NEW
# ---------------------------------------------------------------------------

class CodeChunk(BaseModel):
    """
    Represents one chunk of code stored in ChromaDB.
    A single file is split into many overlapping chunks.
    """
    chunk_id: str = Field(..., description="Unique ID: session_filename_chunkindex")
    session_id: str = Field(..., description="Upload session this chunk belongs to")
    filename: str = Field(..., description="Source file name")
    language: str = Field(..., description="Programming language")
    content: str = Field(..., description="The actual code text of this chunk")
    start_line: int = Field(..., description="First line number in original file")
    end_line: int = Field(..., description="Last line number in original file")
    chunk_index: int = Field(..., description="Position of this chunk within the file")
    total_chunks: int = Field(..., description="Total chunks this file was split into")


class RAGSearchResult(BaseModel):
    """One result returned from a ChromaDB similarity search."""
    chunk_id: str
    filename: str
    language: str
    content: str
    start_line: int
    end_line: int
    similarity_score: float = Field(
        ..., description="Cosine similarity 0.0–1.0 (higher = more similar)"
    )


class RAGSearchResponse(BaseModel):
    """Response from the RAG search endpoint."""
    query: str
    session_id: str
    results: List[RAGSearchResult]
    total_results: int


class RAGStoreResponse(BaseModel):
    """Response after storing code chunks in ChromaDB."""
    session_id: str
    total_chunks_stored: int
    files_processed: List[str]
    message: str


# ---------------------------------------------------------------------------
# Generic Responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    debug_mode: bool