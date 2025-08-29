# Docker Deployment Guide - Hybrid Chunking Pipeline

This guide covers deploying the Learning Objectives Generation system with full OCR and hybrid chunking capabilities using Docker.

## 🏗️ Architecture Overview

The Docker deployment includes:

- **API Service**: FastAPI application with hybrid chunking pipeline
- **PostgreSQL**: Primary database for textbooks, chunks, and learning objectives
- **Redis**: Message broker and caching layer
- **Qdrant**: Vector database for semantic search
- **Ollama**: Local model serving for embeddings
- **Celery Worker**: Background job processing with OCR support
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

## 📋 Prerequisites

### System Requirements

- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 20GB free space
- **Docker**: Version 20.10+ 
- **Docker Compose**: Version 2.0+

### API Keys Required

Before deployment, obtain these API keys:

1. **Gemini API Key** (Required for agentic chunking)
   - Get from: https://ai.google.dev/
   - Used for: OCR text processing and intelligent chunking

2. **OpenAI API Key** (Optional)
   - Get from: https://platform.openai.com/
   - Used for: Alternative LO generation

3. **Hugging Face API Key** (Optional)
   - Get from: https://huggingface.co/settings/tokens
   - Used for: BGE-M3 embeddings

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

#### Linux/macOS:
```bash
# Clone and navigate to project
git clone <repository-url>
cd LOs_Generation

# Run automated setup
./scripts/setup-docker-ocr.sh
```

#### Windows:
```cmd
REM Clone and navigate to project
git clone <repository-url>
cd LOs_Generation

REM Run automated setup
scripts\setup-docker-ocr.bat
```

### Option 2: Manual Setup

#### 1. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Key variables to configure:
```bash
# Required API keys
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here  # Optional
HUGGINGFACE_API_KEY=your-hf-api-key-here  # Optional

# OCR Configuration
TESSERACT_PATH=/usr/bin/tesseract
OCR_LANGUAGES=eng,tha
OCR_CONFIDENCE_THRESHOLD=60

# Processing Settings
CHUNK_SIZE=500
PARENT_CHUNK_SIZE=1000
CHILD_CHUNK_SIZE=300
OCR_MAX_CONCURRENT_PAGES=3
```

#### 2. Create Required Directories

```bash
mkdir -p input_data output_data uploads processed logs
mkdir -p monitoring/prometheus monitoring/grafana/{dashboards,datasources}
```

#### 3. Build and Deploy

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

## 📊 Service Configuration

### Main API Service
- **Port**: 8000
- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs`
- **Features**: 
  - Document type detection
  - OCR processing with Tesseract
  - Agentic chunking with Gemini
  - Structural chunking for native PDFs

### OCR Configuration
```yaml
# In docker-compose.yml
environment:
  TESSERACT_PATH: /usr/bin/tesseract
  TESSERACT_DATA_PATH: /usr/share/tesseract-ocr/4.00/tessdata
  OCR_LANGUAGES: eng,tha
  OCR_TEMP_DIR: /tmp/ocr
  OCR_MAX_CONCURRENT_PAGES: 3
  OCR_PROCESSING_TIMEOUT: 180
```

### Celery Worker
- **Concurrency**: 2 workers
- **OCR Support**: Full Tesseract integration
- **Processing**: Hybrid chunking pipeline
- **Monitoring**: Integrated with Prometheus

## 🔍 Monitoring & Observability

### Grafana Dashboard
- **URL**: http://localhost:3000
- **Login**: admin/admin
- **Features**:
  - OCR processing metrics
  - Chunking quality scores
  - API performance metrics
  - Cost tracking

### Prometheus Metrics
- **URL**: http://localhost:9090
- **Metrics**:
  - `ocr_processing_time_seconds`
  - `chunk_quality_score`
  - `agentic_chunking_tokens_used`
  - `document_processing_requests_total`

### Log Monitoring
```bash
# View all logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f api
docker-compose logs -f celery-worker

# OCR-specific logs
docker-compose logs -f api | grep OCR
```

## 🧪 Testing the Deployment

### 1. Health Checks
```bash
# API health
curl http://localhost:8000/health

