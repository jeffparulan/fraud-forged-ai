"""Unit tests for RAG engine."""
import pytest
from unittest.mock import Mock, patch
from app.core.rag_engine import RAGEngine


class TestRAGEngine:
    def test_init_without_api_key(self):
        with patch.dict('os.environ', {}, clear=True):
            rag = RAGEngine()
            assert rag.initialized is False
            assert rag.api_key is None
    
    def test_init_with_namespace(self):
        rag = RAGEngine(namespace="test")
        assert rag.namespace == "test"
    
    def test_query_without_initialization(self):
        rag = RAGEngine()
        result = rag.query_similar_patterns("banking", "test query")
        assert result["count"] == 0
        assert "not initialized" in result["context"].lower()
    
    def test_get_collection_count_not_initialized(self):
        rag = RAGEngine()
        count = rag.get_collection_count()
        assert count == 0
    
    @patch('app.core.rag_engine.Pinecone')
    def test_initialize_success(self, mock_pinecone):
        mock_index = Mock()
        mock_index.describe_index_stats.return_value = {
            'total_vector_count': 100,
            'namespaces': {'rag': {'vector_count': 50}},
            'dimension': 384
        }
        mock_pc = Mock()
        mock_pc.Index.return_value = mock_index
        mock_pinecone.return_value = mock_pc
        
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            rag = RAGEngine()
            rag.initialize()
            assert rag.initialized is True
    
    @patch('app.core.rag_engine.Pinecone')
    def test_query_similar_patterns_success(self, mock_pinecone):
        mock_index = Mock()
        mock_index.describe_index_stats.return_value = {
            'namespaces': {'rag': {'vector_count': 50}}
        }
        mock_pc = Mock()
        mock_pc.Index.return_value = mock_index
        mock_pinecone.return_value = mock_pc
        
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            with patch('app.core.rag_engine.query_similar_patterns') as mock_query:
                mock_query.return_value = {
                    "context": "test context",
                    "count": 3,
                    "patterns": []
                }
                
                rag = RAGEngine()
                rag.initialize()
                result = rag.query_similar_patterns("banking", "test query")
                
                assert result["count"] == 3
                assert result["context"] == "test context"
