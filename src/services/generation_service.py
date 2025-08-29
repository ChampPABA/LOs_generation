"""
Generation Service for Learning Objective creation with quality scoring and validation.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from .base import BaseService
from .llm_service import LLMService
from .vector_service import VectorService


class GenerationService(BaseService):
    """Service for Learning Objective generation with quality scoring."""
    
    def __init__(self):
        super().__init__("GenerationService")
        self.llm_service = None
        self.vector_service = None
        self._generation_semaphore = None
    
    async def _initialize(self) -> None:
        """Initialize generation service with dependencies."""
        try:
            # Initialize dependent services
            self.llm_service = LLMService()
            self.vector_service = VectorService()
            
            await self.llm_service.initialize()
            await self.vector_service.initialize()
            
            # Limit concurrent generations
            self._generation_semaphore = asyncio.Semaphore(self.settings.max_concurrent_jobs)
            
            self.logger.info("Generation service initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize generation service", error=str(e))
            raise
    
    async def _shutdown(self) -> None:
        """Shutdown generation service and dependencies."""
        if self.llm_service:
            await self.llm_service.shutdown()
        if self.vector_service:
            await self.vector_service.shutdown()
    
    async def retrieve_context(
        self,
        topic: str,
        max_chunks: int = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for learning objective generation.
        
        Args:
            topic: Physics topic to search for
            max_chunks: Maximum number of chunks to retrieve
            
        Returns:
            Retrieved context with chunks and metadata
        """
        try:
            max_chunks = max_chunks or self.settings.max_retrieval_chunks
            
            self.logger.info(
                "Retrieving context for topic",
                topic=topic,
                max_chunks=max_chunks
            )
            
            # Search for similar chunks
            similar_chunks = await self.vector_service.search_similar(
                query_text=topic,
                limit=max_chunks,
                score_threshold=0.6
            )
            
            if not similar_chunks:
                self.logger.warning("No relevant context found for topic", topic=topic)
                return {
                    "topic": topic,
                    "chunks": [],
                    "context_text": "",
                    "relevance_scores": [],
                    "total_chunks": 0
                }
            
            # Aggregate context text
            context_chunks = []
            relevance_scores = []
            context_text = f"Learning context for topic: {topic}\n\n"
            
            for i, chunk in enumerate(similar_chunks):
                context_text += f"--- Context {i+1} (Relevance: {chunk['score']:.3f}) ---\n"
                context_text += f"{chunk['text']}\n\n"
                
                context_chunks.append({
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "score": chunk["score"],
                    "language": chunk["language"],
                    "metadata": chunk["metadata"]
                })
                relevance_scores.append(chunk["score"])
            
            result = {
                "topic": topic,
                "chunks": context_chunks,
                "context_text": context_text.strip(),
                "relevance_scores": relevance_scores,
                "total_chunks": len(context_chunks),
                "avg_relevance": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            }
            
            self.logger.info(
                "Context retrieval completed",
                topic=topic,
                chunks_found=len(context_chunks),
                avg_relevance=result["avg_relevance"]
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Context retrieval failed", topic=topic, error=str(e))
            return {
                "topic": topic,
                "chunks": [],
                "context_text": "",
                "relevance_scores": [],
                "total_chunks": 0,
                "error": str(e)
            }
    
    def _parse_generated_objectives(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse generated learning objectives from LLM response.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            List of parsed learning objectives
        """
        try:
            # Try to extract JSON from response
            if "{" in response_text and "}" in response_text:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                json_str = response_text[start_idx:end_idx]
                
                parsed = json.loads(json_str)
                objectives = parsed.get("objectives", [])
                
                # Validate required fields
                valid_objectives = []
                for obj in objectives:
                    if all(key in obj for key in ["objective_text", "bloom_level"]):
                        # Set defaults for missing fields
                        obj.setdefault("action_verbs", [])
                        obj.setdefault("difficulty", "beginner")
                        obj.setdefault("assessment_suggestions", [])
                        valid_objectives.append(obj)
                
                return valid_objectives
            else:
                # Fallback: create simple objectives from text
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                objectives = []
                
                for i, line in enumerate(lines[:5]):  # Limit to 5 objectives
                    if len(line) > 20:  # Reasonable objective length
                        objectives.append({
                            "objective_text": line,
                            "bloom_level": "understand",  # Default level
                            "action_verbs": ["understand", "explain"],
                            "difficulty": "beginner",
                            "assessment_suggestions": ["written assessment"]
                        })
                
                return objectives
                
        except Exception as e:
            self.logger.error("Failed to parse generated objectives", error=str(e))
            return []
    
    async def validate_learning_objective(
        self,
        objective: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        Validate single learning objective quality.
        
        Args:
            objective: Learning objective to validate
            context: Source context for validation
            
        Returns:
            Validation results with quality scores
        """
        try:
            # Use LLM service for validation
            validation_result = await self.llm_service.validate_learning_objective(
                objective["objective_text"],
                context
            )
            
            # Add additional validation metrics
            text = objective["objective_text"]
            
            # Length validation
            length_score = 1.0 if 20 <= len(text) <= 200 else 0.7
            
            # Action verb validation
            action_verbs = objective.get("action_verbs", [])
            verb_score = 1.0 if action_verbs else 0.5
            
            # Bloom's taxonomy validation
            bloom_level = objective.get("bloom_level", "unknown")
            bloom_score = 1.0 if bloom_level in [
                "remember", "understand", "apply", "analyze", "evaluate", "create"
            ] else 0.6
            
            # Combine scores
            combined_score = (
                validation_result.get("overall_score", 0.7) * 0.5 +
                length_score * 0.2 +
                verb_score * 0.15 +
                bloom_score * 0.15
            )
            
            return {
                "overall_score": min(combined_score, 1.0),
                "clarity_score": validation_result.get("clarity_score", 0.7),
                "relevance_score": validation_result.get("relevance_score", 0.7),
                "structure_score": validation_result.get("structure_score", 0.7),
                "length_score": length_score,
                "verb_score": verb_score,
                "bloom_score": bloom_score,
                "feedback": validation_result.get("feedback", "No specific feedback available"),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Objective validation failed", error=str(e))
            return {
                "overall_score": 0.5,
                "clarity_score": 0.5,
                "relevance_score": 0.5,
                "structure_score": 0.5,
                "length_score": 0.5,
                "verb_score": 0.5,
                "bloom_score": 0.5,
                "feedback": f"Validation error: {str(e)}",
                "validated_at": datetime.utcnow().isoformat()
            }
    
    async def generate_learning_objectives(
        self,
        topic: str,
        target_count: int = 5,
        quality_threshold: float = 0.7,
        custom_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate learning objectives for a given Physics topic.
        
        Args:
            topic: Physics topic for LO generation
            target_count: Number of learning objectives to generate
            quality_threshold: Minimum quality threshold for objectives
            custom_context: Optional custom context (overrides retrieval)
            
        Returns:
            Generation results with validated learning objectives
        """
        async with self._generation_semaphore:
            try:
                start_time = datetime.utcnow()
                
                self.logger.info(
                    "Starting LO generation",
                    topic=topic,
                    target_count=target_count,
                    quality_threshold=quality_threshold
                )
                
                # Get context (either custom or retrieved)
                if custom_context:
                    context_data = {
                        "topic": topic,
                        "context_text": custom_context,
                        "total_chunks": 1,
                        "avg_relevance": 1.0
                    }
                else:
                    context_data = await self.retrieve_context(topic)
                
                if not context_data["context_text"]:
                    raise Exception(f"No context available for topic: {topic}")
                
                # Generate learning objectives using LLM
                raw_response = await self.llm_service.generate_learning_objectives(
                    topic=topic,
                    context=context_data["context_text"],
                    target_count=target_count
                )
                
                # Parse generated objectives
                objectives = self._parse_generated_objectives(raw_response)
                
                if not objectives:
                    raise Exception("No valid objectives could be parsed from generation response")
                
                # Validate each objective
                validated_objectives = []
                for obj in objectives:
                    validation = await self.validate_learning_objective(
                        obj, 
                        context_data["context_text"]
                    )
                    
                    # Only include objectives meeting quality threshold
                    if validation["overall_score"] >= quality_threshold:
                        obj_with_validation = {
                            **obj,
                            "quality_scores": validation,
                            "generated_at": start_time.isoformat(),
                            "topic": topic
                        }
                        validated_objectives.append(obj_with_validation)
                
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                # Compile results
                result = {
                    "topic": topic,
                    "generation_successful": True,
                    "requested_count": target_count,
                    "generated_count": len(objectives),
                    "validated_count": len(validated_objectives),
                    "quality_threshold": quality_threshold,
                    "objectives": validated_objectives,
                    "context_info": {
                        "source_chunks": context_data.get("total_chunks", 0),
                        "avg_relevance": context_data.get("avg_relevance", 0.0)
                    },
                    "generation_stats": {
                        "processing_time_seconds": processing_time,
                        "avg_quality_score": (
                            sum(obj["quality_scores"]["overall_score"] for obj in validated_objectives) /
                            len(validated_objectives)
                        ) if validated_objectives else 0,
                        "bloom_distribution": self._calculate_bloom_distribution(validated_objectives),
                        "difficulty_distribution": self._calculate_difficulty_distribution(validated_objectives)
                    },
                    "generated_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat()
                }
                
                self.logger.info(
                    "LO generation completed successfully",
                    topic=topic,
                    validated_count=len(validated_objectives),
                    avg_quality=result["generation_stats"]["avg_quality_score"],
                    processing_time=processing_time
                )
                
                return result
                
            except Exception as e:
                self.logger.error("LO generation failed", topic=topic, error=str(e))
                return {
                    "topic": topic,
                    "generation_successful": False,
                    "error": str(e),
                    "objectives": [],
                    "generated_at": datetime.utcnow().isoformat()
                }
    
    def _calculate_bloom_distribution(self, objectives: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of Bloom's taxonomy levels."""
        distribution = {}
        for obj in objectives:
            level = obj.get("bloom_level", "unknown")
            distribution[level] = distribution.get(level, 0) + 1
        return distribution
    
    def _calculate_difficulty_distribution(self, objectives: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of difficulty levels."""
        distribution = {}
        for obj in objectives:
            difficulty = obj.get("difficulty", "beginner")
            distribution[difficulty] = distribution.get(difficulty, 0) + 1
        return distribution
    
    async def health_check(self) -> Dict[str, Any]:
        """Check generation service health."""
        try:
            if not self.is_initialized():
                return {
                    "status": "unhealthy",
                    "message": "Service not initialized"
                }
            
            # Check dependent services
            llm_health = await self.llm_service.health_check()
            vector_health = await self.vector_service.health_check()
            
            # Test generation pipeline with simple topic
            try:
                test_result = await self.generate_learning_objectives(
                    topic="Force and Motion",
                    target_count=2,
                    custom_context="Force is a push or pull that can change the motion of objects."
                )
                generation_test_passed = test_result.get("generation_successful", False)
            except:
                generation_test_passed = False
            
            overall_healthy = (
                llm_health.get("status") == "healthy" and
                vector_health.get("status") == "healthy" and
                generation_test_passed
            )
            
            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "message": "Generation service operational" if overall_healthy else "Service issues detected",
                "dependencies": {
                    "llm_service": llm_health.get("status", "unknown"),
                    "vector_service": vector_health.get("status", "unknown")
                },
                "generation_test": {
                    "passed": generation_test_passed,
                    "max_concurrent_jobs": self.settings.max_concurrent_jobs
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }