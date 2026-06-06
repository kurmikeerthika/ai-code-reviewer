from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        logger.info("Loading local embedding model...")
        
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        logger.info("Local embedding model loaded successfully")

    async def create_embedding(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return [embedding.tolist() for embedding in embeddings]


embedding_service = EmbeddingService()