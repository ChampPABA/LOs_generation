#!/bin/bash

# Docker Setup Script for Learning Objectives Generation with OCR Support
# This script sets up the complete environment with hybrid chunking capabilities

set -e

echo "🚀 Setting up Learning Objectives Generation with Hybrid Chunking..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed ✓"

# Create necessary directories
print_status "Creating required directories..."
mkdir -p input_data output_data uploads processed logs
mkdir -p monitoring/prometheus monitoring/grafana/dashboards monitoring/grafana/datasources
print_success "Directories created successfully"

# Check if .env file exists, create from template if not
if [ ! -f .env ]; then
    print_warning ".env file not found"
    if [ -f .env.example ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created from template"
        print_warning "Please edit .env file with your actual configuration values before proceeding"
        echo
        echo "Key variables to set in .env:"
        echo "  - GEMINI_API_KEY: Your Google Gemini API key"
        echo "  - OPENAI_API_KEY: Your OpenAI API key (optional)"
        echo "  - HUGGINGFACE_API_KEY: Your Hugging Face API key"
        echo "  - OCR_LANGUAGES: Languages for OCR processing (default: eng,tha)"
        echo
        read -p "Press Enter when you've configured the .env file..." -r
    else
        print_error ".env.example file not found. Cannot create .env file."
        exit 1
    fi
fi

# Validate critical environment variables
print_status "Validating environment configuration..."

if ! grep -q "GEMINI_API_KEY=your-gemini-api-key-here" .env; then
    print_success "GEMINI_API_KEY appears to be configured"
else
    print_warning "GEMINI_API_KEY still has default value - agentic chunking will fail"
fi

# Create monitoring configuration files
print_status "Creating monitoring configuration..."

# Prometheus configuration
cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'los-generation-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

# Grafana datasource configuration
cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

print_success "Monitoring configuration created"

# Build and start services
print_status "Building Docker images..."
docker-compose build --no-cache

print_success "Docker images built successfully"

print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check service health
print_status "Checking service health..."

services=("postgres" "redis" "qdrant" "ollama" "api")
healthy_services=0

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        print_success "$service is running"
        ((healthy_services++))
    else
        print_error "$service is not running properly"
        docker-compose logs "$service" | tail -10
    fi
done

echo
if [ $healthy_services -eq ${#services[@]} ]; then
    print_success "All services are running successfully! 🎉"
    echo
    echo "Available endpoints:"
    echo "  🌐 API: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  📈 Grafana: http://localhost:3000 (admin/admin)"
    echo "  🔍 Prometheus: http://localhost:9090"
    echo "  🗄️  Qdrant: http://localhost:6333/dashboard"
    echo
    echo "🧪 Testing OCR capabilities:"
    echo "  curl -X POST 'http://localhost:8000/api/v1/content/analyze-document' \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -H 'X-API-Key: development-key-12345' \\"
    echo "    -d '{\"textbook_id\": 1}'"
    echo
    echo "📚 Next steps:"
    echo "  1. Upload a PDF for processing via the API"
    echo "  2. Monitor processing in Grafana"
    echo "  3. Check logs: docker-compose logs -f api"
    echo
else
    print_error "Some services failed to start properly"
    echo
    echo "Check logs with:"
    echo "  docker-compose logs [service-name]"
    echo
    echo "Restart services with:"
    echo "  docker-compose restart"
fi

# Show OCR system information
print_status "OCR System Information:"
docker-compose exec api tesseract --version || print_warning "Could not check Tesseract version"

echo
print_status "Setup completed! Check the status above and review any errors."
echo "For support, check the logs or documentation."