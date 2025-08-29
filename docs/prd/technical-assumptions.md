# Technical Assumptions

## Repository Structure: Monorepo
Single repository containing all components (RAG pipeline, API layer, data models, configurations) for simplified development, testing, and deployment coordination during MVP phase.

## Service Architecture
**Monolith with Async Processing**: Core application as single deployable unit with background task processing via Celery workers. This approach balances development speed with scalability, allowing future microservices migration without immediate complexity overhead.

## Testing Requirements
**Basic Testing Pyramid**: Essential testing strategy including unit tests (60% coverage), integration tests (basic end-to-end pipeline validation), and automated quality scoring. Manual validation deferred to post-MVP.

## Additional Technical Assumptions and Requests

**Local Development Infrastructure:**
- PostgreSQL, Qdrant, Redis running locally via Docker Compose for development speed and cost optimization
- Ollama hosting local models (Qwen3 series) to reduce API dependencies
- Cloud-ready architecture design for future scaling without major refactoring

**LLM Integration Strategy:**
- Primary reliance on Gemini 2.5 Pro/Flash APIs for text generation and validation
- Basic fallback mechanisms for API rate limiting and service interruptions
- Cost optimization through appropriate model selection (Pro for complex tasks, Flash for lighter operations)

**Language Processing (MVP Scope):**
- bge-m3 embedding model for basic multilingual content processing
- English-first approach with basic Thai support (advanced Thai optimization deferred to post-MVP)
- Simple mixed-language content handling

**Data Pipeline Assumptions:**
- Standard Physics textbooks provide sufficient coverage for TBAT Physics topic requirements
- Simple chunking strategy will provide adequate context while enabling basic retrieval
- Direct chunk relationships will effectively support LO generation

**Quality Assurance Framework (MVP):**
- Generated LOs can be meaningfully scored using automated quality metrics
- 80% quality score is achievable through proper prompt engineering and context retrieval
- Manual validation and human review workflow deferred to post-MVP

**Scalability and Future-Proofing:**
- Database schema design accommodates multi-exam expansion without major migration
- Configuration-driven approach enables rapid adaptation to new exam formats and requirements
- Basic observability provides insights for continuous improvement
