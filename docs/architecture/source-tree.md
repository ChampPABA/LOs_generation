# Source Tree Organization - LOs Generation System

## Directory Structure Overview

```
LOs_Generation/
├── src/                    # Application source code
├── tests/                  # Test suite
├── configs/                # Configuration files
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── migrations/             # Database migrations
├── docker/                 # Container configurations
├── monitoring/             # Observability configs
└── .github/               # CI/CD workflows
```

## Source Code Organization (`src/`)

The `src/` directory follows a layered architecture pattern with clear separation of concerns:

### API Layer (`src/api/`)
**Purpose:** HTTP request handling, routing, and response formatting
**Dependencies:** Services layer only, no direct model or database access

```
src/api/v1/
├── router.py              # Main router aggregation
├── endpoints/             # Feature-specific endpoints
│   ├── health.py         # System health checks
│   ├── jobs.py           # Job status and results
│   ├── generation.py     # LO generation endpoints
│   └── learning_objectives.py  # CRUD operations
└── middleware/           # Cross-cutting concerns
    ├── auth.py          # Authentication
    ├── rate_limit.py    # Rate limiting
    └── error_handler.py # Global error handling
```

**Key principles:**
- Controllers are thin, delegate business logic to services
- All endpoints use dependency injection for database sessions
- Response models defined with Pydantic schemas

### Core Configuration (`src/core/`)
**Purpose:** Application-wide configuration, security, and shared utilities
**Dependencies:** None (foundation layer)

```
src/core/
├── config.py             # Environment-based configuration
├── security.py          # Authentication utilities
└── logging.py           # Structured logging setup
```

**Key principles:**
- Centralized configuration management
- Type-safe configuration with Pydantic
- Environment variable abstraction

### Database Layer (`src/database/`)
**Purpose:** Data persistence, connection management, and repository pattern
**Dependencies:** Models only

```
src/database/
├── connection.py         # Async session management
└── repositories/         # Data access objects
    ├── base.py          # Generic repository base class
    ├── learning_objectives.py
    ├── chunks.py
    └── jobs.py
```

**Key principles:**
- Repository pattern abstracts database operations
- Async session management throughout
- Generic base repository for common CRUD operations

### Domain Models (`src/models/`)
**Purpose:** SQLAlchemy models representing business entities
**Dependencies:** None (foundation layer)

```
src/models/
├── base.py              # Base model with common fields
├── learning_objectives.py
├── chunks.py            # Parent/child chunk models
├── exam_types.py       # Taxonomy hierarchy
├── jobs.py             # Background job tracking
└── api_keys.py         # Authentication
```

**Key principles:**
- Rich domain models with behavior
- Proper relationships and constraints
- Database-agnostic where possible

### Request/Response Schemas (`src/schemas/`)
**Purpose:** API contract definition and validation
**Dependencies:** Models for field definitions

```
src/schemas/
├── requests.py          # API request validation
├── responses.py         # API response formatting
└── internal.py          # Service-to-service DTOs
```

**Key principles:**
- Separate schemas from models for API flexibility
- Comprehensive validation rules
- Clear separation of external vs internal schemas

### Business Logic (`src/services/`)
**Purpose:** Core business logic, orchestration, and external integrations
**Dependencies:** Repositories, external services

```
src/services/
├── base.py              # Base service class
├── health_service.py    # System health monitoring
├── generation_service.py # Main LO generation orchestration
├── processing_service.py # Content processing pipeline
├── document_analyzer.py # PDF type detection (native vs scanned)
├── ocr_service.py      # OCR processing with Tesseract
├── chunking_service.py # Hybrid chunking coordinator
├── structural_chunker.py # Native PDF chunking (existing logic)
├── agentic_chunker.py  # AI-powered OCR content chunking
├── vector_service.py    # Embedding and similarity search
├── llm_service.py       # LLM API integration
└── validation_service.py # Quality scoring and validation
```

**Key principles:**
- Single responsibility per service
- Dependency injection for testability
- Async operations throughout

### Background Tasks (`src/tasks/`)
**Purpose:** Celery task definitions for async processing
**Dependencies:** Services layer

```
src/tasks/
├── celery_app.py        # Celery configuration and app setup
├── generation.py        # LO generation workflow tasks
├── processing.py        # Content processing tasks
└── monitoring.py        # Health checks and cleanup
```

