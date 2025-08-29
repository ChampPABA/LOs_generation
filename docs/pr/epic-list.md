# Epic List

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
