# LOs Generation Pipeline

A RAG (Retrieval-Augmented Generation) system that transforms Thai university entrance exam content into structured, Bloom's taxonomy-aligned Learning Objectives.

## 🎯 Project Overview

This system addresses the critical gap in Thai entrance exams (TBAT) where only high-level content blueprints exist without granular Learning Objectives. The MVP pipeline processes Physics textbooks to generate detailed, exam-aligned learning objectives that enable:

- **Consistent Exam Generation**: Standardized question creation with proper difficulty mapping
- **Adaptive Learning Systems**: Granular competency tracking for personalized recommendations  
- **Data-Driven Education**: Foundation for automated content generation and student analytics

## 🏗️ Architecture

### MVP Core Components

- **Simplified RAG Pipeline**: Structural chunking strategy with vector similarity search
- **Language-Specific Support**: Qwen3-Embedding-0.6B for English, bge-m3 for Thai/multilingual content, with reranking models
- **Basic LO Generation**: Gemini 2.5 Pro + Pydantic AI integration
- **Automated Quality Scoring**: Relevance, clarity, structure, and length metrics
- **Required Observability**: Langfuse integration for comprehensive LLM tracking and monitoring

### Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Celery, Redis
- **Databases**: PostgreSQL (structured data), Qdrant (vectors)
- **LLM Integration**: Gemini 2.5 Pro/Flash, Ollama (Qwen3 series)
- **Infrastructure**: Docker, Docker Compose
- **Testing**: pytest, basic integration testing

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Poetry (install from [python-poetry.org](https://python-poetry.org/docs/#installation))
- Docker & Docker Compose
- Git
- Gemini API key from [Google AI Studio](https://ai.google.dev/)

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd LOs_Generation
   cp .env.example .env
   # Edit .env with your Gemini API key and other settings
   ```

2. **Install dependencies**:
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install project dependencies
   poetry install
   poetry shell
   ```

3. **Start infrastructure services**:
   ```bash
   docker-compose up -d postgres redis qdrant ollama
   ```

4. **Setup database**:
   ```bash
   poetry run alembic upgrade head
   ```

5. **Pull required AI models**:
   ```bash
   # This may take several minutes (total ~4.8GB)
   docker exec -it los_generation-ollama-1 ollama pull dengcao/Qwen3-Embedding-0.6B:F16
   docker exec -it los_generation-ollama-1 ollama pull bge-m3:latest
   docker exec -it los_generation-ollama-1 ollama pull dengcao/Qwen3-Reranker-0.6B:F16
   docker exec -it los_generation-ollama-1 ollama pull xitao/bge-reranker-v2-m3:latest
   ```

6. **Start the application**:
   ```bash
   # Terminal 1: API Server
   poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   
   # Terminal 2: Celery Worker
   poetry run celery -A src.tasks.celery_app worker --loglevel=info
   ```

7. **Verify installation**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "healthy"}
   ```

### Developer Setup

For development with testing and debugging capabilities:

```bash
# Install with development dependencies
poetry install --with dev

# Setup pre-commit hooks
poetry run pre-commit install

# Run tests to verify everything works
poetry run pytest tests/services/ -v

# Generate a development API key
poetry run python -c "
from src.core.security import create_development_api_key
print('Dev API Key:', create_development_api_key())
"
```

### Quick Test

Generate your first learning objectives:

```bash
curl -X POST "http://localhost:8000/api/v1/generate-los" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Forces and Motion",
    "target_count": 3,
    "difficulty": "beginner"
  }'
```

### Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   # Required: GEMINI_API_KEY, DATABASE_URL, REDIS_URL, QDRANT_URL
   ```

3. **Start development environment**:
   ```bash
   python scripts/dev.py start
   ```

4. **Access the application**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

## 📖 Usage

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

#### Generate Learning Objectives
```bash
curl -X POST http://localhost:8000/api/v1/generate-los \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Kinematics and Forces",
    "content": "Physics textbook content here...",
    "exam_type": "TBAT"
  }'
```

#### Check Job Status
```bash
curl http://localhost:8000/api/v1/status/{job_id}
```

### Content Processing (MVP)

1. **Prepare content**: Physics textbook content (text format)
2. **Process via API**: Submit content directly through API endpoints
3. **Monitor progress**: Check job status via API
4. **Review results**: Generated LOs with quality scores in database

### Configuration

Key configuration files:
- `configs/models.yaml`: Model settings and routing
- `configs/prompts.yaml`: Prompt templates and versions
- `.env`: Environment variables and API keys

## 🧪 Development

### Running Tests
```bash
python scripts/dev.py test
```

### Code Quality
```bash
python scripts/dev.py lint
```

### Database Operations
```bash
# Run migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "Description"
```

### Monitoring

#### Logs
```bash
# Application logs
docker-compose logs -f api

# Celery worker logs
docker-compose logs -f celery-worker
```

## 📊 MVP Performance Targets

### Success Criteria (14-day timeline)
- **Subject Coverage**: Complete TBAT Physics "Kinematics and Forces" topic
- **LO Generation**: 50+ learning objectives with Bloom's taxonomy
- **Quality Score**: 80%+ average on automated metrics
- **API Performance**: <1 second response for status queries  
- **Processing Time**: <4 hours per Physics subject
- **System Reliability**: 95%+ pipeline success rate

### Quality Metrics
- **Coverage**: All key Physics concepts addressed
- **Relevance**: LOs directly related to TBAT requirements
- **Clarity**: Clear, actionable learning objectives
- **Structure**: Proper Bloom's taxonomy classification
- **Traceability**: Source textbook linkage maintained

## 🗂️ Project Structure

```
LOs_Generation/
├── src/                    # Source code
│   ├── api/               # FastAPI routes and endpoints
│   ├── core/              # Configuration and logging
│   ├── database/          # Database connection and sessions
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Business logic and external integrations
│   ├── tasks/             # Celery tasks
│   └── utils/             # Utility functions
├── configs/               # Configuration files
├── migrations/            # Database migrations
├── scripts/               # Development and deployment scripts
├── tests/                 # Test suite (basic coverage)
├── input_data/            # Input content (development)
├── output_data/           # Generated learning objectives
└── docs/                  # Documentation
```

## 🔧 Configuration

### Environment Variables

Key variables in `.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://los_user:los_password@localhost:5432/los_generation

# APIs
GEMINI_API_KEY=your_gemini_api_key
OLLAMA_URL=http://localhost:11434

# Vector Database
QDRANT_URL=http://localhost:6333

# Processing
MAX_CONCURRENT_JOBS=3
DEFAULT_RATE_LIMIT=50
```

### Model Configuration

Edit `configs/models.yaml` to adjust:
- Embedding model selection (Qwen3-0.6B for English, bge-m3 for Thai)
- Reranker model selection (Qwen3-Reranker-0.6B, bge-reranker-v2-m3)
- Language detection thresholds
- Basic model routing rules

### Prompt Engineering

Customize prompts in `configs/prompts.yaml`:
- Learning objective generation templates
- Quality scoring criteria
- Basic validation prompts

## 📋 MVP Deployment

### Docker Development
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### Basic Testing
```bash
# Run test suite
python scripts/dev.py test

# Integration test
python scripts/dev.py integration-test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `python scripts/dev.py test`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write tests for new features (60%+ coverage target)
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: API docs at `/docs` endpoint
- **Health Check**: Monitor system status at `/health` endpoint

## 🚧 MVP Roadmap

### ✅ Phase 1 (Current): MVP Pipeline (14 days)
- [x] Basic project structure and configuration
- [x] Database schema and models
- [ ] Complete services architecture
- [ ] Simplified RAG pipeline
- [ ] Basic LO generation with quality scoring
- [ ] API endpoints and deployment

### 🔄 Phase 2: Enhanced Features (Weeks 3-4)
- [ ] Multi-subject support (Chemistry, Biology)
- [ ] Advanced validation against TBAT questions
- [ ] Performance optimization
- [ ] Enhanced quality metrics

### 🎯 Phase 3: Production Ready (Weeks 5-6)
- [ ] Advanced RAG features (Late Chunking, Reranking)
- [ ] Multi-language optimization
- [ ] Human review interface
- [ ] Production monitoring and alerting

### 🌟 Phase 4: Scale & Integration (Weeks 7-8)
- [ ] Multi-exam support (PMAT, GAT, PAT)
- [ ] Advanced analytics dashboard
- [ ] API marketplace integration
- [ ] Adaptive learning system integration

---

Built with ❤️ for Thai education | **MVP Timeline: 14 days** | **Focus: Physics Subject Proof of Concept**