**Key principles:**
- Thin task wrappers around service methods
- Proper error handling and retry logic
- Progress tracking and status updates

### Utilities (`src/utils/`)
**Purpose:** Shared utilities and helper functions
**Dependencies:** None (foundation layer)

```
src/utils/
├── text_processing.py   # Text manipulation utilities
├── file_handling.py     # File I/O operations
├── validation.py        # Custom validation functions
└── exceptions.py        # Domain-specific exceptions
```

**Key principles:**
- Pure functions where possible
- Domain-specific utility grouping
- Comprehensive error handling

## Test Organization (`tests/`)

Test organization mirrors source structure with additional categorization:

```
tests/
├── conftest.py          # Shared test configuration
├── fixtures/            # Test data and mock objects
├── unit/               # Fast, isolated tests
│   ├── test_services/
│   ├── test_models/
│   └── test_utils/
├── integration/        # Database and external service tests
│   ├── test_repositories/
│   ├── test_api_endpoints.py
│   └── test_database_operations.py
└── e2e/               # Full system tests
    └── test_generation_pipeline.py
```

**Testing principles:**
- Fast unit tests with mocked dependencies
- Integration tests against real database
- End-to-end tests for critical user journeys
- Fixtures for consistent test data

## Configuration Management (`configs/`)

External configuration files organized by purpose:

```
configs/
├── models.yaml          # AI model configurations
├── prompts.yaml         # LLM prompt templates
├── processing.yaml      # Content processing parameters
└── environments/        # Environment-specific overrides
    ├── local.yaml
    ├── staging.yaml
    └── production.yaml
```

**Configuration principles:**
- Environment-specific overrides
- Version controlled prompt templates
- Type-safe loading through Pydantic

## Documentation (`docs/`)

Comprehensive documentation structure:

```
docs/
├── README.md           # Project overview
├── architecture/       # Technical architecture docs
│   ├── architecture.md # This document
│   ├── coding-standards.md
│   ├── tech-stack.md
│   └── source-tree.md  # This file
├── api/               # API documentation
├── deployment/        # Deployment guides
├── development/       # Developer guides
└── stories/           # Product requirements
```

## Import and Dependency Rules

### Allowed Dependencies
```
API Layer → Services Layer → Repository Layer → Models
       ↓         ↓              ↓
   Schemas    Utilities      Database
```

### Forbidden Dependencies
- **Models cannot import services** - Keep models lean
- **Repositories cannot import services** - Avoid circular dependencies  
- **Core cannot import application layers** - Maintain foundation independence
- **Tests cannot import production code beyond the unit under test** - Maintain test isolation

### Import Style
```python
# ✅ Good - Explicit imports
from src.services.generation_service import GenerationService
from src.models.learning_objectives import LearningObjective

# ❌ Bad - Star imports
from src.services import *
from src.models import *
```

## File Naming Conventions

### Python Files
- **Snake case:** `generation_service.py`, `learning_objectives.py`
- **Descriptive names:** File name should clearly indicate contents
- **Consistent suffixes:** `_service.py`, `_repository.py`, `_test.py`

### Configuration Files
- **Lowercase with hyphens:** `docker-compose.yml`
- **Extension indicates format:** `.yaml` for YAML, `.json` for JSON
- **Environment prefixes:** `staging.yaml`, `production.yaml`

### Documentation Files
- **Kebab case:** `coding-standards.md`, `api-reference.md`
- **Clear hierarchy:** Directory structure reflects information architecture

## Module Organization Best Practices

### Service Modules
- **One primary class per file:** `GenerationService` in `generation_service.py`
- **Related utilities in same module:** Helper functions near main class
- **Clear public interface:** Use `__all__` to define public API

### Model Modules
- **Related models together:** `Parent/ChildChunk` in `chunks.py`
- **Logical grouping:** Group by business domain, not technical concerns
- **Relationship clarity:** Related models in same or adjacent files

### Configuration Loading
```python
# Pattern for loading configuration
from src.core.config import settings
from configs.models import load_model_config

# Always validate configuration at startup
model_config = load_model_config(settings.environment)
```

This source tree organization provides a solid foundation for maintainable, scalable Python development while supporting the specific requirements of the LO generation system.