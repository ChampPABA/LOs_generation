"""
Hybrid Chunking Service - Coordinates the dual-path processing pipeline.
Routes documents through structural or OCR+agentic processing based on document type.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import time
import asyncio
from pathlib import Path

from pydantic import BaseModel

from src.services.document_analyzer import DocumentAnalyzer, DocumentAnalysisResult, DocumentType, ProcessingPath
from src.services.ocr_service import OCRService, OCRResult
from src.services.agentic_chunker import AgenticChunker, ChunkingResult
from src.services.structural_chunker import StructuralChunker
from src.models.chunks import ParentChunk, ChildChunk

logger = logging.getLogger(__name__)


class HybridChunkingResult(BaseModel):
    """Result of hybrid chunking process with metadata."""
    
    # Processing information
    document_analysis: DocumentAnalysisResult
    processing_path_used: ProcessingPath
    fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    
    # Chunking results
    parent_chunks: List[Dict[str, Any]]  # Will be converted to database models
    child_chunks: List[Dict[str, Any]]   # Will be converted to database models
    
    # Performance metrics
    processing_time_seconds: float
    ocr_metrics: Optional[Dict[str, Any]] = None
    agentic_metrics: Optional[Dict[str, Any]] = None
    
    # Quality assessment
    quality_score: float
    confidence_score: float
    
    # Processing metadata
    metadata: Dict[str, Any] = {}


class ChunkingService:
    """Main service for hybrid document chunking coordination."""
    
    def __init__(self):
        self.document_analyzer = DocumentAnalyzer()
        self.ocr_service = OCRService()
        self.agentic_chunker = AgenticChunker()
        self.structural_chunker = StructuralChunker()
        
        # Configuration
        self.enable_fallback = True
        self.quality_threshold = 0.6
        self.max_processing_time = 3600  # 1 hour max processing time
    
    async def process_document(
        self, 
        pdf_path: str, 
        textbook_id: int,
        force_processing_path: Optional[ProcessingPath] = None
    ) -> HybridChunkingResult:
        """
        Process a document through the hybrid chunking pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            textbook_id: ID of the source textbook
            force_processing_path: Optional override for processing path
            
        Returns:
            HybridChunkingResult with chunks and processing metadata
        """
        start_time = time.time()
        logger.info(f"Starting hybrid chunking for document: {pdf_path}")
        
        try:
            # Step 1: Analyze document type
            document_analysis = await self.document_analyzer.analyze_pdf_type(pdf_path)
            logger.info(f"Document analyzed as {document_analysis.document_type} with {document_analysis.confidence:.2f} confidence")
            
            # Step 2: Determine processing path
            processing_path = force_processing_path or document_analysis.processing_path
            logger.info(f"Using processing path: {processing_path}")
            
            # Step 3: Route to appropriate processing
            result = await self._route_processing(pdf_path, processing_path, document_analysis, textbook_id)
            
            # Step 4: Calculate processing time
            result.processing_time_seconds = time.time() - start_time
            result.document_analysis = document_analysis
            result.processing_path_used = processing_path
            
            logger.info(f"Document processing completed in {result.processing_time_seconds:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Hybrid chunking failed for {pdf_path}: {str(e)}")
            
            # Create fallback result
            return await self._create_fallback_result(
                pdf_path, textbook_id, str(e), time.time() - start_time
            )
    
    async def _route_processing(
        self, 
        pdf_path: str, 
        processing_path: ProcessingPath,
        document_analysis: DocumentAnalysisResult,
        textbook_id: int
    ) -> HybridChunkingResult:
        """Route document to appropriate processing path."""
        
        if processing_path == ProcessingPath.STRUCTURAL:
            return await self._process_structural_path(pdf_path, document_analysis, textbook_id)
        else:
            return await self._process_ocr_agentic_path(pdf_path, document_analysis, textbook_id)
    
    async def _process_structural_path(
        self, 
        pdf_path: str, 
        document_analysis: DocumentAnalysisResult,
        textbook_id: int
    ) -> HybridChunkingResult:
        """Process document through structural chunking path."""
        logger.info("Processing through structural chunking path")
        
        try:
            # Use structural chunker
            structural_result = await self.structural_chunker.process_document(pdf_path, textbook_id)
            
            # Convert to hybrid result format
            parent_chunks_data = []
            child_chunks_data = []
            
            for i, parent_chunk in enumerate(structural_result['parent_chunks']):
                parent_data = {
                    'content': parent_chunk.content,
                    'document_type': 'native',
                    'processing_path': 'structural',
                    'textbook_id': textbook_id,
                    'page_number': parent_chunk.page_number,
                    'chapter_title': parent_chunk.chapter_title,
                    'chunk_size': len(parent_chunk.content),
                    'processing_metadata': {
                        'chunking_method': 'MarkdownHeaderTextSplitter',
                        'confidence': 0.9
                    }
                }
                parent_chunks_data.append(parent_data)
                
                # Process child chunks
                for j, child_chunk in enumerate(structural_result['child_chunks'][i]):
                    child_data = {
                        'content': child_chunk.content,
                        'sequence_number': j + 1,
                        'embedding_model': 'bge-m3',
                        'embedding_dimension': 1024,
                        'language_code': 'en',
                        'chunk_size': len(child_chunk.content),
                        'processing_metadata': {
                            'chunking_method': 'RecursiveCharacterTextSplitter',
                            'overlap_size': child_chunk.overlap_size
                        }
                    }
                    child_chunks_data.append(child_data)
            
            return HybridChunkingResult(
                parent_chunks=parent_chunks_data,
                child_chunks=child_chunks_data,
                processing_path_used=ProcessingPath.STRUCTURAL,
                quality_score=0.85,
                confidence_score=document_analysis.confidence,
                metadata={
                    'method': 'structural',
                    'total_parent_chunks': len(parent_chunks_data),
                    'total_child_chunks': len(child_chunks_data)
                }
            )
            
        except Exception as e:
            logger.warning(f"Structural processing failed: {str(e)}")
            
            if self.enable_fallback:
                logger.info("Falling back to OCR+agentic processing")
                result = await self._process_ocr_agentic_path(pdf_path, document_analysis, textbook_id)
                result.fallback_occurred = True
                result.fallback_reason = f"Structural processing failed: {str(e)}"
                return result
            else:
                raise
    
    async def _process_ocr_agentic_path(
        self, 
        pdf_path: str, 
        document_analysis: DocumentAnalysisResult,
        textbook_id: int
    ) -> HybridChunkingResult:
        """Process document through OCR + agentic chunking path."""
        logger.info("Processing through OCR + agentic chunking path")
        
        ocr_start_time = time.time()
        
        try:
            # Step 1: OCR Processing
            ocr_results = await self.ocr_service.extract_text_from_pdf(pdf_path)
            ocr_processing_time = time.time() - ocr_start_time
            
            if not ocr_results:
                raise Exception("OCR processing produced no results")
            
            logger.info(f"OCR completed in {ocr_processing_time:.1f}s, {len(ocr_results)} pages processed")
            
            # Step 2: Agentic Chunking
            agentic_start_time = time.time()
            page_context = {
                'document_type': document_analysis.document_type,
                'total_pages': document_analysis.total_pages,
                'textbook_id': textbook_id
            }
            
            chunking_result = await self.agentic_chunker.chunk_ocr_content(ocr_results, page_context)
            agentic_processing_time = time.time() - agentic_start_time
            
            logger.info(f"Agentic chunking completed in {agentic_processing_time:.1f}s")
            
            # Step 3: Convert to database format
            parent_chunks_data, child_chunks_data = await self._convert_agentic_result_to_db_format(
                chunking_result, ocr_results, textbook_id
            )
            
            # Step 4: Calculate metrics
            ocr_metrics = self._calculate_ocr_metrics(ocr_results, ocr_processing_time)
            agentic_metrics = self._calculate_agentic_metrics(chunking_result, agentic_processing_time)
            
            # Step 5: Assess quality
            quality_score = self._calculate_quality_score(ocr_results, chunking_result)
            
            return HybridChunkingResult(
                parent_chunks=parent_chunks_data,
                child_chunks=child_chunks_data,
                processing_path_used=ProcessingPath.OCR_AGENTIC,
                ocr_metrics=ocr_metrics,
                agentic_metrics=agentic_metrics,
                quality_score=quality_score,
                confidence_score=min(document_analysis.confidence, quality_score),
                metadata={
                    'method': 'ocr_agentic',
                    'ocr_processing_time': ocr_processing_time,
                    'agentic_processing_time': agentic_processing_time,
                    'total_parent_chunks': len(parent_chunks_data),
                    'total_child_chunks': len(child_chunks_data)
                }
            )
            
        except Exception as e:
            logger.error(f"OCR+Agentic processing failed: {str(e)}")
            
            if self.enable_fallback:
                logger.info("Attempting fallback to structural processing")
                result = await self._process_structural_path(pdf_path, document_analysis, textbook_id)
                result.fallback_occurred = True
                result.fallback_reason = f"OCR+Agentic processing failed: {str(e)}"
                return result
            else:
                raise
    
    async def _convert_agentic_result_to_db_format(
        self, 
        chunking_result: ChunkingResult, 
        ocr_results: List[OCRResult], 
        textbook_id: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Convert agentic chunking result to database format."""
        parent_chunks_data = []
        child_chunks_data = []
        
        # Calculate average OCR confidence
        avg_ocr_confidence = sum(r.confidence for r in ocr_results) / len(ocr_results) if ocr_results else 0
        primary_language = self._detect_primary_language(ocr_results)
        
        for parent_chunk in chunking_result.parent_chunks:
            # Create parent chunk data
            parent_data = {
                'content': parent_chunk.content,
                'document_type': 'scanned',
                'processing_path': 'agentic',
                'ocr_confidence': int(avg_ocr_confidence),
                'ocr_language_detected': primary_language,
                'textbook_id': textbook_id,
                'chunk_size': len(parent_chunk.content),
                'processing_metadata': {
                    'chunking_method': 'agentic',
                    'thematic_summary': parent_chunk.thematic_summary,
                    'confidence': parent_chunk.confidence_score,
                    'ocr_pages': len(ocr_results)
                }
            }
            parent_chunks_data.append(parent_data)
            
            # Create child chunks data
            for child_chunk in parent_chunk.child_chunks:
                child_data = {
                    'content': child_chunk.content,
                    'sequence_number': child_chunk.sequence_number,
                    'embedding_model': 'bge-m3',
                    'embedding_dimension': 1024,
                    'language_code': primary_language,
                    'chunk_size': len(child_chunk.content),
                    'processing_metadata': {
                        'chunking_method': 'agentic',
                        'semantic_role': child_chunk.semantic_role,
                        'ocr_confidence': avg_ocr_confidence
                    }
                }
                child_chunks_data.append(child_data)
        
        return parent_chunks_data, child_chunks_data
    
    def _detect_primary_language(self, ocr_results: List[OCRResult]) -> str:
        """Detect the primary language from OCR results."""
        language_counts = {}
        for result in ocr_results:
            lang = result.language_detected
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        if not language_counts:
            return 'en'
        
        return max(language_counts.items(), key=lambda x: x[1])[0]
    
    def _calculate_ocr_metrics(self, ocr_results: List[OCRResult], processing_time: float) -> Dict[str, Any]:
        """Calculate OCR processing metrics."""
        if not ocr_results:
            return {}
        
        confidences = [r.confidence for r in ocr_results]
        processing_times = [r.processing_time_ms for r in ocr_results]
        
        return {
            'pages_processed': len(ocr_results),
            'average_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'low_confidence_pages': len([c for c in confidences if c < 70]),
            'total_processing_time_ms': sum(processing_times),
            'average_processing_time_ms': sum(processing_times) / len(processing_times),
            'total_processing_time_seconds': processing_time,
            'preprocessing_applied': any(
                r.preprocessing_applied.get('noise_reduction', False) 
                for r in ocr_results
            )
        }
    
    def _calculate_agentic_metrics(self, chunking_result: ChunkingResult, processing_time: float) -> Dict[str, Any]:
        """Calculate agentic chunking metrics."""
        metadata = chunking_result.processing_metadata
        
        return {
            'total_parent_chunks': len(chunking_result.parent_chunks),
            'total_child_chunks': sum(len(chunk.child_chunks) for chunk in chunking_result.parent_chunks),
            'average_chunk_confidence': sum(chunk.confidence_score for chunk in chunking_result.parent_chunks) / len(chunking_result.parent_chunks) if chunking_result.parent_chunks else 0,
            'processing_time_seconds': processing_time,
            'tokens_used': metadata.get('tokens_used', 0),
            'api_calls_made': metadata.get('api_calls_made', 0),
            'quality_assessment': metadata.get('quality_assessment', {}),
            'fallback_used': metadata.get('status') == 'fallback'
        }
    
    def _calculate_quality_score(self, ocr_results: List[OCRResult], chunking_result: ChunkingResult) -> float:
        """Calculate overall quality score for the processing result."""
        scores = []
        
        # OCR quality component (0-1)
        if ocr_results:
            avg_ocr_confidence = sum(r.confidence for r in ocr_results) / len(ocr_results)
            ocr_quality = min(1.0, avg_ocr_confidence / 100.0)
            scores.append(ocr_quality * 0.4)  # 40% weight
        
        # Chunking quality component (0-1)
        if chunking_result.parent_chunks:
            avg_chunk_confidence = sum(chunk.confidence_score for chunk in chunking_result.parent_chunks) / len(chunking_result.parent_chunks)
            scores.append(avg_chunk_confidence * 0.4)  # 40% weight
            
            # Coverage quality - ensure we have reasonable chunk distribution
            total_content_length = sum(len(chunk.content) for chunk in chunking_result.parent_chunks)
            if total_content_length > 100:  # Minimum meaningful content
                scores.append(0.2)  # 20% weight for having content
        
        return sum(scores) if scores else 0.3  # Fallback low score
    
    async def _create_fallback_result(
        self, 
        pdf_path: str, 
        textbook_id: int, 
        error: str, 
        processing_time: float
    ) -> HybridChunkingResult:
        """Create a fallback result when all processing fails."""
        logger.error(f"Creating fallback result due to error: {error}")
        
        # Try to create minimal document analysis
        try:
            document_analysis = await self.document_analyzer.analyze_pdf_type(pdf_path)
        except:
            from src.services.document_analyzer import DocumentType, ProcessingPath
            document_analysis = DocumentAnalysisResult(
                document_type=DocumentType.SCANNED,
                processing_path=ProcessingPath.OCR_AGENTIC,
                confidence=0.1,
                total_pages=1,
                pages_with_text=0,
                pages_requiring_ocr=1,
                page_analyses=[],
                analysis_method="fallback",
                decision_factors=[f"Analysis failed: {error}"]
            )
        
        # Create minimal empty chunks
        return HybridChunkingResult(
            document_analysis=document_analysis,
            processing_path_used=ProcessingPath.OCR_AGENTIC,
            fallback_occurred=True,
            fallback_reason=error,
            parent_chunks=[],
            child_chunks=[],
            processing_time_seconds=processing_time,
            quality_score=0.1,
            confidence_score=0.1,
            metadata={
                'method': 'fallback',
                'error': error,
                'status': 'failed'
            }
        )