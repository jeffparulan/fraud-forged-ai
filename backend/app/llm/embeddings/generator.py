"""
Embedding generation for fraud pattern RAG.

Uses Hugging Face inference API (sentence-transformers/all-MiniLM-L6-v2)
with hash-based fallback when HF is unavailable.
"""
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Pinecone index dimensions
DEFAULT_DIMENSIONS = 2048


class EmbeddingGenerator:
    """
    Generate text embeddings for RAG.
    Uses HF inference API with hash-based fallback.
    """

    def __init__(self, dimensions: int = DEFAULT_DIMENSIONS):
        self.dimensions = dimensions
        self._cache: dict = {}

    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        Uses HF API first, falls back to hash-based embedding if unavailable.
        """
        if text in self._cache:
            return self._cache[text]

        embedding = self._try_hf_embedding(text)
        if embedding is None:
            embedding = self._hash_fallback(text)

        self._cache[text] = embedding
        return embedding

    def _try_hf_embedding(self, text: str) -> Optional[List[float]]:
        """Try Hugging Face inference API."""
        try:
            from app.core.security import get_huggingface_token
            import httpx

            hf_token = get_huggingface_token()
            if not hf_token:
                return None

            response = httpx.post(
                "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2",
                headers={"Authorization": f"Bearer {hf_token}"},
                json={"inputs": text},
                timeout=10.0,
            )
            if response.status_code != 200:
                return None

            embedding = response.json()
            if isinstance(embedding[0], list):
                embedding = embedding[0]
            while len(embedding) < self.dimensions:
                embedding.extend([0.0] * (self.dimensions - len(embedding)))
            embedding = embedding[: self.dimensions]
            return embedding
        except Exception as e:
            logger.warning(f"HF embedding failed, using fallback: {e}")
            return None

    def _hash_fallback(self, text: str) -> List[float]:
        """Hash-based fallback - not ideal but works when HF unavailable."""
        import hashlib

        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)
        return embedding
