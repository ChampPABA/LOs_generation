"""
Monitoring and metrics collection service.
Provides Prometheus metrics and health monitoring.
"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict, deque

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

from ..core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics registry
REGISTRY = CollectorRegistry()

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Job processing metrics
JOBS_TOTAL = Counter(
    'jobs_total',
    'Total jobs processed',
    ['job_type', 'status'],
    registry=REGISTRY
)

JOB_DURATION = Histogram(
    'job_duration_seconds',
    'Job processing duration in seconds',
    ['job_type', 'processing_path'],
    registry=REGISTRY
)

# System metrics
SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage',
    registry=REGISTRY
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=REGISTRY
)

# Queue metrics
CELERY_QUEUE_SIZE = Gauge(
    'celery_queue_size',
    'Number of tasks in Celery queue',
    ['queue_name'],
    registry=REGISTRY
)

# OCR metrics
OCR_PAGES_PROCESSED = Counter(
    'ocr_pages_processed_total',
    'Total OCR pages processed',
    registry=REGISTRY
)

OCR_PROCESSING_TIME = Histogram(
    'ocr_processing_duration_seconds',
    'OCR processing duration per page',
    registry=REGISTRY
)

# LLM metrics
LLM_REQUESTS_TOTAL = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'status'],
    registry=REGISTRY
)

LLM_TOKENS_USED = Counter(
    'llm_tokens_used_total',
    'Total LLM tokens consumed',
    ['model', 'operation'],
    registry=REGISTRY
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics for Prometheus.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics collection for metrics endpoint
        if request.url.path == '/metrics':
            return await call_next(request)
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint pattern (remove dynamic parts)
        endpoint = self._extract_endpoint_pattern(request.url.path)
        
        # Record metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()
        
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        return response

    def _extract_endpoint_pattern(self, path: str) -> str:
        """Extract endpoint pattern from path, removing IDs and dynamic parts."""
        # Remove common ID patterns
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Replace job IDs with {job_id}
        path = re.sub(r'/job_[a-zA-Z0-9-]+', '/{job_id}', path)
        
        return path or "/"


class MetricsCollector:
    """
    Service for collecting and exposing application metrics.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Internal metrics
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
        self._response_times = defaultdict(deque)
        
        self.logger.info("Metrics collector initialized")

    def record_job_start(self, job_id: str, job_type: str):
        """Record job start."""
        JOBS_TOTAL.labels(job_type=job_type, status='started').inc()
        self.logger.debug(f"Job started metric recorded: {job_id} ({job_type})")

    def record_job_completion(self, job_id: str, job_type: str, processing_path: str, duration: float):
        """Record job completion."""
        JOBS_TOTAL.labels(job_type=job_type, status='completed').inc()
        JOB_DURATION.labels(job_type=job_type, processing_path=processing_path).observe(duration)
        self.logger.debug(f"Job completion metric recorded: {job_id} ({duration:.2f}s)")

    def record_job_failure(self, job_id: str, job_type: str, error_type: str):
        """Record job failure."""
        JOBS_TOTAL.labels(job_type=job_type, status='failed').inc()
        self.logger.debug(f"Job failure metric recorded: {job_id} ({error_type})")

    def record_ocr_processing(self, pages_processed: int, total_duration: float):
        """Record OCR processing metrics."""
        OCR_PAGES_PROCESSED.inc(pages_processed)
        
        if pages_processed > 0:
            avg_duration = total_duration / pages_processed
            for _ in range(pages_processed):
                OCR_PROCESSING_TIME.observe(avg_duration)

    def record_llm_request(self, model: str, operation: str, tokens_used: int, success: bool):
        """Record LLM API request metrics."""
        status = 'success' if success else 'failure'
        
        LLM_REQUESTS_TOTAL.labels(model=model, status=status).inc()
        LLM_TOKENS_USED.labels(model=model, operation=operation).inc(tokens_used)

    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.percent)
            
            self.logger.debug(f"System metrics updated: CPU={cpu_percent}%, Memory={memory.percent}%")
            
        except Exception as e:
            self.logger.error(f"Failed to update system metrics: {str(e)}")

    def update_queue_metrics(self, queue_sizes: Dict[str, int]):
        """Update Celery queue size metrics."""
        for queue_name, size in queue_sizes.items():
            CELERY_QUEUE_SIZE.labels(queue_name=queue_name).set(size)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics."""
        try:
            # Get system info
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_usage_percent": cpu_percent,
                    "memory_usage_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_usage_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                },
                "application": {
                    "uptime_seconds": time.time() - self._start_time if hasattr(self, '_start_time') else 0,
                    "total_requests": sum(self._request_counts.values()),
                    "total_errors": sum(self._error_counts.values())
                },
                "prometheus_metrics_available": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate metrics summary: {str(e)}")
            return {
                "error": "Failed to collect metrics",
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_prometheus_metrics(self) -> bytes:
        """Get Prometheus-formatted metrics."""
        try:
            # Update system metrics before export
            self.update_system_metrics()
            
            return generate_latest(REGISTRY)
            
        except Exception as e:
            self.logger.error(f"Failed to generate Prometheus metrics: {str(e)}")
            return b"# Error generating metrics\n"

    def start_monitoring(self):
        """Start background monitoring tasks."""
        self._start_time = time.time()
        self.logger.info("Metrics monitoring started")

    def stop_monitoring(self):
        """Stop monitoring and cleanup resources."""
        self.logger.info("Metrics monitoring stopped")


# Global metrics collector instance
metrics_collector = MetricsCollector()