"""
Unit tests for LLM Service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.llm_service import LLMService


class TestLLMService:
    """Test cases for LLM Service."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test LLM service initialization."""
        service = LLMService()
        
        # Mock the Gemini API configuration
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model:
            
            mock_model.return_value = MagicMock()
            await service.initialize()
            
            assert service.is_initialized()
            assert service.generation_model is not None
            assert service.validation_model is not None
    
    @pytest.mark.asyncio
    async def test_generate_content_success(self):
        """Test successful content generation."""
        service = LLMService()
        
        # Mock the model and response
        mock_response = MagicMock()
        mock_response.text = "Generated learning objective content"
        
        mock_model = AsyncMock()
        mock_model.generate_content_async.return_value = mock_response
        
        service.generation_model = mock_model
        service._initialized = True
        
        result = await service.generate_content(
            "Create learning objectives for physics",
            model_type="generation"
        )
        
        assert result == "Generated learning objective content"
        mock_model.generate_content_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_content_empty_response(self):
        """Test handling of empty response from API."""
        service = LLMService()
        
        mock_response = MagicMock()
        mock_response.text = ""
        
        mock_model = AsyncMock()
        mock_model.generate_content_async.return_value = mock_response
        
        service.generation_model = mock_model
        service._initialized = True
        
        with pytest.raises(Exception, match="Empty response from Gemini API"):
            await service.generate_content("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_learning_objectives(self):
        """Test learning objectives generation."""
        service = LLMService()
        
        mock_response = """
        {
            "objectives": [
                {
                    "objective_text": "Students will calculate force using F=ma",
                    "bloom_level": "apply",
                    "action_verbs": ["calculate", "solve"],
                    "difficulty": "intermediate"
                }
            ]
        }
        """
        
        # Mock the generate_content method
        service.generate_content = AsyncMock(return_value=mock_response)
        service._initialized = True
        
        result = await service.generate_learning_objectives(
            topic="Forces and Motion",
            context="Force equals mass times acceleration",
            target_count=1
        )
        
        assert result == mock_response
        service.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_learning_objective(self):
        """Test learning objective validation."""
        service = LLMService()
        
        # Mock the generate_content method for validation
        service.generate_content = AsyncMock(return_value="Validation response")
        service._initialized = True
        
        result = await service.validate_learning_objective(
            "Students will calculate force",
            "Force equals mass times acceleration"
        )
        
        assert "overall_score" in result
        assert "clarity_score" in result
        assert "relevance_score" in result
        assert result["overall_score"] == 0.8  # Default from implementation
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        service = LLMService()
        service._initialized = True
        
        # Mock successful generation
        mock_response = MagicMock()
        mock_response.text = "Test response"
        
        mock_model = AsyncMock()
        mock_model.generate_content_async.return_value = mock_response
        
        service.generation_model = mock_model
        
        # Test multiple concurrent requests (should be limited by semaphore)
        tasks = []
        for i in range(15):  # More than semaphore limit of 10
            task = service.generate_content(f"Test prompt {i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 15
        assert all(result == "Test response" for result in results)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        service = LLMService()
        service._initialized = True
        
        # Mock successful test generation
        service.generate_content = AsyncMock(return_value="Test response")
        
        health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert "models" in health
        assert health["models"]["generation"] == "gemini-2.5-pro"
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy_not_initialized(self):
        """Test health check when service is not initialized."""
        service = LLMService()
        
        health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "not initialized" in health["message"]
    
    @pytest.mark.asyncio
    async def test_health_check_api_failure(self):
        """Test health check when API call fails."""
        service = LLMService()
        service._initialized = True
        
        # Mock API failure
        service.generate_content = AsyncMock(side_effect=Exception("API Error"))
        
        health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Health check failed" in health["message"]
    
    def test_prompt_creation_methods(self):
        """Test prompt creation helper methods."""
        service = LLMService()
        
        # Test LO generation prompt
        lo_prompt = service._create_lo_generation_prompt(
            "Forces and Motion",
            "Force equals mass times acceleration",
            3
        )
        
        assert "Forces and Motion" in lo_prompt
        assert "Force equals mass times acceleration" in lo_prompt
        assert "3" in lo_prompt
        assert "Bloom's taxonomy" in lo_prompt
        
        # Test validation prompt
        validation_prompt = service._create_validation_prompt(
            "Students will calculate force",
            "Force context"
        )
        
        assert "Students will calculate force" in validation_prompt
        assert "Force context" in validation_prompt
        assert "clarity_score" in validation_prompt


import asyncio  # Add this import for the rate limiting test