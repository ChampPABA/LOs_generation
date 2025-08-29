"""
Job management service for coordinating background processing tasks.
Handles job creation, status tracking, and task orchestration.
"""

import uuid
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from celery import chain, group, chord
from celery.result import AsyncResult

from ..tasks.celery_app import celery_app
from ..tasks import processing_tasks, ocr_tasks, generation_tasks
from ..core.logging import get_logger
from ..database.connection import get_async_session
from ..models.jobs import JobStatus

logger = get_logger(__name__)

class JobType(str, Enum):
    DIRECT_TEXT = "direct_text"
    TEXTBOOK_ID = "textbook_id"
    PDF_UPLOAD = "pdf_upload"

class ProcessingStage(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    OCR_PROCESSING = "ocr_processing"
    ANALYZING_DOCUMENT = "analyzing_document"
    CHUNKING_CONTENT = "chunking_content"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    GENERATING_OBJECTIVES = "generating_objectives"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class JobProgress:
    stage: ProcessingStage
    progress_percentage: float
    current_step: str
    estimated_remaining_time: Optional[str] = None
    error_message: Optional[str] = None

class JobService:
    """Service for managing background processing jobs."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def create_generation_job(
        self,
        job_type: JobType,
        content: Optional[str] = None,
        textbook_id: Optional[int] = None,
        file_path: Optional[str] = None,
        generation_config: Dict[str, Any] = None,
        processing_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new learning objective generation job."""
        
        job_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Creating generation job {job_id} of type {job_type}")
            
            # Default configurations
            if generation_config is None:
                generation_config = {
                    "model": "gpt-4",
                    "max_objectives": 15,
                    "bloom_levels": [1, 2, 3, 4, 5, 6],
                    "quality_threshold": 0.7
                }
            
            if processing_preferences is None:
                processing_preferences = {
                    "force_processing_path": None,
                    "chunk_size": 500,
                    "overlap_size": 50,
                    "ocr_languages": ["eng", "tha"]
                }
            
            # Build processing pipeline based on job type
            if job_type == JobType.DIRECT_TEXT:
                pipeline = await self._create_direct_text_pipeline(
                    job_id, content, generation_config, processing_preferences
                )
            
            elif job_type == JobType.PDF_UPLOAD:
                pipeline = await self._create_pdf_upload_pipeline(
                    job_id, file_path, generation_config, processing_preferences
                )
            
            elif job_type == JobType.TEXTBOOK_ID:
                pipeline = await self._create_textbook_pipeline(
                    job_id, textbook_id, generation_config, processing_preferences
                )
            
            else:
                raise ValueError(f"Unsupported job type: {job_type}")
            
            # Execute the pipeline
            result = pipeline.apply_async()
            
            # Store job metadata
            job_metadata = {
                "job_id": job_id,
                "job_type": job_type.value,
                "status": ProcessingStage.QUEUED.value,
                "created_at": datetime.utcnow().isoformat(),
                "celery_task_id": result.id,
                "generation_config": generation_config,
                "processing_preferences": processing_preferences,
                "content_summary": {
                    "textbook_id": textbook_id,
                    "has_content": content is not None,
                    "file_path": file_path
                }
            }
            
            # In real implementation, store in database
            await self._store_job_metadata(job_id, job_metadata)
            
            self.logger.info(f"Job {job_id} created successfully with task ID {result.id}")
            
            return {
                "job_id": job_id,
                "status": ProcessingStage.QUEUED.value,
                "celery_task_id": result.id,
                "estimated_completion": datetime.utcnow() + timedelta(minutes=10),
                "processing_pipeline": self._describe_pipeline(job_type),
                "cost_estimate": self._estimate_cost(job_type, content, file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create job {job_id}: {str(e)}")
            raise

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current status and progress of a job."""
        
        try:
            # Get job metadata
            job_metadata = await self._get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job {job_id} not found")
            
            celery_task_id = job_metadata.get("celery_task_id")
            if not celery_task_id:
                raise ValueError(f"No Celery task ID found for job {job_id}")
            
            # Get Celery task result
            task_result = AsyncResult(celery_task_id, app=celery_app)
            
            # Determine current progress
            progress = self._parse_task_progress(task_result)
            
            return {
                "job_id": job_id,
                "status": progress.stage.value,
                "progress": {
                    "percentage": progress.progress_percentage,
                    "current_step": progress.current_step,
                    "estimated_remaining_time": progress.estimated_remaining_time
                },
                "created_at": job_metadata.get("created_at"),
                "job_type": job_metadata.get("job_type"),
                "error_message": progress.error_message,
                "celery_task_status": task_result.status,
                "celery_task_info": task_result.info if task_result.info else {}
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            raise

    async def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Get completed results for a job."""
        
        try:
            job_metadata = await self._get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job {job_id} not found")
            
            celery_task_id = job_metadata.get("celery_task_id")
            task_result = AsyncResult(celery_task_id, app=celery_app)
            
            if task_result.status != 'SUCCESS':
                raise ValueError(f"Job {job_id} is not completed successfully. Status: {task_result.status}")
            
            # Get the final result
            result = task_result.result
            
            self.logger.info(f"Retrieved results for job {job_id}")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "results": result,
                "completion_time": datetime.utcnow().isoformat(),
                "job_metadata": job_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get job results for {job_id}: {str(e)}")
            raise

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        
        try:
            job_metadata = await self._get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job {job_id} not found")
            
            celery_task_id = job_metadata.get("celery_task_id")
            
            # Revoke the Celery task
            celery_app.control.revoke(celery_task_id, terminate=True)
            
            # Update job status
            await self._update_job_status(job_id, "cancelled")
            
            self.logger.info(f"Job {job_id} cancelled successfully")
            
            return {
                "job_id": job_id,
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            raise

    # Pipeline creation methods
    async def _create_direct_text_pipeline(
        self, job_id: str, content: str, generation_config: Dict[str, Any], 
        processing_preferences: Dict[str, Any]
    ):
        """Create pipeline for direct text processing."""
        
        # Simple pipeline for direct text:
        # 1. Process content chunks
        # 2. Generate embeddings  
        # 3. Generate learning objectives
        
        pipeline = chain(
            processing_tasks.process_content_chunks.s(
                job_id=job_id,
                content=content,
                processing_path="structural",
                chunk_config=processing_preferences
            ),
            processing_tasks.generate_embeddings.s(job_id=job_id),
            generation_tasks.generate_learning_objectives.s(
                job_id=job_id,
                generation_config=generation_config
            )
        )
        
        return pipeline

    async def _create_pdf_upload_pipeline(
        self, job_id: str, file_path: str, generation_config: Dict[str, Any], 
        processing_preferences: Dict[str, Any]
    ):
        """Create pipeline for PDF upload processing."""
        
        # Complex pipeline for PDF:
        # 1. Validate PDF
        # 2. OCR processing
        # 3. Document analysis
        # 4. Content chunking
        # 5. Generate embeddings
        # 6. Generate learning objectives
        # 7. Cleanup files
        
        # First validate PDF
        validate_task = ocr_tasks.validate_uploaded_pdf.s(file_path)
        
        # Then create the main processing chain
        main_pipeline = chain(
            ocr_tasks.process_pdf_ocr.s(
                job_id=job_id,
                ocr_config=processing_preferences
            ),
            processing_tasks.analyze_document.s(
                job_id=job_id,
                content_type="pdf"
            ),
            processing_tasks.process_content_chunks.s(job_id=job_id),
            processing_tasks.generate_embeddings.s(job_id=job_id),
            generation_tasks.generate_learning_objectives.s(
                job_id=job_id,
                generation_config=generation_config
            ),
            ocr_tasks.cleanup_processed_files.s(
                job_id=job_id,
                keep_original=True
            )
        )
        
        # Chain validation with main pipeline
        pipeline = chain(validate_task, main_pipeline)
        
        return pipeline

    async def _create_textbook_pipeline(
        self, job_id: str, textbook_id: int, generation_config: Dict[str, Any], 
        processing_preferences: Dict[str, Any]
    ):
        """Create pipeline for textbook processing."""
        
        # Pipeline for existing textbook:
        # 1. Fetch textbook content
        # 2. Document analysis (if needed)
        # 3. Process chunks or use existing
        # 4. Generate embeddings (if needed)
        # 5. Generate learning objectives
        
        pipeline = chain(
            processing_tasks.analyze_document.s(
                job_id=job_id,
                file_path=f"textbook_{textbook_id}",
                content_type="textbook"
            ),
            processing_tasks.process_content_chunks.s(job_id=job_id),
            processing_tasks.generate_embeddings.s(job_id=job_id),
            generation_tasks.generate_learning_objectives.s(
                job_id=job_id,
                generation_config=generation_config
            )
        )
        
        return pipeline

    # Helper methods
    def _parse_task_progress(self, task_result: AsyncResult) -> JobProgress:
        """Parse Celery task result into JobProgress."""
        
        if task_result.status == 'PENDING':
            return JobProgress(
                stage=ProcessingStage.QUEUED,
                progress_percentage=0,
                current_step="Job queued, waiting to start"
            )
        
        elif task_result.status == 'PROGRESS':
            info = task_result.info or {}
            stage_name = info.get('stage', 'processing')
            progress = info.get('progress', 0)
            
            # Map stage names to ProcessingStage enum
            stage_mapping = {
                'validating': ProcessingStage.VALIDATING,
                'ocr_processing': ProcessingStage.OCR_PROCESSING,
                'analyzing_document': ProcessingStage.ANALYZING_DOCUMENT,
                'chunking_content': ProcessingStage.CHUNKING_CONTENT,
                'generating_embeddings': ProcessingStage.GENERATING_EMBEDDINGS,
                'generating_objectives': ProcessingStage.GENERATING_OBJECTIVES
            }
            
            stage = stage_mapping.get(stage_name, ProcessingStage.QUEUED)
            
            return JobProgress(
                stage=stage,
                progress_percentage=progress,
                current_step=info.get('current_step', f"Processing: {stage_name}"),
                estimated_remaining_time=self._estimate_remaining_time(progress)
            )
        
        elif task_result.status == 'SUCCESS':
            return JobProgress(
                stage=ProcessingStage.COMPLETED,
                progress_percentage=100,
                current_step="Job completed successfully"
            )
        
        elif task_result.status == 'FAILURE':
            error_info = str(task_result.info) if task_result.info else "Unknown error"
            return JobProgress(
                stage=ProcessingStage.FAILED,
                progress_percentage=0,
                current_step="Job failed",
                error_message=error_info
            )
        
        else:
            return JobProgress(
                stage=ProcessingStage.QUEUED,
                progress_percentage=0,
                current_step=f"Unknown status: {task_result.status}"
            )

    def _estimate_remaining_time(self, progress: float) -> str:
        """Estimate remaining processing time based on progress."""
        if progress >= 90:
            return "Less than 1 minute"
        elif progress >= 60:
            return "2-3 minutes"
        elif progress >= 30:
            return "5-8 minutes"
        else:
            return "8-15 minutes"

    def _describe_pipeline(self, job_type: JobType) -> List[str]:
        """Describe the processing pipeline steps."""
        
        if job_type == JobType.DIRECT_TEXT:
            return [
                "Content chunking",
                "Embedding generation", 
                "Learning objective generation"
            ]
        
        elif job_type == JobType.PDF_UPLOAD:
            return [
                "PDF validation",
                "OCR processing",
                "Document analysis",
                "Content chunking",
                "Embedding generation",
                "Learning objective generation",
                "File cleanup"
            ]
        
        elif job_type == JobType.TEXTBOOK_ID:
            return [
                "Content retrieval",
                "Document analysis", 
                "Content chunking",
                "Embedding generation",
                "Learning objective generation"
            ]
        
        return ["Unknown pipeline"]

    def _estimate_cost(self, job_type: JobType, content: Optional[str], file_path: Optional[str]) -> Dict[str, float]:
        """Estimate processing cost."""
        
        base_costs = {
            JobType.DIRECT_TEXT: 0.05,
            JobType.TEXTBOOK_ID: 0.10,
            JobType.PDF_UPLOAD: 0.25
        }
        
        base_cost = base_costs.get(job_type, 0.10)
        
        # Adjust based on content size
        if content:
            content_multiplier = min(len(content) / 10000, 3.0)  # Cap at 3x
            base_cost *= (1 + content_multiplier)
        
        return {
            "estimated_cost_usd": round(base_cost, 2),
            "cost_breakdown": {
                "processing": round(base_cost * 0.6, 2),
                "llm_generation": round(base_cost * 0.4, 2)
            }
        }

    # Database operations (mock implementations)
    async def _store_job_metadata(self, job_id: str, metadata: Dict[str, Any]):
        """Store job metadata in database."""
        # In real implementation, this would store in PostgreSQL
        self.logger.debug(f"Storing metadata for job {job_id}")
        pass

    async def _get_job_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job metadata from database."""
        # In real implementation, this would query PostgreSQL
        # For now, return mock data
        return {
            "job_id": job_id,
            "job_type": "pdf_upload",
            "created_at": datetime.utcnow().isoformat(),
            "celery_task_id": "mock-task-id"
        }

    async def _update_job_status(self, job_id: str, status: str):
        """Update job status in database."""
        # In real implementation, this would update PostgreSQL
        self.logger.debug(f"Updating job {job_id} status to {status}")
        pass