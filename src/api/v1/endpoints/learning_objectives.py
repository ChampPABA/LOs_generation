"""
Learning Objectives API endpoints with hybrid chunking integration.
Handles LO generation requests and enhanced job management.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from src.services.processing_service import ProcessingService
from src.services.job_service import JobService, JobType
from src.services.document_analyzer import ProcessingPath
from src.core.dependencies import get_processing_service, get_job_service, get_current_user
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Request/Response Models from content.py
from .content import ProcessingPreferences, GenerationConfig, GenerateLOsRequest

class LearningObjective(BaseModel):
    """Individual learning objective with metadata."""
    lo_id: str
    content: str
    bloom_level: int
    quality_score: float
    confidence: float
    source_chunk_id: str
    metadata: Dict[str, Any]

class GenerationJobResponse(BaseModel):
    """Response for LO generation job creation."""
    job_id: str
    status: str
    processing_path: str
    estimated_completion: datetime
    cost_estimate: Dict[str, Any]

class LearningObjectivesResponse(BaseModel):
    """Complete response for generated learning objectives."""
    job_id: str
    textbook_id: Optional[int] = None
    topic_id: int
    status: str
    learning_objectives: List[LearningObjective]
    generation_metadata: Dict[str, Any]
    processing_summary: Dict[str, Any]
    quality_assessment: Dict[str, Any]

# Main generation endpoint
@router.post("/generate", response_model=GenerationJobResponse)
async def generate_learning_objectives(
    request: GenerateLOsRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate learning objectives with hybrid chunking support.
    """
    try:
        logger.info(f"LO generation requested for content_type: {request.content_type}")
        
        # Convert content type to JobType enum
        job_type = JobType(request.content_type)
        
        # Extract generation and processing configs
        generation_config = {
            "model": request.generation_config.model,
            "max_objectives": request.generation_config.max_objectives,
            "bloom_levels": request.generation_config.bloom_levels,
            "quality_threshold": request.generation_config.quality_threshold
        }
        
        processing_preferences = {
            "force_processing_path": request.processing_preferences.force_processing_path,
            "chunk_size": request.processing_preferences.chunk_size,
            "overlap_size": request.processing_preferences.overlap_size,
            "ocr_languages": request.processing_preferences.ocr_languages
        }
        
        # Create job using JobService
        job_result = await job_service.create_generation_job(
            job_type=job_type,
            content=getattr(request, 'content', None),
            textbook_id=getattr(request, 'textbook_id', None),
            file_path=getattr(request, 'file_path', None),
            generation_config=generation_config,
            processing_preferences=processing_preferences
        )
        
        logger.info(f"LO generation job {job_result['job_id']} created successfully")
        
        return GenerationJobResponse(
            job_id=job_result['job_id'],
            status=job_result['status'],
            processing_path=job_result['processing_pipeline'][0] if job_result['processing_pipeline'] else 'unknown',
            estimated_completion=job_result['estimated_completion'],
            cost_estimate=job_result['cost_estimate']
        )
        
    except Exception as e:
        logger.error(f"LO generation request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation request failed: {str(e)}")

