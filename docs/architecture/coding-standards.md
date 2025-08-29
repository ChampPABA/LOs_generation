# Coding Standards - LOs Generation System

## Critical Python Rules

### **Type Safety**
- **All functions must have type hints:** Use `typing` module for complex types, `Optional` for nullable values
- **Pydantic for data validation:** All API requests/responses must use Pydantic schemas
- **Async typing:** Use `Awaitable`, `AsyncGenerator`, and `AsyncSession` appropriately
- **OCR result typing:** Use proper typing for OCR results and confidence scores

```python
# ✅ Good - OCR service with proper typing
from typing import Optional, List, Tuple
from PIL import Image
import pytesseract

async def process_ocr_page(
    page_image: Image.Image,
    languages: List[str] = ["eng", "tha"],
    confidence_threshold: float = 0.6
) -> Optional[OCRResult]:
    pass
```

```python
# ✅ Good
async def generate_learning_objectives(
    content: str, 
    topic_id: int,
    config: GenerationConfig
) -> List[LearningObjective]:
    pass

# ❌ Bad
def generate_learning_objectives(content, topic_id, config):
    pass
```

### **Error Handling**
- **Custom exceptions:** Use domain-specific exceptions from `src.utils.exceptions`
- **Never suppress exceptions:** Always log and handle appropriately
- **Async error handling:** Proper exception handling in async contexts

```python
# ✅ Good
from src.utils.exceptions import LLMServiceError, ValidationError

async def call_gemini_api(prompt: str) -> str:
    try:
        response = await gemini_client.generate(prompt)
        return response.text
    except RateLimitError as e:
        logger.warning(f"Rate limit hit: {e}")
        raise LLMServiceError("API rate limit exceeded") from e
    except ValidationError as e:
        logger.error(f"Response validation failed: {e}")
        raise
```

### **Database Operations**
- **Always use async sessions:** `AsyncSession` for all database operations
- **Repository pattern:** Never use models directly in services, always through repositories
- **Transaction management:** Explicit commits, rollbacks on errors

```python
# ✅ Good
async def create_learning_objective(
    self, 
    db: AsyncSession,
    **kwargs
) -> LearningObjective:
    try:
        lo_repo = LearningObjectiveRepository(db)
        lo = await lo_repo.create(**kwargs)
        await db.commit()
        return lo
    except Exception:
        await db.rollback()
        raise
```

### **Configuration Management**
- **Never use environment variables directly:** Access through `src.core.config`
- **YAML configs for business logic:** Prompts, model parameters, processing settings
- **Type-safe config:** Use Pydantic settings for validation
- **OCR configuration:** Centralized OCR settings with validation

```python
# ✅ Good - OCR configuration
from src.core.config import settings

# OCR settings properly configured
tesseract_cmd = settings.ocr.tesseract_command
languages = settings.ocr.supported_languages
confidence_threshold = settings.ocr.minimum_confidence

# ❌ Bad - Direct environment access
import os
tesseract_cmd = os.getenv("TESSERACT_CMD")
```

```python
# ✅ Good
from src.core.config import settings
api_key = settings.gemini_api_key

# ❌ Bad
import os
api_key = os.getenv("GEMINI_API_KEY")
```

### **Logging**
- **Structured logging:** Use `structlog` for all logging operations
- **Context preservation:** Include request_id, job_id, user context
- **Appropriate levels:** DEBUG for development, INFO for business events, ERROR for failures

```python
# ✅ Good
import structlog
logger = structlog.get_logger(__name__)

async def process_content(content: str, job_id: str):
    logger.info("Starting content processing", 
                job_id=job_id, 
                content_length=len(content))
```

## Service Layer Patterns

### **Dependency Injection**
- **Constructor injection:** Dependencies passed to service constructors
- **Interface dependencies:** Depend on abstractions, not concrete classes
- **Async service methods:** All service methods should be async

### **Hybrid Processing Patterns**
- **Document type detection:** Always validate PDF type before processing
- **Fallback mechanisms:** Implement robust fallback between processing paths
- **Resource management:** Proper cleanup of OCR temporary files and images

```python
# ✅ Good - Hybrid chunking service pattern
class ChunkingService:
    def __init__(
        self,
        document_analyzer: DocumentAnalyzer,
        structural_chunker: StructuralChunker,
        ocr_service: OCRService,
        agentic_chunker: AgenticChunker
    ):
        self.document_analyzer = document_analyzer
        self.structural_chunker = structural_chunker
        self.ocr_service = ocr_service
        self.agentic_chunker = agentic_chunker
    
    async def process_document(self, pdf_path: str) -> ChunkingResult:
        # Always detect document type first
        doc_type = await self.document_analyzer.analyze_pdf_type(pdf_path)
        
        try:
            if doc_type == DocumentType.NATIVE:
                return await self.structural_chunker.process(pdf_path)
            else:
                # OCR path with fallback
                ocr_result = await self.ocr_service.extract_text(pdf_path)
                return await self.agentic_chunker.process(ocr_result)
        except Exception as e:
            # Fallback to alternative path
            logger.warning(f"Primary path failed: {e}, trying fallback")
            return await self._fallback_processing(pdf_path, doc_type)
```

### **Repository Pattern**
- **Single responsibility:** One repository per aggregate root
- **Async operations:** All repository methods async
- **Generic base:** Inherit from `BaseRepository` for common operations

### **Business Logic Isolation**
- **Services contain business logic:** No business logic in controllers or models
- **Domain models:** Rich domain models with behavior, not just data containers
- **Validation:** Business rule validation in services, not controllers

## API Design Standards

### **FastAPI Best Practices**
- **Dependency injection:** Use FastAPI dependencies for common operations
- **Response models:** Always specify response models with Pydantic
- **Error handling:** Use HTTPException for API errors

