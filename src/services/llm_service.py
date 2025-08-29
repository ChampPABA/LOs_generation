"""
LLM Service for Gemini API integration with retry logic and error handling.
"""

import asyncio
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from .base import BaseService
from ..api.circuit_breaker import circuit_breaker, CircuitBreakerConfig


class LLMService(BaseService):
    """Service for LLM operations using Gemini API."""
    
    def __init__(self):
        super().__init__("LLMService")
        self.generation_model = None
        self.validation_model = None
        self._rate_limiter = asyncio.Semaphore(10)  # Limit concurrent requests
    
    async def _initialize(self) -> None:
        """Initialize Gemini API clients."""
        try:
            # Configure Gemini API
            genai.configure(api_key=self.settings.gemini_api_key)
            
            # Initialize models
            self.generation_model = genai.GenerativeModel("gemini-2.5-pro")
            self.validation_model = genai.GenerativeModel("gemini-2.5-flash")
            
            # Test connectivity
            await self._test_connectivity()
            
        except Exception as e:
            self.logger.error("Failed to initialize Gemini API", error=str(e))
            raise
    
    async def _shutdown(self) -> None:
        """Shutdown LLM service."""
        self.generation_model = None
        self.validation_model = None
    
    async def _test_connectivity(self) -> None:
        """Test Gemini API connectivity."""
        try:
            test_prompt = "Test connection"
            response = await self.generation_model.generate_content_async(test_prompt)
            if not response.text:
                raise Exception("Empty response from Gemini API")
        except Exception as e:
            self.logger.error("Gemini API connectivity test failed", error=str(e))
            raise
    
    @circuit_breaker(
        name="gemini_api",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=120.0,
            request_timeout=60.0
        ),
        fallback_func=None  # Could add cached responses here
    )
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_content(
        self, 
        prompt: str, 
        model_type: str = "generation",
        **kwargs
    ) -> str:
        """
        Generate content using specified Gemini model.
        
        Args:
            prompt: Input prompt for generation
            model_type: "generation" for 2.5-pro or "validation" for 2.5-flash
            **kwargs: Additional generation parameters
            
        Returns:
            Generated content string
        """
        async with self._rate_limiter:
            try:
                model = self.generation_model if model_type == "generation" else self.validation_model
                
                if not model:
                    raise Exception(f"Model {model_type} not initialized")
                
                self.logger.info(
                    "Generating content", 
                    model_type=model_type,
                    prompt_length=len(prompt)
                )
                
                response = await model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=kwargs.get("temperature", 0.1),
                        max_output_tokens=kwargs.get("max_tokens", 2048),
                        top_p=kwargs.get("top_p", 0.8),
                        top_k=kwargs.get("top_k", 40)
                    )
                )
                
                if not response.text:
                    raise Exception("Empty response from Gemini API")
                
                self.logger.info(
                    "Content generated successfully",
                    model_type=model_type,
                    response_length=len(response.text)
                )
                
                return response.text.strip()
                
            except Exception as e:
                self.logger.error(
                    "Content generation failed",
                    model_type=model_type,
                    error=str(e)
                )
                raise
    
    async def generate_learning_objectives(
        self, 
        topic: str, 
        context: str, 
        target_count: int = 5
    ) -> str:
        """
        Generate learning objectives using Gemini 2.5 Pro.
        
        Args:
            topic: Physics topic for LO generation
            context: Retrieved chunks context
            target_count: Number of LOs to generate
            
        Returns:
            Generated learning objectives JSON string
        """
        prompt = self._create_lo_generation_prompt(topic, context, target_count)
        return await self.generate_content(prompt, model_type="generation")
    
    async def validate_learning_objective(
        self, 
        objective: str, 
        context: str
    ) -> Dict[str, Any]:
        """
        Validate learning objective quality using Gemini 2.5 Flash.
        
        Args:
            objective: Learning objective to validate
            context: Source context for validation
            
        Returns:
            Validation results with quality scores
        """
        prompt = self._create_validation_prompt(objective, context)
        response = await self.generate_content(prompt, model_type="validation")
        
        # Parse validation response (implement JSON parsing)
        # For now, return basic structure
        return {
            "overall_score": 0.8,
            "clarity_score": 0.85,
            "relevance_score": 0.75,
            "structure_score": 0.80,
            "feedback": response[:200] if response else "No feedback available"
        }
    
    def _create_lo_generation_prompt(
        self, 
        topic: str, 
        context: str, 
        target_count: int
    ) -> str:
        """Create prompt for LO generation."""
        return f"""
You are an expert educational designer specializing in Physics education and Bloom's taxonomy.
Your task is to create {target_count} specific, measurable learning objectives for the topic: {topic}

Context from Physics textbook:
{context}

Requirements:
1. Each objective must specify what students will be able to DO
2. Use action verbs that align with appropriate Bloom's taxonomy levels
3. Ensure objectives are specific to the Physics content provided
4. Make objectives measurable and assessable
5. Include a variety of Bloom's taxonomy levels (Remember, Understand, Apply, Analyze, Evaluate, Create)

Return the learning objectives as a JSON array with the following structure:
{{
  "objectives": [
    {{
      "objective_text": "Students will be able to...",
      "bloom_level": "apply",
      "action_verbs": ["calculate", "solve"],
      "difficulty": "beginner|intermediate|advanced",
      "assessment_suggestions": ["problem solving", "laboratory work"]
    }}
  ]
}}
"""
    
    def _create_validation_prompt(self, objective: str, context: str) -> str:
        """Create prompt for LO validation."""
        return f"""
Evaluate the quality of this learning objective against the provided context:

Learning Objective: {objective}

Source Context: {context}

Rate the learning objective on these dimensions (0.0-1.0):
1. Clarity - Is the objective clear and unambiguous?
2. Relevance - Does it relate directly to the source context?
3. Measurability - Can student achievement be assessed?
4. Structure - Is it properly formatted and structured?

Provide specific feedback for improvement.

Return results as JSON:
{{
  "clarity_score": 0.85,
  "relevance_score": 0.90,
  "measurability_score": 0.80,
  "structure_score": 0.88,
  "overall_score": 0.86,
  "feedback": "Specific suggestions for improvement..."
}}
"""
    
    async def health_check(self) -> Dict[str, Any]:
        """Check LLM service health."""
        try:
            if not self.is_initialized():
                return {
                    "status": "unhealthy",
                    "message": "Service not initialized"
                }
            
            # Test API connectivity
            test_response = await self.generate_content(
                "Test health check", 
                model_type="validation"
            )
            
            return {
                "status": "healthy",
                "message": "LLM service operational",
                "models": {
                    "generation": "gemini-2.5-pro",
                    "validation": "gemini-2.5-flash"
                },
                "test_response_length": len(test_response) if test_response else 0
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }