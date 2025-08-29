# Project Brief: Phase 1 - Pipeline for LO Generation

## Executive Summary

**Phase 1 MVP: Learning Objectives Generation Pipeline** is a proof-of-concept system that transforms TBAT Physics content into structured, Bloom's Taxonomy-aligned Learning Objectives using a simplified RAG (Retrieval-Augmented Generation) pipeline. This MVP addresses the critical gap where **TBAT entrance exams provide only chapter-level Physics content without defined Learning Objectives**, making quality question generation inconsistent. The primary goal is to establish a working foundation system demonstrating LO generation capability that will enable future expansion to create an Adaptive Learning System for personalized product recommendations in an existing profitable education business (camps/courses). Target users include internal curriculum teams and the MVP will process **Physics textbook content** to generate standardized, quality-scored Learning Objectives that serve as proof of concept for automated exam generation, ultimately supporting high school students preparing for TBAT Physics.

## Problem Statement

### Current State and Pain Points

The Thai university entrance exam system, specifically **TBAT (Thai Basic Aptitude Test)**, operates with only high-level content blueprints that lack granular Learning Objectives. Current blueprint provides broad topics like "Kinematics and forces" or "Atomic structure" without specifying what students should actually know, understand, or be able to do. This creates several critical problems:

**For Exam Creation:**
- Inconsistent question difficulty and coverage across exam sessions
- No systematic way to ensure comprehensive topic coverage  
- Question writers rely on personal interpretation of broad topics
- Difficult to create parallel forms with equivalent difficulty

**For Adaptive Learning Systems:**
- Cannot accurately assess specific knowledge gaps
- Unable to provide targeted recommendations 
- No systematic way to measure learning progress
- Impossible to create personalized learning paths based on precise competency mapping

**Business Impact:**
- Current education business (camps/courses) cannot offer data-driven personalization
- Product recommendations are based on general performance rather than specific learning needs
- Missing opportunity to scale adaptive learning products for Thailand's competitive exam market

### Why Existing Solutions Fall Short

- Manual LO creation is time-intensive and inconsistent across subjects
- Generic international LOs don't align with Thai exam specifications  
- Existing educational platforms use broad categorizations rather than detailed competency mapping
- No systematic approach to transform textbook content into exam-aligned learning objectives

## Proposed Solution

### Core Concept and Approach

**Phase 1: Learning Objectives Generation Pipeline** is a RAG (Retrieval-Augmented Generation) system that systematically transforms TBAT blueprint topics into detailed, Bloom's taxonomy-aligned Learning Objectives by processing standard educational textbooks.

**The Solution Architecture:**

**Input Processing (MVP Scope):**
- TBAT Physics content blueprints (Kinematics and Forces focus)
- Standard Physics textbooks (focused content extraction)
- Automated content extraction and chunking using simplified fixed-size strategy

**Core RAG Pipeline:**
- **Phase 1.A**: Basic Ingestion & Indexing - Transform Physics textbook into searchable vector database
- **Phase 1.B**: MVP LO Generation - Use basic retrieval to generate Physics learning objectives
- **Phase 1.C**: Automated Scoring & Storage - Quality scoring and structured storage for validation

**Output (MVP):**
- Structured Learning Objectives database for TBAT Physics (50+ LOs)
- Each LO tagged with Bloom's taxonomy level, basic topic mapping, and source traceability
- Working prototype demonstrating automated LO generation capability

### Key Differentiators

**Systematic Blueprint Alignment:** Unlike generic LO libraries, this system specifically maps to Thai exam requirements while maintaining international educational standards.

**Textbook-Grounded Generation:** LOs are derived from actual educational content rather than abstract topic names, ensuring practical applicability and comprehensive coverage.

**Built for Scale:** Foundation system designed to support multiple exam types (TBAT, PMAT, etc.) and enable downstream adaptive learning applications.

### Why This Solution Will Succeed

- **Addresses Root Cause**: Solves the fundamental gap between broad blueprints and specific assessments
- **Leverages Proven Technology**: RAG systems have demonstrated success in educational content processing
- **Business-Aligned**: Directly enables the adaptive learning system needed for personalized product recommendations
- **Scalable Foundation**: Once built, can rapidly extend to other Thai entrance exams with existing LOs

## Target Users

### Primary User Segment: Internal Curriculum Development Team

**Demographic/Role Profile:**
- Educational content creators and curriculum designers within the existing education business
- Team members responsible for creating and maintaining exam content for camps/courses
- Technical staff who will integrate LO database with downstream systems

**Current Behaviors and Workflows:**
- Manually analyze TBAT blueprints to create course content and practice questions
- Spend significant time interpreting broad topic descriptions like "Kinematics and forces" 
- Create exam content based on personal understanding of topic scope and difficulty
- Struggle to ensure consistent coverage across different subjects and difficulty levels

**Specific Needs and Pain Points:**
- Need systematic way to break down **any exam topics without existing LOs** into teachable/assessable components
- Require consistent framework for content creation across **multiple exam types** (TBAT, PMAT, and others)
- Need traceability between textbook content and exam requirements **for exams lacking standardized LOs**
- Want to reduce manual interpretation time while improving content quality
- **Key insight**: Skip LO generation entirely when exams already have published LOs - directly import existing LOs into database

**Goals They're Trying to Achieve:**
- Create comprehensive, well-structured learning objectives that align with **any Thai entrance exam requirements** (not just TBAT)
- Build foundation for data-driven adaptive learning system **across all exam types**
- Scale content creation efficiency while maintaining educational quality
- Enable systematic approach to exam question generation in future phases **for all supported exams**

### Secondary User Segment: Business Intelligence/Product Team

**Demographic/Role Profile:**
- Product managers and data analysts responsible for adaptive learning system development
- Business stakeholders who need to understand learning competency data for product recommendations

**Current Behaviors and Workflows:**
- Currently rely on broad performance metrics rather than granular learning analytics
- Need to make product recommendations based on limited assessment data
- Plan future adaptive learning features without detailed competency framework

**Specific Needs and Pain Points:**
- Need structured learning objective data to build sophisticated recommendation algorithms
- Require clear mapping between student performance and specific knowledge gaps
- Want foundation for personalized learning path creation

**Goals They're Trying to Achieve:**
- Enable data-driven personalization for existing education products
- Build comprehensive learner profiles based on specific competencies
- Create scalable framework for adaptive learning across multiple exam types

## Goals & Success Metrics

### Business Objectives

- **Establish working LO database for TBAT Physics subject** → **Phase 1 MVP: 14 days completion**
- **Demonstrate automated LO generation capability** reducing manual content creation time for Physics topics
- **Create foundation system enabling future adaptive learning system expansion** with proof-of-concept competency tracking
- **Validate technical approach supporting future scale** to additional exam types and subjects
- **Build working prototype for automated exam generation pipeline** demonstrating LO-aligned generation capability → **Complete exam generation system: Future phase post-MVP**

### User Success Metrics

- **LO Generation Efficiency**: Average time to generate complete LO set for one exam subject reduced from manual estimation to <2 hours automated processing
- **Content Quality Consistency**: 95%+ of generated LOs pass validation against actual exam questions during testing phase
- **Coverage Completeness**: 100% of blueprint topics covered by specific, measurable learning objectives
- **Cross-Exam Standardization**: Consistent Bloom's taxonomy classification across all exam types in database
- **Traceability Achievement**: Every LO linked to source textbook content and target exam specification

### Key Performance Indicators (KPIs)

- **LO Database Growth**: Number of learning objectives by exam type and subject area
- **Generation vs Import Ratio**: Percentage of LOs generated vs imported from existing sources  
- **Validation Success Rate**: Percentage of generated LOs that successfully validate against real exam questions
- **System Utilization**: Frequency of LO database queries for downstream applications (adaptive learning, question generation)
- **Content Quality Score**: Expert review ratings of generated LO accuracy and educational value
- **Processing Efficiency**: Average time per LO generation and total system throughput

## MVP Scope

### Core Features (Must Have)

- **TBAT Blueprint Processing**: System can parse TBAT content blueprints and map topics to textbook sections for Physics, Chemistry, Biology

