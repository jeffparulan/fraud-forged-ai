"""
Pinecone integration for MCP server.
Uses a separate namespace from RAG for external context data.
"""

from pinecone import Pinecone
from typing import Dict, List, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class MCPPinecone:
    """
    Pinecone client for MCP server.
    Uses 'mcp' namespace to store external context data separately from RAG.
    """
    
    def __init__(self):
        self.pc = None
        self.index = None
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "fraudforge-master")
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.namespace = "mcp"  # Separate namespace for MCP data
        self.initialized = False
        self.dimensions = 2048
        
    def initialize(self):
        """Initialize Pinecone connection for MCP"""
        if self.initialized:
            return
        
        if not self.api_key:
            logger.warning(f"[Pinecone] PINECONE_API_KEY not set - MCP Pinecone disabled for namespace '{self.namespace}'")
            return
        
        try:
            logger.info(f"🔧 [Pinecone] Initializing MCP client for namespace: '{self.namespace}'")
            logger.info(f"🔗 [Pinecone] Creating Pinecone client...")
            self.pc = Pinecone(api_key=self.api_key)
            logger.info(f"✅ [Pinecone] Client created successfully")
            
            logger.info(f"🔗 [Pinecone] Connecting to index: '{self.index_name}'")
            self.index = self.pc.Index(self.index_name)
            logger.info(f"✅ [Pinecone] Index connection established")
            
            logger.info(f"📊 [Pinecone] Fetching index statistics...")
            stats = self.index.describe_index_stats()
            namespace_stats = stats.get('namespaces', {}).get(self.namespace, {})
            
            logger.info(f"✅ [Pinecone] MCP client initialized for namespace '{self.namespace}'")
            logger.info(f"   📦 Namespace: '{self.namespace}'")
            logger.info(f"   📈 Vectors in '{self.namespace}' namespace: {namespace_stats.get('vector_count', 0)}")
            
            self.initialized = True
        except Exception as e:
            logger.error(f"❌ [Pinecone] Failed to initialize MCP client for namespace '{self.namespace}': {e}")
            self.initialized = False
    
    def store_context(self, context_type: str, key: str, data: Dict[str, Any], embedding: Optional[List[float]] = None):
        """
        Store external context data in Pinecone MCP namespace.
        
        Args:
            context_type: Type of context (e.g., "wallet", "transaction", "provider", "seller")
            key: Unique identifier for this context
            data: Context data to store
            embedding: Optional pre-computed embedding, otherwise will generate from key+data
        """
        if not self.initialized or not self.index:
            logger.warning("MCP Pinecone not initialized, cannot store context")
            return
        
        try:
            # Generate embedding if not provided
            if embedding is None:
                # Simple embedding from key + context type
                text = f"{context_type} {key} {str(data)}"
                embedding = self._generate_simple_embedding(text)
            
            # Store in Pinecone
            vector_id = f"{context_type}_{key}"
            metadata = {
                "context_type": context_type,
                "key": key,
                **data  # Include all data in metadata
            }
            
            logger.debug(f"[Pinecone] Upserting to namespace '{self.namespace}': {context_type}/{key}")
            self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=self.namespace
            )
            
            logger.debug(f"✅ [Pinecone] Stored MCP context to namespace '{self.namespace}': {context_type}/{key}")
            
        except Exception as e:
            logger.error(f"❌ [Pinecone] Error storing MCP context to namespace '{self.namespace}': {e}", exc_info=True)
    
    def search_context(self, query_embedding: List[float], context_type: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar context in MCP namespace.
        
        Args:
            query_embedding: Query vector
            context_type: Optional filter by context type
            top_k: Number of results to return
        
        Returns:
            List of matching context data
        """
        if not self.initialized or not self.index:
            return []
        
        try:
            filter_dict = None
            if context_type:
                filter_dict = {"context_type": {"$eq": context_type}}
            
            logger.debug(f"🔍 [Pinecone] Querying namespace '{self.namespace}' (context_type={context_type}, top_k={top_k})")
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace,
                filter=filter_dict
            )
            logger.debug(f"✅ [Pinecone] Query returned {len(results.matches)} matches from namespace '{self.namespace}'")
            
            contexts = []
            for match in results.matches:
                contexts.append({
                    "metadata": match.metadata or {},
                    "score": match.score
                })
            
            return contexts
            
        except Exception as e:
            logger.error(f"❌ [Pinecone] Error searching MCP context in namespace '{self.namespace}': {e}", exc_info=True)
            return []
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """Generate simple hash-based embedding (for MCP context storage)"""
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        embedding = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)
        
        return embedding

