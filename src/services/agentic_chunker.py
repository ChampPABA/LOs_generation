"""
Agentic Chunker Service for AI-powered semantic chunking of OCR-extracted text.
Uses Gemini Flash with Pydantic AI for intelligent content segmentation.
"""

import logging
from typing import List, Dict, Any, Optional
import time
import asyncio

from pydantic import BaseModel, Field
import google.generativeai as genai
from pydantic_ai import Agent

from src.services.ocr_service import OCRResult
from src.core.config import settings

logger = logging.getLogger(__name__)


class ChildChunk(BaseModel):
    """Individual sentence or thought unit within a parent chunk."""
    content: str = Field(description="Complete sentence or coherent thought")
    sequence_number: int = Field(description="Order within parent chunk")
    semantic_role: str = Field(description="Role in content structure", 
                              examples=["introduction", "main_point", "example", "conclusion", "transition"])


class ParentChunk(BaseModel):
    """Thematic grouping of related content with semantic coherence."""
    content: str = Field(description="Complete thematic content")
    thematic_summary: str = Field(description="Brief summary of the chunk's main theme")
    confidence_score: float = Field(description="Confidence in chunk quality (0.0-1.0)")
    child_chunks: List[ChildChunk] = Field(description="Sentence-level subdivisions")


class ChunkingResult(BaseModel):
    """Complete result of agentic chunking process."""
    parent_chunks: List[ParentChunk] = Field(description="Semantically coherent parent chunks")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)


