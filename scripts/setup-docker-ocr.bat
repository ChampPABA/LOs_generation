@echo off
REM Docker Setup Script for Learning Objectives Generation with OCR Support
REM This script sets up the complete environment with hybrid chunking capabilities

echo 🚀 Setting up Learning Objectives Generation with Hybrid Chunking...
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo [INFO] Docker and Docker Compose are installed ✓
echo.

REM Create necessary directories
echo [INFO] Creating required directories...
mkdir input_data 2>nul
mkdir output_data 2>nul
mkdir uploads 2>nul
mkdir processed 2>nul
mkdir logs 2>nul
mkdir monitoring\prometheus 2>nul
mkdir monitoring\grafana\dashboards 2>nul
mkdir monitoring\grafana\datasources 2>nul

echo [SUCCESS] Directories created successfully
echo.

REM Check if .env file exists, create from template if not
if not exist .env (
    echo [WARNING] .env file not found
    if exist .env.example (
        echo [INFO] Creating .env file from template...
        copy .env.example .env >nul
        echo [SUCCESS] .env file created from template
        echo.
        echo [WARNING] Please edit .env file with your actual configuration values before proceeding
        echo.
        echo Key variables to set in .env:
        echo   - GEMINI_API_KEY: Your Google Gemini API key
        echo   - OPENAI_API_KEY: Your OpenAI API key (optional)
        echo   - HUGGINGFACE_API_KEY: Your Hugging Face API key
        echo   - OCR_LANGUAGES: Languages for OCR processing (default: eng,tha)
        echo.
        pause
    ) else (
        echo [ERROR] .env.example file not found. Cannot create .env file.
        pause
        exit /b 1
    )
)

REM Create monitoring configuration files
echo [INFO] Creating monitoring configuration...

REM Prometheus configuration
(
echo global:
echo   scrape_interval: 15s
echo   evaluation_interval: 15s
echo.
echo scrape_configs:
echo   - job_name: 'los-generation-api'
echo     static_configs:
echo       - targets: ['api:8000']
echo     metrics_path: '/metrics'
echo.
echo   - job_name: 'prometheus'
echo     static_configs:
echo       - targets: ['localhost:9090']
) > monitoring\prometheus.yml

REM Grafana datasource configuration
(
echo apiVersion: 1
echo.
echo datasources:
echo   - name: Prometheus
echo     type: prometheus
echo     access: proxy
echo     url: http://prometheus:9090
echo     isDefault: true
) > monitoring\grafana\datasources\prometheus.yml

echo [SUCCESS] Monitoring configuration created
echo.

REM Build and start services
echo [INFO] Building Docker images...
docker-compose build --no-cache
if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed
    pause
    exit /b 1
)

echo [SUCCESS] Docker images built successfully
echo.

echo [INFO] Starting services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

REM Wait for services to be ready
echo [INFO] Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Check service health
echo [INFO] Checking service health...
docker-compose ps

echo.
echo [SUCCESS] Setup completed! 🎉
echo.
echo Available endpoints:
echo   🌐 API: http://localhost:8000
echo   📊 API Docs: http://localhost:8000/docs
echo   📈 Grafana: http://localhost:3000 (admin/admin)
echo   🔍 Prometheus: http://localhost:9090
echo   🗄️  Qdrant: http://localhost:6333/dashboard
echo.
echo 🧪 Testing OCR capabilities:
echo   curl -X POST "http://localhost:8000/api/v1/content/analyze-document" ^
echo     -H "Content-Type: application/json" ^
echo     -H "X-API-Key: development-key-12345" ^
echo     -d "{\"textbook_id\": 1}"
echo.
echo 📚 Next steps:
echo   1. Upload a PDF for processing via the API
echo   2. Monitor processing in Grafana  
echo   3. Check logs: docker-compose logs -f api
echo.

REM Show OCR system information
echo [INFO] Checking OCR system...
docker-compose exec api tesseract --version 2>nul || echo [WARNING] Could not check Tesseract version

echo.
echo Setup completed! Check the status above and review any errors.
echo For support, check the logs or documentation.
echo.
pause