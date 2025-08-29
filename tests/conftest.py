"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import asyncio
from typing import Dict, Any, Generator
from unittest.mock import MagicMock, AsyncMock
import tempfile
from pathlib import Path

from src.core.config import Settings
from src.services import (
    LLMService, 
    VectorService, 
    ProcessingService, 
    GenerationService,
    HealthService
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    return Settings(
        SECRET_KEY="test-secret-key-for-testing-only-32chars",
        ENVIRONMENT="test",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/15",  # Use different DB for tests
        QDRANT_URL="http://localhost:6333",
        GEMINI_API_KEY="test-api-key-for-testing-purposes",
        OLLAMA_URL="http://localhost:11434",
        LANGFUSE_PUBLIC_KEY=None,
        LANGFUSE_SECRET_KEY=None
    )


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_llm_service() -> AsyncMock:
    """Create a mock LLM service for testing."""
    mock_service = AsyncMock(spec=LLMService)
    mock_service.is_initialized.return_value = True
    mock_service.generate_content.return_value = "Mock generated content"
    mock_service.generate_learning_objectives.return_value = """
    {
        "objectives": [
            {
                "objective_text": "Students will be able to calculate force using Newton's second law",
                "bloom_level": "apply",
                "action_verbs": ["calculate", "solve"],
                "difficulty": "intermediate",
                "assessment_suggestions": ["problem solving", "laboratory work"]
            }
        ]
    }
    """
    mock_service.validate_learning_objective.return_value = {
        "overall_score": 0.85,
        "clarity_score": 0.9,
        "relevance_score": 0.8,
        "structure_score": 0.85,
        "feedback": "Well-structured learning objective"
    }
    mock_service.health_check.return_value = {
        "status": "healthy",
        "message": "Mock LLM service operational"
    }
    return mock_service


@pytest.fixture
def mock_vector_service() -> AsyncMock:
    """Create a mock vector service for testing."""
    mock_service = AsyncMock(spec=VectorService)
    mock_service.is_initialized.return_value = True
    mock_service.generate_embedding.return_value = [0.1] * 1024  # Mock embedding
    mock_service.index_chunk.return_value = True
    mock_service.search_similar.return_value = [
        {
            "id": "test-chunk-1",
            "score": 0.85,
            "text": "Force is a push or pull that can change the motion of objects.",
            "language": "en",
            "metadata": {"source": "physics_textbook.pdf", "page": 1}
        }
    ]
    mock_service.get_collection_stats.return_value = {
        "vectors_count": 100,
        "indexed_vectors_count": 100,
        "points_count": 100
    }
    mock_service.health_check.return_value = {
        "status": "healthy",
        "qdrant": {"status": "healthy"},
        "ollama": {"status": "healthy"}
    }
    return mock_service


@pytest.fixture
def mock_processing_service() -> AsyncMock:
    """Create a mock processing service for testing."""
    mock_service = AsyncMock(spec=ProcessingService)
    mock_service.is_initialized.return_value = True
    mock_service.extract_text_from_pdf.return_value = {
        "filename": "test.pdf",
        "total_pages": 5,
        "full_text": "This is test content about physics and forces.",
        "document_language": "en",
        "document_language_confidence": 0.95
    }
    mock_service.create_chunks.return_value = [
        {
            "chunk_id": "chunk-1",
            "content": "This is test content about physics.",
            "quality_score": 0.8,
            "metadata": {
                "source_document": "test.pdf",
                "language_code": "en",
                "language_confidence": 0.9
            }
        }
    ]
    mock_service.process_pdf_file.return_value = {
        "source_file": "test.pdf",
        "processing_successful": True,
        "chunks": [
            {
                "chunk_id": "chunk-1",
                "content": "This is test content about physics.",
                "quality_score": 0.8,
                "metadata": {"source_document": "test.pdf"}
            }
        ]
    }
    mock_service.health_check.return_value = {
        "status": "healthy",
        "message": "Mock processing service operational"
    }
    return mock_service


@pytest.fixture
def mock_generation_service() -> AsyncMock:
    """Create a mock generation service for testing."""
    mock_service = AsyncMock(spec=GenerationService)
    mock_service.is_initialized.return_value = True
    mock_service.retrieve_context.return_value = {
        "topic": "Forces and Motion",
        "chunks": [
            {
                "id": "chunk-1",
                "text": "Force is a push or pull that can change motion.",
                "score": 0.85,
                "language": "en"
            }
        ],
        "context_text": "Force is a push or pull that can change motion.",
        "total_chunks": 1,
        "avg_relevance": 0.85
    }
    mock_service.generate_learning_objectives.return_value = {
        "topic": "Forces and Motion",
        "generation_successful": True,
        "requested_count": 3,
        "generated_count": 3,
        "validated_count": 3,
        "objectives": [
            {
                "objective_text": "Students will be able to identify different types of forces",
                "bloom_level": "remember",
                "quality_scores": {"overall_score": 0.8}
            }
        ],
        "generation_stats": {
            "avg_quality_score": 0.8,
            "processing_time_seconds": 5.2
        }
    }
    mock_service.health_check.return_value = {
        "status": "healthy",
        "message": "Mock generation service operational"
    }
    return mock_service


@pytest.fixture
def sample_physics_content() -> Dict[str, Any]:
    """Sample physics content for testing."""
    return {
        "topic": "Forces and Motion",
        "content": """
        Force is a push or pull that can change the motion of an object. 
        According to Newton's first law, an object at rest stays at rest 
        and an object in motion stays in motion unless acted upon by an 
        external force. Newton's second law states that F = ma, where F 
        is force, m is mass, and a is acceleration.
        """,
        "expected_chunks": 2,
        "expected_language": "en"
    }


@pytest.fixture
def sample_learning_objectives() -> list:
    """Sample learning objectives for testing."""
    return [
        {
            "objective_text": "Students will be able to calculate force using F=ma",
            "bloom_level": "apply",
            "action_verbs": ["calculate", "solve"],
            "difficulty": "intermediate",
            "assessment_suggestions": ["problem solving"]
        },
        {
            "objective_text": "Students will be able to explain Newton's first law",
            "bloom_level": "understand",
            "action_verbs": ["explain", "describe"],
            "difficulty": "beginner",
            "assessment_suggestions": ["written explanation"]
        }
    ]


@pytest.fixture
def api_test_client():
    """Create test client for API testing."""
    # This will be implemented when we have the FastAPI app
    pass


# Performance test fixtures
@pytest.fixture
def performance_test_data():
    """Data for performance testing."""
    return {
        "large_text": "This is test content. " * 1000,
        "multiple_topics": [
            "Forces and Motion",
            "Energy Conservation", 
            "Wave Properties",
            "Electric Circuits",
            "Thermodynamics"
        ] * 10,  # 50 topics total
        "stress_test_count": 100
    }


# Integration test helpers
@pytest.fixture
def integration_test_setup():
    """Setup for integration tests."""
    return {
        "test_pdf_path": "tests/fixtures/sample_physics.pdf",
        "test_topic": "Forces and Motion",
        "expected_min_chunks": 5,
        "expected_min_quality": 0.6
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test paths."""
    for item in items:
        # Add markers based on test file location
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        elif "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


# Async test helpers
def async_test(f):
    """Decorator to run async tests."""
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))
    return wrapper