class AgenticChunker:
    """AI-powered semantic chunking service for OCR-extracted content."""
    
    def __init__(self):
        self.model_name = "gemini-2.5-flash"
        self.max_retries = 3
        self.timeout_seconds = 120
        self.target_parent_chunk_size = 500  # Target words per parent chunk
        self.max_child_chunks_per_parent = 10
        
        # Initialize Gemini
        if hasattr(settings, 'gemini_api_key'):
            genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize Pydantic AI agent
        self.agent = Agent(
            model=self.model_name,
            result_type=ChunkingResult,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for agentic chunking."""
        return """
### ROLE & GOAL ###
You are an expert document analyst specializing in semantic chunking of unstructured text, often from OCR output. Your task is to analyze the provided raw text from a document page and intelligently group it into logical, contextually complete "Parent Chunks". Each Parent Chunk should then be broken down into sentence-level "Child Chunks".

### CONTEXT ###
This text was extracted via OCR and may contain formatting errors, missing punctuation, or lack clear structural separators like headers. Your primary goal is to identify thematic shifts and logical groupings based on the content's semantic meaning rather than formatting cues.

### CHUNKING PRINCIPLES ###
1. **Semantic Coherence**: Group content by meaning and theme, not by formatting
2. **Concept Preservation**: Never split concepts across chunk boundaries
3. **Logical Flow**: Maintain natural reading flow within chunks
4. **Size Balance**: Aim for 200-800 words per parent chunk
5. **Sentence Integrity**: Child chunks should be complete thoughts
6. **OCR Error Tolerance**: Handle OCR mistakes gracefully, don't split on obvious errors

### QUALITY CRITERIA ###
- Parent chunks should represent complete thematic units
- Child chunks should be grammatically complete when possible
- Maintain context and meaning throughout the chunking process
- Provide meaningful thematic summaries
- Assign confidence scores based on content clarity and coherence

### OUTPUT REQUIREMENTS ###
Structure your response according to the ChunkingResult schema with:
- Complete parent chunks with thematic coherence
- Properly sequenced child chunks within each parent
- Accurate semantic role assignments
- Confidence scores reflecting chunk quality
- Processing metadata for quality tracking
"""
    
    async def chunk_ocr_content(
        self, 
        ocr_results: List[OCRResult], 
        page_context: Optional[Dict[str, Any]] = None
    ) -> ChunkingResult:
        """
        Perform semantic chunking on OCR-extracted text.
        
        Args:
            ocr_results: List of OCR results from document pages
            page_context: Optional context information about the document
            
        Returns:
            ChunkingResult with parent and child chunks
        """
        logger.info(f"Starting agentic chunking for {len(ocr_results)} OCR results")
        
        try:
            # Combine OCR results into structured text
            combined_text = self._combine_ocr_results(ocr_results)
            
            if not combined_text.strip():
                logger.warning("No meaningful text found in OCR results")
                return self._create_empty_result("No meaningful text content")
            
            # Prepare context for the AI agent
            context = self._prepare_context(combined_text, ocr_results, page_context)
            
            # Perform chunking with retry logic
            result = await self._chunk_with_retry(combined_text, context)
            
            # Validate and enhance the result
            validated_result = await self._validate_and_enhance_result(result, combined_text)
            
            logger.info(f"Chunking completed: {len(validated_result.parent_chunks)} parent chunks created")
            return validated_result
            
        except Exception as e:
            logger.error(f"Agentic chunking failed: {str(e)}")
            return self._create_fallback_result(ocr_results, str(e))
    
    def _combine_ocr_results(self, ocr_results: List[OCRResult]) -> str:
        """Combine multiple OCR results into coherent text."""
        combined_parts = []
        
        for ocr_result in sorted(ocr_results, key=lambda x: x.page_number):
            if ocr_result.text.strip():
                # Add page separator for multi-page documents
                if len(ocr_results) > 1:
                    combined_parts.append(f"\n--- Page {ocr_result.page_number} ---\n")
                
                combined_parts.append(ocr_result.text)
                combined_parts.append("\n\n")
        
        return ''.join(combined_parts).strip()
    
    def _prepare_context(
        self, 
        text: str, 
        ocr_results: List[OCRResult], 
        page_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context information for the AI agent."""
        # Calculate OCR quality metrics
        avg_confidence = sum(r.confidence for r in ocr_results) / len(ocr_results)
        total_pages = len(ocr_results)
        total_chars = len(text)
        
        # Detect primary language
        language_counts = {}
        for result in ocr_results:
            lang = result.language_detected
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        primary_language = max(language_counts.items(), key=lambda x: x[1])[0] if language_counts else 'unknown'
        
        context = {
            'text_length': total_chars,
            'page_count': total_pages,
            'average_ocr_confidence': avg_confidence,
            'primary_language': primary_language,
            'estimated_chunks_needed': max(1, total_chars // self.target_parent_chunk_size),
            'ocr_quality': 'high' if avg_confidence > 80 else 'medium' if avg_confidence > 60 else 'low'
        }
        
        # Add page context if provided
        if page_context:
            context.update(page_context)
        
        return context
    
    async def _chunk_with_retry(self, text: str, context: Dict[str, Any]) -> ChunkingResult:
        """Perform chunking with retry logic for API failures."""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Chunking attempt {attempt}/{self.max_retries}")
                
                # Prepare the prompt with context
                prompt = self._create_chunking_prompt(text, context)
                
                # Run the AI agent
                start_time = time.time()
                result = await asyncio.wait_for(
                    self.agent.run(prompt),
                    timeout=self.timeout_seconds
                )
                
                processing_time = time.time() - start_time
                
                # Add metadata
                if hasattr(result, 'data') and isinstance(result.data, ChunkingResult):
                    result.data.processing_metadata.update({
                        'processing_time_seconds': processing_time,
                        'attempt_number': attempt,
                        'model_used': self.model_name,
                        'context': context
                    })
                    return result.data
                
                return result
                
            except asyncio.TimeoutError:
                last_error = f"Chunking timeout after {self.timeout_seconds}s"
                logger.warning(f"Attempt {attempt} timed out")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        raise Exception(f"All chunking attempts failed. Last error: {last_error}")
    
    def _create_chunking_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Create the chunking prompt with context."""
        return f"""
### INPUT TEXT ###
Raw OCR text ({context.get('text_length', 0)} characters from {context.get('page_count', 1)} pages):

"{text}"

### PROCESSING CONTEXT ###
- OCR Quality: {context.get('ocr_quality', 'unknown')}
- Average Confidence: {context.get('average_ocr_confidence', 0):.1f}%
- Primary Language: {context.get('primary_language', 'unknown')}
- Estimated Chunks Needed: {context.get('estimated_chunks_needed', 1)}

### TASK ###
1. Read the entire text carefully and identify logical breaks and thematic groupings
2. Create Parent Chunks that represent complete concepts (200-800 words each)
3. Split each Parent Chunk into coherent sentence-level Child Chunks
4. Assign semantic roles to each Child Chunk
5. Provide confidence scores based on content clarity and OCR quality
6. Handle OCR errors gracefully - don't split on obvious mistakes

### QUALITY REQUIREMENTS ###
- Maintain semantic coherence within each parent chunk
- Ensure child chunks are complete thoughts when possible
- Avoid breaking concepts across chunk boundaries
- Provide meaningful thematic summaries
- Consider the OCR quality when assigning confidence scores

Please structure your response according to the ChunkingResult format.
"""
    
    async def _validate_and_enhance_result(self, result: ChunkingResult, original_text: str) -> ChunkingResult:
        """Validate the chunking result and enhance with quality metrics."""
        if not result.parent_chunks:
            logger.warning("No parent chunks generated, creating fallback")
            return self._create_simple_fallback_chunks(original_text)
        
        # Validate coverage
        total_chunk_length = sum(len(chunk.content) for chunk in result.parent_chunks)
        coverage_ratio = total_chunk_length / len(original_text) if original_text else 0
        
        # Enhance processing metadata
        result.processing_metadata.update({
            'total_parent_chunks': len(result.parent_chunks),
            'total_child_chunks': sum(len(chunk.child_chunks) for chunk in result.parent_chunks),
            'coverage_ratio': coverage_ratio,
            'average_parent_chunk_size': sum(len(chunk.content) for chunk in result.parent_chunks) / len(result.parent_chunks),
            'average_confidence': sum(chunk.confidence_score for chunk in result.parent_chunks) / len(result.parent_chunks),
            'quality_assessment': self._assess_chunk_quality(result)
        })
        
        # Fix any quality issues
        if coverage_ratio < 0.8:
            logger.warning(f"Low coverage ratio: {coverage_ratio:.2f}, may need fallback processing")
        
        return result
    
    def _assess_chunk_quality(self, result: ChunkingResult) -> Dict[str, Any]:
        """Assess the quality of the chunking result."""
        if not result.parent_chunks:
            return {'overall_quality': 'poor', 'issues': ['no_chunks_created']}
        
        issues = []
        quality_scores = []
        
        for chunk in result.parent_chunks:
            # Check chunk size
            if len(chunk.content) < 50:
                issues.append('chunk_too_small')
            elif len(chunk.content) > 1500:
                issues.append('chunk_too_large')
            
            # Check child chunks
            if not chunk.child_chunks:
                issues.append('no_child_chunks')
            elif len(chunk.child_chunks) > self.max_child_chunks_per_parent:
                issues.append('too_many_child_chunks')
            
            quality_scores.append(chunk.confidence_score)
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        if avg_quality > 0.8 and not issues:
            overall_quality = 'excellent'
        elif avg_quality > 0.6 and len(issues) <= 2:
            overall_quality = 'good'
        elif avg_quality > 0.4:
            overall_quality = 'acceptable'
        else:
            overall_quality = 'poor'
        
        return {
            'overall_quality': overall_quality,
            'average_confidence': avg_quality,
            'issues': list(set(issues)),
            'requires_fallback': overall_quality in ['poor'] or 'no_chunks_created' in issues
        }
    
    def _create_empty_result(self, reason: str) -> ChunkingResult:
        """Create empty result with reason."""
        return ChunkingResult(
            parent_chunks=[],
            processing_metadata={
                'status': 'empty',
                'reason': reason,
                'timestamp': time.time()
            }
        )
    
    def _create_fallback_result(self, ocr_results: List[OCRResult], error: str) -> ChunkingResult:
        """Create fallback result using simple text splitting."""
        logger.info(f"Creating fallback chunking result due to error: {error}")
        
        # Combine text
        combined_text = self._combine_ocr_results(ocr_results)
        
        if not combined_text:
            return self._create_empty_result(f"Fallback failed: {error}")
        
        return self._create_simple_fallback_chunks(combined_text)
    
    def _create_simple_fallback_chunks(self, text: str) -> ChunkingResult:
        """Create simple chunks using basic text splitting."""
        words = text.split()
        if not words:
            return self._create_empty_result("No words found")
        
        # Create chunks of approximately target size
        chunks = []
        current_chunk_words = []
        
        for word in words:
            current_chunk_words.append(word)
            current_text = ' '.join(current_chunk_words)
            
            # Split when reaching target size or finding natural breaks
            if len(current_text) >= self.target_parent_chunk_size or word.endswith('.'):
                if len(current_text) >= 100:  # Minimum chunk size
                    chunk_text = current_text.strip()
                    
                    # Create simple child chunks (sentences)
                    sentences = [s.strip() for s in chunk_text.split('.') if s.strip()]
                    child_chunks = [
                        ChildChunk(
                            content=f"{sentence}." if not sentence.endswith('.') else sentence,
                            sequence_number=i + 1,
                            semantic_role="main_point"
                        )
                        for i, sentence in enumerate(sentences[:self.max_child_chunks_per_parent])
                    ]
                    
                    parent_chunk = ParentChunk(
                        content=chunk_text,
                        thematic_summary=f"Content section {len(chunks) + 1}",
                        confidence_score=0.6,  # Lower confidence for fallback
                        child_chunks=child_chunks
                    )
                    
                    chunks.append(parent_chunk)
                    current_chunk_words = []
        
        # Handle remaining words
        if current_chunk_words:
            remaining_text = ' '.join(current_chunk_words).strip()
            if len(remaining_text) >= 50:
                child_chunks = [
                    ChildChunk(
                        content=remaining_text,
                        sequence_number=1,
                        semantic_role="conclusion"
                    )
                ]
                
                chunks.append(ParentChunk(
                    content=remaining_text,
                    thematic_summary=f"Final content section",
                    confidence_score=0.5,
                    child_chunks=child_chunks
                ))
        
        return ChunkingResult(
            parent_chunks=chunks,
            processing_metadata={
                'status': 'fallback',
                'method': 'simple_splitting',
                'total_chunks': len(chunks),
                'timestamp': time.time()
            }
        )