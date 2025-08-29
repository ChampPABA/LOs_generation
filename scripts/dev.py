#!/usr/bin/env python3
"""
Development helper script for LOs Generation Pipeline
"""
import asyncio
import os
import sys
import subprocess
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


class DevServer:
    """Development server manager."""
    
    def __init__(self):
        self.processes = {}
        self.running = False
    
    async def start_services(self):
        """Start all development services."""
        logger.info("Starting development services...")
        
        # Start Docker services
        try:
            subprocess.run([
                "docker-compose", "up", "-d", 
                "postgres", "redis", "qdrant", "ollama"
            ], check=True)
            logger.info("Docker services started")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False
        
        # Wait for services to be ready
        await self.wait_for_services()
        
        return True
    
    async def wait_for_services(self):
        """Wait for services to be ready."""
        logger.info("Waiting for services to be ready...")
        
        services = [
            ("PostgreSQL", "docker-compose exec postgres pg_isready -U los_user"),
            ("Redis", "docker-compose exec redis redis-cli ping"),
            ("Qdrant", "curl -f http://localhost:6333/health"),
        ]
        
        max_attempts = 30
        for service_name, check_command in services:
            for attempt in range(max_attempts):
                try:
                    subprocess.run(
                        check_command.split(),
                        check=True,
                        capture_output=True
                    )
                    logger.info(f"{service_name} is ready")
                    break
                except subprocess.CalledProcessError:
                    if attempt < max_attempts - 1:
                        logger.info(f"Waiting for {service_name}... ({attempt + 1}/{max_attempts})")
                        await asyncio.sleep(2)
                    else:
                        logger.warning(f"{service_name} not ready after {max_attempts} attempts")
    
    async def start_api(self):
        """Start the FastAPI development server."""
        logger.info("Starting FastAPI server...")
        
        cmd = [
            "poetry", "run", "uvicorn", 
            "src.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--log-level", "info"
        ]
        
        process = subprocess.Popen(cmd)
        self.processes["api"] = process
        logger.info("FastAPI server started on http://localhost:8000")
        
        return process
    
    async def start_celery_worker(self):
        """Start Celery worker."""
        logger.info("Starting Celery worker...")
        
        cmd = [
            "poetry", "run", "celery",
            "-A", "src.tasks.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=2"
        ]
        
        process = subprocess.Popen(cmd)
        self.processes["celery_worker"] = process
        logger.info("Celery worker started")
        
        return process
    
    async def start_celery_beat(self):
        """Start Celery beat scheduler."""
        logger.info("Starting Celery beat...")
        
        cmd = [
            "poetry", "run", "celery",
            "-A", "src.tasks.celery_app",
            "beat",
            "--loglevel=info"
        ]
        
        process = subprocess.Popen(cmd)
        self.processes["celery_beat"] = process
        logger.info("Celery beat started")
        
        return process
    
    def stop_all(self):
        """Stop all processes."""
        logger.info("Stopping all processes...")
        
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Force killed {name}")
        
        # Stop Docker services
        try:
            subprocess.run(["docker-compose", "stop"], check=True)
            logger.info("Docker services stopped")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop Docker services: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.running = False
        self.stop_all()
        sys.exit(0)


async def run_tests():
    """Run test suite."""
    logger.info("Running tests...")
    
    cmd = [
        "poetry", "run", "pytest",
        "-v",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("Tests completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Tests failed: {e}")


async def lint_code():
    """Run code linting."""
    logger.info("Running code linting...")
    
    commands = [
        (["poetry", "run", "black", "src", "tests"], "Black formatting"),
        (["poetry", "run", "flake8", "src", "tests"], "Flake8 linting"),
        (["poetry", "run", "mypy", "src"], "MyPy type checking")
    ]
    
    for cmd, description in commands:
        try:
            logger.info(f"Running {description}...")
            subprocess.run(cmd, check=True)
            logger.info(f"{description} passed")
        except subprocess.CalledProcessError as e:
            logger.error(f"{description} failed: {e}")


async def main():
    """Main development function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev.py [command]")
        print("Commands:")
        print("  start     - Start all development services")
        print("  stop      - Stop all services")
        print("  test      - Run test suite")
        print("  lint      - Run code linting")
        print("  setup     - Run initial setup")
        return
    
    command = sys.argv[1]
    
    if command == "setup":
        from setup import main as setup_main
        await setup_main()
    
    elif command == "start":
        dev_server = DevServer()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, dev_server.signal_handler)
        signal.signal(signal.SIGTERM, dev_server.signal_handler)
        
        # Start services
        if not await dev_server.start_services():
            logger.error("Failed to start services")
            return
        
        # Start application components
        await dev_server.start_api()
        await dev_server.start_celery_worker()
        await dev_server.start_celery_beat()
        
        logger.info("Development environment is ready!")
        logger.info("API: http://localhost:8000")
        logger.info("API Docs: http://localhost:8000/docs")
        logger.info("Grafana: http://localhost:3000 (admin/admin)")
        logger.info("Prometheus: http://localhost:9090")
        
        # Keep running
        dev_server.running = True
        while dev_server.running:
            await asyncio.sleep(1)
    
    elif command == "stop":
        try:
            subprocess.run(["docker-compose", "stop"], check=True)
            logger.info("Services stopped")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop services: {e}")
    
    elif command == "test":
        await run_tests()
    
    elif command == "lint":
        await lint_code()
    
    else:
        logger.error(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())