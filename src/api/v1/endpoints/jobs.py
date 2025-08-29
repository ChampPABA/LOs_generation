"""
Enhanced job management API endpoints with hybrid chunking support.
Provides detailed status tracking, processing metrics, and cost monitoring.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from src.services.job_service import JobService
from src.core.dependencies import get_current_user, get_job_service
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Enums and Models
class JobStatus(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingStep(str, Enum):
    ANALYZING = "analyzing"
    CHUNKING = "chunking"
    OCR_PROCESSING = "ocr_processing"
    AGENTIC_CHUNKING = "agentic_chunking"
    VECTORIZING = "vectorizing"
    GENERATING = "generating"
    VALIDATING = "validating"

class DocumentAnalysis(BaseModel):
    """Document analysis information."""
    document_type: str = Field(..., regex="^(native|scanned|mixed)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    total_pages: int
    pages_with_text: int
    pages_requiring_ocr: int

class OCRMetrics(BaseModel):
    """OCR processing metrics."""
    pages_processed: int
    average_confidence: float
    low_confidence_pages: int
    preprocessing_applied: bool

class AgenticChunkingMetrics(BaseModel):
    """Agentic chunking processing metrics."""
    tokens_used: int
    api_calls_made: int
    average_chunk_quality: float
    retry_count: int

class ProgressInfo(BaseModel):
    """Detailed progress information."""
    current_step: ProcessingStep
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    processed_pages: int
    total_pages: int
    ocr_metrics: Optional[OCRMetrics] = None
    agentic_chunking_metrics: Optional[AgenticChunkingMetrics] = None

class CostTracking(BaseModel):
    """Cost tracking information."""
    tokens_consumed: int
    api_calls_made: int
    estimated_cost_usd: float

class FallbackInfo(BaseModel):
    """Information about fallback processing."""
    original_path: str
    fallback_path: str
    fallback_reason: str

class HybridJobStatus(BaseModel):
    """Enhanced job status with hybrid processing details."""
    job_id: str
    status: JobStatus
    processing_path: Optional[str] = None
    document_analysis: Optional[DocumentAnalysis] = None
    progress: Optional[ProgressInfo] = None
    cost_tracking: Optional[CostTracking] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    fallback_info: Optional[FallbackInfo] = None

class ProcessingDetails(BaseModel):
    """Detailed processing information."""
    job_id: str
    document_analysis: Dict[str, Any]
    chunking_results: Dict[str, Any]

# Job Management Endpoints
@router.get("/{job_id}/status", response_model=HybridJobStatus)
async def get_job_status(
    job_id: str = Path(..., description="Job ID to check status for"),
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enhanced job status with hybrid processing details.
    """
    try:
        logger.info(f"Job status requested for: {job_id}")
        
        # Get actual job status from JobService
        job_status = await job_service.get_job_status(job_id)
        
        # Convert to HybridJobStatus format
        progress_info = job_status.get('progress', {})
        
        hybrid_status = HybridJobStatus(
            job_id=job_id,
            status=JobStatus(job_status['status']),
            processing_path=job_status.get('job_metadata', {}).get('processing_path'),
            created_at=datetime.fromisoformat(job_status.get('created_at', datetime.utcnow().isoformat())),
            updated_at=datetime.utcnow(),
            error_message=job_status.get('error_message'),
            progress=ProgressInfo(
                current_step=ProcessingStep.ANALYZING,  # Would map from actual progress
                completion_percentage=progress_info.get('percentage', 0),
                processed_pages=0,  # Would come from actual job data
                total_pages=0
            ) if progress_info else None
        )
        
        return hybrid_status
        
    except Exception as e:
        logger.error(f"Job status retrieval failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@router.get("/{job_id}/processing-details", response_model=ProcessingDetails)
async def get_processing_details(
    job_id: str = Path(..., description="Job ID to get processing details for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed processing information for hybrid chunking analysis.
    """
    try:
        logger.info(f"Processing details requested for: {job_id}")
        
        # Mock processing details
        mock_details = ProcessingDetails(
            job_id=job_id,
            document_analysis={
                "file_info": {
                    "file_size_bytes": 2045678,
                    "total_pages": 25,
                    "pdf_version": "1.4"
                },
                "page_analysis": [
                    {
                        "page_number": i,
                        "has_text": i % 4 != 0,  # Some pages have text
                        "text_density": 0.15 + (i * 0.02),
                        "requires_ocr": i % 4 == 0,  # Every 4th page needs OCR
                        "ocr_confidence": 0.85 + (i * 0.01) if i % 4 == 0 else None,
                        "processing_time_ms": 1500 + (i * 50)
                    }
                    for i in range(1, 26)
                ],
                "processing_decision": {
                    "chosen_path": "ocr_agentic",
                    "confidence": 0.88,
                    "decision_factors": [
                        "Mixed content detected",
                        "High OCR quality potential",
                        "Complex layout structure"
                    ]
                }
            },
            chunking_results={
                "total_parent_chunks": 42,
                "total_child_chunks": 168,
                "average_parent_chunk_size": 485,
                "average_child_chunk_size": 145,
                "quality_scores": {
                    "coverage": 0.94,
                    "coherence": 0.87,
                    "completeness": 0.91
                }
            }
        )
        
        return mock_details
        
    except Exception as e:
        logger.error(f"Processing details retrieval failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing details failed: {str(e)}")

@router.get("")
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    processing_path: Optional[str] = Query(None, description="Filter by processing path"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    current_user: dict = Depends(get_current_user)
):
    """
    List jobs with filtering and pagination support.
    """
    try:
        logger.info(f"Jobs list requested with filters: status={status}, path={processing_path}")
        
        # Mock job list
        mock_jobs = [
            _generate_mock_job_status(f"job_{i}") 
            for i in range(offset, min(offset + limit, 50))
        ]
        
        # Apply filters
        if status:
            mock_jobs = [job for job in mock_jobs if job.status == status]
        if processing_path:
            mock_jobs = [job for job in mock_jobs if job.processing_path == processing_path]
        
        return {
            "jobs": mock_jobs,
            "total_count": len(mock_jobs),
            "filters_applied": {
                "status": status,
                "processing_path": processing_path
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(mock_jobs) < 50
            }
        }
        
    except Exception as e:
        logger.error(f"Jobs list retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Jobs list failed: {str(e)}")

@router.delete("/{job_id}")
async def cancel_job(
    job_id: str = Path(..., description="Job ID to cancel"),
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a queued or running job.
    """
    try:
        logger.info(f"Job cancellation requested for: {job_id}")
        
        # Cancel job using JobService
        cancellation_result = await job_service.cancel_job(job_id)
        
        return {
            "job_id": job_id,
            "status": cancellation_result['status'],
            "message": "Job cancelled successfully",
            "cancelled_at": cancellation_result['cancelled_at']
        }
        
    except Exception as e:
        logger.error(f"Job cancellation failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job cancellation failed: {str(e)}")

@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str = Path(..., description="Job ID to retry"),
    retry_config: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a failed job with optional configuration changes.
    """
    try:
        logger.info(f"Job retry requested for: {job_id}")
        
        # Generate new job ID for retry
        retry_job_id = str(uuid.uuid4())
        
        # In real implementation, this would:
        # 1. Validate job can be retried
        # 2. Apply retry configuration
        # 3. Queue new job with original parameters
        # 4. Link to original job for tracking
        
        return {
            "original_job_id": job_id,
            "retry_job_id": retry_job_id,
            "status": "queued",
            "retry_config": retry_config or {},
            "message": "Job retry queued successfully",
            "estimated_start": datetime.utcnow() + timedelta(minutes=1)
        }
        
    except Exception as e:
        logger.error(f"Job retry failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job retry failed: {str(e)}")

@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str = Path(..., description="Job ID to get logs for"),
    log_level: Optional[str] = Query("info", regex="^(debug|info|warning|error)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """
    Get processing logs for a job.
    """
    try:
        logger.info(f"Job logs requested for: {job_id}")
        
        # Mock log entries
        mock_logs = [
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=10-i),
                "level": "info",
                "step": "analyzing",
                "message": f"Log entry {i}: Processing step completed",
                "details": {"pages_processed": i * 2, "confidence": 0.85 + (i * 0.01)}
            }
            for i in range(min(limit, 20))
        ]
        
        return {
            "job_id": job_id,
            "logs": mock_logs,
            "total_entries": len(mock_logs),
            "log_level_filter": log_level,
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Job logs retrieval failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job logs failed: {str(e)}")

@router.get("/statistics")
async def get_job_statistics(
    date_from: Optional[datetime] = Query(None, description="Start date for statistics"),
    date_to: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get job processing statistics and metrics.
    """
    try:
        logger.info("Job statistics requested")
        
        # Mock statistics
        stats = {
            "summary": {
                "total_jobs": 1250,
                "completed_jobs": 1180,
                "failed_jobs": 45,
                "cancelled_jobs": 25,
                "success_rate": 0.944
            },
            "processing_paths": {
                "structural": {
                    "count": 750,
                    "avg_processing_time_minutes": 2.3,
                    "success_rate": 0.98
                },
                "ocr_agentic": {
                    "count": 500,
                    "avg_processing_time_minutes": 8.7,
                    "success_rate": 0.89
                }
            },
            "cost_analysis": {
                "total_cost_usd": 145.67,
                "avg_cost_per_job": 0.116,
                "cost_by_path": {
                    "structural": 0.04,
                    "ocr_agentic": 0.23
                }
            },
            "quality_metrics": {
                "avg_ocr_confidence": 0.87,
                "avg_chunk_quality": 0.84,
                "avg_lo_quality": 0.89
            },
            "performance_trends": {
                "processing_time_trend": "stable",
                "quality_trend": "improving",
                "cost_trend": "decreasing"
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Job statistics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")

# Helper functions
def _generate_mock_job_status(job_id: str) -> HybridJobStatus:
    """Generate mock job status for demonstration."""
    import random
    
    statuses = list(JobStatus)
    status = random.choice(statuses)
    
    # Base job data
    base_time = datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
    
    mock_status = HybridJobStatus(
        job_id=job_id,
        status=status,
        processing_path=random.choice(["structural", "ocr_agentic"]),
        created_at=base_time,
        updated_at=base_time + timedelta(minutes=random.randint(1, 30))
    )
    
    # Add status-specific data
    if status in [JobStatus.PROCESSING, JobStatus.COMPLETED]:
        mock_status.document_analysis = DocumentAnalysis(
            document_type=random.choice(["native", "scanned", "mixed"]),
            confidence=0.8 + random.random() * 0.2,
            total_pages=random.randint(10, 50),
            pages_with_text=random.randint(5, 25),
            pages_requiring_ocr=random.randint(0, 30)
        )
        
        mock_status.progress = ProgressInfo(
            current_step=random.choice(list(ProcessingStep)),
            completion_percentage=random.randint(20, 100) if status == JobStatus.PROCESSING else 100,
            processed_pages=random.randint(1, 25),
            total_pages=25,
            ocr_metrics=OCRMetrics(
                pages_processed=random.randint(1, 20),
                average_confidence=0.8 + random.random() * 0.2,
                low_confidence_pages=random.randint(0, 3),
                preprocessing_applied=True
            ) if mock_status.processing_path == "ocr_agentic" else None,
            agentic_chunking_metrics=AgenticChunkingMetrics(
                tokens_used=random.randint(1000, 10000),
                api_calls_made=random.randint(5, 25),
                average_chunk_quality=0.8 + random.random() * 0.2,
                retry_count=random.randint(0, 3)
            ) if mock_status.processing_path == "ocr_agentic" else None
        )
        
        mock_status.cost_tracking = CostTracking(
            tokens_consumed=random.randint(1000, 15000),
            api_calls_made=random.randint(5, 30),
            estimated_cost_usd=round(random.uniform(0.05, 0.30), 3)
        )
    
    if status == JobStatus.COMPLETED:
        mock_status.completed_at = mock_status.updated_at
    elif status == JobStatus.FAILED:
        mock_status.error_message = "Mock error: Processing timeout occurred"
        # Sometimes include fallback info
        if random.choice([True, False]):
            mock_status.fallback_info = FallbackInfo(
                original_path="ocr_agentic",
                fallback_path="structural",
                fallback_reason="OCR processing failed"
            )
    
    return mock_status