- **Late Chunking RAG Implementation**: 
  - **Parent Chunks**: Large, contextually complete sections stored in PostgreSQL
  - **Child Chunks**: Sentence-level chunks with vectors stored in Qdrant
  - **Small-to-Big Retrieval**: Search child chunks for precision, retrieve parent chunks for context

- **RAG Fusion + Reranking Pipeline**:
  - **Query Expansion**: Multiple query variations for better retrieval coverage  
  - **Parallel Retrieval**: Both vector similarity (Qdrant) and keyword search capabilities
  - **Reranking**: Cross-encoder model (Qwen3-Reranker for English, bge-reranker-v2-m3 for Thai)

- **Vector Database Integration**: Qdrant setup with proper indexing strategy for educational content retrieval

- **LO Generation Engine**: Generate specific, measurable learning objectives using retrieved parent chunks with Bloom's taxonomy classification via Gemini 2.5 Pro + Pydantic AI

- **Basic API Endpoints**: RESTful endpoints for testing and integration (`/generate-los`, `/health`, `/status/{job_id}`) accessible via Postman for development validation

- **Async Processing**: Celery + Redis for background task processing with basic failure handling

- **Database Storage**: PostgreSQL schema with proper relationships (learning_objectives, parent_chunks, textbooks, etc.)

- **Configuration Management**: YAML-based configuration for prompts, model settings, RAG parameters, and processing settings

### Out of Scope for MVP

- Human review interface/workflow
- Advanced validation against actual exam questions
- Multiple exam type support (PMAT, others)
- Performance optimization and scaling features
- Monitoring dashboards and analytics  
- Integration with existing business systems

### MVP Success Criteria

**Functional Success**: System generates complete set of learning objectives for TBAT Physics "Kinematics and Forces" topic (50+ LOs) within 14-day development timeline.

**Quality Success**: Generated LOs achieve 80%+ automated quality score and are properly classified by Bloom's taxonomy levels with clear, actionable learning outcomes.

**Technical Success**: End-to-end pipeline runs successfully from Physics textbook input to structured LO database output with 95%+ reliability and <4 hour processing time.

## Post-MVP Vision

### Phase 2 Features (Month 2-3)

**AI-Powered LO Validation System:**
- **AI Agent Validator** using secondary LLM model for automated quality assessment
- Validation workflow against actual TBAT exam questions using AI comparison
- **Self-improving system** through AI validation results
- **Automated processing** with confidence scores

**Human-in-the-Loop Exam Generation System:**
- **Question Validation Platform**: Web interface for human reviewers to assess generated exam questions
- **Scoring & Payment System**: Reviewers submit quality scores and appropriateness ratings per question
- **Reviewer Management**: Track validation workload, calculate compensation, payment processing
- **Admin Dashboard**: Monitor reviewer productivity, quality metrics, payment tracking
- **Quality Assurance**: Multi-reviewer consensus, reviewer performance analytics

**Multi-Exam Support Expansion:**  
- PMAT learning objectives generation
- Additional Thai entrance exams (GAT, PAT, etc.)
- Automated detection of exams with existing LOs vs those needing generation
- Cross-exam LO relationship mapping

### Long-term Vision (6-12 months)

**Adaptive Learning Integration:**
- Real-time competency assessment based on LO mastery
- Personalized learning path recommendations
- Integration with existing education business products
- Student progress analytics and reporting

**Advanced RAG Enhancements:**
- Multi-modal content processing (images, diagrams from textbooks)
- Cross-reference detection between subjects
- Automated curriculum gap analysis
- Content freshness tracking and updates

**Business Intelligence Platform:**
- Learning analytics dashboard for educators
- Market intelligence on Thai entrance exam trends
- Performance benchmarking across exam types
- ROI tracking for adaptive learning recommendations

### Expansion Opportunities

**Geographic Expansion:**
- Adaptation to other Southeast Asian entrance exam systems
- Support for multiple languages and educational standards
- Partnership opportunities with international education providers

**Product Line Extension:**
- Professional certification LO generation (medical, engineering boards)
- Corporate training competency mapping
- K-12 curriculum alignment tools
- University course objective standardization

**Technology Licensing:**
- White-label LO generation platform for educational institutions
- API marketplace for third-party integrations
- Educational content validation services

## Technical Considerations

### Platform Requirements

