# app/rag/rag_pipeline.py
# Orchestrates the full RAG pipeline:
#   Upload → Chunk → Embed → Store → Search
#
# This is the single entry point the rest of the app uses for RAG.
# Other modules don't need to know about ChromaDB or embeddings directly.

import logging
from typing import List, Optional

from app.models.schemas import (
    CodeChunk,
    RAGSearchResult,
    RAGStoreResponse,
)
from app.rag.chunker import code_chunker
from app.rag.chroma_client import chroma_client

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    High-level orchestrator for the Retrieval-Augmented Generation pipeline.

    Usage:
        # Store uploaded files
        response = await rag_pipeline.store_files(
            file_contents={"main.py": "def foo(): ..."},
            session_id="abc123",
            file_language_map={"main.py": "Python"},
        )

        # Search for relevant chunks
        results = await rag_pipeline.search(
            query="functions without input validation",
            session_id="abc123",
        )
    """

    async def store_files(
        self,
        file_contents: dict,
        session_id: str,
        file_language_map: dict,
    ) -> RAGStoreResponse:
        """
        Full pipeline: chunk all files → embed → store in ChromaDB.

        Args:
            file_contents:     dict of filename → full code string
            session_id:        unique session ID from upload
            file_language_map: dict of filename → language string

        Returns:
            RAGStoreResponse with count of stored chunks
        """
        logger.info(
            f"RAG store starting: session={session_id}, "
            f"files={list(file_contents.keys())}"
        )

        # Step 1: Chunk all files into overlapping windows
        all_chunks: List[CodeChunk] = code_chunker.chunk_multiple_files(
            file_contents=file_contents,
            session_id=session_id,
            file_language_map=file_language_map,
        )

        if not all_chunks:
            logger.warning(f"No chunks generated for session {session_id}")
            return RAGStoreResponse(
                session_id=session_id,
                total_chunks_stored=0,
                files_processed=list(file_contents.keys()),
                message="No chunks were generated. Files may be too small.",
            )

        # Step 2: Embed and store chunks in ChromaDB
        stored_count = await chroma_client.store_chunks(all_chunks)

        logger.info(
            f"RAG store complete: session={session_id}, "
            f"stored={stored_count} chunks"
        )

        return RAGStoreResponse(
            session_id=session_id,
            total_chunks_stored=stored_count,
            files_processed=list(file_contents.keys()),
            message=(
                f"Successfully stored {stored_count} code chunks "
                f"from {len(file_contents)} file(s) into ChromaDB."
            ),
        )

    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        filename_filter: Optional[str] = None,
    ) -> List[RAGSearchResult]:
        """
        Search ChromaDB for code chunks semantically similar to the query.

        Args:
            query:           What to search for (e.g. "SQL injection vulnerability")
            session_id:      Limit search to this session's files (recommended)
            top_k:           Max results to return
            filename_filter: Limit search to one specific file

        Returns:
            List of RAGSearchResult sorted best-first
        """
        logger.info(f"RAG search: '{query[:80]}' session={session_id}")

        results = await chroma_client.search(
            query=query,
            session_id=session_id,
            top_k=top_k,
            filename_filter=filename_filter,
        )

        return results

    async def build_context_for_review(
        self,
        session_id: str,
        review_queries: List[str],
        top_k_per_query: int = 3,
    ) -> str:
        """
        Build a rich context string for the AI agents by running
        multiple targeted searches and combining unique results.

        This is called by the AI agents in Step 4. They pass in
        domain-specific queries like:
          - "SQL injection vulnerability"
          - "hardcoded passwords and secrets"
          - "nested loops O(n²) complexity"

        Args:
            session_id:       Filter to this session's code
            review_queries:   List of search queries (one per concern)
            top_k_per_query:  Results per query

        Returns:
            Formatted string with the most relevant code chunks,
            ready to paste into an LLM prompt.
        """
        seen_chunk_ids = set()
        all_results: List[RAGSearchResult] = []

        # Run each query and collect unique results
        for query in review_queries:
            results = await self.search(
                query=query,
                session_id=session_id,
                top_k=top_k_per_query,
            )
            for result in results:
                if result.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(result.chunk_id)
                    all_results.append(result)

        if not all_results:
            return "No relevant code chunks found in the vector store."

        # Format results as a readable context block for the LLM
        context_parts = [
            f"## Retrieved Code Context ({len(all_results)} chunks)\n"
        ]

        for i, result in enumerate(all_results, 1):
            context_parts.append(
                f"### Chunk {i}: {result.filename} "
                f"(lines {result.start_line}–{result.end_line}) "
                f"| {result.language} "
                f"| similarity: {result.similarity_score:.2f}\n"
                f"```{result.language.lower()}\n"
                f"{result.content}\n"
                f"```\n"
            )

        return "\n".join(context_parts)

    def get_stats(self) -> dict:
        """Returns ChromaDB collection statistics."""
        return chroma_client.get_collection_stats()


# Shared singleton
rag_pipeline = RAGPipeline()