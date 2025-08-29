"""
Learning objectives generation tasks.
Handles LO generation, refinement, and quality assessment.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import current_task

from .celery_app import celery_app
from ..services.generation_service import GenerationService
from ..services.llm_service import LLMService
from ..services.vector_service import VectorService
from ..core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, name='src.tasks.generation_tasks.generate_learning_objectives')
def generate_learning_objectives(self, job_id: str, chunk_ids: List[str], 
                                generation_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate learning objectives from processed chunks.
    """
    try:
        logger.info(f"Starting LO generation for job {job_id}: {len(chunk_ids)} chunks")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'initializing_generation', 'progress': 85}
        )
        
        async def _generate():
            generation_service = GenerationService()
            
            # Generate learning objectives
            los = await generation_service.generate_learning_objectives(
                chunk_ids=chunk_ids,
                config=generation_config,
                progress_callback=lambda progress: current_task.update_state(
                    state='PROGRESS',
                    meta={'stage': 'generating_objectives', 'progress': 85 + (progress * 0.1)}
                )
            )
            
            current_task.update_state(
                state='PROGRESS',
                meta={'stage': 'assessing_quality', 'progress': 95}
            )
            
            # Quality assessment
            quality_assessment = await generation_service.assess_generation_quality(los)
            
            return los, quality_assessment
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        learning_objectives, quality_assessment = loop.run_until_complete(_generate())
        loop.close()
        
        logger.info(f"LO generation completed for job {job_id}: {len(learning_objectives)} objectives generated")
        
        # Prepare response data
        lo_data = []
        for lo in learning_objectives:
            lo_data.append({
                'lo_id': lo.lo_id,
                'content': lo.content,
                'bloom_level': lo.bloom_level,
                'quality_score': lo.quality_score,
                'confidence': lo.confidence,
                'source_chunk_id': lo.source_chunk_id,
                'metadata': lo.metadata
            })
        
        return {
            'job_id': job_id,
            'learning_objectives': lo_data,
            'generation_metadata': {
                'total_chunks_processed': len(chunk_ids),
                'los_generated': len(learning_objectives),
                'generation_model': generation_config.get('model', 'gpt-4'),
                'generation_time': datetime.utcnow().isoformat(),
                'generation_config': generation_config
            },
            'quality_assessment': quality_assessment
        }
        
    except Exception as e:
        logger.error(f"LO generation failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'generation'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.generation_tasks.refine_learning_objectives')
def refine_learning_objectives(self, job_id: str, original_los: List[Dict[str, Any]], 
                              refinement_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refine learning objectives based on user feedback and criteria.
    """
    try:
        logger.info(f"Starting LO refinement for job {job_id}: {len(original_los)} objectives")
        
        current_task.update_state(
            state='PROGRESS',
            meta={'stage': 'analyzing_objectives', 'progress': 10}
        )
        
        async def _refine():
            generation_service = GenerationService()
            
            # Convert dict data back to LO objects
            from ..models.learning_objectives import LearningObjective
            
            lo_objects = []
            for lo_data in original_los:
                lo = LearningObjective(
                    lo_id=lo_data['lo_id'],
                    content=lo_data['content'],
                    bloom_level=lo_data['bloom_level'],
                    quality_score=lo_data['quality_score'],
                    confidence=lo_data['confidence'],
                    source_chunk_id=lo_data['source_chunk_id'],
                    metadata=lo_data['metadata']
                )
                lo_objects.append(lo)
            
            current_task.update_state(
                state='PROGRESS',
                meta={'stage': 'applying_refinements', 'progress': 30}
            )
            
            # Apply refinements
            refined_los = await generation_service.refine_learning_objectives(
                original_los=lo_objects,
                refinement_criteria=refinement_config,
                progress_callback=lambda progress: current_task.update_state(
                    state='PROGRESS',
                    meta={'stage': 'refining_objectives', 'progress': 30 + (progress * 0.6)}
                )
            )
            
            current_task.update_state(
                state='PROGRESS',
                meta={'stage': 'quality_assessment', 'progress': 90}
            )
            
            # Re-assess quality
            quality_assessment = await generation_service.assess_generation_quality(refined_los)
            
            return refined_los, quality_assessment
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        refined_objectives, quality_assessment = loop.run_until_complete(_refine())
        loop.close()
        
        logger.info(f"LO refinement completed for job {job_id}: {len(refined_objectives)} refined objectives")
        
        # Prepare response data
        refined_data = []
        for lo in refined_objectives:
            refined_data.append({
                'lo_id': lo.lo_id,
                'content': lo.content,
                'bloom_level': lo.bloom_level,
                'quality_score': lo.quality_score,
                'confidence': lo.confidence,
                'source_chunk_id': lo.source_chunk_id,
                'metadata': lo.metadata
            })
        
        return {
            'job_id': job_id,
            'refined_objectives': refined_data,
            'refinement_summary': {
                'original_count': len(original_los),
                'refined_count': len(refined_objectives),
                'refinement_criteria': refinement_config,
                'improvements_made': quality_assessment.get('improvements', []),
                'refinement_time': datetime.utcnow().isoformat()
            },
            'quality_assessment': quality_assessment
        }
        
    except Exception as e:
        logger.error(f"LO refinement failed for job {job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'refinement'}
        )
        raise

@celery_app.task(bind=True, name='src.tasks.generation_tasks.batch_generate_objectives')
def batch_generate_objectives(self, batch_job_id: str, job_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate learning objectives for multiple jobs in batch.
    """
    try:
        logger.info(f"Starting batch generation {batch_job_id}: {len(job_configs)} jobs")
        
        completed_jobs = []
        failed_jobs = []
        total_jobs = len(job_configs)
        
        for i, job_config in enumerate(job_configs):
            try:
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': f'processing_job_{i+1}',
                        'progress': (i / total_jobs) * 100,
                        'current_job': job_config['job_id']
                    }
                )
                
                # Generate objectives for this job
                result = generate_learning_objectives(
                    job_id=job_config['job_id'],
                    chunk_ids=job_config['chunk_ids'],
                    generation_config=job_config['generation_config']
                )
                
                completed_jobs.append({
                    'job_id': job_config['job_id'],
                    'status': 'completed',
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Batch job {job_config['job_id']} failed: {str(e)}")
                failed_jobs.append({
                    'job_id': job_config['job_id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Batch generation completed {batch_job_id}: {len(completed_jobs)} succeeded, {len(failed_jobs)} failed")
        
        return {
            'batch_job_id': batch_job_id,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'batch_summary': {
                'total_jobs': total_jobs,
                'successful': len(completed_jobs),
                'failed': len(failed_jobs),
                'completion_time': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Batch generation failed for {batch_job_id}: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(e), 'stage': 'batch_generation'}
        )
        raise