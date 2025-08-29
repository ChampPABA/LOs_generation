"""
Performance tests for the Learning Objectives Generation Pipeline.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any
import statistics

from src.services.llm_service import LLMService
from src.services.vector_service import VectorService
from src.services.processing_service import ProcessingService
from src.api.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


@pytest.mark.performance
class TestLLMServicePerformance:
    """Performance tests for LLM service."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service with realistic delays."""
        service = AsyncMock(spec=LLMService)
        
        async def mock_generate_content(prompt, **kwargs):
            # Simulate realistic API response time (0.5-2.0 seconds)
            await asyncio.sleep(0.8)
            return f"Generated content for: {prompt[:50]}..."
        
        service.generate_content = mock_generate_content
        return service
    
    @pytest.mark.asyncio
    async def test_concurrent_llm_requests(self, mock_llm_service):
        """Test concurrent LLM request performance."""
        num_requests = 10
        prompts = [f"Generate learning objective for topic {i}" for i in range(num_requests)]
        
        start_time = time.time()
        
        # Run requests concurrently
        tasks = [mock_llm_service.generate_content(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert len(results) == num_requests
        assert total_time < 3.0  # Should complete within 3 seconds (concurrent)
        
        # Calculate throughput
        throughput = num_requests / total_time
        assert throughput > 3.0  # At least 3 requests per second
        
        print(f"Concurrent LLM Performance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} req/s")
        print(f"  Average per request: {total_time/num_requests:.2f}s")
    
    @pytest.mark.asyncio
    async def test_llm_request_latency(self, mock_llm_service):
        """Test LLM request latency distribution."""
        num_samples = 20
        latencies = []
        
        for i in range(num_samples):
            start_time = time.time()
            await mock_llm_service.generate_content(f"Test prompt {i}")
            latency = time.time() - start_time
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Performance assertions
        assert avg_latency < 2.0  # Average under 2 seconds
        assert max_latency < 3.0  # Max under 3 seconds
        assert min_latency > 0.5  # Min over 0.5 seconds (realistic)
        
        print(f"LLM Latency Statistics:")
        print(f"  Average: {avg_latency:.3f}s")
        print(f"  Median: {median_latency:.3f}s")
        print(f"  Min: {min_latency:.3f}s")
        print(f"  Max: {max_latency:.3f}s")


@pytest.mark.performance
class TestVectorServicePerformance:
    """Performance tests for vector service."""
    
    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service with realistic performance."""
        service = AsyncMock(spec=VectorService)
        
        async def mock_generate_embedding(text, language="en"):
            # Simulate embedding generation (0.1-0.3 seconds)
            await asyncio.sleep(0.15)
            return [0.1] * 1024  # Mock embedding vector
        
        async def mock_search_similar(query_text, limit=10, **kwargs):
            # Simulate vector search (0.05-0.2 seconds)
            await asyncio.sleep(0.08)
            return [
                {
                    "id": f"chunk-{i}",
                    "score": 0.9 - (i * 0.05),
                    "text": f"Similar content {i}",
                    "metadata": {"source": f"doc_{i}"}
                }
                for i in range(limit)
            ]
        
        service.generate_embedding = mock_generate_embedding
        service.search_similar = mock_search_similar
        return service
    
    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self, mock_vector_service):
        """Test batch embedding generation performance."""
        texts = [f"This is test content number {i} for embedding" for i in range(50)]
        
        start_time = time.time()
        
        # Generate embeddings concurrently
        tasks = [mock_vector_service.generate_embedding(text) for text in texts]
        embeddings = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert len(embeddings) == 50
        assert total_time < 5.0  # Should complete within 5 seconds
        
        throughput = len(texts) / total_time
        assert throughput > 10.0  # At least 10 embeddings per second
        
        print(f"Batch Embedding Performance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} embeddings/s")
        print(f"  Average per embedding: {total_time/len(texts):.3f}s")
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, mock_vector_service):
        """Test vector search performance with different result sizes."""
        query = "Find similar content about physics"
        result_sizes = [5, 10, 20, 50]
        
        for size in result_sizes:
            start_time = time.time()
            results = await mock_vector_service.search_similar(query, limit=size)
            search_time = time.time() - start_time
            
            # Performance assertions
            assert len(results) == size
            assert search_time < 0.5  # Should be fast
            
            print(f"Vector Search (limit={size}): {search_time:.3f}s")


@pytest.mark.performance
class TestProcessingServicePerformance:
    """Performance tests for processing service."""
    
    @pytest.fixture
    def mock_processing_service(self):
        """Create mock processing service."""
        service = AsyncMock(spec=ProcessingService)
        
        async def mock_process_content(content, **kwargs):
            # Simulate content processing time based on content size
            processing_time = len(content) / 10000.0  # 10k chars per second
            await asyncio.sleep(min(processing_time, 2.0))  # Max 2 seconds
            
            # Return mock chunks
            chunk_count = max(1, len(content) // 1000)
            return {
                "chunks": [
                    {
                        "id": f"chunk-{i}",
                        "content": content[i*1000:(i+1)*1000],
                        "metadata": {"chunk_index": i}
                    }
                    for i in range(chunk_count)
                ],
                "processing_time": processing_time
            }
        
        service.process_content = mock_process_content
        return service
    
    @pytest.mark.asyncio
    async def test_content_processing_scalability(self, mock_processing_service):
        """Test content processing performance with different content sizes."""
        content_sizes = [1000, 5000, 10000, 25000]  # Characters
        
        for size in content_sizes:
            content = "This is test content. " * (size // 20)  # Approximate size
            
            start_time = time.time()
            result = await mock_processing_service.process_content(content)
            processing_time = time.time() - start_time
            
            # Performance assertions
            assert len(result["chunks"]) > 0
            assert processing_time < 3.0  # Max 3 seconds for any size
            
            # Calculate processing rate
            chars_per_second = len(content) / processing_time
            assert chars_per_second > 1000  # At least 1k chars/second
            
            print(f"Content Processing ({size} chars): {processing_time:.3f}s ({chars_per_second:.0f} chars/s)")


@pytest.mark.performance
class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker functionality."""
    
    @pytest.fixture
    def fast_config(self):
        """Circuit breaker config optimized for performance testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=0.1,  # Very short timeout for testing
            request_timeout=0.05,
            failure_rate_threshold=0.5,
            min_requests=5
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self, fast_config):
        """Test circuit breaker performance overhead."""
        circuit_breaker = CircuitBreaker("performance_test", fast_config)
        
        async def fast_function():
            return "success"
        
        # Measure baseline performance (direct calls)
        num_calls = 100
        
        start_time = time.time()
        for _ in range(num_calls):
            await fast_function()
        baseline_time = time.time() - start_time
        
        # Measure circuit breaker performance
        start_time = time.time()
        for _ in range(num_calls):
            await circuit_breaker.call(fast_function)
        circuit_time = time.time() - start_time
        
        # Calculate overhead
        overhead = (circuit_time - baseline_time) / baseline_time * 100
        
        # Performance assertions
        assert overhead < 50  # Less than 50% overhead
        assert circuit_time < baseline_time * 2  # Less than 2x slower
        
        print(f"Circuit Breaker Performance:")
        print(f"  Baseline: {baseline_time:.4f}s ({num_calls/baseline_time:.0f} req/s)")
        print(f"  Circuit Breaker: {circuit_time:.4f}s ({num_calls/circuit_time:.0f} req/s)")
        print(f"  Overhead: {overhead:.1f}%")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_performance(self, fast_config):
        """Test circuit breaker performance under concurrent load."""
        circuit_breaker = CircuitBreaker("concurrent_test", fast_config)
        
        async def mock_service_call():
            await asyncio.sleep(0.01)  # Simulate small delay
            return "success"
        
        num_concurrent = 50
        num_batches = 5
        
        total_start = time.time()
        
        for batch in range(num_batches):
            batch_start = time.time()
            
            tasks = [
                circuit_breaker.call(mock_service_call)
                for _ in range(num_concurrent)
            ]
            results = await asyncio.gather(*tasks)
            
            batch_time = time.time() - batch_start
            throughput = num_concurrent / batch_time
            
            assert len(results) == num_concurrent
            assert throughput > 20  # At least 20 req/s per batch
            
            print(f"Batch {batch + 1}: {batch_time:.3f}s ({throughput:.0f} req/s)")
        
        total_time = time.time() - total_start
        total_requests = num_concurrent * num_batches
        overall_throughput = total_requests / total_time
        
        print(f"Overall Performance: {overall_throughput:.0f} req/s")
        assert overall_throughput > 15  # Minimum overall throughput


@pytest.mark.performance
class TestEndToEndPerformance:
    """End-to-end performance tests."""
    
    @pytest.mark.asyncio
    async def test_learning_objective_generation_pipeline(self):
        """Test complete LO generation pipeline performance."""
        # Mock the entire pipeline
        async def mock_pipeline(topic: str, content: str):
            # Simulate realistic pipeline stages
            await asyncio.sleep(0.1)  # Content processing
            await asyncio.sleep(0.2)  # Vector embedding
            await asyncio.sleep(0.3)  # Context retrieval
            await asyncio.sleep(0.8)  # LLM generation
            await asyncio.sleep(0.1)  # Validation
            
            return {
                "topic": topic,
                "objectives": [
                    {
                        "text": f"Students will be able to understand {topic}",
                        "bloom_level": "understand",
                        "quality_score": 0.85
                    }
                    for _ in range(5)
                ],
                "generation_time": 1.5
            }
        
        # Test single pipeline execution
        start_time = time.time()
        result = await mock_pipeline("Forces and Motion", "Test content about physics")
        single_time = time.time() - start_time
        
        assert single_time < 3.0  # Should complete within 3 seconds
        assert len(result["objectives"]) == 5
        
        # Test concurrent pipeline executions
        topics = [f"Physics Topic {i}" for i in range(5)]
        content = "Test content for physics learning objectives generation."
        
        start_time = time.time()
        tasks = [mock_pipeline(topic, content) for topic in topics]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Performance assertions
        assert len(results) == 5
        assert concurrent_time < 5.0  # Should complete within 5 seconds
        assert concurrent_time < single_time * 3  # Should be faster than sequential
        
        print(f"Pipeline Performance:")
        print(f"  Single execution: {single_time:.2f}s")
        print(f"  5 concurrent executions: {concurrent_time:.2f}s")
        print(f"  Speedup: {(single_time * 5) / concurrent_time:.1f}x")
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self):
        """Test system performance under sustained load."""
        async def mock_request():
            # Simulate various request types with different load
            request_type = hash(asyncio.current_task()) % 3
            
            if request_type == 0:  # Light request
                await asyncio.sleep(0.1)
            elif request_type == 1:  # Medium request
                await asyncio.sleep(0.3)
            else:  # Heavy request
                await asyncio.sleep(0.8)
            
            return f"completed_type_{request_type}"
        
        # Sustained load test parameters
        duration_seconds = 10
        requests_per_second = 20
        total_requests = duration_seconds * requests_per_second
        
        start_time = time.time()
        completed_requests = 0
        failed_requests = 0
        
        # Generate load over time
        for second in range(duration_seconds):
            second_start = time.time()
            
            # Create batch of requests for this second
            tasks = [mock_request() for _ in range(requests_per_second)]
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=2.0
                )
                
                for result in results:
                    if isinstance(result, Exception):
                        failed_requests += 1
                    else:
                        completed_requests += 1
            
            except asyncio.TimeoutError:
                failed_requests += requests_per_second
            
            # Rate limiting to maintain requests per second
            second_duration = time.time() - second_start
            if second_duration < 1.0:
                await asyncio.sleep(1.0 - second_duration)
        
        total_time = time.time() - start_time
        success_rate = completed_requests / (completed_requests + failed_requests) * 100
        actual_rps = completed_requests / total_time
        
        # Performance assertions
        assert success_rate > 80  # At least 80% success rate
        assert actual_rps > 10   # At least 10 successful requests per second
        
        print(f"Sustained Load Performance:")
        print(f"  Duration: {total_time:.1f}s")
        print(f"  Completed requests: {completed_requests}")
        print(f"  Failed requests: {failed_requests}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Actual RPS: {actual_rps:.1f}")


@pytest.mark.performance
class TestMemoryPerformance:
    """Memory usage performance tests."""
    
    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate memory-intensive operations
        large_data = []
        for i in range(1000):
            # Create and process data
            data = {
                "id": i,
                "content": "This is test content " * 100,
                "embeddings": [0.1] * 1024,
                "metadata": {"source": f"document_{i}", "processed": True}
            }
            large_data.append(data)
            
            # Simulate processing and cleanup
            if i % 100 == 0:
                processed_data = [item for item in large_data if item["id"] < i - 50]
                large_data = large_data[-50:]  # Keep only recent items
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory assertions
        assert memory_growth < 100  # Less than 100MB growth
        
        print(f"Memory Performance:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory growth: {memory_growth:.1f} MB")
