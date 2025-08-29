"""
Vector Service for Qdrant vector database operations with language-specific embeddings.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
import httpx
import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
import structlog

from .base import BaseService
from ..api.circuit_breaker import circuit_breaker, CircuitBreakerConfig


class VectorService(BaseService):
    """Service for vector database operations using Qdrant."""
    
    def __init__(self):
        super().__init__("VectorService")
        self.qdrant_client = None
        self.ollama_client = None
        self.collection_name = None
    
    async def _initialize(self) -> None:
        """Initialize Qdrant and Ollama clients."""
        try:
            # Initialize Qdrant client
            self.qdrant_client = AsyncQdrantClient(url=self.settings.qdrant_url)
            self.collection_name = self.settings.qdrant_collection_name
            
            # Initialize Ollama HTTP client
            self.ollama_client = httpx.AsyncClient(base_url=self.settings.ollama_url)
            
            # Test connections
            await self._test_connections()
            
            # Ensure collection exists
            await self._ensure_collection()
            
        except Exception as e:
            self.logger.error("Failed to initialize Vector service", error=str(e))
            raise
    
    async def _shutdown(self) -> None:
        """Shutdown vector service."""
        if self.qdrant_client:
            await self.qdrant_client.close()
        if self.ollama_client:
            await self.ollama_client.aclose()
    
    async def _test_connections(self) -> None:
        """Test Qdrant and Ollama connectivity."""
        try:
            # Test Qdrant
            collections = await self.qdrant_client.get_collections()
            self.logger.info("Qdrant connection successful", collections_count=len(collections.collections))
            
            # Test Ollama
            response = await self.ollama_client.get("/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                self.logger.info("Ollama connection successful", models_count=len(models_data.get("models", [])))
            else:
                raise Exception(f"Ollama API returned status {response.status_code}")
                
        except Exception as e:
            self.logger.error("Vector service connectivity test failed", error=str(e))
            raise
    
    async def _ensure_collection(self) -> None:
        """Ensure vector collection exists with proper configuration."""
        try:
            collections = await self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.logger.info("Creating vector collection", collection_name=self.collection_name)
                
                await self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.settings.vector_dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
                
                self.logger.info("Vector collection created successfully")
            else:
                self.logger.info("Vector collection already exists")
                
        except Exception as e:
            self.logger.error("Failed to ensure collection", error=str(e))
            raise
    
    @circuit_breaker(
        name="ollama_embeddings",
        config=CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout=60.0,
            request_timeout=30.0
        )
    )
    async def generate_embedding(self, text: str, language: str = "en") -> List[float]:
        """
        Generate embedding for text using appropriate language-specific model.
        
        Args:
            text: Text to embed
            language: Language code (en/th/mixed)
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Select model based on language
            model = self._select_embedding_model(language)
            
            self.logger.info(
                "Generating embedding", 
                text_length=len(text),
                language=language,
                model=model
            )
            
            # Call Ollama embedding API
            response = await self.ollama_client.post(
                "/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama embedding API returned status {response.status_code}")
            
            result = response.json()
            embedding = result.get("embedding")
            
            if not embedding:
                raise Exception("No embedding returned from Ollama API")
            
            self.logger.info(
                "Embedding generated successfully",
                embedding_dimension=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(
                "Embedding generation failed",
                text_length=len(text),
                language=language,
                error=str(e)
            )
            raise
    
    def _select_embedding_model(self, language: str) -> str:
        """Select appropriate embedding model based on language."""
        if language == "en":
            return "dengcao/Qwen3-Embedding-0.6B:F16"
        elif language == "th" or language == "mixed":
            return "bge-m3:latest"
        else:
            # Default to multilingual model
            return "bge-m3:latest"
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character analysis."""
        # Count Thai characters
        thai_chars = sum(1 for char in text if '\u0e00' <= char <= '\u0e7f')
        english_chars = sum(1 for char in text if char.isascii() and char.isalpha())
        
        total_chars = thai_chars + english_chars
        if total_chars == 0:
            return "en"  # Default to English
        
        thai_ratio = thai_chars / total_chars
        
        if thai_ratio > 0.7:
            return "th"
        elif thai_ratio > 0.1:
            return "mixed"
        else:
            return "en"
    
    async def index_chunk(
        self, 
        chunk_id: str, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Index a single chunk in the vector database.
        
        Args:
            chunk_id: Unique identifier for the chunk
            text: Text content to embed and index
            metadata: Additional metadata to store with the vector
            
        Returns:
            True if indexing successful
        """
        try:
            # Detect language and generate embedding
            language = self._detect_language(text)
            embedding = await self.generate_embedding(text, language)
            
            # Prepare point for insertion
            point = models.PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "text": text,
                    "language": language,
                    **metadata
                }
            )
            
            # Insert into Qdrant
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            self.logger.info(
                "Chunk indexed successfully",
                chunk_id=chunk_id,
                language=language
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Chunk indexing failed",
                chunk_id=chunk_id,
                error=str(e)
            )
            return False
    
    @circuit_breaker(
        name="qdrant_search",
        config=CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout=30.0,
            request_timeout=15.0
        )
    )
    async def search_similar(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks based on semantic similarity.
        
        Args:
            query_text: Query text to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            filters: Optional metadata filters
            
        Returns:
            List of similar chunks with scores and metadata
        """
        try:
            # Detect language and generate query embedding
            language = self._detect_language(query_text)
            query_embedding = await self.generate_embedding(query_text, language)
            
            self.logger.info(
                "Performing similarity search",
                query_length=len(query_text),
                language=language,
                limit=limit
            )
            
            # Build search filters
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    ))
                
                if conditions:
                    search_filter = models.Filter(must=conditions)
            
            # Perform search
            search_results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "language": result.payload.get("language", "unknown"),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "language"]}
                })
            
            self.logger.info(
                "Similarity search completed",
                results_count=len(results)
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Similarity search failed",
                query_length=len(query_text),
                error=str(e)
            )
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = await self.qdrant_client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status.value if info.status else "unknown"
            }
        except Exception as e:
            self.logger.error("Failed to get collection stats", error=str(e))
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vector service health."""
        try:
            if not self.is_initialized():
                return {
                    "status": "unhealthy",
                    "message": "Service not initialized"
                }
            
            # Test Qdrant
            collections = await self.qdrant_client.get_collections()
            qdrant_healthy = len(collections.collections) >= 0
            
            # Test Ollama
            ollama_response = await self.ollama_client.get("/api/tags", timeout=5.0)
            ollama_healthy = ollama_response.status_code == 200
            
            # Get collection stats
            stats = await self.get_collection_stats()
            
            overall_status = "healthy" if (qdrant_healthy and ollama_healthy) else "unhealthy"
            
            return {
                "status": overall_status,
                "qdrant": {
                    "status": "healthy" if qdrant_healthy else "unhealthy",
                    "collections_count": len(collections.collections),
                    "collection_stats": stats
                },
                "ollama": {
                    "status": "healthy" if ollama_healthy else "unhealthy",
                    "models_available": ollama_response.json().get("models", []) if ollama_healthy else []
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }