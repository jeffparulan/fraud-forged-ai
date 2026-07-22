"""
Embedding generation for fraud pattern RAG.

Uses Hugging Face Inference (sentence-transformers/all-MiniLM-L6-v2, 384-dim)
zero-padded to the Pinecone index dimension. Zero-padding preserves cosine
similarity exactly (dot products and norms are unchanged), so semantic search
quality is identical to a native 384-dim index.

A deterministic hash fallback exists only to keep the service alive when HF
is unreachable; hash vectors carry no semantic meaning, so retrieval quality
degrades and we log loudly when it happens.
"""
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)

# Must match the Pinecone index dimension (override via env for new indexes)
DEFAULT_DIMENSIONS = int(os.getenv("PINECONE_DIMENSIONS", "2048"))

# HF moved inference to router.huggingface.co; the old
# api-inference.huggingface.co pipeline endpoint is deprecated.
HF_EMBEDDING_URLS = [
    "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",
    "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2",
]


class EmbeddingGenerator:
    """
    Generate text embeddings for RAG.
    Uses HF inference API with hash-based fallback.
    """

    def __init__(self, dimensions: int = DEFAULT_DIMENSIONS):
        self.dimensions = dimensions
        self._cache: dict = {}
        self.last_source: str = "none"  # "hf" | "hash" - exposed for observability

    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        Uses HF API first, falls back to hash-based embedding if unavailable.
        """
        if text in self._cache:
            return self._cache[text]

        embedding = self._try_hf_embedding(text)
        if embedding is not None:
            self.last_source = "hf"
        else:
            logger.warning(
                "Using hash-based fallback embedding - RAG retrieval will be "
                "non-semantic for this query. Check HUGGINGFACE_API_TOKEN / HF availability."
            )
            embedding = self._hash_fallback(text)
            self.last_source = "hash"

        self._cache[text] = embedding
        return embedding

    def _try_hf_embedding(self, text: str) -> Optional[List[float]]:
        """Try Hugging Face inference API (current router URL first, legacy second)."""
        try:
            from app.core.security import get_huggingface_token
            import httpx

            hf_token = get_huggingface_token()
            if not hf_token:
                return None

            for url in HF_EMBEDDING_URLS:
                try:
                    response = httpx.post(
                        url,
                        headers={"Authorization": f"Bearer {hf_token}"},
                        json={"inputs": text},
                        timeout=10.0,
                    )
                    if response.status_code != 200:
                        continue

                    embedding = response.json()
                    if isinstance(embedding[0], list):
                        embedding = embedding[0]
                    # Zero-pad to the index dimension (cosine-similarity safe)
                    if len(embedding) < self.dimensions:
                        embedding.extend([0.0] * (self.dimensions - len(embedding)))
                    return embedding[: self.dimensions]
                except httpx.HTTPError:
                    continue
            return None
        except Exception as e:
            logger.warning(f"HF embedding failed, using fallback: {e}")
            return None

    def _hash_fallback(self, text: str) -> List[float]:
        """Deterministic hash-based fallback - keeps the service alive, not semantic."""
        import hashlib

        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)
        return embedding
