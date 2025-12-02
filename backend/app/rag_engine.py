"""
Pinecone-powered RAG engine for fraud pattern retrieval.
Replaces ChromaDB with Pinecone for better scalability and smaller Docker images.
"""

from pinecone import Pinecone
from typing import Dict, List, Any, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Pinecone-powered RAG engine for fraud pattern retrieval.
    Uses Pinecone vector database for scalable, cloud-based pattern matching.
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
        self.host = os.getenv("PINECONE_HOST")  # e.g., https://fraudforge-master-kgn0lb7.svc.aped-4627-b74a.pinecone.io
        self.namespace = namespace  # Namespace for RAG data
        self.initialized = False
        self.embedding_model = "llama-text-embed-v2"
        self.dimensions = 2048
        
        # For embedding generation (using Hugging Face or local model)
        self._embedding_cache = {}
    
    def initialize(self):
        """Initialize Pinecone connection and verify index exists"""
        if self.initialized:
            return
        
        logger.info(f"🔧 [Pinecone] Initializing RAG engine for namespace: '{self.namespace}'")
        
        if not self.api_key:
            logger.warning("⚠️  [Pinecone] PINECONE_API_KEY not set - RAG will not work")
            logger.warning("   Container will continue with rule-based fallback only")
            # Don't raise exception - allow container to start without Pinecone
            # This is critical for Cloud Run - container must start even without all credentials
            return
        
        try:
            # Initialize Pinecone client
            logger.info(f"🔗 [Pinecone] Creating Pinecone client...")
            self.pc = Pinecone(api_key=self.api_key)
            logger.info(f"✅ [Pinecone] Client created successfully")
            
            # Connect to index
            logger.info(f"🔗 [Pinecone] Connecting to index: '{self.index_name}'")
            if self.host:
                logger.info(f"   📍 [Pinecone] Using custom host: {self.host}")
            
            self.index = self.pc.Index(self.index_name)
            logger.info(f"✅ [Pinecone] Index connection established")
            
            # Verify index exists and get stats
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
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Hugging Face inference API.
        Falls back to simple hash-based embedding if HF is unavailable.
        """
        # Check cache first
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        try:
            # Try to use Hugging Face inference API for embeddings
            from app.utils.llm_client import get_huggingface_token
            import httpx
            
            hf_token = get_huggingface_token()
            if hf_token:
                # Use HF inference API for embeddings
                response = httpx.post(
                    "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2",
                    headers={"Authorization": f"Bearer {hf_token}"},
                    json={"inputs": text},
                    timeout=10.0
                )
                if response.status_code == 200:
                    embedding = response.json()
                    # Pad or truncate to match Pinecone dimensions
                    if isinstance(embedding[0], list):
                        embedding = embedding[0]
                    # Normalize to 2048 dimensions
                    while len(embedding) < self.dimensions:
                        embedding.extend([0.0] * (self.dimensions - len(embedding)))
                    embedding = embedding[:self.dimensions]
                    self._embedding_cache[text] = embedding
                    return embedding
        except Exception as e:
            logger.warning(f"HF embedding failed, using fallback: {e}")
        
        # Fallback: Use simple hash-based embedding (not ideal but works)
        # In production, you should use a proper embedding model
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 2048-dim vector (repeat hash bytes)
        embedding = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)  # Normalize to [-1, 1]
        
        self._embedding_cache[text] = embedding
        return embedding
    
    def query_similar_patterns(self, sector: str, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Query similar fraud patterns from Pinecone"""
        
        if not self.initialized or not self.index:
            logger.warning(f"[Pinecone] Not initialized for namespace '{self.namespace}', returning empty results")
            return {
                "context": "No similar patterns found (Pinecone not initialized).",
                "count": 0,
                "patterns": []
            }
        
        try:
            logger.info(f"🔍 [Pinecone] Querying namespace '{self.namespace}' for sector '{sector}' (top_k={n_results})")
            
            # Generate embedding for query
            logger.debug(f"[Pinecone] Generating embedding for query text...")
            query_embedding = self._generate_embedding(query_text)
            logger.debug(f"[Pinecone] Embedding generated (dimensions: {len(query_embedding)})")
            
            # Query Pinecone with namespace and filter
            # Note: Filter syntax may vary by Pinecone version
            # Try with filter first, fallback to no filter if it fails
            try:
                logger.info(f"🔍 [Pinecone] Executing query with filter: sector='{sector}' in namespace '{self.namespace}'")
                results = self.index.query(
                    vector=query_embedding,
                    top_k=n_results,
                    include_metadata=True,
                    namespace=self.namespace,  # Query specific namespace
                    filter={"sector": {"$eq": sector}}  # Filter by sector
                )
                logger.info(f"✅ [Pinecone] Query successful: found {len(results.matches)} matches")
            except Exception as filter_error:
                # If filter fails, try without filter (older Pinecone versions)
                logger.warning(f"[Pinecone] Filter query failed, trying without filter: {filter_error}")
                logger.info(f"🔍 [Pinecone] Executing query without filter in namespace '{self.namespace}'")
                results = self.index.query(
                    vector=query_embedding,
                    top_k=n_results * 2,  # Get more results to filter manually
                    include_metadata=True,
                    namespace=self.namespace  # Still use namespace
                )
                logger.info(f"✅ [Pinecone] Query successful: found {len(results.matches)} matches (before filtering)")
                # Filter results manually by sector
                if results.matches:
                    filtered_matches = [
                        m for m in results.matches 
                        if m.metadata and m.metadata.get("sector") == sector
                    ]
                    logger.info(f"🔍 [Pinecone] Filtered to {len(filtered_matches)} matches for sector '{sector}'")
                    # Create a new results object with filtered matches
                    results.matches = filtered_matches[:n_results]
            
            if not results.matches:
                return {
                    "context": "No similar patterns found.",
                    "count": 0,
                    "patterns": []
                }
            
            patterns = []
            for match in results.matches:
                metadata = match.metadata or {}
                patterns.append({
                    "description": metadata.get("description", ""),
                    "risk_level": metadata.get("risk_level", "unknown"),
                    "indicators": json.loads(metadata.get("indicators", "[]")),
                    "score": match.score
                })
            
            context = self._format_context(patterns)
            
            return {
                "context": context,
                "count": len(patterns),
                "patterns": patterns
            }
            
        except Exception as e:
            logger.error(f"❌ [Pinecone] Query error in namespace '{self.namespace}': {e}", exc_info=True)
            return {
                "context": "Error retrieving patterns.",
                "count": 0,
                "patterns": []
            }
    
    def _format_context(self, patterns: List[Dict[str, Any]]) -> str:
        """Format retrieved patterns as context string"""
        
        if not patterns:
            return "No similar fraud patterns found."
        
        context_parts = ["Similar fraud patterns from database:"]
        
        for i, pattern in enumerate(patterns[:3], 1):
            risk = pattern["risk_level"].upper()
            desc = pattern["description"]
            score = pattern.get("score", 0.0)
            context_parts.append(f"{i}. [{risk} RISK] {desc} (similarity: {score:.2f})")
        
        return "\n".join(context_parts)
    
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
                # Generate embedding
                embedding = self._generate_embedding(pattern["description"])
                
                # Create vector with metadata
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
            
            # Upsert in batches of 100 with namespace
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
