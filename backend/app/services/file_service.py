# app/services/file_service.py
# Handles all file-related operations:
# - Validating uploaded files (size, type)
# - Reading file content safely
# - Detecting programming language from extension
# - Extracting file metadata (line count, size, preview)

import os
import secrets
import logging
from pathlib import Path
from typing import List, Tuple

from fastapi import UploadFile, HTTPException, status

from app.core.constants import (
    EXTENSION_TO_LANGUAGE,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_SIZE_BYTES,
    MAX_FILES_PER_UPLOAD,
    CONTENT_PREVIEW_LENGTH,
    SESSION_ID_LENGTH,
)
from app.models.schemas import FileInfo

# Set up logging so we can see what the service is doing
logger = logging.getLogger(__name__)


class FileService:
    """
    Service class responsible for processing uploaded code files.

    All methods are async so FastAPI can handle many requests at once
    without blocking (important for file I/O operations).
    """

    def generate_session_id(self) -> str:
        """
        Generate a cryptographically secure random session ID.
        Used to track this upload session through the review pipeline.

        Example output: 'a3f8c2e1b4d09f7a'
        """
        return secrets.token_hex(SESSION_ID_LENGTH // 2)

    def get_file_extension(self, filename: str) -> str:
        """
        Extract the lowercase file extension from a filename.

        Examples:
            'main.py'        → '.py'
            'App.JS'         → '.js'
            'index.test.ts'  → '.ts'
        """
        return Path(filename).suffix.lower()

    def detect_language(self, filename: str) -> str:
        """
        Detect the programming language from the file extension.

        Returns 'Unknown' if the extension is not in our supported list.
        """
        extension = self.get_file_extension(filename)
        return EXTENSION_TO_LANGUAGE.get(extension, "Unknown")

    def validate_file_extension(self, filename: str) -> None:
        """
        Check that the file has an allowed extension.
        Raises HTTP 400 if not supported.
        """
        extension = self.get_file_extension(filename)

        if not extension:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' has no extension. "
                       f"Please upload a source code file.",
            )

        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{extension}' is not supported. "
                       f"Supported types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

    def validate_file_count(self, files: List[UploadFile]) -> None:
        """
        Check that the user hasn't uploaded too many files at once.
        Raises HTTP 400 if too many.
        """
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many files. Maximum allowed: {MAX_FILES_PER_UPLOAD}. "
                       f"You uploaded: {len(files)}",
            )

        if len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files were uploaded. Please select at least one file.",
            )

    async def read_file_content(self, file: UploadFile) -> Tuple[bytes, str]:
        """
        Read the raw bytes from an uploaded file, then decode to string.

        Returns:
            Tuple of (raw_bytes, decoded_string_content)

        Raises:
            HTTP 400 if file is too large
            HTTP 422 if file cannot be decoded as UTF-8 text
        """
        # Read all bytes from the upload
        raw_bytes = await file.read()

        # Check file size
        file_size = len(raw_bytes)
        if file_size > MAX_FILE_SIZE_BYTES:
            size_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is too large "
                       f"({file_size / 1024:.1f} KB). "
                       f"Maximum allowed size: {size_mb:.0f} MB.",
            )

        # Check for empty files
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is empty.",
            )

        # Decode bytes to string (UTF-8 encoding)
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{file.filename}' could not be read as text. "
                       f"Please upload plain text source code files.",
            )

        return raw_bytes, content

    def extract_file_metadata(
        self, filename: str, raw_bytes: bytes, content: str
    ) -> FileInfo:
        """
        Extract all useful metadata from a file's content.

        Args:
            filename:  Original filename from the upload
            raw_bytes: Raw file bytes (used for size calculation)
            content:   Decoded text content of the file

        Returns:
            FileInfo schema with all metadata populated
        """
        extension = self.get_file_extension(filename)
        language = self.detect_language(filename)
        line_count = content.count("\n") + 1  # +1 for last line without newline
        char_count = len(content)
        file_size = len(raw_bytes)

        # Create a preview of the first N characters
        preview = content[:CONTENT_PREVIEW_LENGTH]
        if len(content) > CONTENT_PREVIEW_LENGTH:
            preview += "..."  # Indicate content was truncated

        logger.info(
            f"Processed file: {filename} | "
            f"Language: {language} | "
            f"Lines: {line_count} | "
            f"Size: {file_size} bytes"
        )

        return FileInfo(
            filename=filename,
            file_size=file_size,
            file_extension=extension,
            language=language,
            line_count=line_count,
            char_count=char_count,
            content_preview=preview,
        )

    async def process_uploads(
        self, files: List[UploadFile]
    ) -> Tuple[str, List[FileInfo], dict]:
        """
        Main method: validates, reads, and processes all uploaded files.

        Args:
            files: List of FastAPI UploadFile objects

        Returns:
            Tuple of:
                - session_id (str): unique ID for this upload batch
                - file_infos (List[FileInfo]): metadata for each file
                - file_contents (dict): maps filename → full content string
                  (used later by the AI review agents)

        Raises:
            HTTPException for any validation failures
        """
        # Step 1: Validate number of files
        self.validate_file_count(files)

        # Step 2: Validate each file extension before reading content
        for file in files:
            self.validate_file_extension(file.filename)

        # Step 3: Read and process each file
        file_infos: List[FileInfo] = []
        file_contents: dict = {}  # filename → content (for AI agents later)
        total_size = 0

        for file in files:
            logger.info(f"Reading file: {file.filename}")

            # Read content
            raw_bytes, content = await self.read_file_content(file)
            total_size += len(raw_bytes)

            # Check cumulative total size
            if total_size > MAX_TOTAL_SIZE_BYTES:
                total_mb = MAX_TOTAL_SIZE_BYTES / (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total upload size exceeds {total_mb:.0f} MB limit. "
                           f"Please upload fewer or smaller files.",
                )

            # Extract metadata
            file_info = self.extract_file_metadata(file.filename, raw_bytes, content)
            file_infos.append(file_info)

            # Store full content for AI agents (Step 4+)
            file_contents[file.filename] = content

        # Step 4: Generate a unique session ID for this batch
        session_id = self.generate_session_id()

        logger.info(
            f"Upload session created: {session_id} | "
            f"Files: {len(file_infos)} | "
            f"Total size: {total_size} bytes"
        )

        return session_id, file_infos, file_contents


# Create a single shared instance (singleton pattern)
# Routes import this directly instead of creating new instances
file_service = FileService()