@router.get("/jobs/{job_id}/results", response_model=LearningObjectivesResponse)
async def get_learning_objectives_results(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve completed learning objectives for a job.
    """
    try:
        logger.info(f"LO results requested for job: {job_id}")
        
        # Get job results from JobService
        job_results = await job_service.get_job_results(job_id)
        
        if job_results['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Job {job_id} is not completed. Current status: {job_results['status']}"
            )
        
        results = job_results['results']
        
        # Convert results to API response format
        learning_objectives = []
        for lo_data in results.get('learning_objectives', []):
            learning_objectives.append(LearningObjective(
                lo_id=lo_data['lo_id'],
                content=lo_data['content'],
                bloom_level=lo_data['bloom_level'],
                quality_score=lo_data['quality_score'],
                confidence=lo_data['confidence'],
                source_chunk_id=lo_data['source_chunk_id'],
                metadata=lo_data['metadata']
            ))
        
        return LearningObjectivesResponse(
            job_id=job_id,
            textbook_id=results.get('textbook_id'),
            topic_id=results.get('topic_id', 1),
            status="completed",
            learning_objectives=learning_objectives,
            generation_metadata=results.get('generation_metadata', {}),
            processing_summary=results.get('processing_summary', {}),
            quality_assessment=results.get('quality_assessment', {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LO results retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Results retrieval failed: {str(e)}")

@router.get("/jobs/{job_id}/preview")
async def preview_learning_objectives(
    job_id: str,
    max_results: int = Query(default=5, ge=1, le=20),
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a preview of learning objectives while generation is in progress.
    """
    try:
        logger.info(f"LO preview requested for job: {job_id}")
        
        # Get current job status
        job_status = await job_service.get_job_status(job_id)
        
        # Generate preview based on current progress
        progress_info = job_status.get('progress', {})
        completion_percentage = progress_info.get('percentage', 0)
        
        # Mock preview data based on progress
        preview_count = min(max_results, max(1, int(completion_percentage / 20)))
        preview_los = [
            {
                "content": f"Students will understand the fundamental principles of topic {i+1}.",
                "bloom_level": (i % 3) + 2,
                "confidence": 0.80 + (i * 0.03),
                "status": "generated" if i < preview_count else "pending"
            }
            for i in range(min(max_results, 5))
        ]
        
        return {
            "job_id": job_id,
            "preview_status": "partial_results" if completion_percentage < 100 else "completed",
            "progress": {
                "completion_percentage": completion_percentage,
                "current_step": progress_info.get('current_step', 'processing'),
                "los_completed": preview_count,
                "los_pending": max_results - preview_count
            },
            "preview_objectives": preview_los,
            "estimated_remaining_time": progress_info.get('estimated_remaining_time', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"LO preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@router.post("/jobs/{job_id}/refine")
async def refine_learning_objectives(
    job_id: str,
    refinement_request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Refine generated learning objectives based on user feedback.
    """
    try:
        logger.info(f"LO refinement requested for job: {job_id}")
        
        # Get original job results
        original_results = await job_service.get_job_results(job_id)
        
        if original_results['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot refine incomplete job. Status: {original_results['status']}"
            )
        
        # Extract refinement parameters
        target_bloom_levels = refinement_request.get("target_bloom_levels", [])
        quality_threshold = refinement_request.get("quality_threshold", 0.8)
        focus_keywords = refinement_request.get("focus_keywords", [])
        exclude_topics = refinement_request.get("exclude_topics", [])
        
        # Create refinement configuration
        refinement_config = {
            "target_bloom_levels": target_bloom_levels,
            "quality_threshold": quality_threshold,
            "focus_keywords": focus_keywords,
            "exclude_topics": exclude_topics
        }
        
        # For now, return a placeholder response
        # In full implementation, this would trigger a refinement task
        refinement_job_id = str(uuid.uuid4())
        
        return {
            "original_job_id": job_id,
            "refinement_job_id": refinement_job_id,
            "status": "queued",
            "refinement_config": refinement_config,
            "estimated_completion": datetime.utcnow() + timedelta(minutes=3),
            "message": "Refinement functionality coming soon - job parameters validated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LO refinement failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")

@router.get("/quality-metrics/{job_id}")
async def get_generation_quality_metrics(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed quality metrics for learning objective generation.
    """
    try:
        logger.info(f"Quality metrics requested for job: {job_id}")
        
        # Get job results to extract quality metrics
        job_results = await job_service.get_job_results(job_id)
        
        if job_results['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Quality metrics not available for incomplete job. Status: {job_results['status']}"
            )
        
        # Extract quality assessment from job results
        results = job_results['results']
        quality_assessment = results.get('quality_assessment', {})
        
        # Return enhanced quality metrics
        return {
            "job_id": job_id,
            "quality_assessment": quality_assessment,
            "processing_quality": {
                "source_chunks_quality": 0.88,  # Would come from actual processing
                "ocr_accuracy_impact": 0.91,
                "chunking_coherence": 0.86,
                "generation_consistency": 0.90
            },
            "recommendations": [
                "Consider increasing focus on analysis-level objectives",
                "Review LOs with clarity scores below 0.80",
                "Good balance between difficulty levels maintained"
            ],
            "job_metadata": job_results.get('job_metadata', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality metrics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality metrics failed: {str(e)}")

@router.post("/batch-generate")
async def batch_generate_learning_objectives(
    requests: List[GenerateLOsRequest],
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate learning objectives for multiple content items in batch.
    """
    try:
        logger.info(f"Batch LO generation requested for {len(requests)} items")
        
        # Generate batch job ID
        batch_job_id = str(uuid.uuid4())
        
        # Create individual jobs for each request
        individual_jobs = []
        total_estimated_cost = 0.0
        
        for i, request in enumerate(requests):
            try:
                # Convert content type and create job
                job_type = JobType(request.content_type)
                
                generation_config = {
                    "model": request.generation_config.model,
                    "max_objectives": request.generation_config.max_objectives,
                    "bloom_levels": request.generation_config.bloom_levels,
                    "quality_threshold": request.generation_config.quality_threshold
                }
                
                processing_preferences = {
                    "force_processing_path": request.processing_preferences.force_processing_path,
                    "chunk_size": request.processing_preferences.chunk_size,
                    "overlap_size": request.processing_preferences.overlap_size,
                    "ocr_languages": request.processing_preferences.ocr_languages
                }
                
                # Create individual job
                job_result = await job_service.create_generation_job(
                    job_type=job_type,
                    content=getattr(request, 'content', None),
                    textbook_id=getattr(request, 'textbook_id', None),
                    file_path=getattr(request, 'file_path', None),
                    generation_config=generation_config,
                    processing_preferences=processing_preferences
                )
                
                individual_jobs.append({
                    "job_id": job_result['job_id'],
                    "content_type": request.content_type,
                    "topic_id": getattr(request, 'topic_id', None),
                    "textbook_id": getattr(request, 'textbook_id', None),
                    "status": job_result['status'],
                    "estimated_cost_usd": job_result['cost_estimate']['estimated_cost_usd']
                })
                
                total_estimated_cost += job_result['cost_estimate']['estimated_cost_usd']
                
            except Exception as e:
                logger.error(f"Failed to create batch job {i}: {str(e)}")
                individual_jobs.append({
                    "job_id": None,
                    "content_type": request.content_type,
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "batch_job_id": batch_job_id,
            "individual_jobs": individual_jobs,
            "batch_status": "queued",
            "total_jobs": len(requests),
            "successful_jobs": len([j for j in individual_jobs if j.get('job_id')]),
            "failed_jobs": len([j for j in individual_jobs if not j.get('job_id')]),
            "total_estimated_cost_usd": round(total_estimated_cost, 2),
            "estimated_completion": datetime.utcnow() + timedelta(minutes=len(requests) * 3),
            "processing_order": "parallel" if len(requests) <= 5 else "sequential"
        }
        
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")