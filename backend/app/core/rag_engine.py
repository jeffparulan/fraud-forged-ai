"""
Pinecone-powered RAG engine for fraud pattern retrieval.
Uses llm.embeddings for generation and retrieval.
"""

from pinecone import Pinecone
from typing import Dict, List, Any
import json
import os
import logging

from app.llm.embeddings import EmbeddingGenerator, query_similar_patterns, DEFAULT_DIMENSIONS

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Pinecone-powered RAG engine for fraud pattern retrieval.
    Uses llm.embeddings for generation and retrieval.
    """

    def __init__(self, namespace: str = "rag"):
        """
        Initialize RAG engine with Pinecone.

        Args:
            namespace: Pinecone namespace to use (default: "rag" for fraud patterns)
        """
        self.pc = None
        self.index = None
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "fraudforge-master")
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.host = os.getenv("PINECONE_HOST")
        self.namespace = namespace
        self.initialized = False
        self.dimensions = DEFAULT_DIMENSIONS
        self._embedding_generator = EmbeddingGenerator(dimensions=self.dimensions)
    
    def initialize(self):
        """Initialize Pinecone connection and verify index exists"""
        if self.initialized:
            return
        
        logger.info(f"🔧 [Pinecone] Initializing RAG engine for namespace: '{self.namespace}'")
        
        if not self.api_key:
            logger.warning("⚠️  [Pinecone] PINECONE_API_KEY not set - RAG will not work")
            logger.warning("   Container will continue with rule-based fallback only")
            return
        
        try:
            logger.info(f"🔗 [Pinecone] Creating Pinecone client...")
            self.pc = Pinecone(api_key=self.api_key)
            logger.info(f"✅ [Pinecone] Client created successfully")
            
            logger.info(f"🔗 [Pinecone] Connecting to index: '{self.index_name}'")
            if self.host:
                logger.info(f"   📍 [Pinecone] Using custom host: {self.host}")
            
            self.index = self.pc.Index(self.index_name)
            logger.info(f"✅ [Pinecone] Index connection established")
            
            logger.info(f"📊 [Pinecone] Fetching index statistics...")
            stats = self.index.describe_index_stats()
            namespace_stats = stats.get('namespaces', {}).get(self.namespace, {})
            
            logger.info(f"✅ [Pinecone] Index '{self.index_name}' connected successfully")
            logger.info(f"   📦 Namespace: '{self.namespace}'")
            logger.info(f"   📈 Total vectors (all namespaces): {stats.get('total_vector_count', 0)}")
            logger.info(f"   📈 Vectors in '{self.namespace}' namespace: {namespace_stats.get('vector_count', 0)}")
            logger.info(f"   📏 Dimensions: {stats.get('dimension', self.dimensions)}")
            
            self.initialized = True
            logger.info(f"✅ [Pinecone] RAG engine initialized for namespace '{self.namespace}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {e}")
            raise
    
    def query_similar_patterns(self, sector: str, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Query similar fraud patterns from Pinecone."""
        if not self.initialized or not self.index:
            logger.warning(f"[Pinecone] Not initialized for namespace '{self.namespace}', returning empty results")
            return {
                "context": "No similar patterns found (Pinecone not initialized).",
                "count": 0,
                "patterns": [],
            }

        try:
            logger.info(f"🔍 [Pinecone] Querying namespace '{self.namespace}' for sector '{sector}' (top_k={n_results})")
            query_embedding = self._embedding_generator.generate(query_text)
            logger.debug(f"[Pinecone] Embedding generated (dimensions: {len(query_embedding)})")
            return query_similar_patterns(
                self.index,
                self.namespace,
                sector,
                query_embedding,
                n_results,
            )
        except Exception as e:
            logger.error(f"❌ [Pinecone] Query error in namespace '{self.namespace}': {e}", exc_info=True)
            return {"context": "Error retrieving patterns.", "count": 0, "patterns": []}
    
    def get_collection_count(self) -> int:
        """Get total number of fraud patterns in Pinecone namespace"""
        if not self.initialized or not self.index:
            logger.warning(f"[Pinecone] Cannot get count - not initialized for namespace '{self.namespace}'")
            return 0
        
        try:
            logger.debug(f"📊 [Pinecone] Fetching vector count for namespace '{self.namespace}'...")
            stats = self.index.describe_index_stats()
            namespace_stats = stats.get('namespaces', {}).get(self.namespace, {})
            count = namespace_stats.get('vector_count', 0)
            logger.debug(f"📊 [Pinecone] Namespace '{self.namespace}' contains {count} vectors")
            return count
        except Exception as e:
            logger.error(f"❌ [Pinecone] Error getting index stats for namespace '{self.namespace}': {e}")
            return 0
    
    def upsert_patterns(self, patterns: List[Dict[str, Any]], sector: str):
        """
        Upsert fraud patterns into Pinecone.
        
        Args:
            patterns: List of pattern dicts with 'description', 'risk_level', 'indicators'
            sector: Sector name (banking, medical, ecommerce, supply_chain)
        """
        if not self.initialized or not self.index:
            logger.error("Pinecone not initialized, cannot upsert patterns")
            return
        
        try:
            vectors = []
            for i, pattern in enumerate(patterns):
                embedding = self._embedding_generator.generate(pattern["description"])
                
                vector_id = f"{sector}_{i}_{hash(pattern['description']) % 100000}"
                metadata = {
                    "sector": sector,
                    "description": pattern["description"],
                    "risk_level": pattern.get("risk_level", "medium"),
                    "indicators": json.dumps(pattern.get("indicators", []))
                }
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            batch_size = 100
            total_batches = (len(vectors) + batch_size - 1) // batch_size
            logger.info(f"📤 [Pinecone] Upserting {len(vectors)} vectors to namespace '{self.namespace}' in {total_batches} batch(es)")
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                batch_num = i//batch_size + 1
                logger.info(f"📤 [Pinecone] Upserting batch {batch_num}/{total_batches} ({len(batch)} vectors) to namespace '{self.namespace}'...")
                self.index.upsert(vectors=batch, namespace=self.namespace)
                logger.info(f"✅ [Pinecone] Batch {batch_num} upserted successfully to namespace '{self.namespace}'")
            
            logger.info(f"✅ [Pinecone] Upserted {len(patterns)} patterns for sector '{sector}' to namespace '{self.namespace}'")
            
        except Exception as e:
            logger.error(f"❌ [Pinecone] Error upserting patterns to namespace '{self.namespace}': {e}", exc_info=True)
            raise
    
    def reset(self):
        """Reset connection (Pinecone index is persistent, so we just reset connection)"""
        self.index = None
        self.pc = None
        self.initialized = False
