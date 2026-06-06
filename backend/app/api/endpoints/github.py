# app/api/endpoints/github.py
# GitHub PR integration endpoints.
# Fetches PR files, runs AI review, and posts results as PR comments.
import traceback
import logging
import secrets
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.services.github_service import github_service
from app.services.review_store import review_store
from app.rag.rag_pipeline import rag_pipeline
from app.agents.graph import run_review_pipeline
from app.core.constants import EXTENSION_TO_LANGUAGE

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/github",
    tags=["GitHub Integration"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PRReviewRequest(BaseModel):
    """Request body for reviewing a GitHub PR."""
    pr_url: str = Field(
        ...,
        description="Full GitHub PR URL e.g. https://github.com/owner/repo/pull/42",
    )
    post_comment: bool = Field(
        default=True,
        description="Whether to post the review as a comment on the PR",
    )
    max_files: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of changed files to review",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/review-pr",
    summary="Review a GitHub Pull Request",
    description="""
Fetch all changed files from a GitHub PR, run the full AI review pipeline,
and optionally post the findings as a comment directly on the PR.

**What happens:**
1. PR URL is validated and metadata fetched
2. Changed files are downloaded from GitHub
3. Files are chunked and stored in ChromaDB
4. The 5-agent LangGraph pipeline runs
5. A formatted Markdown report is posted as a PR comment (if enabled)

**Requirements:**
- `GITHUB_TOKEN` must be set in your `.env` file
- Token needs `repo` scope (for private repos) or `public_repo` (for public repos)
- `OPENAI_API_KEY` must be set

**Note:** Takes 30–120 seconds depending on PR size.
    """,
)
async def review_pull_request(request: PRReviewRequest):
    """
    End-to-end PR review: fetch → chunk → review → comment.
    """
    logger.info(f"PR review requested: {request.pr_url}")

    # Step 1: Validate and fetch PR metadata
    try:
        pr_metadata = github_service.get_pr_metadata(request.pr_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    

    logger.info(
        f"Reviewing PR #{pr_metadata['pr_number']}: "
        f"'{pr_metadata['title']}' by @{pr_metadata['author']}"
    )

    # Step 2: Fetch changed file contents from GitHub
    try:
        file_contents = github_service.fetch_pr_files(
            pr_url=request.pr_url,
            max_files=request.max_files,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
   

    # Step 3: Build language map for fetched files
    filenames = list(file_contents.keys())
    language_map = {}
    for filename in filenames:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        language_map[filename] = EXTENSION_TO_LANGUAGE.get(ext, "Unknown")

    # Step 4: Generate a session ID for this PR review
    session_id = f"pr_{secrets.token_hex(8)}"

    # Step 5: Store chunks in ChromaDB
    logger.info(f"Storing {len(filenames)} PR file(s) in ChromaDB...")
    try:
        await rag_pipeline.store_files(
            file_contents=file_contents,
            session_id=session_id,
            file_language_map=language_map,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store files in vector store: {str(e)}",
        )

    # Step 6: Save session to store
    review_store.save_session(
        session_id=session_id,
        filenames=filenames,
        language_map=language_map,
        file_contents=file_contents,
    )

    # # Step 7: Run the full AI review pipeline
    logger.info(f"Running AI review pipeline for session: {session_id}")
    try:
        report = await run_review_pipeline(
            session_id=session_id,
            filenames=filenames,
            language_map=language_map,
            file_contents=file_contents,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI review pipeline failed: {str(e)}",
        )
    
    

    # Enrich report with PR metadata
    report["pr_metadata"] = pr_metadata

    # Save report to store
    review_store.save_report(session_id, report)

    # Step 8: Post comment to GitHub PR (if requested)
    comment_url = None
    if request.post_comment:
        try:
            markdown_report = github_service.format_review_as_markdown(report)
            comment_url = github_service.post_review_comment(
                pr_url=request.pr_url,
                comment_body=markdown_report,
            )
            logger.info(f"Review comment posted: {comment_url}")
        except ValueError as e:
            # Don't fail the whole request just because comment posting failed
            logger.error(f"Failed to post GitHub comment: {e}")
            report["comment_error"] = str(e)

    return {
        "session_id": session_id,
        "pr_metadata": pr_metadata,
        "files_reviewed": filenames,
        "comment_posted": comment_url is not None,
        "comment_url": comment_url,
        "report": report,
    }


@router.get(
    "/pr-info",
    summary="Fetch PR metadata without running review",
    description="Preview PR information before committing to a full review.",
)
async def get_pr_info(pr_url: str):
    """
    Fetch and return GitHub PR metadata.
    Useful to confirm the correct PR before triggering a full review.
    """
    try:
        metadata = github_service.get_pr_metadata(pr_url)
        files = github_service.fetch_pr_files(pr_url=pr_url, max_files=20)
        filenames = list(files.keys())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "pr_metadata": metadata,
        "reviewable_files": filenames,
        "total_reviewable_files": len(filenames),
    }