# app/services/review_store.py
# Simple in-memory store for review results and session metadata.
#
# Why not a database?
# For this project we keep it simple — results live in memory
# while the server is running. In production you'd use Redis or PostgreSQL.
#
# The store holds:
#   - File contents per session (needed by the review pipeline)
#   - Language maps per session
#   - Completed review reports

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReviewStore:
    """
    In-memory store that maps session_id to session data.

    Structure:
        {
            "abc123": {
                "session_id": "abc123",
                "filenames": ["main.py"],
                "language_map": {"main.py": "Python"},
                "file_contents": {"main.py": "def foo(): ..."},
                "created_at": "2025-01-01T12:00:00",
                "report": { ... }   ← added after review completes
            }
        }
    """

    def __init__(self):
        # Main storage dictionary — session_id → session data
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------

    def save_session(
        self,
        session_id: str,
        filenames: list,
        language_map: dict,
        file_contents: dict,
    ) -> None:
        """
        Save upload session data so it can be retrieved later
        by the review and GitHub endpoints.
        """
        self._sessions[session_id] = {
            "session_id": session_id,
            "filenames": filenames,
            "language_map": language_map,
            "file_contents": file_contents,
            "created_at": datetime.utcnow().isoformat(),
            "report": None,
            "status": "uploaded",
        }
        logger.info(
            f"Session saved: {session_id} | "
            f"files: {filenames}"
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by session_id.
        Returns None if session doesn't exist.
        """
        return self._sessions.get(session_id)

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in the store."""
        return session_id in self._sessions

    # -----------------------------------------------------------------------
    # Report Management
    # -----------------------------------------------------------------------

    def save_report(self, session_id: str, report: Dict[str, Any]) -> None:
        """
        Save a completed review report to its session.
        Called after the LangGraph pipeline finishes.
        """
        if session_id not in self._sessions:
            logger.warning(
                f"Tried to save report for unknown session: {session_id}"
            )
            # Create a minimal session entry so the report isn't lost
            self._sessions[session_id] = {
                "session_id": session_id,
                "filenames": [],
                "language_map": {},
                "file_contents": {},
                "created_at": datetime.utcnow().isoformat(),
                "status": "completed",
            }

        self._sessions[session_id]["report"] = report
        self._sessions[session_id]["status"] = "completed"
        self._sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Report saved for session: {session_id}")

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a completed review report by session_id.
        Returns None if session doesn't exist or review not yet complete.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session.get("report")

    def list_sessions(self) -> list:
        """
        Return a summary list of all sessions.
        Useful for debugging and the /sessions endpoint.
        """
        return [
            {
                "session_id": sid,
                "filenames": data.get("filenames", []),
                "status": data.get("status", "unknown"),
                "created_at": data.get("created_at"),
                "has_report": data.get("report") is not None,
            }
            for sid, data in self._sessions.items()
        ]

    def delete_session(self, session_id: str) -> bool:
        """
        Remove a session from the store.
        Returns True if deleted, False if not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False

    @property
    def total_sessions(self) -> int:
        """Total number of sessions currently in the store."""
        return len(self._sessions)


# Shared singleton — imported by all endpoints
review_store = ReviewStore()