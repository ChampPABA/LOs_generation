"""
Content processing API endpoints with hybrid chunking support.
Handles document analysis, OCR processing, and chunking operations.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from src.services.processing_service import ProcessingService
from src.services.job_service import JobService, JobType
from src.services.document_analyzer import ProcessingPath, DocumentType
from src.core.dependencies import get_processing_service, get_job_service, get_current_user
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Request/Response Models
class ProcessingPreferences(BaseModel):
    """Processing preferences for hybrid chunking."""
    force_processing_path: Optional[str] = Field("auto", regex="^(auto|structural|ocr_agentic)$")
    ocr_languages: List[str] = Field(default=["eng", "tha"])
    ocr_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    image_preprocessing: bool = Field(default=True)
    
    @validator('force_processing_path')
    def validate_processing_path(cls, v):
        valid_paths = ["auto", "structural", "ocr_agentic"]
        if v not in valid_paths:
            raise ValueError(f"Invalid processing path. Must be one of: {valid_paths}")
        return v


class GenerationConfig(BaseModel):
    """Generation configuration for learning objectives."""
    model: str = Field(default="gpt-4")
    max_objectives: int = Field(default=15, ge=1, le=50)
    bloom_levels: List[int] = Field(default=[1, 2, 3, 4, 5, 6])
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    @validator('bloom_levels')
    def validate_bloom_levels(cls, v):
        for level in v:
            if level < 1 or level > 6:
                raise ValueError("Bloom levels must be between 1 and 6")
        return v

class ProcessingPreferences(BaseModel):
    """Processing preferences for hybrid chunking."""
    force_processing_path: Optional[str] = Field("auto", regex="^(auto|structural|ocr_agentic)$")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    overlap_size: int = Field(default=50, ge=0, le=500)
    ocr_languages: List[str] = Field(default=["eng", "tha"])
    ocr_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    image_preprocessing: bool = Field(default=True)
    
    @validator('force_processing_path')
    def validate_processing_path(cls, v):
        valid_paths = ["auto", "structural", "ocr_agentic"]
        if v not in valid_paths:
            raise ValueError(f"Invalid processing path. Must be one of: {valid_paths}")
        return v

class GenerateLOsRequest(BaseModel):
    """Request model for learning objectives generation."""
    content_type: str = Field(regex="^(direct_text|pdf_upload|textbook_id)$")
    content: Optional[str] = Field(None)
    textbook_id: Optional[int] = Field(None)
    file_path: Optional[str] = Field(None)  # For PDF upload processing
    topic_id: int
    processing_preferences: Optional[ProcessingPreferences] = Field(default_factory=ProcessingPreferences)
    generation_config: Optional[GenerationConfig] = Field(default_factory=GenerationConfig)
    
    @validator('content')
    def validate_content(cls, v, values):
        content_type = values.get('content_type')
        if content_type == 'direct_text' and not v:
            raise ValueError("Content is required when content_type is 'direct_text'")
        return v
    
    @validator('textbook_id')
    def validate_textbook_id(cls, v, values):
        content_type = values.get('content_type')
        if content_type == 'textbook_id' and not v:
            raise ValueError("Textbook ID is required when content_type is 'textbook_id'")
        return v
    
    @validator('file_path')
    def validate_file_path(cls, v, values):
        content_type = values.get('content_type')
        if content_type == 'pdf_upload' and not v:
            raise ValueError("File path is required when content_type is 'pdf_upload'")
        return v

class DocumentAnalysisRequest(BaseModel):
    """Request model for document analysis."""
    textbook_id: Optional[int] = None

class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis."""
    document_type: str
    processing_path: str
    confidence: float
    total_pages: int
    pages_with_text: int
    pages_requiring_ocr: int
    analysis_method: str
    decision_factors: List[str]

class OCRPreprocessRequest(BaseModel):
    """Request model for OCR preprocessing."""
    textbook_id: int
    languages: List[str] = Field(default=["eng", "tha"])
    enable_preprocessing: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

