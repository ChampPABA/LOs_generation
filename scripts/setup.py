#!/usr/bin/env python3
"""
Setup script for LOs Generation Pipeline
"""
import asyncio
import os
import sys
import subprocess
import yaml
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.core.config import get_settings
from src.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def check_dependencies():
    """Check if all required services are available."""
    logger.info("Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ is required")
        return False
    
    # Check Poetry
    try:
        subprocess.run(["poetry", "--version"], check=True, capture_output=True)
        logger.info("Poetry found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Poetry not found. Please install Poetry first.")
        return False
    
    # Check Docker
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        logger.info("Docker found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Docker not found. You'll need to run services manually.")
    
    return True


async def setup_environment():
    """Setup environment files and directories."""
    logger.info("Setting up environment...")
    
    # Copy .env.example to .env if it doesn't exist
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists() and not env_file.exists():
        env_file.write_text(env_example.read_text())
        logger.info("Created .env file from .env.example")
        logger.warning("Please update the .env file with your actual configuration")
    
    # Create necessary directories
    directories = [
        "input_data",
        "output_data", 
        "logs",
        "monitoring/prometheus",
        "monitoring/grafana/dashboards",
        "monitoring/grafana/datasources"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


async def install_dependencies():
    """Install Python dependencies with Poetry."""
    logger.info("Installing Python dependencies...")
    
    try:
        subprocess.run(["poetry", "install"], check=True)
        logger.info("Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
    
    return True


async def setup_database():
    """Initialize database with migrations."""
    logger.info("Setting up database...")
    
    try:
        # Run Alembic migrations
        subprocess.run(["poetry", "run", "alembic", "upgrade", "head"], check=True)
        logger.info("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run database migrations: {e}")
        return False
    
    return True


async def setup_ollama_models():
    """Download required Ollama models."""
    logger.info("Setting up Ollama models...")
    
    models = [
        "bge-m3:latest",
        "qwen/qwen3-embedding-8b",
        "qwen/qwen3-reranker-8b",
        "bge-reranker-v2-m3:latest"
    ]
    
    for model in models:
        try:
            logger.info(f"Pulling model: {model}")
            subprocess.run(["ollama", "pull", model], check=True)
            logger.info(f"Successfully pulled {model}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to pull {model}: {e}")
        except FileNotFoundError:
            logger.warning("Ollama not found. Please install Ollama and run this script again.")
            break


async def create_monitoring_config():
    """Create monitoring configuration files."""
    logger.info("Setting up monitoring configuration...")
    
    # Prometheus configuration
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": [
            {
                "job_name": "los-generation-api",
                "static_configs": [
                    {"targets": ["api:8000"]}
                ]
            }
        ]
    }
    
    prometheus_path = Path("monitoring/prometheus.yml")
    with open(prometheus_path, "w") as f:
        yaml.dump(prometheus_config, f, default_flow_style=False)
    
    logger.info("Monitoring configuration created")


async def verify_setup():
    """Verify that setup completed successfully."""
    logger.info("Verifying setup...")
    
    # Check if key files exist
    required_files = [
        ".env",
        "pyproject.toml",
        "docker-compose.yml",
        "configs/models.yaml",
        "configs/prompts.yaml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False
    
    logger.info("Setup verification completed successfully")
    return True


async def main():
    """Main setup function."""
    logger.info("Starting LOs Generation Pipeline setup...")
    
    # Run setup steps
    steps = [
        ("Checking dependencies", check_dependencies),
        ("Setting up environment", setup_environment),
        ("Installing dependencies", install_dependencies),
        ("Creating monitoring config", create_monitoring_config),
        # ("Setting up database", setup_database),  # Skip for now, run manually
        # ("Setting up Ollama models", setup_ollama_models),  # Skip for now, run manually
        ("Verifying setup", verify_setup),
    ]
    
    for step_name, step_func in steps:
        logger.info(f"Running: {step_name}")
        try:
            result = await step_func()
            if result is False:
                logger.error(f"Setup failed at: {step_name}")
                return False
        except Exception as e:
            logger.error(f"Error during {step_name}: {e}")
            return False
    
    logger.info("Setup completed successfully!")
    logger.info("Next steps:")
    logger.info("1. Update .env file with your configuration")
    logger.info("2. Start services: docker-compose up -d")
    logger.info("3. Run database migrations: poetry run alembic upgrade head")
    logger.info("4. Pull Ollama models: ollama pull bge-m3 && ollama pull qwen/qwen3-embedding-8b")
    logger.info("5. Start the application: poetry run uvicorn src.main:app --reload")
    
    return True


if __name__ == "__main__":
    asyncio.run(main())