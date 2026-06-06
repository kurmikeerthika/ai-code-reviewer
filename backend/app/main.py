# app/main.py
# Entry point for the FastAPI application.
# Updated to include the API router with all endpoints.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import upload, review
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.constants import API_V1_PREFIX
from app.api.router import api_router

# Configure logging so all modules can write structured logs
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.
    """
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        ## AI Code Reviewer

        An intelligent code review system powered by LLMs, LangGraph multi-agent workflow,
        and ChromaDB vector search.

        ### Features
        - 📁 **Upload** source code files for review
        - 🐛 **Bug Detection** — find logical and runtime errors
        - 🔒 **Security Analysis** — detect vulnerabilities (SQLi, XSS, etc.)
        - ⏱️ **Complexity Analysis** — Big-O time/space complexity
        - 💡 **Optimization Suggestions** — performance improvements
        - 🤖 **Multi-agent Workflow** — powered by LangGraph
        - 🔍 **RAG Pipeline** — contextual review via ChromaDB
        - 🐙 **GitHub Integration** — post PR review comments

        ### How to use
        1. **POST** `/api/v1/upload/` — Upload your code files
        2. **POST** `/api/v1/review/` — Trigger AI review (coming soon)
        3. **GET** `/api/v1/results/{session_id}` — Fetch results (coming soon)
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.debug,
    )

    # CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all API routes under /api/v1
    application.include_router(api_router, prefix=API_V1_PREFIX)

    logger.info(f"{settings.app_name} v{settings.app_version} started")
    return application


app = create_application()


# ---------------------------------------------------------------------------
# Root Endpoints (outside /api/v1 — always accessible)
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — confirms the API is running."""
    return {
        "message": f"Welcome to {settings.app_name}!",
        "version": settings.app_version,
        "status": "running",
        "docs": "http://localhost:8000/docs",
        "api_base": f"http://localhost:8000{API_V1_PREFIX}",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "debug_mode": settings.debug,
        },
    )


@app.get("/info", tags=["Health"])
async def app_info():
    """Returns non-sensitive application configuration info."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "model": settings.openai_model,
        "chroma_collection": settings.chroma_collection_name,
        "openai_key_set": bool(settings.openai_api_key),
        "github_token_set": bool(settings.github_token),
        "api_prefix": API_V1_PREFIX,
    }
