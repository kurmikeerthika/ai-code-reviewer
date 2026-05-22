# app/main.py
# This is the entry point of your FastAPI application.
# FastAPI is a modern Python web framework that auto-generates API docs.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings


def create_application() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.
    Using a factory pattern makes it easy to create test instances later.
    """

    # Initialize FastAPI with metadata (shown in auto-generated docs)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        ## AI Code Reviewer

        An intelligent code review system powered by LLMs, LangGraph multi-agent workflow,
        and ChromaDB vector search.

        ### Features
        - 📁 Upload source code files for review
        - 🐛 Bug detection
        - 🔒 Security vulnerability analysis
        - ⏱️ Time complexity analysis
        - 💡 Optimization suggestions
        - 🤖 Multi-agent AI workflow
        - 🔍 RAG-powered contextual review
        - 🐙 GitHub PR integration
        """,
        docs_url="/docs",       # Swagger UI at http://localhost:8000/docs
        redoc_url="/redoc",     # ReDoc UI at http://localhost:8000/redoc
        debug=settings.debug,
    )

    # --- CORS Middleware ---
    # CORS allows your frontend (running on a different port) to call this API.
    # In production, replace ["*"] with your actual frontend domain.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # Allow all origins (change in production)
        allow_credentials=True,
        allow_methods=["*"],          # Allow GET, POST, PUT, DELETE, etc.
        allow_headers=["*"],          # Allow all headers
    )

    return application


# Create the app instance
app = create_application()


# ---------------------------------------------------------------------------
# Root Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint — confirms the API is running.
    Visit http://localhost:8000/ in your browser to see this.
    """
    return {
        "message": f"Welcome to {settings.app_name}!",
        "version": settings.app_version,
        "status": "running",
        "docs": "http://localhost:8000/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint — used by Docker and monitoring tools
    to verify the service is alive.
    """
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
    """
    Returns non-sensitive application configuration info.
    Useful for debugging which settings are loaded.
    """
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "model": settings.openai_model,
        "chroma_collection": settings.chroma_collection_name,
        "openai_key_set": bool(settings.openai_api_key),
        "github_token_set": bool(settings.github_token),
    }