- **Target Platforms:** Web-based system with RESTful API architecture
- **Browser/OS Support:** Modern browsers for admin interfaces, API-first design for integration flexibility
- **Performance Requirements:** 
  - LO generation: <2 hours per complete exam subject
  - API response time: <500ms for status queries
  - Concurrent processing: Support 3-5 parallel generation jobs

### Technology Preferences

- **Frontend:** FastAPI for API development, React/Next.js for future admin interfaces
- **Backend:** Python ecosystem with FastAPI, Celery for async processing, SQLAlchemy for database ORM  
- **Database:** PostgreSQL (structured data), Qdrant (vector storage), Redis (task queue & caching)
- **LLM Integration:** 
  - **Primary LLM:** Gemini 2.5 Pro/Flash APIs for text generation and validation
  - **Embedding Models:** 
    - **English content:** Qwen3-Embedding via Ollama
    - **Thai content:** bge-m3 for multilingual Thai embedding support
  - **Reranking Models:**
    - **English content:** Qwen3-Reranker via Ollama  
    - **Thai content:** bge-reranker-v2-m3 for Thai language reranking optimization
- **Hosting/Infrastructure:** Local development initially, cloud-ready architecture for future scaling

### Architecture Considerations

- **Repository Structure:** Monorepo with clear separation between RAG pipeline, API layer, and data models
- **Service Architecture:** Microservices-ready design with async task processing, language-specific model routing
- **Integration Requirements:** 
  - Qdrant vector database with multi-model support (different embedding dimensions)
  - Gemini API integration with Thai language prompt optimization
  - PostgreSQL with proper schemas for multilingual educational content
- **Security/Compliance:** 
  - API key management for LLM services
  - Basic input validation and sanitization
  - Educational data privacy considerations (future requirement)

## Constraints & Assumptions

### Constraints

- **Budget:** Development phase limited to infrastructure and API costs (Gemini API, server hosting), minimal upfront investment for MVP validation
- **Timeline:** **Aggressive 1-week MVP delivery** for core LO generation pipeline, 3-month total for exam generation system
- **Resources:** 
  - Primary developer (you) with support from PM agent for planning and documentation
  - Access to educational content (textbooks) for processing
  - Limited to existing hardware/local development environment initially
- **Technical:** 
  - Dependency on external APIs (Gemini) with rate limits and potential downtime
  - Local model performance constraints (bge-m3, Qwen3) on available hardware
  - Qdrant and PostgreSQL setup requirements for data storage

### Key Assumptions

- **Content Availability**: Standard textbooks (Campbell Biology, Physics/Chemistry texts) provide sufficient depth for comprehensive LO generation covering TBAT blueprint topics
- **API Reliability**: Gemini 2.5 Pro/Flash APIs will maintain stable availability and consistent quality for educational content generation  
- **Thai Language Processing**: bge-m3 embedding and bge-reranker-v2-m3 models will effectively handle Thai educational terminology and concepts
- **Validation Approach**: Generated LOs can be meaningfully validated against actual TBAT exam questions to ensure practical utility
- **Market Readiness**: Thai education market will adopt systematically generated learning objectives despite traditional manual approaches
- **Business Model**: Automated LO generation will provide sufficient ROI to justify development investment and enable adaptive learning system expansion
- **Technical Scalability**: Architecture choices will support growth from MVP to multi-exam system without major refactoring

## Risks & Open Questions

### Key Risks

- **LLM API Dependency**: Gemini API service disruption, rate limiting, or cost escalation could halt LO generation pipeline entirely - **Impact: Critical system downtime**
- **Content Quality Variance**: Generated LOs may be inconsistent across different textbook sections or subjects, creating uneven educational standards - **Impact: Poor adoption by educators** 
- **Thai Language Model Limitations**: bge-m3 and reranker models may struggle with specialized Thai educational terminology or mixed Thai-English content - **Impact: Reduced accuracy for Thai materials**
- **Timeline Pressure**: 1-week MVP delivery may force compromises in data validation, error handling, or system reliability - **Impact: Technical debt and system instability**
- **Validation Gap**: Without immediate access to comprehensive TBAT question banks, LO quality assessment may be incomplete - **Impact: Unknown real-world effectiveness**
- **Textbook Licensing**: Potential copyright issues with processing copyrighted educational materials for commercial use - **Impact: Legal constraints on content sources**