# Service-specific health
curl http://localhost:8000/api/v1/content/processing-quality/1
```

### 2. OCR Capability Test
```bash
# Test document analysis
curl -X POST "http://localhost:8000/api/v1/content/analyze-document" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: development-key-12345" \
  -d '{"textbook_id": 1}'
```

### 3. Hybrid Processing Test
```bash
# Upload and process PDF
curl -X POST "http://localhost:8000/api/v1/content/process-pdf" \
  -H "X-API-Key: development-key-12345" \
  -F "file=@sample.pdf" \
  -F "processing_preferences={\"force_processing_path\":\"auto\"}"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. OCR Processing Fails
```bash
# Check Tesseract installation
docker-compose exec api tesseract --version

# Check language data
docker-compose exec api ls /usr/share/tesseract-ocr/4.00/tessdata/

# Test OCR directly
docker-compose exec api tesseract --list-langs
```

#### 2. Memory Issues
```bash
# Monitor resource usage
docker stats

# Reduce OCR concurrency in docker-compose.yml
OCR_MAX_CONCURRENT_PAGES: 1
```

#### 3. API Key Issues
```bash
# Check environment variables
docker-compose exec api env | grep API_KEY

# Test Gemini connection
docker-compose exec api python -c "
import google.generativeai as genai
genai.configure(api_key='your-key')
print('Gemini connection OK')
"
```

#### 4. Storage Issues
```bash
# Check disk space
df -h

# Clean up temp files
docker-compose exec api rm -rf /tmp/ocr/*

# Clean up Docker
docker system prune -a
```

### Log Analysis
```bash
# OCR processing errors
docker-compose logs api | grep -i "ocr.*error"

# Chunking failures  
docker-compose logs api | grep -i "chunking.*failed"

# API errors
docker-compose logs api | grep -E "(ERROR|CRITICAL)"

# Performance issues
docker-compose logs api | grep -i "timeout\|slow"
```

## 📈 Performance Tuning

### OCR Optimization
```yaml
# In docker-compose.yml - adjust based on resources
environment:
  OCR_MAX_CONCURRENT_PAGES: 5     # Increase for more CPU/RAM
  OCR_PROCESSING_TIMEOUT: 120     # Reduce for faster failure detection
  OCR_CONFIDENCE_THRESHOLD: 70    # Increase for better quality
```

### Memory Management
```yaml
# Resource limits
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2.0'
    reservations:
      memory: 2G
      cpus: '1.0'
```

### Scaling Workers
```bash
# Scale Celery workers
docker-compose up -d --scale celery-worker=3
```

## 🔐 Production Deployment

### Security Configuration
```bash
# In .env for production
ENVIRONMENT=production
DEBUG=false
API_KEY=your-secure-production-key
JWT_SECRET_KEY=your-super-secret-jwt-key

# Enable HTTPS
FORCE_HTTPS=true
SSL_CERT_PATH=/etc/ssl/certs/fullchain.pem
SSL_KEY_PATH=/etc/ssl/certs/privkey.pem
```

### Performance Settings
```bash
# Production optimizations
WORKERS=4
MAX_WORKERS=8
OCR_MAX_CONCURRENT_PAGES=8
REDIS_MAX_CONNECTIONS=20
DATABASE_POOL_SIZE=20
```

### Backup Strategy
```bash
# Database backup
docker-compose exec postgres pg_dump -U los_user los_generation > backup.sql

# Vector database backup
docker-compose exec qdrant curl -X POST "http://localhost:6333/collections/los_chunks/snapshots"

# Configuration backup
tar -czf config-backup.tar.gz configs/ .env monitoring/
```

## 📚 Additional Resources

- [API Documentation](http://localhost:8000/docs)
- [OCR Configuration Guide](configs/ocr.yaml)
- [Monitoring Setup](monitoring/)
- [Development Guide](DEVELOPMENT.md)

## 🆘 Support

For issues and support:

1. Check service logs: `docker-compose logs -f [service]`
2. Verify system resources: `docker stats`
3. Test individual components using the troubleshooting guide above
4. Review configuration files for typos or missing values

The hybrid chunking pipeline provides robust document processing with automatic fallback between OCR and structural processing paths.