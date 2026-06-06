# app/api/endpoints/upload.py
# File upload routes — validates, chunks, stores in ChromaDB,
# and saves session data to the review store.

import logging
from typing import List

from fastapi import APIRouter, UploadFile, File, status

from app.models.schemas import UploadResponse, ReviewStatus
from app.services.file_service import file_service
from app.services.review_store import review_store
from app.rag.rag_pipeline import rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["File Upload"],
)


@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload source code files for review",
    description="""
Upload one or more source code files to begin an AI code review session.

After upload, files are:
1. Validated (type, size)
2. Chunked and stored in ChromaDB for semantic search
3. Saved in session store for later retrieval

**Returns:** A `session_id` — use this in the `/review/` or `/github/review-pr` endpoints.
    """,
)
async def upload_files(
    files: List[UploadFile] = File(
        ...,
        description="One or more source code files to review",
    )
):
    logger.info(f"Upload request: {len(files)} file(s)")

    # Step 1: Validate and read all files
    session_id, file_infos, file_contents = await file_service.process_uploads(files)

    # Step 2: Build language map
    file_language_map = {info.filename: info.language for info in file_infos}
    filenames = [info.filename for info in file_infos]

    # Step 3: Store chunks in ChromaDB
    rag_response = await rag_pipeline.store_files(
        file_contents=file_contents,
        session_id=session_id,
        file_language_map=file_language_map,
    )

    # Step 4: Save session data for later retrieval
    review_store.save_session(
        session_id=session_id,
        filenames=filenames,
        language_map=file_language_map,
        file_contents=file_contents,
    )

    logger.info(
        f"Session {session_id}: {len(file_infos)} file(s) uploaded, "
        f"{rag_response.total_chunks_stored} chunks stored"
    )

    return UploadResponse(
        session_id=session_id,
        message=(
            f"Successfully uploaded {len(file_infos)} file(s) and stored "
            f"{rag_response.total_chunks_stored} code chunks in ChromaDB. "
            f"Use session_id '{session_id}' to start the AI review."
        ),
        total_files=len(file_infos),
        files=file_infos,
        status=ReviewStatus.PENDING,
        rag_chunks_stored=rag_response.total_chunks_stored,
    )


@router.get(
    "/supported-languages",
    summary="List all supported programming languages",
)
async def get_supported_languages():
    """Returns all file extensions and languages supported for review."""
    from app.core.constants import EXTENSION_TO_LANGUAGE
    return {
        "total_supported": len(EXTENSION_TO_LANGUAGE),
        "languages": EXTENSION_TO_LANGUAGE,
    }