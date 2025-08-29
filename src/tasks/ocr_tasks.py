"""
OCR processing tasks for PDF documents.
Handles PDF upload, OCR processing, and text extraction.
"""

import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from celery import current_task
from pathlib import Path

from .celery_app import celery_app
from ..services.ocr_service import OCRService
from ..core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, name='src.tasks.ocr_tasks.process_pdf_ocr')
def process_pdf_ocr(self, job_id: str, pdf_path: str, ocr_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process PDF document through OCR pipeline.
    """
    try:
        logger.info(f"Starting OCR processing for job {job_id}: {pdf_path}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'initializing_ocr', 'progress': 5}
        )
        
        # Validate PDF file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        async def _process_ocr():
            ocr_service = OCRService()
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'stage': 'extracting_pages', 'progress': 10}
            )
            
            # Extract pages and process OCR
            result = await ocr_service.process_pdf_document(
                pdf_path=pdf_path,
                job_id=job_id,
                languages=ocr_config.get('languages', ['eng', 'tha']),
                max_concurrent_pages=ocr_config.get('max_concurrent_pages', 3),
                progress_callback=lambda progress: current_task.update_state(
                    state='PROGRESS',
                    meta={'stage': 'processing_ocr', 'progress': 10 + (progress * 0.7)}
                )
            )
            
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ocr_result = loop.run_until_complete(_process_ocr())
        loop.close()
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'finalizing_ocr', 'progress': 90}
        )
        
        logger.info(f"OCR processing completed for job {job_id}: {ocr_result.total_pages} pages processed")
        
        return {
            'job_id': job_id,
            'pdf_path': pdf_path,
            'extracted_text': ocr_result.extracted_text,
            'processing_summary': {
                'total_pages': ocr_result.total_pages,
                'pages_processed': ocr_result.pages_processed,
                'average_confidence': ocr_result.average_confidence,
                'total_text_length': len(ocr_result.extracted_text),
                'processing_time_seconds': ocr_result.processing_time,
                'languages_detected': ocr_result.languages_detected,
                'ocr_quality': ocr_result.quality_assessment
            },
            'page_results': [
                {
                    'page_number': page.page_number,
                    'confidence': page.confidence,
                    'text_length': len(page.text),
                    'processing_time': page.processing_time
                }
                for page in ocr_result.page_results
            ]
        }
        
    except Exception as e:
        logger.error(f"OCR processing failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'ocr_processing'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.ocr_tasks.validate_uploaded_pdf')
def validate_uploaded_pdf(self, file_path: str, max_size_mb: int = 50, 
                         max_pages: int = 100) -> Dict[str, Any]:
    """
    Validate uploaded PDF file for processing.
    """
    try:
        logger.info(f"Validating PDF file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            raise ValueError(f"File too large: {file_size_mb:.2f}MB (max {max_size_mb}MB)")
        
        # Quick PDF validation using OCR service
        async def _validate():
            ocr_service = OCRService()
            page_count = await ocr_service.get_pdf_page_count(file_path)
            
            if page_count > max_pages:
                raise ValueError(f"Too many pages: {page_count} (max {max_pages})")
                
            return page_count
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        page_count = loop.run_until_complete(_validate())
        loop.close()
        
        validation_result = {
            'file_path': file_path,
            'file_size_mb': file_size_mb,
            'page_count': page_count,
            'valid': True,
            'estimated_processing_time_minutes': page_count * 0.5,  # 30 seconds per page
            'estimated_cost_usd': page_count * 0.02  # 2 cents per page
        }
        
        logger.info(f"PDF validation completed: {validation_result}")
        return validation_result
        
    except Exception as e:
        logger.error(f"PDF validation failed: {str(e)}")
        return {
            'file_path': file_path,
            'valid': False,
            'error': str(e)
        }

@celery_app.task(bind=True, name='src.tasks.ocr_tasks.cleanup_processed_files')
def cleanup_processed_files(self, job_id: str, file_paths: List[str], 
                           keep_original: bool = True) -> Dict[str, Any]:
    """
    Clean up temporary files created during OCR processing.
    """
    try:
        logger.info(f"Cleaning up processed files for job {job_id}")
        
        cleaned_files = []
        errors = []
        
        for file_path in file_paths:
            try:
                # Skip original PDF if keep_original is True
                if keep_original and file_path.endswith('.pdf'):
                    continue
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_files.append(file_path)
                    logger.debug(f"Removed file: {file_path}")
            
            except Exception as e:
                errors.append(f"Failed to remove {file_path}: {str(e)}")
                logger.error(f"File cleanup error: {str(e)}")
        
        return {
            'job_id': job_id,
            'cleaned_files': cleaned_files,
            'errors': errors,
            'cleanup_completed': len(errors) == 0
        }
        
    except Exception as e:
        logger.error(f"File cleanup failed for job {job_id}: {str(e)}")
        return {
            'job_id': job_id,
            'cleanup_completed': False,
            'error': str(e)
        }