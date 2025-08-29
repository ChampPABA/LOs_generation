# LOs_Generation Product Requirements Document (PRD)

## Goals and Background Context

### Goals
• Establish LO database covering TBAT Physics subject within 2-week delivery timeline (MVP scope reduction)
• Create robust RAG pipeline that transforms chapter-level content into structured, Bloom's taxonomy-aligned Learning Objectives
• Build scalable foundation system supporting future adaptive learning integration for personalized product recommendations
• Enable systematic, consistent LO generation replacing manual interpretation of broad blueprint topics
• Achieve 80%+ automated LO quality score using relevance and clarity metrics (revised from TBAT validation)

### Background Context

Thai university entrance exams (TBAT) provide only high-level content blueprints without granular Learning Objectives, creating critical gaps in exam question consistency and adaptive learning capabilities. Current blueprint topics like "Kinematics and forces" lack specific, measurable learning outcomes, forcing question writers to rely on personal interpretation. This inconsistency prevents systematic competency assessment and limits the existing profitable education business from offering data-driven personalized recommendations.

Phase 1 addresses this foundational gap by implementing a RAG (Retrieval-Augmented Generation) pipeline that systematically processes standard educational textbooks (Physics focus for MVP) to generate detailed, exam-aligned Learning Objectives. The system uses simplified chunking strategy with basic retrieval and multi-language model support (English-first approach) to ensure comprehensive coverage and quality output.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-27 | v1.0 | Initial PRD creation from Project Brief | PM John |
| 2025-01-28 | v2.0 | Scope reduction and timeline adjustment per Sprint Change Proposal | PO Sarah |

## Requirements

### Functional Requirements

**Content Processing & Ingestion:**
**FR1:** System shall process TBAT Physics blueprint format with flexible parser (other exam formats deferred to post-MVP)
**FR2:** PDF ingestion pipeline shall use PyMuPDF (fitz) to extract text content (image processing deferred to post-MVP)
**FR3:** Simplified chunking implementation shall create fixed-size chunks with overlap for basic context preservation (Late Chunking deferred to post-MVP)
**FR4:** System shall generate unique chunk_id (hash-based) and store chunks in PostgreSQL chunks table
**FR5:** Vector indexing preparation for chunks using basic RecursiveCharacterTextSplitter

**RAG Pipeline & Search:**
**FR6:** Vector indexing shall store chunks in Qdrant with basic similarity search capability
**FR7:** Basic retrieval system using vector similarity search only (hybrid search deferred to post-MVP)
**FR8:** Simple query processing using direct text input (RAG Fusion query expansion deferred to post-MVP)
**FR9:** Basic vector similarity retrieval from Qdrant without reranking (reranking pipeline deferred to post-MVP)
**FR10:** Direct chunk retrieval for LO generation context (Small-to-Big retrieval simplified)

**LO Generation & Processing:**
**FR11:** LO Generation Engine shall use retrieved chunks as context for Gemini 2.5 Pro + Pydantic AI validation
**FR12:** Generated LOs shall include Bloom's taxonomy classification, basic topic mapping, and source traceability
**FR13:** Async processing system shall use Celery + Redis for background LO generation with basic job queue management
**FR14:** Configuration management shall externalize prompts, model settings, RAG parameters via YAML files with version control

**API & Integration:**
**FR15:** RESTful API shall provide endpoints: /generate-los, /health, /status/{job_id} for testing and integration
**FR16:** Basic job processing shall accept direct content input (cron job scanning deferred to post-MVP)
**FR17:** Job status tracking shall provide basic progress updates and result retrieval via job_id

**Validation & Storage:**
**FR18:** LO Validation shall use automated quality scoring for Relevance, Clarity, Structure, Length (95% TBAT validation deferred to post-MVP)
**FR19:** Storage logic shall handle all generated LOs with basic quality scores (human review queue deferred to post-MVP)
**FR20:** Data versioning shall track source_data_version and prompt_version for complete traceability
**FR21:** Basic rate limiting using simple request throttling (token bucket algorithm deferred to post-MVP)
**FR22:** Basic API usage logging (detailed analytics deferred to post-MVP)

### Non-Functional Requirements

**Performance & Scalability:**
**NFR1:** API response time for status queries shall be <1 second under normal load (relaxed from 500ms)
**NFR2:** LO generation processing shall complete <4 hours per Physics subject for MVP (relaxed from 2 hours)
**NFR3:** System shall support 2-3 concurrent parallel generation jobs without performance degradation (reduced from 5)
**NFR4:** Database shall handle ~50k chunks for MVP Physics subject with vector dimensions of 1024 (bge-m3)

**Quality & Reliability:**
**NFR5:** Generated LOs shall achieve 80%+ automated quality score using relevance and clarity metrics (revised from 95% TBAT validation)
**NFR6:** Basic failure handling with simple retry mechanism (advanced tenacity and DLQ deferred to post-MVP)
**NFR7:** Optional Langfuse integration for LLM observability (comprehensive observability deferred to post-MVP)
**NFR8:** System shall maintain basic data integrity through proper transaction handling

