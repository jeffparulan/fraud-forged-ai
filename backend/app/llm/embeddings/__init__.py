"""Embedding generation and vector retrieval for RAG."""
from .generator import EmbeddingGenerator, DEFAULT_DIMENSIONS
from .retriever import format_fraud_context, query_similar_patterns

__all__ = [
    "EmbeddingGenerator",
    "DEFAULT_DIMENSIONS",
    "format_fraud_context",
    "query_similar_patterns",
]
