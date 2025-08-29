"""
End-to-end integration tests for the complete LO generation pipeline.
"""

import pytest
from pathlib import Path
from src.services import (
    ProcessingService,
    VectorService,
    GenerationService,
    HealthService
)


class TestE2EGeneration:
    """End-to-end tests for learning objective generation pipeline."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_complete_generation_pipeline(
        self, 
        sample_physics_content,
        temp_directory
    ):
        """Test complete pipeline from content to learning objectives."""
        
        # Initialize all services
        processing_service = ProcessingService()
        vector_service = VectorService()
        generation_service = GenerationService()
        
        try:
            # Initialize services
            await processing_service.initialize()
            await vector_service.initialize()
            await generation_service.initialize()
            
            # Step 1: Create sample content file
            sample_pdf_path = temp_directory / "sample_physics.pdf"
            # Note: In real test, you'd need actual PDF creation
            # For now, we'll simulate with processed content
            
            # Step 2: Process content
            chunks = await processing_service.create_chunks(
                extracted_data={
                    "filename": "sample_physics.pdf",
                    "full_text": sample_physics_content["content"],
                    "document_language": "en",
                    "document_language_confidence": 0.95
                }
            )
            
            assert len(chunks) >= sample_physics_content["expected_chunks"]
            assert all(chunk["quality_score"] > 0.5 for chunk in chunks)
            
            # Step 3: Index chunks in vector database
            indexed_count = 0
            for chunk in chunks:
                success = await vector_service.index_chunk(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["content"],
                    metadata=chunk["metadata"]
                )
                if success:
                    indexed_count += 1
            
            assert indexed_count == len(chunks)
            
            # Step 4: Generate learning objectives
            generation_result = await generation_service.generate_learning_objectives(
                topic=sample_physics_content["topic"],
                target_count=3,
                quality_threshold=0.6
            )
            
            # Verify generation results
            assert generation_result["generation_successful"] is True
            assert generation_result["validated_count"] >= 2  # At least 2 good objectives
            assert len(generation_result["objectives"]) >= 2
            
            # Verify objective quality
            for objective in generation_result["objectives"]:
                assert len(objective["objective_text"]) > 20
                assert objective["bloom_level"] in [
                    "remember", "understand", "apply", "analyze", "evaluate", "create"
                ]
                assert objective["quality_scores"]["overall_score"] >= 0.6
                assert len(objective["action_verbs"]) > 0
            
            # Step 5: Verify Bloom's taxonomy distribution
            bloom_distribution = generation_result["generation_stats"]["bloom_distribution"]
            assert len(bloom_distribution) >= 2  # Should have variety
            
        finally:
            # Cleanup services
            await processing_service.shutdown()
            await vector_service.shutdown()
            await generation_service.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_service_health_integration(self):
        """Test health monitoring across all services."""
        
        health_service = HealthService()
        
        try:
            await health_service.initialize()
            
            # Check individual service health
            llm_health = await health_service.check_service_health("llm_service")
            vector_health = await health_service.check_service_health("vector_service")
            processing_health = await health_service.check_service_health("processing_service")
            generation_health = await health_service.check_service_health("generation_service")
            
            # All services should report their status
            assert llm_health["service"] == "llm_service"
            assert vector_health["service"] == "vector_service"
            assert processing_health["service"] == "processing_service"
            assert generation_health["service"] == "generation_service"
            
            # Check comprehensive system health
            system_health = await health_service.get_comprehensive_status()
            
            assert "overall_system_status" in system_health
            assert "services" in system_health
            assert "system_metrics" in system_health
            assert system_health["services"]["overall_status"] in ["healthy", "degraded", "unhealthy"]
            
        finally:
            await health_service.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multilingual_content_processing(self):
        """Test processing of multilingual content (English + Thai)."""
        
        processing_service = ProcessingService()
        vector_service = VectorService()
        
        try:
            await processing_service.initialize()
            await vector_service.initialize()
            
            # Test mixed-language content
            mixed_content = """
            Physics (ฟิสิกส์) is the science that studies matter and energy.
            Force (แรง) is a push or pull that can change motion.
            Newton's laws (กฎของนิวตัน) describe the relationship between forces and motion.
            """
            
            # Process mixed content
            chunks = await processing_service.create_chunks(
                extracted_data={
                    "filename": "mixed_language.pdf",
                    "full_text": mixed_content,
                    "document_language": "mixed",
                    "document_language_confidence": 0.8
                }
            )
            
            # Verify language detection
            languages_detected = set()
            for chunk in chunks:
                lang = chunk["metadata"]["language_code"]
                languages_detected.add(lang)
            
            # Should detect mixed or appropriate languages
            assert "mixed" in languages_detected or "en" in languages_detected
            
            # Test indexing with appropriate models
            for chunk in chunks:
                success = await vector_service.index_chunk(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["content"],
                    metadata=chunk["metadata"]
                )
                assert success is True
            
            # Test search with mixed query
            search_results = await vector_service.search_similar(
                query_text="What is force? แรงคืออะไร?",
                limit=3
            )
            
            assert len(search_results) > 0
            
        finally:
            await processing_service.shutdown()
            await vector_service.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_recovery_and_resilience(self):
        """Test system behavior under error conditions."""
        
        generation_service = GenerationService()
        
        try:
            await generation_service.initialize()
            
            # Test generation with insufficient context
            result_no_context = await generation_service.generate_learning_objectives(
                topic="Nonexistent Physics Topic XYZ123",
                target_count=3,
                custom_context=""  # Empty context
            )
            
            # Should handle gracefully
            assert result_no_context["generation_successful"] is False
            assert "error" in result_no_context
            
            # Test generation with very low quality threshold
            result_high_threshold = await generation_service.generate_learning_objectives(
                topic="Forces and Motion",
                target_count=5,
                quality_threshold=0.99,  # Very high threshold
                custom_context="Force equals mass times acceleration."
            )
            
            # Should still attempt generation but may have fewer validated objectives
            assert "validated_count" in result_high_threshold
            
        finally:
            await generation_service.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_generation_performance(self, sample_physics_content):
        """Test concurrent generation performance."""
        import asyncio
        import time
        
        generation_service = GenerationService()
        
        try:
            await generation_service.initialize()
            
            # Prepare multiple topics
            topics = [
                "Forces and Motion",
                "Energy Conservation",
                "Wave Properties",
                "Electric Circuits"
            ]
            
            # Test concurrent generation
            start_time = time.time()
            
            tasks = []
            for topic in topics:
                task = generation_service.generate_learning_objectives(
                    topic=topic,
                    target_count=2,
                    quality_threshold=0.6,
                    custom_context=sample_physics_content["content"]
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify all requests completed
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= len(topics) * 0.75  # At least 75% success
            
            # Performance should be reasonable (adjust threshold as needed)
            assert total_time < 60  # Should complete within 60 seconds
            
            # Verify concurrent processing didn't break results
            for result in successful_results:
                if isinstance(result, dict) and result.get("generation_successful"):
                    assert len(result["objectives"]) > 0
            
        finally:
            await generation_service.shutdown()