class JobStatusResponse(BaseModel):
    """Enhanced job status response with hybrid processing details."""
    job_id: str
    status: str
    processing_path: Optional[str] = None
    document_analysis: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    cost_tracking: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    fallback_info: Optional[Dict[str, Any]] = None

# Endpoint implementations
@router.post("/analyze-document")
async def analyze_document(
    request: DocumentAnalysisRequest,
    processing_service: ProcessingService = Depends(get_processing_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze document type and determine optimal processing path.
    """
    try:
        logger.info(f"Document analysis requested for textbook_id: {request.textbook_id}")
        
        # For now, simulate document analysis since we need textbook path resolution
        # In real implementation, this would resolve textbook_id to PDF path
        if not request.textbook_id:
            raise HTTPException(
                status_code=400,
                detail="Textbook ID is required for document analysis"
            )
        
        # Mock analysis result for demonstration
        # In production, this would call the actual document analyzer
        mock_analysis = DocumentAnalysisResponse(
            document_type="scanned",
            processing_path="ocr_agentic", 
            confidence=0.85,
            total_pages=25,
            pages_with_text=3,
            pages_requiring_ocr=22,
            analysis_method="content_density_analysis",
            decision_factors=[
                "Low text density per page",
                "High image-to-text ratio",
                "OCR-extractable content detected"
            ]
        )
        
        return mock_analysis
        
    except Exception as e:
        logger.error(f"Document analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")

@router.post("/preprocess-ocr")
async def preprocess_ocr(
    request: OCRPreprocessRequest,
    background_tasks: BackgroundTasks,
    processing_service: ProcessingService = Depends(get_processing_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Preprocess document for OCR with image enhancement.
    """
    try:
        logger.info(f"OCR preprocessing requested for textbook_id: {request.textbook_id}")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # For now, return immediate response
        # In real implementation, this would start background OCR preprocessing
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "OCR preprocessing job queued successfully",
            "preprocessing_config": {
                "languages": request.languages,
                "enable_preprocessing": request.enable_preprocessing,
                "confidence_threshold": request.confidence_threshold
            },
            "estimated_completion": datetime.utcnow() + timedelta(minutes=5)
        }
        
    except Exception as e:
        logger.error(f"OCR preprocessing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR preprocessing failed: {str(e)}")

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload PDF file and create processing job.
    """
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Check file size (50MB limit)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("/app/uploads")
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # Save uploaded file
        with open(file_path, "wb") as temp_file:
            temp_file.write(content)
        
        logger.info(f"PDF uploaded successfully: {file.filename} -> {file_path}")
        
        return {
            "message": "PDF uploaded successfully",
            "file_path": str(file_path),
            "original_filename": file.filename,
            "file_size_bytes": len(content),
            "upload_timestamp": datetime.utcnow().isoformat(),
            "next_step": "Use file_path in generation request to process this PDF"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {str(e)}")

@router.post("/process-pdf")
async def process_pdf(
    file: UploadFile = File(...),
    processing_preferences: Optional[str] = None,
    generation_config: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    job_service: JobService = Depends(get_job_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload PDF and immediately start processing pipeline.
    """
    try:
        # First upload the PDF
        upload_result = await upload_pdf(file, background_tasks, job_service, current_user)
        file_path = upload_result["file_path"]
        
        # Parse configurations
        processing_prefs = {}
        if processing_preferences:
            import json
            processing_prefs = json.loads(processing_preferences)
        
        generation_cfg = {
            "model": "gpt-4",
            "max_objectives": 15,
            "bloom_levels": [1, 2, 3, 4, 5, 6],
            "quality_threshold": 0.7
        }
        if generation_config:
            import json
            generation_cfg.update(json.loads(generation_config))
        
        # Create processing job
        job_result = await job_service.create_generation_job(
            job_type=JobType.PDF_UPLOAD,
            file_path=file_path,
            generation_config=generation_cfg,
            processing_preferences=processing_prefs
        )
        
        logger.info(f"PDF processing job created: {job_result['job_id']}")
        
        return {
            "job_id": job_result["job_id"],
            "status": job_result["status"],
            "processing_pipeline": job_result["processing_pipeline"],
            "estimated_completion": job_result["estimated_completion"],
            "cost_estimate": job_result["cost_estimate"],
            "file_info": {
                "filename": file.filename,
                "file_path": file_path,
                "size_bytes": upload_result["file_size_bytes"]
            }
        }
        
    except Exception as e:
        logger.error(f"PDF processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@router.get("/chunks/{textbook_id}")
async def get_chunks(
    textbook_id: int,
    processing_path: Optional[str] = None,
    page_number: Optional[int] = None,
    chunk_type: Optional[str] = "parent",
    processing_service: ProcessingService = Depends(get_processing_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve chunks for a processed textbook with filtering options.
    """
    try:
        logger.info(f"Retrieving chunks for textbook_id: {textbook_id}")
        
        # Mock chunk data for demonstration
        # In real implementation, this would query the database
        mock_chunks = [
            {
                "chunk_id": f"chunk_{i}",
                "content": f"Sample content for chunk {i}",
                "chunk_type": chunk_type,
                "processing_path": processing_path or "ocr_agentic",
                "quality_score": 0.85,
                "page_number": page_number or (i % 10) + 1,
                "metadata": {
                    "ocr_confidence": 0.92,
                    "language": "en",
                    "semantic_role": "main_point"
                }
            }
            for i in range(1, 11)
        ]
        
        return {
            "textbook_id": textbook_id,
            "chunks": mock_chunks,
            "total_count": len(mock_chunks),
            "filters_applied": {
                "processing_path": processing_path,
                "page_number": page_number,
                "chunk_type": chunk_type
            }
        }
        
    except Exception as e:
        logger.error(f"Chunk retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chunk retrieval failed: {str(e)}")

@router.get("/processing-quality/{textbook_id}")
async def get_processing_quality(
    textbook_id: int,
    processing_service: ProcessingService = Depends(get_processing_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get processing quality metrics for a textbook.
    """
    try:
        logger.info(f"Quality metrics requested for textbook_id: {textbook_id}")
        
        # Mock quality metrics
        # In real implementation, this would query processing results
        mock_metrics = {
            "textbook_id": textbook_id,
            "overall_quality_score": 0.87,
            "processing_path_used": "ocr_agentic",
            "ocr_metrics": {
                "pages_processed": 25,
                "average_confidence": 0.89,
                "low_confidence_pages": 2,
                "preprocessing_applied": True,
                "language_distribution": {
                    "en": 0.70,
                    "th": 0.30
                }
            },
            "chunking_metrics": {
                "total_parent_chunks": 45,
                "total_child_chunks": 180,
                "average_parent_chunk_size": 520,
                "average_quality_score": 0.85,
                "coverage_ratio": 0.94
            },
            "processing_time_seconds": 127.5,
            "cost_breakdown": {
                "ocr_processing": 0.05,
                "agentic_chunking": 0.08,
                "total_usd": 0.13
            }
        }
        
        return mock_metrics
        
    except Exception as e:
        logger.error(f"Quality metrics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality metrics retrieval failed: {str(e)}")

@router.post("/validate-chunks")
async def validate_chunks(
    textbook_id: int,
    chunk_ids: Optional[List[str]] = None,
    processing_service: ProcessingService = Depends(get_processing_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Validate chunk quality and coherence for a textbook.
    """
    try:
        logger.info(f"Chunk validation requested for textbook_id: {textbook_id}")
        
        # Mock validation results
        validation_results = {
            "textbook_id": textbook_id,
            "validation_status": "completed",
            "overall_quality": "good",
            "chunk_validations": [
                {
                    "chunk_id": chunk_id or f"chunk_{i}",
                    "quality_score": 0.85 + (i * 0.02),
                    "issues": [] if i % 3 != 0 else ["minor_ocr_errors"],
                    "coherence_score": 0.90,
                    "completeness_score": 0.88
                }
                for i, chunk_id in enumerate(chunk_ids or [f"chunk_{j}" for j in range(5)])
            ],
            "recommendations": [
                "Consider re-processing pages with OCR confidence < 0.70",
                "Review chunks with quality scores < 0.75"
            ]
        }
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Chunk validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chunk validation failed: {str(e)}")