"""
Vector similarity retrieval for fraud pattern RAG.

Queries Pinecone with sector filter and formats results as context.
"""
from typing import Dict, List, Any
import json
import logging

logger = logging.getLogger(__name__)


def format_fraud_context(patterns: List[Dict[str, Any]]) -> str:
    """Format retrieved fraud patterns as context string."""
    if not patterns:
        return "No similar fraud patterns found."

    context_parts = ["Similar fraud patterns from database:"]
    for i, pattern in enumerate(patterns[:3], 1):
        risk = pattern["risk_level"].upper()
        desc = pattern["description"]
        score = pattern.get("score", 0.0)
        context_parts.append(f"{i}. [{risk} RISK] {desc} (similarity: {score:.2f})")
    return "\n".join(context_parts)


def query_similar_patterns(
    index,
    namespace: str,
    sector: str,
    query_embedding: List[float],
    n_results: int = 5,
) -> Dict[str, Any]:
    """
    Query Pinecone for similar fraud patterns.

    Args:
        index: Pinecone index
        namespace: Pinecone namespace
        sector: Sector filter (banking, medical, ecommerce, supply_chain)
        query_embedding: Query vector
        n_results: Max results to return

    Returns:
        Dict with context, count, patterns
    """
    try:
        logger.info(f"🔍 [Pinecone] Executing query with filter: sector='{sector}' in namespace '{namespace}'")
        results = index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            namespace=namespace,
            filter={"sector": {"$eq": sector}},
        )
        logger.info(f"✅ [Pinecone] Query successful: found {len(results.matches)} matches")
    except Exception as filter_error:
        logger.warning(f"[Pinecone] Filter query failed, trying without filter: {filter_error}")
        results = index.query(
            vector=query_embedding,
            top_k=n_results * 2,
            include_metadata=True,
            namespace=namespace,
        )
        if results.matches:
            filtered = [m for m in results.matches if m.metadata and m.metadata.get("sector") == sector]
            results.matches = filtered[:n_results]

    if not results.matches:
        return {"context": "No similar patterns found.", "count": 0, "patterns": []}

    patterns = []
    for match in results.matches:
        metadata = match.metadata or {}
        patterns.append({
            "description": metadata.get("description", ""),
            "risk_level": metadata.get("risk_level", "unknown"),
            "indicators": json.loads(metadata.get("indicators", "[]")),
            "score": match.score,
        })

    return {
        "context": format_fraud_context(patterns),
        "count": len(patterns),
        "patterns": patterns,
    }