**Technical Architecture:**
**NFR9:** Database schema shall support normalized relationships (learning_objectives, chunks, textbooks, topics, bloom_levels - simplified schema)
**NFR10:** Vector storage shall use Qdrant with basic indexing strategy for educational content retrieval
**NFR11:** Configuration shall be version-controlled with Git for YAML configurations (DVC deferred to post-MVP)
**NFR12:** System shall be designed with clean architecture supporting future scaling without major refactoring

**Testing & Quality Assurance:**
**NFR13:** All new functionality shall have unit tests with minimum 60% code coverage for MVP (80% deferred to post-MVP)
**NFR14:** Integration tests shall validate basic end-to-end pipeline (ingestion → retrieval → generation) for core workflow
**NFR15:** API endpoints shall have basic testing covering success cases and primary error scenarios
**NFR16:** LO generation quality shall be validated through automated scoring against defined criteria
**NFR17:** Basic performance testing to verify NFR1-NFR4 requirements before release
**NFR18:** Database operations shall have basic transaction testing ensuring data consistency
**NFR19:** English-first processing with basic multi-language support (advanced Thai processing deferred to post-MVP)

## Technical Assumptions

### Repository Structure: Monorepo
Single repository containing all components (RAG pipeline, API layer, data models, configurations) for simplified development, testing, and deployment coordination during MVP phase.

### Service Architecture
**Monolith with Async Processing**: Core application as single deployable unit with background task processing via Celery workers. This approach balances development speed with scalability, allowing future microservices migration without immediate complexity overhead.

### Testing Requirements
**Basic Testing Pyramid**: Essential testing strategy including unit tests (60% coverage), integration tests (basic end-to-end pipeline validation), and automated quality scoring. Manual validation deferred to post-MVP.

### Additional Technical Assumptions and Requests

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

## Epic List

The following epics represent the MVP implementation sequence for the LO Generation Pipeline. Each epic delivers significant, end-to-end functionality that provides tangible value and builds upon previous work following agile best practices.

**Epic 1: Foundation & Core Infrastructure (Days 1-4)**
Establish project setup, complete database schemas, basic API framework, and essential services (PostgreSQL, Qdrant, Redis) while delivering a working health-check endpoint and complete services architecture.

**Epic 2: Simplified RAG Pipeline (Days 5-8)**
Implement basic chunking strategy, vector indexing in Qdrant, and simple retrieval system providing a functional content processing and retrieval foundation with English-first approach.

**Epic 3: MVP LO Generation Engine (Days 9-12)**
Build the core LO generation workflow including basic retrieval, Gemini API integration, and Pydantic AI validation delivering the primary business functionality with automated quality scoring.

**Epic 4: Integration & Deployment (Days 13-14)**
Implement API endpoints, basic testing, Docker deployment, and end-to-end validation ensuring production-ready MVP with complete documentation.

**Post-MVP Epics (Future Phases):**
- Advanced RAG features (Late Chunking, RAG Fusion, Reranking)
- Multi-language optimization and Thai language processing
- Human review interface and advanced validation
- Multi-exam support (PMAT, GAT, PAT)
- Production monitoring and advanced analytics

**Rationale:** This epic structure prioritizes core functionality delivery within realistic 14-day timeline. Epic 1 establishes complete foundation, Epic 2 enables content processing, Epic 3 delivers core business value, and Epic 4 ensures deployable system. The sequence allows for incremental delivery and testing at each stage, critical for MVP success. Advanced features are explicitly deferred to maintain focus on achievable, working system.

## MVP Success Criteria (Revised)

### Core Deliverables
- ✅ Process 1 Physics textbook chapter successfully
- ✅ Generate 50+ learning objectives with Bloom's taxonomy classification
- ✅ Store results in database with proper relationships and traceability
- ✅ API endpoints functional with <1 second response time
- ✅ End-to-end pipeline completes without errors
- ✅ Docker deployment works locally with health checks
- ✅ Automated quality scoring achieves 80%+ average

### Quality Metrics
- **Coverage**: Complete TBAT Physics "Kinematics and Forces" topic coverage
- **Quality**: 80%+ average score on automated metrics (relevance, clarity, structure)
- **Performance**: <4 hours processing time for complete subject
- **Reliability**: 95%+ success rate for pipeline execution
- **Testability**: 60%+ code coverage with integration tests

### Post-MVP Roadmap
**Phase 2 (Weeks 3-4):** Multi-subject support, advanced validation, TBAT question alignment  
**Phase 3 (Weeks 5-6):** Multi-language optimization, human review interface, production monitoring  
**Phase 4 (Weeks 7-8):** Cross-exam support, analytics dashboard, performance optimization

---

*This PRD reflects the approved Sprint Change Proposal adjustments for realistic MVP delivery within 14-day timeline while maintaining core value proposition and building foundation for future expansion.*