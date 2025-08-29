"""
Unit tests for Vector Service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.vector_service import VectorService


class TestVectorService:
    """Test cases for Vector Service."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test vector service initialization."""
        service = VectorService()
        
        with patch('qdrant_client.AsyncQdrantClient') as mock_qdrant, \
             patch('httpx.AsyncClient') as mock_httpx:
            
            # Mock successful connections
            mock_qdrant.return_value = AsyncMock()
            mock_httpx.return_value = AsyncMock()
            
            # Mock test connections
            service._test_connections = AsyncMock()
            service._ensure_collection = AsyncMock()
            
            await service.initialize()
            
            assert service.is_initialized()
            assert service.qdrant_client is not None
            assert service.ollama_client is not None
    
    @pytest.mark.asyncio
    async def test_language_detection(self):
        """Test language detection functionality."""
        service = VectorService()
        
        # Test English text
        english_result = service._detect_language("This is English text about physics.")
        assert english_result == "en"
        
        # Test Thai text
        thai_result = service._detect_language("นี่คือข้อความภาษาไทยเกี่ยวกับฟิสิกส์")
        assert thai_result == "th"
        
        # Test mixed content
        mixed_result = service._detect_language("Physics ฟิสิกส์ is a science.")
        assert mixed_result == "mixed"
    
    def test_embedding_model_selection(self):
        """Test embedding model selection based on language."""
        service = VectorService()
        
        # Test English model selection
        english_model = service._select_embedding_model("en")
        assert english_model == "qwen/qwen3-embedding-8b"
        
        # Test Thai model selection
        thai_model = service._select_embedding_model("th")
        assert thai_model == "bge-m3:latest"
        
        # Test mixed content model selection
        mixed_model = service._select_embedding_model("mixed")
        assert mixed_model == "bge-m3:latest"
        
        # Test unknown language (should default to multilingual)
        unknown_model = service._select_embedding_model("unknown")
        assert unknown_model == "bge-m3:latest"
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Test successful embedding generation."""
        service = VectorService()
        
        # Mock Ollama client response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3] * 341 + [0.1]  # 1024 dimensions
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        service.ollama_client = mock_client
        service._initialized = True
        
        result = await service.generate_embedding("Test physics content", "en")
        
        assert len(result) == 1024
        assert all(isinstance(val, float) for val in result)
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding_api_error(self):
        """Test embedding generation with API error."""
        service = VectorService()
        
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        service.ollama_client = mock_client
        service._initialized = True
        
        with pytest.raises(Exception, match="Ollama embedding API returned status 500"):
            await service.generate_embedding("Test content", "en")
    
    @pytest.mark.asyncio
    async def test_index_chunk_success(self):
        """Test successful chunk indexing."""
        service = VectorService()
        
        # Mock embedding generation
        mock_embedding = [0.1] * 1024
        service.generate_embedding = AsyncMock(return_value=mock_embedding)
        
        # Mock Qdrant client
        mock_qdrant = AsyncMock()
        mock_qdrant.upsert.return_value = None
        service.qdrant_client = mock_qdrant
        service.collection_name = "test_collection"
        service._initialized = True
        
        result = await service.index_chunk(
            chunk_id="test-chunk-1",
            text="Physics content about forces",
            metadata={"source": "textbook.pdf", "page": 1}
        )
        
        assert result is True
        service.generate_embedding.assert_called_once()
        mock_qdrant.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_index_chunk_failure(self):
        """Test chunk indexing failure."""
        service = VectorService()
        
        # Mock embedding generation failure
        service.generate_embedding = AsyncMock(side_effect=Exception("Embedding failed"))
        service._initialized = True
        
        result = await service.index_chunk(
            chunk_id="test-chunk-1",
            text="Physics content",
            metadata={"source": "textbook.pdf"}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_similar_success(self):
        """Test successful similarity search."""
        service = VectorService()
        
        # Mock embedding generation
        mock_embedding = [0.1] * 1024
        service.generate_embedding = AsyncMock(return_value=mock_embedding)
        
        # Mock Qdrant search results
        mock_result = MagicMock()
        mock_result.id = "chunk-1"
        mock_result.score = 0.85
        mock_result.payload = {
            "text": "Physics content about forces",
            "language": "en",
            "source": "textbook.pdf"
        }
        
        mock_qdrant = AsyncMock()
        mock_qdrant.search.return_value = [mock_result]
        service.qdrant_client = mock_qdrant
        service.collection_name = "test_collection"
        service._initialized = True
        
        results = await service.search_similar(
            query_text="What is force?",
            limit=5,
            score_threshold=0.7
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "chunk-1"
        assert results[0]["score"] == 0.85
        assert results[0]["text"] == "Physics content about forces"
        assert results[0]["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_search_similar_with_filters(self):
        """Test similarity search with metadata filters."""
        service = VectorService()
        
        # Mock embedding generation
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1024)
        
        # Mock Qdrant client
        mock_qdrant = AsyncMock()
        mock_qdrant.search.return_value = []
        service.qdrant_client = mock_qdrant
        service.collection_name = "test_collection"
        service._initialized = True
        
        await service.search_similar(
            query_text="forces",
            filters={"source": "textbook.pdf", "language": "en"}
        )
        
        # Verify that search was called with filters
        mock_qdrant.search.assert_called_once()
        call_args = mock_qdrant.search.call_args
        assert call_args[1]["query_filter"] is not None
    
    @pytest.mark.asyncio
    async def test_search_similar_failure(self):
        """Test similarity search failure."""
        service = VectorService()
        
        # Mock embedding generation failure
        service.generate_embedding = AsyncMock(side_effect=Exception("Embedding failed"))
        service._initialized = True
        
        results = await service.search_similar("test query")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """Test collection statistics retrieval."""
        service = VectorService()
        
        # Mock Qdrant collection info
        mock_info = MagicMock()
        mock_info.vectors_count = 1000
        mock_info.indexed_vectors_count = 1000
        mock_info.points_count = 1000
        mock_info.segments_count = 2
        mock_info.status = MagicMock()
        mock_info.status.value = "green"
        
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collection.return_value = mock_info
        service.qdrant_client = mock_qdrant
        service.collection_name = "test_collection"
        service._initialized = True
        
        stats = await service.get_collection_stats()
        
        assert stats["vectors_count"] == 1000
        assert stats["points_count"] == 1000
        assert stats["status"] == "green"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        service = VectorService()
        service._initialized = True
        
        # Mock healthy Qdrant response
        mock_collections = MagicMock()
        mock_collections.collections = []
        
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collections.return_value = mock_collections
        service.qdrant_client = mock_qdrant
        
        # Mock healthy Ollama response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        
        mock_ollama = AsyncMock()
        mock_ollama.get.return_value = mock_response
        service.ollama_client = mock_ollama
        
        # Mock collection stats
        service.get_collection_stats = AsyncMock(return_value={"vectors_count": 100})
        
        health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert health["qdrant"]["status"] == "healthy"
        assert health["ollama"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy_not_initialized(self):
        """Test health check when service is not initialized."""
        service = VectorService()
        
        health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "not initialized" in health["message"]
    
    @pytest.mark.asyncio
    async def test_ensure_collection_creation(self):
        """Test collection creation when it doesn't exist."""
        service = VectorService()
        
        # Mock collections response (empty)
        mock_collections = MagicMock()
        mock_collections.collections = []
        
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collections.return_value = mock_collections
        mock_qdrant.create_collection.return_value = None
        
        service.qdrant_client = mock_qdrant
        service.collection_name = "test_collection"
        service.settings = MagicMock()
        service.settings.vector_dimension = 1024
        
        await service._ensure_collection()
        
        # Verify collection creation was called
        mock_qdrant.create_collection.assert_called_once_with(
            collection_name="test_collection",
            vectors_config=pytest.mock.ANY
        )