# Requirements

## Functional Requirements

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

## Non-Functional Requirements

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
