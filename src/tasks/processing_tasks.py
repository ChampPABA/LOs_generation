"""
Background processing tasks for content pipeline.
Handles document analysis, chunking, and embedding generation.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task
from celery.exceptions import Retry

from .celery_app import celery_app
from ..services.document_analyzer import DocumentAnalyzer, ProcessingPath
from ..services.chunking_service import ChunkingService
from ..services.vector_service import VectorService
from ..services.processing_service import ProcessingService
from ..core.logging import get_logger
from ..database.connection import get_async_session

logger = get_logger(__name__)

@celery_app.task(bind=True, name='src.tasks.processing_tasks.analyze_document')
def analyze_document(self, job_id: str, file_path: str, content_type: str) -> Dict[str, Any]:
    """
    Analyze document to determine optimal processing path.
    """
    try:
        logger.info(f"Starting document analysis for job {job_id}")
        
        # Update job status
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'analyzing_document', 'progress': 10}
        )
        
        # Run analysis
        async def _analyze():
            analyzer = DocumentAnalyzer()
            result = await analyzer.analyze_document(file_path, content_type)
            return result
        
        # Run async analysis in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analysis_result = loop.run_until_complete(_analyze())
        loop.close()
        
        logger.info(f"Document analysis completed for job {job_id}: {analysis_result.processing_path}")
        
        return {
            'job_id': job_id,
            'processing_path': analysis_result.processing_path.value,
            'document_metadata': analysis_result.metadata,
            'quality_score': analysis_result.quality_score,
            'estimated_processing_time': analysis_result.estimated_processing_time,
            'recommendations': analysis_result.recommendations
        }
        
    except Exception as e:
        logger.error(f"Document analysis failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'analyzing_document'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.processing_tasks.process_content_chunks')
def process_content_chunks(self, job_id: str, content: str, processing_path: str, 
                          chunk_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process content into chunks using specified chunking strategy.
    """
    try:
        logger.info(f"Starting content chunking for job {job_id} with path: {processing_path}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'chunking_content', 'progress': 30}
        )
        
        async def _chunk():
            chunking_service = ChunkingService()
            
            if processing_path == 'structural':
                chunks = await chunking_service.structural_chunk(content, chunk_config)
            elif processing_path == 'ocr_agentic':
                chunks = await chunking_service.agentic_chunk(content, chunk_config)
            else:
                # Hybrid approach
                chunks = await chunking_service.hybrid_chunk(content, chunk_config)
            
            return chunks
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        chunks = loop.run_until_complete(_chunk())
        loop.close()
        
        logger.info(f"Content chunking completed for job {job_id}: {len(chunks)} chunks created")
        
        # Store chunks in database
        chunk_ids = []
        for chunk in chunks:
            chunk_ids.append(chunk.chunk_id)
        
        return {
            'job_id': job_id,
            'chunk_ids': chunk_ids,
            'total_chunks': len(chunks),
            'processing_summary': {
                'processing_path': processing_path,
                'average_chunk_size': sum(len(chunk.content) for chunk in chunks) / len(chunks),
                'total_tokens_estimated': sum(chunk.metadata.get('token_count', 0) for chunk in chunks)
            }
        }
        
    except Exception as e:
        logger.error(f"Content chunking failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'chunking_content'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.processing_tasks.generate_embeddings')
def generate_embeddings(self, job_id: str, chunk_ids: List[str]) -> Dict[str, Any]:
    """
    Generate vector embeddings for processed chunks.
    """
    try:
        logger.info(f"Starting embedding generation for job {job_id}: {len(chunk_ids)} chunks")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'generating_embeddings', 'progress': 60}
        )
        
        async def _generate_embeddings():
            vector_service = VectorService()
            
            # Process chunks in batches
            batch_size = 10
            processed_chunks = 0
            
            for i in range(0, len(chunk_ids), batch_size):
                batch_chunk_ids = chunk_ids[i:i + batch_size]
                
                # Generate embeddings for batch
                await vector_service.generate_chunk_embeddings(batch_chunk_ids)
                
                processed_chunks += len(batch_chunk_ids)
                progress = 60 + (processed_chunks / len(chunk_ids)) * 20  # 60-80% progress
                
                current_task.update_state(
                    state='PROGRESS',
                    meta={'stage': 'generating_embeddings', 'progress': progress}
                )
            
            return processed_chunks
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        processed_count = loop.run_until_complete(_generate_embeddings())
        loop.close()
        
        logger.info(f"Embedding generation completed for job {job_id}: {processed_count} embeddings created")
        
        return {
            'job_id': job_id,
            'embeddings_generated': processed_count,
            'vector_store_updated': True,
            'processing_summary': {
                'total_chunks_processed': processed_count,
                'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2',
                'vector_dimension': 384
            }
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'generating_embeddings'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.processing_tasks.complete_processing_pipeline')
def complete_processing_pipeline(self, job_id: str, analysis_result: Dict[str, Any], 
                                chunks_result: Dict[str, Any], embeddings_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete the content processing pipeline and prepare for LO generation.
    """
    try:
        logger.info(f"Completing processing pipeline for job {job_id}")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'finalizing_processing', 'progress': 80}
        )
        
        # Combine results
        processing_complete = {
            'job_id': job_id,
            'processing_path': analysis_result['processing_path'],
            'document_metadata': analysis_result['document_metadata'],
            'chunks_created': chunks_result['total_chunks'],
            'embeddings_generated': embeddings_result['embeddings_generated'],
            'ready_for_generation': True,
            'processing_summary': {
                **chunks_result['processing_summary'],
                **embeddings_result['processing_summary'],
                'quality_score': analysis_result['quality_score'],
                'completion_time': datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"Processing pipeline completed for job {job_id}")
        
        return processing_complete
        
    except Exception as e:
        logger.error(f"Processing pipeline completion failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'finalizing_processing'}
        )
        raise