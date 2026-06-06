# app/rag/chroma_client.py
# Manages the ChromaDB vector database connection.
#
# ChromaDB stores:
# - The embedding vectors (for similarity search)
# - The original text (returned with results)
# - Metadata (filename, language, line numbers, session_id)
#
# Think of it as a special database where you search by meaning,
# not by exact keywords.

import logging
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.constants import CHROMA_DISTANCE_METRIC, RAG_TOP_K_RESULTS
from app.models.schemas import CodeChunk, RAGSearchResult
from app.rag.embeddings import embedding_service

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """
    Wrapper around ChromaDB for storing and searching code embeddings.

    ChromaDB concepts:
    - Collection: like a table in SQL — holds related documents
    - Document: the text content of a chunk
    - Embedding: the vector representation of the document
    - Metadata: extra fields stored alongside (filename, line numbers, etc.)
    - ID: unique string identifier for each document
    """

    def __init__(self):
        self._client: chromadb.ClientAPI | None = None
        self._collection = None

    def _get_client(self) -> chromadb.ClientAPI:
        """
        Lazy initialization of ChromaDB persistent client.
        Data is saved to disk at CHROMA_PERSIST_DIRECTORY.
        """
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # Don't send usage data
                ),
            )
            logger.info(
                f"ChromaDB client initialized at: "
                f"{settings.chroma_persist_directory}"
            )
        return self._client

    def _get_collection(self):
        """
        Get or create the ChromaDB collection.
        Collections use cosine distance for similarity (best for text).
        """
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={
                    "hnsw:space": CHROMA_DISTANCE_METRIC,
                    "description": "AI Code Reviewer — code chunk embeddings",
                },
            )
            logger.info(
                f"Using ChromaDB collection: '{settings.chroma_collection_name}' "
                f"with {self._collection.count()} existing documents"
            )
        return self._collection

    async def store_chunks(self, chunks: List[CodeChunk]) -> int:
        """
        Embed and store a list of CodeChunk objects in ChromaDB.

        Process:
        1. Extract text content from each chunk
        2. Send all texts to OpenAI Embeddings API
        3. Store (id, embedding, text, metadata) in ChromaDB

        Args:
            chunks: List of CodeChunk objects to store

        Returns:
            Number of chunks successfully stored
        """
        if not chunks:
            logger.warning("store_chunks called with empty list")
            return 0

        collection = self._get_collection()

        # Prepare parallel lists (ChromaDB API requires this format)
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[dict] = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.content)
            metadatas.append({
                # Store everything we might want to filter or display later
                "session_id": chunk.session_id,
                "filename": chunk.filename,
                "language": chunk.language,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
            })

        # Generate embeddings for all chunks in one API call
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = await embedding_service.create_embeddings(documents)
        # Upsert = insert or update if ID already exists
        # This makes re-uploads safe (no duplicates)
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            f"Stored {len(chunks)} chunks in ChromaDB "
            f"(collection now has {collection.count()} total documents)"
        )

        return len(chunks)

    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = RAG_TOP_K_RESULTS,
        filename_filter: Optional[str] = None,
    ) -> List[RAGSearchResult]:
        """
        Search ChromaDB for code chunks similar to the query.

        Args:
            query:           Natural language or code search query
            session_id:      If set, only search within this session's chunks
            top_k:           Number of results to return
            filename_filter: If set, only return chunks from this file

        Returns:
            List of RAGSearchResult sorted by similarity (best first)
        """
        collection = self._get_collection()

        if collection.count() == 0:
            logger.warning("ChromaDB collection is empty — no chunks to search")
            return []

        # Build metadata filter
        # ChromaDB uses a MongoDB-like filter syntax
        where_filter = None
        if session_id and filename_filter:
            where_filter = {
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"filename": {"$eq": filename_filter}},
                ]
            }
        elif session_id:
            where_filter = {"session_id": {"$eq": session_id}}
        elif filename_filter:
            where_filter = {"filename": {"$eq": filename_filter}}

        # Embed the query
        # Embed the query
        query_embedding = await embedding_service.create_embedding(query)

        # Query ChromaDB
        logger.info(
            f"Searching ChromaDB: query='{query[:60]}...' "
            f"session_id={session_id} top_k={top_k}"
        )

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Parse ChromaDB results into our schema
        search_results: List[RAGSearchResult] = []

        # ChromaDB returns nested lists (one per query)
        # We only sent one query, so we take index [0]
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            meta = metadatas[i]
            distance = distances[i]

            # Convert cosine distance to similarity score
            # distance=0 means identical, distance=2 means opposite
            # similarity = 1 - (distance / 2) → range 0.0 to 1.0
            similarity = round(1.0 - (distance / 2.0), 4)

            search_results.append(
                RAGSearchResult(
                    chunk_id=chunk_id,
                    filename=meta.get("filename", "unknown"),
                    language=meta.get("language", "unknown"),
                    content=documents[i],
                    start_line=meta.get("start_line", 0),
                    end_line=meta.get("end_line", 0),
                    similarity_score=similarity,
                )
            )

        logger.info(f"ChromaDB search returned {len(search_results)} results")
        return search_results

    async def delete_session(self, session_id: str) -> int:
        """
        Delete all chunks belonging to a specific session.
        Useful for cleanup or re-upload.

        Returns:
            Number of chunks deleted
        """
        collection = self._get_collection()

        # Find all chunk IDs for this session
        results = collection.get(
            where={"session_id": {"$eq": session_id}},
            include=[],
        )

        ids_to_delete = results.get("ids", [])

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                f"Deleted {len(ids_to_delete)} chunks for session {session_id}"
            )

        return len(ids_to_delete)

    def get_collection_stats(self) -> dict:
        """Returns basic stats about the ChromaDB collection."""
        collection = self._get_collection()
        return {
            "collection_name": settings.chroma_collection_name,
            "total_documents": collection.count(),
            "persist_directory": settings.chroma_persist_directory,
        }


# Shared singleton
chroma_client = ChromaDBClient()