### Open Questions

- How will system handle mixed-language content (Thai textbooks with English scientific terms) in embedding and retrieval processes?
- What specific metrics should define "sufficient LO quality" for TBAT exam alignment beyond basic Bloom's taxonomy classification?
- How many parallel generation jobs can local hardware realistically support while maintaining acceptable performance?
- Should system prioritize breadth (covering all topics) or depth (comprehensive LOs per topic) given 1-week timeline constraint?
- What fallback mechanisms are needed if Gemini API becomes unavailable during critical generation periods?
- How will system detect and handle cases where textbook content doesn't adequately cover specific TBAT blueprint topics?

### Areas Needing Further Research

- **TBAT Question Analysis**: Deep dive into actual exam questions to understand required LO granularity and cognitive complexity patterns
- **Thai Educational Standards**: Research existing Thai curriculum frameworks to ensure generated LOs align with local educational practices
- **Competitive Analysis**: Investigation of existing educational AI tools in Thailand and their approaches to learning objective generation
- **Model Performance Benchmarking**: Testing bge-m3 vs other multilingual models on Thai educational content to optimize embedding quality
- **Hardware Requirements**: Performance testing of local model inference to determine optimal configuration for 1-week delivery timeline

## Appendices

### A. Research Summary

**Market Research Findings:**
- Thai university entrance exam system currently lacks standardized learning objectives for TBAT, creating opportunity for systematic approach
- Existing education business has proven market demand with first-dollar revenue from camps and courses
- Target market (high school students preparing for university entrance) represents significant scale in Thailand's education sector

**Competitive Analysis:**
- No direct competitors identified for Thai-specific entrance exam LO generation
- International education platforms use generic LO libraries rather than exam-specific generation
- Gap exists between broad exam blueprints and specific assessment requirements in Thai market

**Technical Feasibility Studies:**
- RAG (Retrieval-Augmented Generation) approach proven effective for educational content processing
- Late chunking strategy demonstrated superior performance for precision retrieval with contextual completeness
- Thai language models (bge-m3, bge-reranker-v2-m3) show adequate performance for multilingual educational content

### B. Stakeholder Input

**Business Stakeholder Requirements:**
- 1-week MVP delivery timeline for Phase 1 LO generation pipeline
- 3-month total timeline including exam generation system with human validation
- Foundation system must support adaptive learning integration for product recommendations
- Cost-effective approach prioritizing local development over cloud infrastructure initially

**Technical Requirements:**
- Multi-language support (Thai and English) for diverse educational content processing
- API endpoints for integration testing and future system connectivity
- Scalable architecture supporting expansion to multiple exam types beyond TBAT
- Quality validation mechanisms ensuring educational content meets standards

### C. References

**Technical Documentation:**
- Master Blueprint v8.0: Comprehensive RAG Pipeline Architecture
- TBAT Content Blueprint: Physics, Chemistry, Biology topic specifications
- Sample exam questions for validation reference (available for testing)

**Educational Resources:**
- Campbell Biology textbook for biology content processing
- Standard Physics and Chemistry textbooks for content extraction
- Thai educational curriculum frameworks for alignment reference

## Next Steps

### Immediate Actions

1. **Setup development environment** with PostgreSQL, Qdrant, and Redis infrastructure
2. **Create project structure** following Master Blueprint v8.0 specifications  
3. **Implement core RAG pipeline** with late chunking and multi-language model support
4. **Develop basic API endpoints** for testing and validation workflows
5. **Process TBAT blueprint topics** through complete LO generation pipeline
6. **Validate generated LOs** against available sample exam questions
7. **Document system performance** and prepare for Phase 2 planning

### PM Handoff

This Project Brief provides the full context for **Phase 1: Pipeline for LO Generation**. The system will transform TBAT content blueprints into structured, Bloom's taxonomy-aligned Learning Objectives using a sophisticated RAG pipeline with Thai language support. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section as the template indicates, asking for any necessary clarification or suggesting improvements.

---

*Generated with PM Agent John | Project Brief v2.0*