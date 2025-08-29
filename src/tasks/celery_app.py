"""
Celery application configuration for background task processing.
"""

import os
from celery import Celery
from kombu import Queue

# Get Redis URL from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery instance
celery_app = Celery(
    'los_generation',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'src.tasks.processing_tasks',
        'src.tasks.ocr_tasks',
        'src.tasks.generation_tasks',
        'src.tasks.monitoring_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'src.tasks.ocr_tasks.*': {'queue': 'ocr'},
        'src.tasks.processing_tasks.*': {'queue': 'processing'},
        'src.tasks.generation_tasks.*': {'queue': 'generation'},
        'src.tasks.monitoring_tasks.*': {'queue': 'monitoring'},
    },
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task results
    result_expires=3600,  # 1 hour
    result_backend_max_retries=10,
    
    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Task retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-expired-jobs': {
            'task': 'src.tasks.monitoring_tasks.cleanup_expired_jobs',
            'schedule': 3600.0,  # Every hour
        },
        'update-system-metrics': {
            'task': 'src.tasks.monitoring_tasks.update_system_metrics',
            'schedule': 300.0,  # Every 5 minutes
        },
    },
    
    # Timezone
    timezone='UTC',
)

# Define queues
celery_app.conf.task_queues = (
    Queue('default', routing_key='default'),
    Queue('ocr', routing_key='ocr'),
    Queue('processing', routing_key='processing'),
    Queue('generation', routing_key='generation'),
    Queue('monitoring', routing_key='monitoring'),
)

# Task annotations for specific configurations
celery_app.conf.task_annotations = {
    'src.tasks.ocr_tasks.process_pdf_ocr': {
        'rate_limit': '3/m',  # Max 3 OCR tasks per minute
        'time_limit': 600,    # 10 minute timeout
        'soft_time_limit': 540,  # 9 minute soft timeout
    },
    'src.tasks.generation_tasks.generate_learning_objectives': {
        'rate_limit': '10/m',  # Max 10 generation tasks per minute
        'time_limit': 300,     # 5 minute timeout
    },
}

if __name__ == '__main__':
    celery_app.start()