### **REST Conventions**
- **Resource naming:** Plural nouns for collections (`/learning-objectives`)
- **HTTP methods:** GET (read), POST (create), PUT (replace), PATCH (update), DELETE (remove)
- **Status codes:** Use appropriate HTTP status codes (200, 201, 400, 404, 500)

### **Request/Response Patterns**
- **Pagination:** Always paginate large collections
- **Filtering:** Support filtering via query parameters
- **Sorting:** Support sorting with `?sort=field&order=asc`

## Testing Standards

### **Test Organization**
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Database and external service tests  
└── e2e/           # Full system tests
```

### **Test Naming**
- **Descriptive names:** `test_generate_lo_with_invalid_topic_raises_error`
- **Given-When-Then:** Structure tests with clear setup, action, assertion
- **Async testing:** Use `pytest-asyncio` for async test functions

### **Mocking Strategy**
- **Mock external services:** Always mock Gemini API, Qdrant, Redis
- **Repository mocking:** Mock repositories in service tests
- **Test doubles:** Use fakes for complex dependencies

```python
# ✅ Good
@pytest.mark.asyncio
async def test_generate_lo_with_valid_content_returns_learning_objectives():
    # Given
    mock_llm_service = Mock(spec=LLMService)
    mock_llm_service.generate_objectives.return_value = [mock_lo]
    generation_service = GenerationService(llm_service=mock_llm_service)
    
    # When
    result = await generation_service.generate_from_content("test content", topic_id=1)
    
    # Then
    assert len(result) == 1
    assert result[0].objective_text == "Expected text"
```

## Code Quality Tools

### **Formatting and Linting**
- **Black:** Line length 100, Python 3.10+ target
- **Flake8:** Code style enforcement  
- **MyPy:** Static type checking
- **isort:** Import sorting

### **Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
        args: [--line-length=100]
  - repo: https://github.com/pycqa/flake8  
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

### **Coverage Requirements**
- **Minimum 60% overall coverage** for MVP
- **80% coverage for critical paths** (generation pipeline, API endpoints)
- **100% coverage for utilities** and shared functions

## Security Standards

### **Input Validation**
- **Pydantic schemas:** All external input validated through Pydantic
- **SQL injection prevention:** Use parameterized queries via SQLAlchemy
- **File upload security:** Validate file types, scan for malware

### **Authentication & Authorization**
- **API key validation:** Hash-based API key storage and validation
- **Rate limiting:** Implement per-key rate limiting
- **Audit logging:** Log all authentication attempts and API usage

### **Data Protection**
- **Secrets management:** Never commit secrets, use environment variables
- **Data encryption:** Encrypt sensitive data at rest
- **PII handling:** Minimize collection and storage of personal information

## Performance Standards

### **Database Optimization**
- **Query optimization:** Use appropriate indexes, avoid N+1 queries
- **Connection pooling:** Configure async connection pools
- **Batch operations:** Use bulk operations for large datasets
- **OCR metadata indexing:** Proper indexes for document type and OCR confidence queries

### **Async Patterns**
- **Concurrent processing:** Use `asyncio.gather()` for parallel operations
- **Resource cleanup:** Proper async context managers
- **Backpressure handling:** Implement queuing and rate limiting
- **OCR resource management:** Proper cleanup of temporary images and OCR processes

```python
# ✅ Good - OCR resource management
import tempfile
import os
from contextlib import asynccontextmanager

@asynccontextmanager
async def ocr_processing_context(pdf_pages: List[bytes]):
    """Manage temporary files for OCR processing."""
    temp_files = []
    try:
        # Create temporary image files
        for i, page_bytes in enumerate(pdf_pages):
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_page_{i}.png",
                delete=False
            )
            temp_file.write(page_bytes)
            temp_file.close()
            temp_files.append(temp_file.name)
        
        yield temp_files
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass  # Already cleaned up
```

### **Caching**
- **Redis caching:** Cache expensive computations and external API responses
- **Memory usage:** Monitor and limit memory usage in long-running processes
- **Cache invalidation:** Implement proper cache invalidation strategies

## Documentation Standards

### **Code Documentation**
- **Docstrings:** Google-style docstrings for all public functions
- **Type information:** Include parameter types and return types in docstrings
- **Examples:** Include usage examples for complex functions

```python
async def generate_learning_objectives(
    content: str, 
    topic_id: int, 
    config: GenerationConfig
) -> List[LearningObjective]:
    """Generate learning objectives from educational content.
    
    Args:
        content: The educational text content to process
        topic_id: ID of the target curriculum topic
        config: Generation configuration parameters
        
    Returns:
        List of generated learning objectives with quality scores
        
    Raises:
        LLMServiceError: If the LLM API fails
        ValidationError: If the generated content is invalid
        
    Example:
        >>> config = GenerationConfig(max_objectives=5)
        >>> objectives = await generate_learning_objectives(
        ...     "Physics content about forces", 
        ...     topic_id=123, 
        ...     config=config
        ... )
    """
```

### **API Documentation**
- **OpenAPI schemas:** Automatically generated from Pydantic models
- **Example requests/responses:** Include in API documentation
- **Error responses:** Document all possible error conditions

## Development Workflow

### **Git Workflow**
- **Feature branches:** Create feature branches from `develop`
- **Commit messages:** Use conventional commit format
- **Pull requests:** Required for all changes to `main` and `develop`

### **Code Review Standards**
- **All code reviewed:** No direct pushes to protected branches
- **Review checklist:** Security, performance, maintainability, testing
- **Automated checks:** All CI checks must pass before merge

This document serves as the definitive guide for development standards. All AI agents and human developers must follow these patterns to ensure code consistency and maintainability.