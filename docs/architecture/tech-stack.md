# Technology Stack - LOs Generation System

## Core Technology Decisions

This document outlines the definitive technology stack for the Learning Objectives Generation system. All development must use these exact technologies and versions.

## Backend Stack

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Python** | 3.10+ | Core language | Excellent AI/ML ecosystem, mature async support |
| **FastAPI** | 0.104.1+ | Web framework | High performance, automatic docs, async support |
| **SQLAlchemy** | 2.0.23+ | ORM | Mature async ORM, excellent migration support |
| **Alembic** | 1.13.1+ | Database migrations | Standard SQLAlchemy migration tool |
| **PostgreSQL** | 15+ | Primary database | ACID compliance, JSON support, performance |
| **Redis** | 7.0+ | Cache and queue | High performance, reliable for Celery |
| **Celery** | 5.3.4+ | Task queue | Mature async processing, Redis integration |

## AI/ML Stack

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Google Generative AI** | 0.3.2+ | LLM integration | Cost-effective, multilingual, reliable |
| **Pydantic AI** | 0.0.13+ | LLM validation | Type-safe outputs, error handling |
| **Qdrant** | 1.7.0+ | Vector database | Purpose-built for similarity search |
| **sentence-transformers** | 2.2.2+ | Text embeddings | bge-m3 multilingual support |
| **PyMuPDF** | 1.23.8+ | PDF processing | Fast, reliable text extraction |
| **LangChain Text Splitters** | 0.0.1+ | Text chunking | Intelligent segmentation |

## OCR & Document Processing

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **pytesseract** | 0.3.10+ | OCR Python wrapper | Industry-standard OCR integration |
| **Tesseract OCR Engine** | 5.3.0+ | OCR engine | High-accuracy text recognition |
| **Pillow (PIL)** | 10.0.1+ | Image processing | OCR preprocessing and optimization |
| **pdf2image** | 1.16.3+ | PDF to image conversion | Convert PDF pages to images for OCR |
| **opencv-python** | 4.8.1+ | Advanced image processing | Image enhancement for better OCR results |

## Development Tools

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Poetry** | 1.6+ | Dependency management | Modern Python packaging |
| **Black** | 23.11.0+ | Code formatting | Consistent code style |
| **Flake8** | 6.1.0+ | Linting | Code quality enforcement |
| **MyPy** | 1.7.1+ | Type checking | Static type safety |
| **pytest** | 7.4.3+ | Testing framework | Comprehensive test ecosystem |
| **pytest-asyncio** | 0.21.1+ | Async testing | Async test support |

## Infrastructure

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Docker** | Latest | Containerization | Consistent environments |
| **Docker Compose** | Latest | Local orchestration | Multi-service development |
| **Uvicorn** | 0.24.0+ | ASGI server | High-performance Python server |

## Configuration Management

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **PyYAML** | 6.0.1+ | Configuration files | Human-readable, version controlled |
| **python-dotenv** | 1.0.0+ | Environment variables | Local development support |
| **Pydantic Settings** | Built-in | Config validation | Type-safe configuration |

## Security & Authentication

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **python-jose** | 3.3.0+ | JWT handling | Token authentication |
| **passlib** | 1.7.4+ | Password hashing | Secure password handling |
| **slowapi** | 0.1.9+ | Rate limiting | API protection |

## Monitoring & Observability

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **structlog** | 23.2.0+ | Structured logging | Machine-readable logs |
| **Langfuse** | 2.40.0+ | LLM observability | AI operation tracking |
| **prometheus-client** | 0.19.0+ | Metrics collection | Standard metrics format |

## HTTP & Networking

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **httpx** | 0.25.2+ | HTTP client | Modern async HTTP client |
| **aiofiles** | 23.2.0+ | Async file I/O | Non-blocking file operations |

## Data Processing

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **markdownify** | 0.11.6+ | HTML to Markdown | Content format conversion |
| **tenacity** | 8.2.3+ | Retry logic | Resilient external API calls |

## Version Pinning Strategy

### Production Dependencies
- **Exact versions** for critical components (FastAPI, SQLAlchemy, PostgreSQL)
- **Minor version pinning** for AI/ML libraries to ensure model compatibility
- **Patch level updates** allowed for utilities and development tools

### Development Dependencies  
- **Latest compatible versions** for development tools
- **Flexible versioning** for testing and linting tools
- **Regular updates** encouraged for security patches

## Upgrade Policy

### Major Version Updates
- **Planned updates** during maintenance windows
- **Comprehensive testing** in staging environment
- **Rollback plan** documented and tested

### Security Updates
- **Immediate updates** for critical security vulnerabilities
- **Monthly review** of security advisories
- **Automated scanning** with dependency-check tools

### AI/ML Model Updates
- **Careful evaluation** of new model versions
- **A/B testing** for quality impact assessment  
- **Prompt compatibility** verification required

## System Dependencies

### External System Requirements
- **Tesseract OCR Engine**: Must be installed at system level
  - Ubuntu/Debian: `apt-get install tesseract-ocr tesseract-ocr-tha tesseract-ocr-eng`
  - macOS: `brew install tesseract`
  - Windows: Download from GitHub releases
- **Language Packs**: Thai and English language models required
  - Thai: `tesseract-ocr-tha` for Thai language support
  - English: `tesseract-ocr-eng` for English text recognition

### Docker Configuration
```dockerfile
# OCR system dependencies in Dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tha \
    tesseract-ocr-eng \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*
```

## Environment-Specific Variations

### Development
- **Local models** (Ollama) allowed for cost optimization
- **Debug logging** enabled by default
- **Hot reloading** for rapid development
- **OCR debugging** with image output enabled

### Staging
- **Production-identical stack** for realistic testing
- **Performance monitoring** enabled
- **Synthetic data** for testing
- **OCR performance profiling** enabled

### Production
- **Optimized configurations** for performance
- **Monitoring and alerting** fully enabled
- **High availability** configurations
- **OCR caching** for processed documents

## Deprecated Technologies

The following technologies are **not** to be used in new development:

- **Django** - FastAPI chosen for API-first architecture
- **Flask** - FastAPI provides better async and documentation support
- **SQLModel** - SQLAlchemy 2.0 provides equivalent functionality
- **OpenAI API** - Google Gemini chosen for cost and multilingual support
- **Pinecone** - Qdrant chosen for self-hosted vector storage

## Technology Evaluation Process

### New Technology Adoption
1. **Business case** - Clear benefit over current solution
2. **Proof of concept** - Small-scale implementation and testing
3. **Team review** - Architecture and development team approval
4. **Migration plan** - Clear path from current to new technology
5. **Training plan** - Team upskilling requirements

### Technology Retirement
1. **Deprecation notice** - 6-month advance warning
2. **Migration timeline** - Phased replacement plan
3. **Documentation update** - Reflect new technology choices
4. **Team communication** - Clear communication to all stakeholders

This technology stack provides a solid foundation for the Learning Objectives Generation system while maintaining flexibility for future evolution.