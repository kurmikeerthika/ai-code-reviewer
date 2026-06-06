# app/api/endpoints/review.py
# Review endpoints — trigger AI review and fetch results by session ID.
from app.services.groq_services import review_code
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.graph import run_review_pipeline
from app.services.review_store import review_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/review",
    tags=["AI Code Review"],
)


class ReviewRequest(BaseModel):
    """Request body for triggering a code review."""
    session_id: str = Field(
        ...,
        description="Session ID from the /upload endpoint",
    )


@router.post(
    "/",
    summary="Trigger AI code review for an uploaded session",
    description="""
Run the full 5-agent AI review pipeline on a previously uploaded session.

**Steps:**
1. Looks up session data (files + contents) from the session store
2. Runs the LangGraph multi-agent pipeline
3. Saves the completed report to the session store
4. Returns the full structured report

**Note:** Takes 30–90 seconds depending on code size.
    """,
)
async def trigger_review(request: ReviewRequest):
    """
    Trigger the LangGraph pipeline using a session_id from /upload.
    No need to re-send file contents — they're retrieved from the store.
    """
    logger.info(f"Review triggered for session: {request.session_id}")

    # Look up session data
    session = review_store.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Session '{request.session_id}' not found. "
                f"Please upload files first using POST /api/v1/upload/"
            ),
        )

    # Run the LangGraph pipeline
    report = await run_review_pipeline(
        session_id=request.session_id,
        filenames=session["filenames"],
        language_map=session["language_map"],
        file_contents=session["file_contents"],
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review pipeline failed to produce a report. Check server logs.",
        )

    # Save report to store for later retrieval
    review_store.save_report(request.session_id, report)

    return report


@router.get(
    "/{session_id}",
    summary="Get completed review report",
    description="Fetch a previously completed review report by session ID.",
)
async def get_review_report(session_id: str):
    """Retrieve a completed review report."""
    report = review_store.get_report(session_id)

    if not report:
        session = review_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No completed report for session '{session_id}'. "
                f"Trigger a review first using POST /api/v1/review/"
            ),
        )

    return report


@router.get(
    "/sessions/list",
    summary="List all review sessions",
)
async def list_sessions():
    """Returns all sessions currently in the store."""
    return {
        "total_sessions": review_store.total_sessions,
        "sessions": review_store.list_sessions(),
    }